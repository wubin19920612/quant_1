from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
import yaml
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Label, TabbedContent, TabPane
from src.analytics.alerts import AlertEngine
from src.analytics.rv_calculator import compute_rv_multi_window
from src.analytics.scorer import score_deviation
from src.exchanges.base import Exchange
from src.exchanges.deribit import DeribitExchange
from src.exchanges.okx import OkxExchange
from src.models import AlertEvent, OptionTicker
from src.storage.db import Database
from src.ui.alert_log import AlertLogPanel
from src.ui.dashboard import DashboardPanel
from src.ui.term_structure import TermStructurePanel
from src.ui.vol_smile import VolSmilePanel

logger = logging.getLogger(__name__)

class MonitorApp(App):
    CSS = """
    Screen { layout: vertical; }
    #statusbar { dock: bottom; height: 1; background: $panel; color: $text; padding: 0 1; }
    """
    BINDINGS = [
        Binding("f1", "switch_tab('dashboard')", "IV/RV"),
        Binding("f2", "switch_tab('smile')", "Smile"),
        Binding("f3", "switch_tab('term')", "Term"),
        Binding("f4", "switch_tab('alerts')", "Alerts"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, config_path: str = "config.yaml") -> None:
        super().__init__()
        with open(config_path) as f:
            self._config = yaml.safe_load(f)
        self._exchanges: list[Exchange] = []
        self._tickers: dict[str, OptionTicker] = {}
        self._spot_prices: list[float] = []
        self._db: Database | None = None
        self._alert_engine = AlertEngine(
            iv_rv_ratio_high=self._config["alerts"]["iv_rv_ratio_high"],
            iv_rv_ratio_low=self._config["alerts"]["iv_rv_ratio_low"],
            cross_exchange_iv_diff=self._config["alerts"]["cross_exchange_iv_diff"],
            cooldown_minutes=self._config["alerts"]["cooldown_min"],
        )

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="dashboard"):
            with TabPane("IV/RV [F1]", id="dashboard"):
                yield DashboardPanel(id="dashboard_panel")
            with TabPane("Smile [F2]", id="smile"):
                yield VolSmilePanel(id="smile_panel")
            with TabPane("Term [F3]", id="term"):
                yield TermStructurePanel(id="term_panel")
            with TabPane("Alerts [F4]", id="alerts"):
                yield AlertLogPanel(id="alert_panel")
        yield Label("Initializing...", id="statusbar")
        yield Footer()

    async def on_mount(self) -> None:
        self._db = Database("data/options.db")
        await self._db.initialize()
        await self._db.prune(days=90)
        cfg = self._config["exchanges"]
        if cfg.get("deribit", {}).get("enabled"):
            ex = DeribitExchange(ws_url=cfg["deribit"]["ws_url"])
            ex.on_ticker(self._on_ticker)
            self._exchanges.append(ex)
        if cfg.get("okx", {}).get("enabled"):
            ex = OkxExchange(ws_url=cfg["okx"]["ws_url"])
            ex.on_ticker(self._on_ticker)
            self._exchanges.append(ex)
        for ex in self._exchanges:
            asyncio.create_task(self._run_exchange(ex))
        self.set_interval(self._config.get("refresh_interval", 2), self._refresh_ui)
        self._update_status()

    async def _run_exchange(self, exchange: Exchange) -> None:
        symbol = self._config.get("symbol", "BTC")
        while True:
            try:
                await exchange.connect()
                await exchange.subscribe_options(symbol)
                self._update_status()
                await exchange.listen()
            except Exception as e:
                logger.error("Exchange %s error: %s", exchange.name, e)
            await asyncio.sleep(5)
            self._update_status()

    def _on_ticker(self, ticker: OptionTicker) -> None:
        self._tickers[ticker.instrument] = ticker
        if ticker.underlying_price > 0:
            self._spot_prices.append(ticker.underlying_price)
            max_points = 30 * 24
            if len(self._spot_prices) > max_points:
                self._spot_prices = self._spot_prices[-max_points:]
        rv_data = compute_rv_multi_window(self._spot_prices, self._config.get("rv_windows", [7, 14, 30]), samples_per_day=24)
        rv_14d = rv_data.get("14d", 0) * 100
        if rv_14d > 0:
            alerts = self._alert_engine.check_iv_rv_ratio(ticker.instrument, ticker.iv, rv_14d)
            for alert in alerts:
                self._show_alert(alert)

    def _show_alert(self, alert: AlertEvent) -> None:
        try:
            panel = self.query_one("#alert_panel", AlertLogPanel)
            panel.add_alert(alert)
        except Exception:
            pass

    def _refresh_ui(self) -> None:
        self._refresh_dashboard()
        self._refresh_smile()
        self._refresh_term_structure()
        self._update_status()

    def _refresh_dashboard(self) -> None:
        rv_data = compute_rv_multi_window(self._spot_prices, self._config.get("rv_windows", [7, 14, 30]), samples_per_day=24)
        rows = []
        for ticker in self._tickers.values():
            rv_7d = rv_data.get("7d", 0) * 100
            rv_14d = rv_data.get("14d", 0) * 100
            rv_30d = rv_data.get("30d", 0) * 100
            score = score_deviation(ticker.iv, rv_14d)
            rows.append({"exchange": ticker.exchange, "expiry": ticker.expiry.strftime("%d%b%y"),
                "strike": ticker.strike, "option_type": ticker.option_type, "iv": ticker.iv,
                "rv_7d": rv_7d, "rv_14d": rv_14d, "rv_30d": rv_30d, "ratio": score.ratio, "signal": score.signal})
        rows.sort(key=lambda r: r["ratio"], reverse=True)
        try:
            panel = self.query_one("#dashboard_panel", DashboardPanel)
            panel.update_data(rows[:100])
        except Exception:
            pass

    def _refresh_smile(self) -> None:
        smile_data: dict[str, list[tuple[float, float]]] = {}
        spot = 0.0
        for ticker in self._tickers.values():
            if ticker.underlying_price > 0: spot = ticker.underlying_price
            label = ticker.expiry.strftime("%d%b%y")
            if label not in smile_data: smile_data[label] = []
            smile_data[label].append((ticker.strike, ticker.iv))
        for label in smile_data:
            smile_data[label].sort(key=lambda p: p[0])
        try:
            panel = self.query_one("#smile_panel", VolSmilePanel)
            panel.update_data(smile_data, spot)
        except Exception:
            pass

    def _refresh_term_structure(self) -> None:
        now = datetime.now(timezone.utc)
        atm_by_exchange: dict[str, list[tuple[int, float]]] = {}
        spot = 0.0
        for ticker in self._tickers.values():
            if ticker.underlying_price > 0: spot = ticker.underlying_price
        if spot <= 0: return
        for ticker in self._tickers.values():
            if abs(ticker.strike - spot) / spot > 0.10: continue
            dte = max(0, (ticker.expiry - now).days)
            ex = ticker.exchange
            if ex not in atm_by_exchange: atm_by_exchange[ex] = []
            atm_by_exchange[ex].append((dte, ticker.iv))
        result: dict[str, list[tuple[int, float]]] = {}
        for ex, points in atm_by_exchange.items():
            dte_ivs: dict[int, list[float]] = {}
            for dte, iv in points:
                dte_ivs.setdefault(dte, []).append(iv)
            avg_points = [(dte, sum(ivs) / len(ivs)) for dte, ivs in dte_ivs.items()]
            avg_points.sort(key=lambda p: p[0])
            result[ex] = avg_points
        try:
            panel = self.query_one("#term_panel", TermStructurePanel)
            panel.update_data(result)
        except Exception:
            pass

    def _update_status(self) -> None:
        parts = []
        for ex in self._exchanges:
            indicator = "[green]●[/]" if ex.connected else "[red]●[/]"
            parts.append(f"{indicator} {ex.name.capitalize()}")
        n_tickers = len(self._tickers)
        interval = self._config.get("refresh_interval", 2)
        try:
            label = self.query_one("#statusbar", Label)
            label.update(f"Status: {' '.join(parts)} │ Options: {n_tickers} │ Refresh: {interval}s")
        except Exception:
            pass

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one(TabbedContent).active = tab_id

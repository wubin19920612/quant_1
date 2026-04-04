from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
import yaml
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Label, TabbedContent, TabPane
from src.analytics.alerts import AlertEngine
from src.analytics.regime_detector import RegimeDetector
from src.analytics.rv_calculator import compute_rv_multi_window
from src.analytics.scorer import score_deviation
from src.analytics.strategy_advisor import StrategyAdvisor
from src.exchanges.base import Exchange
from src.exchanges.deribit import DeribitExchange
from src.exchanges.okx import OkxExchange
from src.models import AlertEvent, OptionTicker, Regime
from src.notifications.telegram import TelegramConfig, TelegramNotifier
from src.storage.db import Database
from src.ui.alert_log import AlertLogPanel
from src.ui.dashboard import DashboardPanel
from src.ui.regime_panel import RegimePanel
from src.ui.strategy_panel import StrategyPanel
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
        Binding("f5", "switch_tab('regime')", "Regime"),
        Binding("f6", "switch_tab('strategy')", "Strategy"),
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
            iv_spike_pct=self._config["alerts"].get("iv_spike_pct", 0.20),
            iv_spike_window_min=self._config["alerts"].get("iv_spike_window_min", 30),
        )
        regime_cfg = self._config.get("regime", {})
        self._regime_detector = RegimeDetector(
            lookback_days=regime_cfg.get("lookback_days", 90),
            low_z=regime_cfg.get("low_z", -1.0),
            high_z=regime_cfg.get("high_z", 1.0),
            crisis_z=regime_cfg.get("crisis_z", 2.0),
        )
        self._strategy_advisor = StrategyAdvisor()
        self._regime_history_limit = regime_cfg.get("history_limit", 1000)
        self._current_dvol = 0.0
        self._dvol_history: list[float] = []
        self._current_regime = Regime.NORMAL
        self._current_zscore = 0.0
        self._current_iv_rank = 0.0
        tg_cfg = self._config["alerts"].get("telegram", {})
        self._telegram = TelegramNotifier(TelegramConfig(
            enabled=tg_cfg.get("enabled", False),
            bot_token=tg_cfg.get("bot_token", ""),
            chat_id=tg_cfg.get("chat_id", ""),
        ))

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
            with TabPane("Regime [F5]", id="regime"):
                yield RegimePanel(id="regime_panel")
            with TabPane("Strategy [F6]", id="strategy"):
                yield StrategyPanel(id="strategy_panel")
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
            if hasattr(ex, "on_dvol"):
                ex.on_dvol(self._on_dvol)
            self._exchanges.append(ex)
        if cfg.get("okx", {}).get("enabled"):
            ex = OkxExchange(ws_url=cfg["okx"]["ws_url"])
            ex.on_ticker(self._on_ticker)
            self._exchanges.append(ex)
        for ex in self._exchanges:
            asyncio.create_task(self._run_exchange(ex))
        self.set_interval(self._config.get("refresh_interval", 2), self._refresh_ui)
        self._update_regime()
        self._update_status()

    async def _run_exchange(self, exchange: Exchange) -> None:
        symbol = self._config.get("symbol", "BTC")
        while True:
            try:
                await exchange.connect()
                await exchange.subscribe_options(symbol)
                subscribe_dvol = getattr(exchange, "subscribe_dvol", None)
                if callable(subscribe_dvol):
                    await subscribe_dvol()
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
        spike_alerts = self._alert_engine.check_iv_spike(ticker.instrument, ticker.iv)
        for alert in spike_alerts:
            self._show_alert(alert)

    def _on_dvol(self, dvol: float, ts: datetime | None) -> None:
        self._current_dvol = dvol
        self._dvol_history = [*self._dvol_history, dvol][-self._regime_history_limit:]
        if self._db is not None and ts is not None:
            asyncio.create_task(self._db.save_dvol(dvol, ts))
        self._update_regime(ts)

    def _update_regime(self, ts: datetime | None = None) -> None:
        if self._current_dvol <= 0:
            return
        previous_regime = self._current_regime
        regime, zscore = self._regime_detector.classify(self._dvol_history, self._current_dvol)
        self._current_regime = regime
        self._current_zscore = zscore
        history = self._dvol_history[-self._regime_history_limit:]
        if history:
            low = min(history)
            high = max(history)
            iv_rank = (self._current_dvol - low) / (high - low) if high > low else 0.0
        else:
            iv_rank = 0.0
        self._current_iv_rank = max(0.0, min(1.0, iv_rank))
        if self._db is not None and ts is not None:
            asyncio.create_task(self._db.save_regime(regime.value, self._current_dvol, zscore, ts))
        try:
            panel = self.query_one("#regime_panel", RegimePanel)
            panel.update_regime(regime, self._current_dvol, zscore, self._current_iv_rank)
        except Exception:
            pass
        advice = self._strategy_advisor.advise(regime, self._current_iv_rank)
        try:
            panel = self.query_one("#strategy_panel", StrategyPanel)
            panel.update_advice(advice)
        except Exception:
            pass
        symbol = self._config.get("symbol", "BTC")
        for alert in self._alert_engine.check_regime_change(symbol, regime, previous_regime):
            self._show_alert(alert)

    def _show_alert(self, alert: AlertEvent) -> None:
        try:
            panel = self.query_one("#alert_panel", AlertLogPanel)
            panel.add_alert(alert)
        except Exception:
            pass
        if self._telegram.enabled:
            asyncio.create_task(
                self._telegram.send(f"[{alert.level.upper()}] {alert.message}")
            )

    def _refresh_ui(self) -> None:
        self._refresh_dashboard()
        self._refresh_smile()
        self._refresh_term_structure()
        self._update_regime()
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

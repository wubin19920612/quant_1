from __future__ import annotations
from textual.widgets import DataTable
from textual.widget import Widget
from textual.app import ComposeResult
from src.models import OptionTicker, Signal
from src.analytics.scorer import ScoreResult

SIGNAL_STYLE = {
    Signal.STRONG_SELL: ("bold red", "SELL!"),
    Signal.WEAK_SELL: ("yellow", "sell"),
    Signal.NEUTRAL: ("white", "—"),
    Signal.WEAK_BUY: ("yellow", "buy"),
    Signal.STRONG_BUY: ("bold green", "BUY!"),
}

class DashboardPanel(Widget):
    DEFAULT_CSS = """
    DashboardPanel { height: 1fr; }
    DashboardPanel DataTable { height: 1fr; }
    """
    def compose(self) -> ComposeResult:
        table = DataTable(id="iv_rv_table")
        table.cursor_type = "row"
        table.zebra_stripes = True
        yield table

    def on_mount(self) -> None:
        table = self.query_one("#iv_rv_table", DataTable)
        table.add_columns("Exchange", "Expiry", "Strike", "Type", "IV%", "RV7d%", "RV14d%", "RV30d%", "IV/RV", "Signal")

    def update_data(self, rows: list[dict]) -> None:
        table = self.query_one("#iv_rv_table", DataTable)
        table.clear()
        for row in rows:
            signal = row["signal"]
            _, signal_label = SIGNAL_STYLE.get(signal, ("white", "?"))
            table.add_row(
                row["exchange"], row["expiry"], f"{row['strike']:,.0f}",
                row["option_type"].upper(), f"{row['iv']:.1f}",
                f"{row['rv_7d']:.1f}", f"{row['rv_14d']:.1f}", f"{row['rv_30d']:.1f}",
                f"{row['ratio']:.2f}", signal_label,
            )

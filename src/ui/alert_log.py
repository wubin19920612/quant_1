from __future__ import annotations
from textual.widgets import RichLog
from textual.widget import Widget
from textual.app import ComposeResult
from src.models import AlertEvent

LEVEL_STYLE = {"high": "bold red", "medium": "yellow", "low": "white"}

class AlertLogPanel(Widget):
    DEFAULT_CSS = """
    AlertLogPanel { height: 1fr; }
    AlertLogPanel RichLog { height: 1fr; border: solid $accent; }
    """
    def compose(self) -> ComposeResult:
        yield RichLog(id="alert_log", wrap=True, markup=True)

    def add_alert(self, alert: AlertEvent) -> None:
        log = self.query_one("#alert_log", RichLog)
        style = LEVEL_STYLE.get(alert.level, "white")
        time_str = alert.timestamp.strftime("%H:%M:%S")
        level_tag = alert.level.upper()
        log.write(f"[{style}]{time_str} [{level_tag}] {alert.message}[/{style}]")

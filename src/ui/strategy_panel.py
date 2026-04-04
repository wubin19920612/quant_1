from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog, Static

from src.analytics.strategy_advisor import StrategyAdvice


class StrategyPanel(Widget):
    DEFAULT_CSS = """
    StrategyPanel { height: 1fr; }
    StrategyPanel Static { height: auto; border: solid $accent; padding: 0 1; }
    StrategyPanel RichLog { height: 1fr; border: solid $accent; }
    """

    def compose(self) -> ComposeResult:
        yield Static("Strategy Recommendations", id="strategy_title")
        yield Static("Waiting for strategy advice...", id="strategy_summary")
        yield RichLog(id="strategy_log", wrap=True)

    def update_advice(self, advice: StrategyAdvice) -> None:
        summary = self.query_one("#strategy_summary", Static)
        log = self.query_one("#strategy_log", RichLog)
        summary.update(
            f"Regime: {advice.regime.value}\n"
            f"IV Rank: {advice.iv_rank:.1%}\n"
            f"Description: {advice.description}"
        )
        log.clear()
        for index, strategy in enumerate(advice.strategies, start=1):
            log.write(f"{index}. {strategy}")

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import RichLog, Static

from src.analytics.strategy_advisor import StrategyAdvice
from src.models import Regime
from src.ui.strategy_panel import StrategyPanel


class StrategyApp(App):
    def compose(self) -> ComposeResult:
        yield StrategyPanel(id="panel")


async def test_strategy_panel_mount():
    async with StrategyApp().run_test() as pilot:
        panel = pilot.app.query_one(StrategyPanel)
        assert panel is not None
        assert panel.query_one("#strategy_title", Static).render().plain == "Strategy Recommendations"
        assert panel.query_one("#strategy_summary", Static).render().plain == "Waiting for strategy advice..."
        assert len(panel.query_one("#strategy_log", RichLog).lines) == 0


async def test_strategy_panel_update_advice():
    advice = StrategyAdvice(
        regime=Regime.HIGH,
        iv_rank=0.72,
        description="Options are rich versus recent history.",
        strategies=["Sell put spread", "Iron condor", "Sell covered call"],
    )

    async with StrategyApp().run_test() as pilot:
        panel = pilot.app.query_one(StrategyPanel)
        panel.update_advice(advice)
        await pilot.pause()

        summary = panel.query_one("#strategy_summary", Static).render().plain
        log = panel.query_one("#strategy_log", RichLog)
        lines = ["".join(segment.text for segment in strip._segments) for strip in log.lines]

        assert "Regime: HIGH" in summary
        assert "IV Rank: 72.0%" in summary
        assert "Options are rich versus recent history." in summary
        assert lines == [
            "1. Sell put spread",
            "2. Iron condor",
            "3. Sell covered call",
        ]

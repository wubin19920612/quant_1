from __future__ import annotations

from textual.app import App, ComposeResult
from textual.color import Color

from src.models import Regime
from src.ui.regime_panel import REGIME_STYLE_MAP, RegimePanel


class RegimeApp(App):
    def compose(self) -> ComposeResult:
        yield RegimePanel(id="panel")


async def test_regime_panel_mount():
    async with RegimeApp().run_test() as pilot:
        panel = pilot.app.query_one(RegimePanel)
        assert panel is not None
        assert str(panel.query_one("#regime_value").render()) == "Regime: NORMAL"
        assert str(panel.query_one("#dvol_value").render()) == "DVOL: --"
        assert str(panel.query_one("#zscore_value").render()) == "Z-Score: --"
        assert str(panel.query_one("#iv_rank_value").render()) == "IV Rank: --"


async def test_regime_panel_update_regime():
    async with RegimeApp().run_test() as pilot:
        panel = pilot.app.query_one(RegimePanel)

        panel.update_regime(Regime.HIGH, 72.35, 1.84, 0.67)

        assert str(panel.query_one("#regime_value").render()) == "Regime: HIGH"
        assert str(panel.query_one("#dvol_value").render()) == "DVOL: 72.35"
        assert str(panel.query_one("#zscore_value").render()) == "Z-Score: 1.84"
        assert str(panel.query_one("#iv_rank_value").render()) == "IV Rank: 67.00%"
        assert panel.styles.border.top[1] == Color.parse(REGIME_STYLE_MAP[Regime.HIGH])

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static

from src.models import Regime

REGIME_STYLE_MAP = {
    Regime.LOW: "green",
    Regime.NORMAL: "white",
    Regime.HIGH: "yellow",
    Regime.CRISIS: "red",
}


class RegimePanel(Widget):
    DEFAULT_CSS = """
    RegimePanel {
        height: auto;
        border: solid $accent;
        padding: 0 1;
    }

    RegimePanel > Vertical {
        height: auto;
    }

    RegimePanel Static {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Regime: NORMAL", id="regime_value")
            yield Static("DVOL: --", id="dvol_value")
            yield Static("Z-Score: --", id="zscore_value")
            yield Static("IV Rank: --", id="iv_rank_value")

    def update_regime(
        self,
        regime: Regime | str,
        dvol: float,
        zscore: float,
        iv_rank: float,
    ) -> None:
        normalized_regime = regime if isinstance(regime, Regime) else Regime(regime)
        style = REGIME_STYLE_MAP[normalized_regime]

        self.query_one("#regime_value", Static).update(
            f"Regime: {normalized_regime.value}"
        )
        self.query_one("#regime_value", Static).styles.color = style
        self.query_one("#dvol_value", Static).update(f"DVOL: {dvol:.2f}")
        self.query_one("#zscore_value", Static).update(f"Z-Score: {zscore:.2f}")
        self.query_one("#iv_rank_value", Static).update(f"IV Rank: {iv_rank:.2%}")
        self.styles.border = ("solid", style)

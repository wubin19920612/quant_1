from __future__ import annotations
from dataclasses import dataclass
from src.models import Regime


@dataclass(frozen=True)
class StrategyAdvice:
    regime: Regime
    iv_rank: float
    strategies: list[str]
    description: str


_STRATEGY_MAP: dict[tuple[Regime, str], tuple[list[str], str]] = {
    (Regime.LOW, "low"): (
        ["Buy straddle", "Buy calendar spread", "Long volatility"],
        "Volatility is historically low and cheap — good time to buy options or go long vol.",
    ),
    (Regime.LOW, "mid"): (
        ["Buy calendar spread", "Long call/put"],
        "Vol is low but not at extreme discount — directional plays with limited risk.",
    ),
    (Regime.LOW, "high"): (
        ["Buy calendar spread", "Neutral strategies"],
        "Vol is low overall but IV rank is elevated — calendar spreads benefit from term structure.",
    ),
    (Regime.NORMAL, "low"): (
        ["Buy straddle", "Buy strangle"],
        "Normal vol environment with options priced cheaply — consider buying premium.",
    ),
    (Regime.NORMAL, "mid"): (
        ["Iron condor", "Butterfly spread", "Neutral"],
        "Balanced environment — range-bound strategies or wait for clearer signal.",
    ),
    (Regime.NORMAL, "high"): (
        ["Sell put spread", "Iron condor", "Sell covered call"],
        "Normal vol but IV is relatively elevated — sell premium with defined risk.",
    ),
    (Regime.HIGH, "low"): (
        ["Buy straddle", "Buy strangle"],
        "High vol regime but options are priced low relative to recent history — buy opportunity.",
    ),
    (Regime.HIGH, "mid"): (
        ["Iron condor", "Sell put spread"],
        "Elevated vol with moderate IV rank — sell premium with wider strikes.",
    ),
    (Regime.HIGH, "high"): (
        ["Sell iron condor", "Sell strangle", "Sell put spread"],
        "High vol with rich IV — prime environment to sell premium with defined risk.",
    ),
    (Regime.CRISIS, "low"): (
        ["Buy put protection", "Long volatility"],
        "Crisis regime but options somehow cheap — buy protection immediately.",
    ),
    (Regime.CRISIS, "mid"): (
        ["Buy put spread", "Collar"],
        "Crisis with moderate IV — hedge with spreads to manage cost.",
    ),
    (Regime.CRISIS, "high"): (
        ["Sell iron condor (wide)", "Sell put spread (far OTM)", "Cash / reduce exposure"],
        "Crisis with expensive options — if selling, use very wide wings. Consider reducing exposure.",
    ),
}


class StrategyAdvisor:
    def advise(self, regime: Regime, iv_rank: float) -> StrategyAdvice:
        iv_rank = max(0.0, min(1.0, iv_rank))
        if iv_rank < 0.33:
            bucket = "low"
        elif iv_rank < 0.67:
            bucket = "mid"
        else:
            bucket = "high"
        strategies, description = _STRATEGY_MAP.get(
            (regime, bucket),
            (["No specific recommendation"], "Insufficient data for strategy recommendation."),
        )
        return StrategyAdvice(
            regime=regime,
            iv_rank=iv_rank,
            strategies=list(strategies),
            description=description,
        )

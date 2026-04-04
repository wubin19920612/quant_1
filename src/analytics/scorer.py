from __future__ import annotations

from dataclasses import dataclass

from src.models import Signal


@dataclass(frozen=True)
class ScoreResult:
    iv: float
    rv: float
    diff: float
    ratio: float
    signal: Signal


def score_deviation(
    iv: float,
    rv: float,
    high_threshold: float = 1.5,
    low_threshold: float = 0.5,
) -> ScoreResult:
    if rv <= 0:
        return ScoreResult(iv=iv, rv=rv, diff=iv, ratio=0.0, signal=Signal.NEUTRAL)

    ratio = iv / rv
    diff = iv - rv
    strong_sell_threshold = max(high_threshold, 1.2)

    if ratio > strong_sell_threshold:
        signal = Signal.STRONG_SELL
    elif ratio >= 1.2:
        signal = Signal.WEAK_SELL
    elif ratio >= 0.8:
        signal = Signal.NEUTRAL
    elif ratio >= low_threshold:
        signal = Signal.WEAK_BUY
    else:
        signal = Signal.STRONG_BUY

    return ScoreResult(iv=iv, rv=rv, diff=diff, ratio=ratio, signal=signal)

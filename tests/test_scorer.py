import pytest

from src.analytics.scorer import ScoreResult, score_deviation
from src.models import Signal


def test_strong_sell_signal():
    result = score_deviation(iv=90.0, rv=50.0)
    assert result.signal == Signal.STRONG_SELL
    assert result.ratio == pytest.approx(1.8, rel=0.01)


def test_weak_sell_signal():
    result = score_deviation(iv=60.0, rv=45.0)
    assert result.signal == Signal.WEAK_SELL
    assert 1.2 <= result.ratio <= 1.5


def test_neutral_signal():
    result = score_deviation(iv=50.0, rv=50.0)
    assert result.signal == Signal.NEUTRAL
    assert 0.8 <= result.ratio <= 1.2


def test_weak_buy_signal():
    result = score_deviation(iv=35.0, rv=50.0)
    assert result.signal == Signal.WEAK_BUY


def test_strong_buy_signal():
    result = score_deviation(iv=20.0, rv=50.0)
    assert result.signal == Signal.STRONG_BUY
    assert result.ratio < 0.5


def test_custom_thresholds():
    result = score_deviation(iv=60.0, rv=50.0, high_threshold=1.1)
    assert result.signal == Signal.WEAK_SELL


def test_zero_rv_returns_neutral():
    result = score_deviation(iv=50.0, rv=0.0)
    assert result.signal == Signal.NEUTRAL
    assert result.ratio == 0.0

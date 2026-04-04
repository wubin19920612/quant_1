from __future__ import annotations

from datetime import datetime, timezone

from src.models import OHLC, Regime


def test_regime_enum_values():
    assert Regime.LOW.value == "LOW"
    assert Regime.NORMAL.value == "NORMAL"
    assert Regime.HIGH.value == "HIGH"
    assert Regime.CRISIS.value == "CRISIS"


def test_ohlc_frozen():
    candle = OHLC(
        timestamp=datetime(2025, 3, 28, 0, 0, tzinfo=timezone.utc),
        open=87000.0,
        high=88000.0,
        low=86500.0,
        close=87500.0,
        volume=1234.5,
    )
    assert candle.open == 87000.0
    assert candle.close == 87500.0


def test_ohlc_immutable():
    import pytest
    candle = OHLC(
        timestamp=datetime(2025, 3, 28, 0, 0, tzinfo=timezone.utc),
        open=87000.0, high=88000.0, low=86500.0, close=87500.0, volume=1234.5,
    )
    with pytest.raises(AttributeError):
        candle.open = 99999.0

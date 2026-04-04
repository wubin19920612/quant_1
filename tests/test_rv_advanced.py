from __future__ import annotations
from datetime import datetime, timezone, timedelta
import pytest
from src.models import OHLC
from src.analytics.rv_advanced import parkinson_rv, yang_zhang_rv


def _make_candles(n: int, base_price: float = 87000.0, daily_range_pct: float = 0.02) -> list[OHLC]:
    candles = []
    price = base_price
    for i in range(n):
        high = price * (1 + daily_range_pct / 2)
        low = price * (1 - daily_range_pct / 2)
        close = price * (1 + (0.001 if i % 2 == 0 else -0.001))
        candles.append(OHLC(
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=i),
            open=price, high=high, low=low, close=close, volume=100.0,
        ))
        price = close
    return candles


def test_parkinson_rv_basic():
    candles = _make_candles(30, daily_range_pct=0.02)
    rv = parkinson_rv(candles)
    assert 0.0 < rv < 2.0
    assert isinstance(rv, float)


def test_parkinson_rv_too_few_candles():
    candle = _make_candles(1)
    assert parkinson_rv(candle) == 0.0


def test_yang_zhang_rv_basic():
    candles = _make_candles(30, daily_range_pct=0.02)
    rv = yang_zhang_rv(candles)
    assert 0.0 < rv < 2.0
    assert isinstance(rv, float)


def test_yang_zhang_rv_too_few_candles():
    candles = _make_candles(1)
    assert yang_zhang_rv(candles) == 0.0


def test_yang_zhang_higher_than_close_to_close():
    candles = _make_candles(30, daily_range_pct=0.05)
    yz = yang_zhang_rv(candles)
    pk = parkinson_rv(candles)
    assert yz > 0
    assert pk > 0

from __future__ import annotations
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from src.exchanges.deribit import DeribitExchange


def test_parse_dvol_data():
    ex = DeribitExchange(ws_url="wss://test.deribit.com/ws/api/v2")
    data = {"volatility": 65.3, "timestamp": 1743000000123}
    dvol, ts = ex.parse_dvol(data)
    assert dvol == 65.3
    assert ts.year == 2025


def test_parse_dvol_data_missing_key():
    ex = DeribitExchange(ws_url="wss://test.deribit.com/ws/api/v2")
    result = ex.parse_dvol({})
    assert result is None


def test_parse_ohlc_candles():
    ex = DeribitExchange(ws_url="wss://test.deribit.com/ws/api/v2")
    raw_candles = [
        {"tick": 1743000000000, "open": 87000, "high": 88000, "low": 86500, "close": 87500, "volume": 1234.5},
        {"tick": 1743086400000, "open": 87500, "high": 89000, "low": 87000, "close": 88500, "volume": 2000.0},
    ]
    candles = ex.parse_ohlc_candles(raw_candles)
    assert len(candles) == 2
    assert candles[0].open == 87000.0
    assert candles[1].close == 88500.0


def test_parse_ohlc_candles_empty():
    ex = DeribitExchange(ws_url="wss://test.deribit.com/ws/api/v2")
    assert ex.parse_ohlc_candles([]) == []

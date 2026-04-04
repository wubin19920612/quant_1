import pytest
from datetime import datetime, timezone
from src.exchanges.deribit import DeribitExchange
from src.exchanges.okx import OkxExchange

def test_parse_instrument_name():
    exchange = DeribitExchange(ws_url="wss://test.deribit.com/ws/api/v2")
    strike, expiry, opt_type = exchange.parse_instrument("BTC-28MAR25-80000-C")
    assert strike == 80000.0
    assert opt_type == "call"
    assert expiry.year == 2025
    assert expiry.month == 3
    assert expiry.day == 28

def test_parse_instrument_put():
    exchange = DeribitExchange(ws_url="wss://test.deribit.com/ws/api/v2")
    strike, expiry, opt_type = exchange.parse_instrument("BTC-25APR25-90000-P")
    assert strike == 90000.0
    assert opt_type == "put"
    assert expiry.month == 4

def test_parse_ticker_data():
    exchange = DeribitExchange(ws_url="wss://test.deribit.com/ws/api/v2")
    raw = {
        "instrument_name": "BTC-28MAR25-80000-C",
        "underlying_price": 87500.0,
        "mark_price": 0.045,
        "mark_iv": 68.35,
        "best_bid_price": 0.044,
        "best_ask_price": 0.046,
        "open_interest": 1250.5,
        "volume": 45.2,
        "timestamp": 1743000000123,
    }
    ticker = exchange.parse_ticker(raw)
    assert ticker is not None
    assert ticker.exchange == "deribit"
    assert ticker.iv == 68.35
    assert ticker.underlying_price == 87500.0
    assert ticker.strike == 80000.0
    assert ticker.option_type == "call"
    assert ticker.bid == pytest.approx(0.044)

def test_okx_parse_instrument_id():
    exchange = OkxExchange()
    strike, expiry, opt_type = exchange.parse_instrument("BTC-USD-250328-80000-C")
    assert strike == 80000.0
    assert opt_type == "call"
    assert expiry.year == 2025
    assert expiry.month == 3
    assert expiry.day == 28

def test_okx_parse_ticker_data():
    exchange = OkxExchange()
    raw = {
        "instId": "BTC-USD-250328-80000-C",
        "markVol": "0.6210",
        "markPx": "0.0452",
        "bidPx": "0.0440",
        "askPx": "0.0465",
        "fwdPx": "83200.00",
        "stk": "80000",
        "expTime": "1743148800000",
        "optType": "C",
        "ts": "1712150400000",
    }
    ticker = exchange.parse_ticker(raw)
    assert ticker is not None
    assert ticker.exchange == "okx"
    assert ticker.iv == pytest.approx(62.10, rel=0.01)
    assert ticker.underlying_price == 83200.0
    assert ticker.strike == 80000.0
    assert ticker.option_type == "call"

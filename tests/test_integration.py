import pytest
from datetime import datetime, timezone
from src.models import OptionTicker, Signal
from src.analytics.rv_calculator import compute_rv, compute_rv_multi_window
from src.analytics.scorer import score_deviation
from src.analytics.alerts import AlertEngine
from src.exchanges.deribit import DeribitExchange
from src.exchanges.okx import OkxExchange
import numpy as np


def test_full_pipeline_deribit():
    """Integration: Deribit ticker → RV → scorer → alert check."""
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

    # Simulate spot prices for RV
    np.random.seed(42)
    prices = [87500.0]
    for _ in range(14 * 24):
        prices.append(prices[-1] * np.exp(np.random.normal(0, 0.005)))
    rv_data = compute_rv_multi_window(prices, [7, 14, 30], samples_per_day=24)
    rv_14d = rv_data["14d"] * 100

    score = score_deviation(ticker.iv, rv_14d)
    assert score.ratio > 0
    assert score.signal in list(Signal)

    engine = AlertEngine(iv_rv_ratio_high=1.5, iv_rv_ratio_low=0.5, cooldown_minutes=5)
    alerts = engine.check_iv_rv_ratio(ticker.instrument, ticker.iv, rv_14d)
    # Alerts may or may not fire depending on RV value, but no crash
    assert isinstance(alerts, list)


def test_full_pipeline_okx():
    """Integration: OKX ticker → scorer → alert check."""
    exchange = OkxExchange()
    raw = {
        "instId": "BTC-USD-250328-80000-C",
        "markVol": "0.6210",
        "markPx": "0.0452",
        "bidPx": "0.0440",
        "askPx": "0.0465",
        "fwdPx": "83200.00",
        "ts": "1712150400000",
    }
    ticker = exchange.parse_ticker(raw)
    assert ticker is not None
    assert ticker.iv == pytest.approx(62.10, rel=0.01)

    score = score_deviation(ticker.iv, 50.0)
    assert score.signal == Signal.WEAK_SELL


def test_cross_exchange_alert():
    """Integration: Compare IV across exchanges."""
    engine = AlertEngine(cross_exchange_iv_diff=0.05, cooldown_minutes=5)
    alerts = engine.check_cross_exchange_iv(
        "BTC-80000-C-20250328",
        exchange_a="deribit", iv_a=68.35,
        exchange_b="okx", iv_b=62.10,
    )
    assert len(alerts) == 1
    assert "deribit" in alerts[0].message
    assert "okx" in alerts[0].message


async def test_db_integration(tmp_path):
    """Integration: DB save and retrieve cycle."""
    from src.storage.db import Database
    db = Database(str(tmp_path / "int_test.db"))
    await db.initialize()
    now = datetime.now(timezone.utc)
    await db.save_spot_price("deribit", 87500.0, now)
    await db.save_iv_snapshot("deribit", "BTC-28MAR25-80000-C", 80000.0,
        datetime(2025, 3, 28, tzinfo=timezone.utc), 68.35, now)
    await db.save_alert("iv_rv_ratio", "BTC-28MAR25-80000-C", "test alert", now)

    prices = await db.get_spot_prices("deribit", limit=10)
    assert len(prices) == 1
    snapshots = await db.get_iv_snapshots("BTC-28MAR25-80000-C", limit=10)
    assert len(snapshots) == 1
    alerts = await db.get_alerts(limit=10)
    assert len(alerts) == 1
    await db.close()

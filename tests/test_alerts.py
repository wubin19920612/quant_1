from datetime import datetime, timedelta, timezone

import pytest

from src.analytics.alerts import AlertEngine
from src.models import AlertEvent


@pytest.fixture
def engine():
    return AlertEngine(
        iv_rv_ratio_high=1.5,
        iv_rv_ratio_low=0.5,
        cross_exchange_iv_diff=0.05,
        cooldown_minutes=5,
    )


def test_iv_rv_ratio_alert_triggered(engine):
    alerts = engine.check_iv_rv_ratio(instrument="BTC-28MAR25-80000-C", iv=90.0, rv=50.0)
    assert len(alerts) == 1
    assert alerts[0].level == "high"
    assert "1.80" in alerts[0].message


def test_iv_rv_ratio_no_alert_in_range(engine):
    alerts = engine.check_iv_rv_ratio(instrument="BTC-28MAR25-80000-C", iv=55.0, rv=50.0)
    assert len(alerts) == 0


def test_cooldown_suppresses_duplicate(engine):
    alerts1 = engine.check_iv_rv_ratio("BTC-28MAR25-80000-C", iv=90.0, rv=50.0)
    assert len(alerts1) == 1
    alerts2 = engine.check_iv_rv_ratio("BTC-28MAR25-80000-C", iv=91.0, rv=50.0)
    assert len(alerts2) == 0


def test_cooldown_expires(engine):
    alerts1 = engine.check_iv_rv_ratio("BTC-28MAR25-80000-C", iv=90.0, rv=50.0)
    assert len(alerts1) == 1
    key = ("iv_rv_ratio", "BTC-28MAR25-80000-C")
    engine._last_alert[key] = datetime.now(timezone.utc) - timedelta(minutes=10)
    alerts2 = engine.check_iv_rv_ratio("BTC-28MAR25-80000-C", iv=90.0, rv=50.0)
    assert len(alerts2) == 1


def test_cross_exchange_iv_alert(engine):
    alerts = engine.check_cross_exchange_iv(
        instrument_key="BTC-80000-C-20250328",
        exchange_a="deribit",
        iv_a=70.0,
        exchange_b="okx",
        iv_b=62.0,
    )
    assert len(alerts) == 1
    assert "deribit" in alerts[0].message
    assert "okx" in alerts[0].message


def test_cross_exchange_iv_no_alert_when_close(engine):
    alerts = engine.check_cross_exchange_iv(
        instrument_key="BTC-80000-C-20250328",
        exchange_a="deribit",
        iv_a=70.0,
        exchange_b="okx",
        iv_b=69.0,
    )
    assert len(alerts) == 0


# --- IV Spike tests ---

@pytest.fixture
def spike_engine():
    return AlertEngine(
        iv_spike_pct=0.20,
        iv_spike_window_min=30,
        cooldown_minutes=5,
    )


def test_iv_spike_triggered(spike_engine):
    t0 = datetime(2025, 3, 28, 12, 0, tzinfo=timezone.utc)
    spike_engine.check_iv_spike("BTC-28MAR25-80000-C", iv=50.0, timestamp=t0)
    t1 = t0 + timedelta(minutes=10)
    alerts = spike_engine.check_iv_spike("BTC-28MAR25-80000-C", iv=62.0, timestamp=t1)
    assert len(alerts) == 1
    assert alerts[0].rule == "iv_spike"
    assert "up" in alerts[0].message
    assert "24.0%" in alerts[0].message


def test_iv_spike_small_change_no_alert(spike_engine):
    t0 = datetime(2025, 3, 28, 12, 0, tzinfo=timezone.utc)
    spike_engine.check_iv_spike("BTC-28MAR25-80000-C", iv=50.0, timestamp=t0)
    t1 = t0 + timedelta(minutes=10)
    alerts = spike_engine.check_iv_spike("BTC-28MAR25-80000-C", iv=55.0, timestamp=t1)
    assert len(alerts) == 0


def test_iv_spike_expired_data_evicted(spike_engine):
    t0 = datetime(2025, 3, 28, 12, 0, tzinfo=timezone.utc)
    spike_engine.check_iv_spike("BTC-28MAR25-80000-C", iv=50.0, timestamp=t0)
    # 31 minutes later, old data should be evicted
    t1 = t0 + timedelta(minutes=31)
    spike_engine.check_iv_spike("BTC-28MAR25-80000-C", iv=55.0, timestamp=t1)
    # Now 10 min later, small change from 55 (not from 50)
    t2 = t1 + timedelta(minutes=10)
    alerts = spike_engine.check_iv_spike("BTC-28MAR25-80000-C", iv=60.0, timestamp=t2)
    assert len(alerts) == 0  # 9% change < 20% threshold


def test_iv_spike_cooldown_suppresses(spike_engine):
    t0 = datetime(2025, 3, 28, 12, 0, tzinfo=timezone.utc)
    spike_engine.check_iv_spike("BTC-28MAR25-80000-C", iv=50.0, timestamp=t0)
    t1 = t0 + timedelta(minutes=5)
    alerts1 = spike_engine.check_iv_spike("BTC-28MAR25-80000-C", iv=62.0, timestamp=t1)
    assert len(alerts1) == 1
    # Second spike within cooldown
    t2 = t1 + timedelta(minutes=2)
    alerts2 = spike_engine.check_iv_spike("BTC-28MAR25-80000-C", iv=75.0, timestamp=t2)
    assert len(alerts2) == 0

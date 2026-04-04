from datetime import datetime, timezone

from src.models import AlertEvent, OptionTicker, Signal


def test_option_ticker_is_frozen():
    ticker = OptionTicker(
        exchange="deribit",
        instrument="BTC-28MAR25-80000-C",
        underlying_price=87500.0,
        strike=80000.0,
        expiry=datetime(2025, 3, 28, tzinfo=timezone.utc),
        option_type="call",
        mark_price=0.045,
        bid=0.044,
        ask=0.046,
        iv=68.35,
        volume_24h=45.2,
        open_interest=1250.5,
        timestamp=datetime.now(timezone.utc),
    )
    assert ticker.exchange == "deribit"
    assert ticker.strike == 80000.0
    try:
        ticker.strike = 90000.0
        assert False, "Should have raised"
    except AttributeError:
        pass


def test_signal_enum_values():
    assert Signal.STRONG_SELL.value == "STRONG_SELL"
    assert Signal.NEUTRAL.value == "NEUTRAL"
    assert Signal.STRONG_BUY.value == "STRONG_BUY"


def test_alert_event_creation():
    alert = AlertEvent(
        timestamp=datetime.now(timezone.utc),
        level="high",
        rule="iv_rv_ratio",
        instrument="BTC-28MAR25-80000-C",
        message="IV/RV ratio 1.54 exceeds threshold 1.5",
    )
    assert alert.rule == "iv_rv_ratio"
    assert "1.54" in alert.message

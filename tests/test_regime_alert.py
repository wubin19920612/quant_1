from datetime import datetime, timedelta, timezone

from src.analytics.alerts import AlertEngine
from src.models import Regime


def test_regime_change_triggers_alert():
    engine = AlertEngine(cooldown_minutes=5)

    alerts = engine.check_regime_change("BTC", Regime.HIGH, Regime.NORMAL)

    assert len(alerts) == 1
    assert alerts[0].rule == "regime_change"
    assert alerts[0].instrument == "BTC"
    assert alerts[0].message == "Regime changed: NORMAL → HIGH"


def test_regime_change_no_alert_if_unchanged():
    engine = AlertEngine(cooldown_minutes=5)

    alerts = engine.check_regime_change("BTC", Regime.NORMAL, Regime.NORMAL)

    assert alerts == []


def test_regime_change_escalation_is_high_level():
    engine = AlertEngine(cooldown_minutes=5)

    alerts = engine.check_regime_change("BTC", Regime.HIGH, Regime.NORMAL)

    assert len(alerts) == 1
    assert alerts[0].level == "high"


def test_regime_change_to_crisis_is_high_level():
    engine = AlertEngine(cooldown_minutes=5)

    alerts = engine.check_regime_change("BTC", Regime.CRISIS, Regime.HIGH)

    assert len(alerts) == 1
    assert alerts[0].level == "high"


def test_regime_change_downgrade_is_medium_level():
    engine = AlertEngine(cooldown_minutes=5)

    alerts = engine.check_regime_change("BTC", Regime.NORMAL, Regime.HIGH)

    assert len(alerts) == 1
    assert alerts[0].level == "medium"


def test_regime_change_uses_passed_instrument():
    engine = AlertEngine(cooldown_minutes=5)

    alerts = engine.check_regime_change("ETH", Regime.HIGH, Regime.NORMAL)

    assert len(alerts) == 1
    assert alerts[0].instrument == "ETH"


def test_regime_change_cooldown_suppresses_duplicate():
    engine = AlertEngine(cooldown_minutes=5)

    alerts1 = engine.check_regime_change("BTC", Regime.HIGH, Regime.NORMAL)
    alerts2 = engine.check_regime_change("BTC", Regime.CRISIS, Regime.HIGH)

    assert len(alerts1) == 1
    assert alerts2 == []

    engine._last_alert[("regime_change", "global")] = datetime.now(timezone.utc) - timedelta(minutes=10)

    alerts3 = engine.check_regime_change("BTC", Regime.CRISIS, Regime.HIGH)

    assert len(alerts3) == 1

from __future__ import annotations
from src.models import Regime
from src.analytics.regime_detector import RegimeDetector


def test_classify_low_regime():
    detector = RegimeDetector(lookback_days=90)
    history = [40.0 + (i % 3 - 1) for i in range(90)]
    regime, zscore = detector.classify(history, current_dvol=35.0)
    assert regime == Regime.LOW
    assert zscore < -1.0


def test_classify_normal_regime():
    detector = RegimeDetector(lookback_days=90)
    history = [55.0 + (i % 5 - 2) * 0.5 for i in range(90)]
    regime, zscore = detector.classify(history, current_dvol=55.0)
    assert regime == Regime.NORMAL
    assert -1.0 <= zscore <= 1.0


def test_classify_high_regime():
    detector = RegimeDetector(lookback_days=90)
    history = [55.0 + (i % 5 - 2) * 0.5 for i in range(90)]
    # std ≈ 0.71; dvol=56.2 → z ≈ 1.69, which is in [high_z=1.0, crisis_z=2.0)
    regime, zscore = detector.classify(history, current_dvol=56.2)
    assert regime == Regime.HIGH
    assert zscore > 1.0


def test_classify_crisis_regime():
    detector = RegimeDetector(lookback_days=90)
    history = [55.0 + (i % 5 - 2) * 0.5 for i in range(90)]
    regime, zscore = detector.classify(history, current_dvol=70.0)
    assert regime == Regime.CRISIS
    assert zscore > 2.0


def test_classify_insufficient_history():
    detector = RegimeDetector(lookback_days=90)
    regime, zscore = detector.classify([50.0], current_dvol=50.0)
    assert regime == Regime.NORMAL
    assert zscore == 0.0


def test_custom_thresholds():
    detector = RegimeDetector(
        lookback_days=90,
        low_z=-0.5, high_z=0.5, crisis_z=1.5,
    )
    history = [55.0] * 90
    regime, _ = detector.classify(history, current_dvol=56.0)
    assert regime in (Regime.HIGH, Regime.CRISIS)

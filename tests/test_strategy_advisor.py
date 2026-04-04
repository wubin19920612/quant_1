from __future__ import annotations
from src.models import Regime
from src.analytics.strategy_advisor import StrategyAdvisor, StrategyAdvice


def test_crisis_regime_suggests_protection():
    advisor = StrategyAdvisor()
    advice = advisor.advise(regime=Regime.CRISIS, iv_rank=0.9)
    assert advice.regime == Regime.CRISIS
    assert len(advice.strategies) > 0
    assert any("sell" in s.lower() or "iron" in s.lower() or "spread" in s.lower()
               for s in advice.strategies)


def test_low_regime_low_iv_rank():
    advisor = StrategyAdvisor()
    advice = advisor.advise(regime=Regime.LOW, iv_rank=0.1)
    assert advice.regime == Regime.LOW
    assert len(advice.strategies) > 0
    assert any("buy" in s.lower() or "straddle" in s.lower() or "calendar" in s.lower()
               for s in advice.strategies)


def test_normal_regime_moderate_iv():
    advisor = StrategyAdvisor()
    advice = advisor.advise(regime=Regime.NORMAL, iv_rank=0.5)
    assert advice.regime == Regime.NORMAL
    assert len(advice.strategies) > 0


def test_high_regime_high_iv_rank():
    advisor = StrategyAdvisor()
    advice = advisor.advise(regime=Regime.HIGH, iv_rank=0.8)
    assert len(advice.strategies) > 0
    assert advice.iv_rank == 0.8


def test_iv_rank_clamped():
    advisor = StrategyAdvisor()
    advice = advisor.advise(regime=Regime.NORMAL, iv_rank=1.5)
    assert advice.iv_rank == 1.0
    advice2 = advisor.advise(regime=Regime.NORMAL, iv_rank=-0.3)
    assert advice2.iv_rank == 0.0


def test_advice_has_description():
    advisor = StrategyAdvisor()
    advice = advisor.advise(regime=Regime.HIGH, iv_rank=0.7)
    assert len(advice.description) > 10

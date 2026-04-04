import numpy as np
import pytest

from src.analytics.rv_calculator import compute_rv, compute_rv_multi_window


def test_compute_rv_constant_price():
    prices = [100.0] * 100
    rv = compute_rv(prices)
    assert rv == pytest.approx(0.0, abs=1e-10)


def test_compute_rv_known_value():
    np.random.seed(42)
    n = 1000
    daily_vol = 0.02
    prices = [100.0]
    for _ in range(n):
        ret = np.random.normal(0, daily_vol)
        prices.append(prices[-1] * np.exp(ret))

    rv = compute_rv(prices, samples_per_day=1)
    expected_annual = daily_vol * np.sqrt(365)
    assert abs(rv - expected_annual) < 0.05


def test_compute_rv_insufficient_data():
    assert compute_rv([100.0]) == 0.0
    assert compute_rv([]) == 0.0


def test_compute_rv_multi_window():
    np.random.seed(42)
    prices = [100.0]
    for _ in range(30 * 24):
        prices.append(prices[-1] * np.exp(np.random.normal(0, 0.005)))

    result = compute_rv_multi_window(prices, windows_days=[7, 14, 30], samples_per_day=24)
    assert "7d" in result
    assert "14d" in result
    assert "30d" in result
    assert all(v >= 0 for v in result.values())
    assert result["7d"] > 0

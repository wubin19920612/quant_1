from __future__ import annotations

import math

import numpy as np


def compute_rv(prices: list[float], samples_per_day: int = 24) -> float:
    if len(prices) < 2:
        return 0.0

    arr = np.array(prices)
    log_returns = np.log(arr[1:] / arr[:-1])
    if len(log_returns) == 0:
        return 0.0

    std = float(np.std(log_returns, ddof=1)) if len(log_returns) > 1 else 0.0
    return std * math.sqrt(365 * samples_per_day)


def compute_rv_multi_window(
    prices: list[float],
    windows_days: list[int],
    samples_per_day: int = 24,
) -> dict[str, float]:
    result: dict[str, float] = {}
    for days in windows_days:
        n_samples = days * samples_per_day
        window_prices = prices[-n_samples:] if len(prices) >= n_samples else prices
        rv = compute_rv(window_prices, samples_per_day)
        result[f"{days}d"] = rv
    return result

from __future__ import annotations
import math
import numpy as np
from src.models import OHLC


def parkinson_rv(candles: list[OHLC], trading_days_year: int = 365) -> float:
    if len(candles) < 2:
        return 0.0
    n = len(candles)
    hl_sq_sum = 0.0
    for c in candles:
        if c.low <= 0 or c.high <= 0:
            continue
        hl_sq_sum += math.log(c.high / c.low) ** 2
    factor = 1.0 / (4.0 * n * math.log(2))
    variance = factor * hl_sq_sum
    return math.sqrt(variance * trading_days_year)


def yang_zhang_rv(candles: list[OHLC], trading_days_year: int = 365) -> float:
    if len(candles) < 2:
        return 0.0
    n = len(candles) - 1
    log_oc = []
    for i in range(1, len(candles)):
        if candles[i].open <= 0 or candles[i - 1].close <= 0:
            continue
        log_oc.append(math.log(candles[i].open / candles[i - 1].close))
    if not log_oc:
        return 0.0
    arr_oc = np.array(log_oc)
    sigma_o_sq = float(np.var(arr_oc, ddof=1))
    log_cc = []
    for i in range(1, len(candles)):
        if candles[i].close <= 0 or candles[i - 1].close <= 0:
            continue
        log_cc.append(math.log(candles[i].close / candles[i - 1].close))
    if not log_cc:
        return 0.0
    arr_cc = np.array(log_cc)
    sigma_c_sq = float(np.var(arr_cc, ddof=1))
    rs_sum = 0.0
    count = 0
    for c in candles:
        if c.high <= 0 or c.low <= 0 or c.open <= 0 or c.close <= 0:
            continue
        ho = math.log(c.high / c.open)
        hc = math.log(c.high / c.close)
        lo = math.log(c.low / c.open)
        lc = math.log(c.low / c.close)
        rs_sum += ho * hc + lo * lc
        count += 1
    if count == 0:
        return 0.0
    sigma_rs_sq = rs_sum / count
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    sigma_yz_sq = sigma_o_sq + k * sigma_c_sq + (1 - k) * sigma_rs_sq
    if sigma_yz_sq < 0:
        return 0.0
    return math.sqrt(sigma_yz_sq * trading_days_year)

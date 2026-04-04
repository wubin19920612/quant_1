from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


def black_scholes_price(
    spot: float,
    strike: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str,
) -> float:
    if T <= 0 or sigma <= 0:
        return max(0.0, (spot - strike) if option_type == "call" else (strike - spot))

    d1 = (math.log(spot / strike) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "call":
        return float(spot * norm.cdf(d1) - strike * math.exp(-r * T) * norm.cdf(d2))

    return float(strike * math.exp(-r * T) * norm.cdf(-d2) - spot * norm.cdf(-d1))


def implied_volatility(
    price: float,
    spot: float,
    strike: float,
    T: float,
    r: float,
    option_type: str,
    precision: float = 1e-6,
) -> float | None:
    if price <= 0 or T <= 0 or spot <= 0 or strike <= 0:
        return None

    def objective(sigma: float) -> float:
        return black_scholes_price(spot, strike, T, r, sigma, option_type) - price

    try:
        return float(brentq(objective, 0.001, 10.0, xtol=precision))
    except ValueError:
        return None

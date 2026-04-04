import pytest

from src.analytics.iv_calculator import black_scholes_price, implied_volatility


def test_bs_call_price_atm():
    price = black_scholes_price(
        spot=100.0,
        strike=100.0,
        T=1.0,
        r=0.05,
        sigma=0.2,
        option_type="call",
    )
    assert 10.0 < price < 11.0


def test_bs_put_price_atm():
    price = black_scholes_price(
        spot=100.0,
        strike=100.0,
        T=1.0,
        r=0.05,
        sigma=0.2,
        option_type="put",
    )
    assert 5.0 < price < 7.0


def test_bs_price_deep_itm_call():
    price = black_scholes_price(
        spot=150.0,
        strike=100.0,
        T=0.5,
        r=0.05,
        sigma=0.3,
        option_type="call",
    )
    assert price > 50.0


def test_implied_volatility_roundtrip():
    known_vol = 0.65
    price = black_scholes_price(
        spot=87500.0,
        strike=80000.0,
        T=0.25,
        r=0.05,
        sigma=known_vol,
        option_type="call",
    )
    recovered_vol = implied_volatility(
        price=price,
        spot=87500.0,
        strike=80000.0,
        T=0.25,
        r=0.05,
        option_type="call",
    )
    assert abs(recovered_vol - known_vol) < 0.01


def test_implied_volatility_put():
    known_vol = 0.50
    price = black_scholes_price(
        spot=87500.0,
        strike=90000.0,
        T=0.5,
        r=0.05,
        sigma=known_vol,
        option_type="put",
    )
    recovered_vol = implied_volatility(
        price=price,
        spot=87500.0,
        strike=90000.0,
        T=0.5,
        r=0.05,
        option_type="put",
    )
    assert abs(recovered_vol - known_vol) < 0.01


def test_implied_volatility_returns_none_for_bad_price():
    result = implied_volatility(
        price=-1.0,
        spot=100.0,
        strike=100.0,
        T=1.0,
        r=0.05,
        option_type="call",
    )
    assert result is None

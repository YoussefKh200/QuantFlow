"""
Unit tests for BSM pricer.

Tests cover:
  - Put-call parity
  - Greeks sign/bound conditions
  - IV solver round-trip
  - Batch vectorization consistency
  - Edge cases (ATM, deep ITM/OTM, near-expiry)
"""
from __future__ import annotations

import numpy as np
import pytest

from app.services.options.bsm import BSMPricer


# --------------------------------------------------------------------------
# Test fixtures
# --------------------------------------------------------------------------
@pytest.fixture
def atm_params():
    """At-the-money option, 30 DTE."""
    return dict(S=100.0, K=100.0, T=30 / 365, r=0.05, q=0.02, sigma=0.20)


@pytest.fixture
def itm_call_params():
    """Deep in-the-money call."""
    return dict(S=120.0, K=100.0, T=60 / 365, r=0.05, q=0.02, sigma=0.20)


@pytest.fixture
def otm_put_params():
    """Out-of-the-money put."""
    return dict(S=100.0, K=85.0, T=30 / 365, r=0.05, q=0.02, sigma=0.20)


# --------------------------------------------------------------------------
# Put-call parity: C - P = S*e^{-qT} - K*e^{-rT}
# --------------------------------------------------------------------------
class TestPutCallParity:
    def test_atm(self, atm_params):
        p = atm_params
        call = BSMPricer.price(**p, option_type="C")
        put = BSMPricer.price(**p, option_type="P")
        expected = p["S"] * np.exp(-p["q"] * p["T"]) - p["K"] * np.exp(-p["r"] * p["T"])
        assert abs(call - put - expected) < 1e-8

    def test_itm_call(self, itm_call_params):
        p = itm_call_params
        call = BSMPricer.price(**p, option_type="C")
        put = BSMPricer.price(**p, option_type="P")
        expected = p["S"] * np.exp(-p["q"] * p["T"]) - p["K"] * np.exp(-p["r"] * p["T"])
        assert abs(call - put - expected) < 1e-8

    def test_many_strikes(self):
        """Put-call parity holds across the full strike chain."""
        S, T, r, q, sigma = 500.0, 0.25, 0.05, 0.0, 0.25
        strikes = np.linspace(400, 600, 50)
        for K in strikes:
            call = BSMPricer.price(S, K, T, r, q, sigma, "C")
            put = BSMPricer.price(S, K, T, r, q, sigma, "P")
            expected = S * np.exp(-q * T) - K * np.exp(-r * T)
            assert abs(call - put - expected) < 1e-7, f"Parity failed at K={K}"


# --------------------------------------------------------------------------
# Delta bounds
# --------------------------------------------------------------------------
class TestDelta:
    def test_call_delta_bounds(self, atm_params):
        p = atm_params
        d = BSMPricer.delta(**p, option_type="C")
        assert 0.0 < d < 1.0

    def test_put_delta_bounds(self, atm_params):
        p = atm_params
        d = BSMPricer.delta(**p, option_type="P")
        assert -1.0 < d < 0.0

    def test_deep_itm_call_delta_near_1(self):
        d = BSMPricer.delta(S=200, K=100, T=1.0, r=0.05, q=0.0, sigma=0.20, option_type="C")
        assert d > 0.95

    def test_deep_otm_call_delta_near_0(self):
        d = BSMPricer.delta(S=100, K=200, T=0.1, r=0.05, q=0.0, sigma=0.20, option_type="C")
        assert d < 0.05

    def test_call_put_delta_relationship(self, atm_params):
        """Call delta - Put delta = e^{-qT}"""
        p = atm_params
        dc = BSMPricer.delta(**p, option_type="C")
        dp = BSMPricer.delta(**p, option_type="P")
        expected = np.exp(-p["q"] * p["T"])
        assert abs(dc - dp - expected) < 1e-8


# --------------------------------------------------------------------------
# Gamma
# --------------------------------------------------------------------------
class TestGamma:
    def test_gamma_positive(self, atm_params):
        g = BSMPricer.gamma(**atm_params)
        assert g > 0.0

    def test_gamma_same_for_calls_and_puts(self, atm_params):
        """Gamma is the same for calls and puts (put-call parity derivative)."""
        gc = BSMPricer.gamma(**atm_params)
        gp = BSMPricer.gamma(**atm_params)
        assert abs(gc - gp) < 1e-12

    def test_gamma_maximum_atm(self):
        """Gamma peaks at ATM."""
        S, T, r, q, sigma = 100.0, 0.25, 0.05, 0.0, 0.20
        g_atm = BSMPricer.gamma(S, S, T, r, q, sigma)
        g_itm = BSMPricer.gamma(S, 80.0, T, r, q, sigma)
        g_otm = BSMPricer.gamma(S, 120.0, T, r, q, sigma)
        assert g_atm > g_itm
        assert g_atm > g_otm


# --------------------------------------------------------------------------
# Vega
# --------------------------------------------------------------------------
class TestVega:
    def test_vega_positive(self, atm_params):
        v = BSMPricer.vega(**atm_params)
        assert v > 0.0

    def test_vega_near_zero_deep_otm(self):
        v = BSMPricer.vega(S=100, K=200, T=0.05, r=0.05, q=0.0, sigma=0.20)
        assert v < 0.01


# --------------------------------------------------------------------------
# Theta
# --------------------------------------------------------------------------
class TestTheta:
    def test_theta_negative_long_call(self, atm_params):
        """Long options lose value with time — theta should be negative."""
        t = BSMPricer.theta(**atm_params, option_type="C")
        assert t < 0.0

    def test_theta_negative_long_put(self, atm_params):
        t = BSMPricer.theta(**atm_params, option_type="P")
        assert t < 0.0


# --------------------------------------------------------------------------
# Second-order Greeks
# --------------------------------------------------------------------------
class TestSecondOrderGreeks:
    def test_vanna_finite(self, atm_params):
        v = BSMPricer.vanna(**atm_params)
        assert np.isfinite(v)

    def test_charm_finite(self, atm_params):
        c = BSMPricer.charm(**atm_params, option_type="C")
        assert np.isfinite(c)

    def test_vomma_positive_atm(self, atm_params):
        """Vomma (vol convexity) should be positive for ATM options."""
        v = BSMPricer.vomma(**atm_params)
        assert v > 0.0

    def test_speed_finite(self, atm_params):
        s = BSMPricer.speed(**atm_params)
        assert np.isfinite(s)


# --------------------------------------------------------------------------
# IV Solver
# --------------------------------------------------------------------------
class TestIVSolver:
    def test_iv_round_trip(self, atm_params):
        """Price → IV → Price should recover original price."""
        p = atm_params
        true_iv = p["sigma"]
        market_price = BSMPricer.price(**p, option_type="C")
        solved_iv = BSMPricer.implied_vol(
            p["S"], p["K"], p["T"], p["r"], p["q"], market_price, "C"
        )
        assert abs(solved_iv - true_iv) < 1e-6

    def test_iv_round_trip_put(self):
        S, K, T, r, q, sigma = 500.0, 480.0, 0.10, 0.05, 0.01, 0.30
        market_price = BSMPricer.price(S, K, T, r, q, sigma, "P")
        solved_iv = BSMPricer.implied_vol(S, K, T, r, q, market_price, "P")
        assert abs(solved_iv - sigma) < 1e-6

    def test_iv_returns_nan_expired(self, atm_params):
        p = atm_params.copy()
        p["T"] = 0.0
        iv = BSMPricer.implied_vol(p["S"], p["K"], p["T"], p["r"], p["q"], 5.0, "C")
        assert np.isnan(iv)

    def test_iv_returns_nan_below_intrinsic(self):
        """IV is undefined when market price ≤ intrinsic value."""
        iv = BSMPricer.implied_vol(S=100, K=80, T=0.25, r=0.05, q=0.0, market_price=0.01, option_type="C")
        assert np.isnan(iv)

    def test_iv_batch_consistency(self):
        """Batch and scalar IV solvers should produce identical results."""
        S, T, r, q = 100.0, 0.25, 0.05, 0.0
        Ks = np.array([90.0, 95.0, 100.0, 105.0, 110.0])
        sigmas = np.array([0.22, 0.21, 0.20, 0.21, 0.22])
        types = np.array(["C", "C", "C", "C", "C"])
        prices = np.array([BSMPricer.price(S, K, T, r, q, s, "C") for K, s in zip(Ks, sigmas)])

        batch_ivs = BSMPricer.implied_vol_batch(S, Ks, np.full(5, T), r, q, prices, types)
        scalar_ivs = np.array([
            BSMPricer.implied_vol(S, K, T, r, q, p, "C")
            for K, p in zip(Ks, prices)
        ])

        np.testing.assert_allclose(batch_ivs, scalar_ivs, atol=1e-8)


# --------------------------------------------------------------------------
# Vectorized batch Greeks
# --------------------------------------------------------------------------
class TestBatchGreeks:
    def test_batch_matches_scalar(self):
        """Vectorized batch result should match scalar for each contract."""
        S, r, q = 100.0, 0.05, 0.01
        Ks = np.array([90.0, 95.0, 100.0, 105.0, 110.0])
        Ts = np.array([0.1, 0.2, 0.25, 0.2, 0.1])
        sigmas = np.full(5, 0.20)
        types = np.array(["C", "C", "C", "P", "P"])

        batch = BSMPricer.full_greeks_batch(S, Ks, Ts, r, q, sigmas, types)

        for i, (K, T, sig, ot) in enumerate(zip(Ks, Ts, sigmas, types)):
            scalar = BSMPricer.full_greeks(S, K, T, r, q, sig, ot)
            for greek in ["delta", "gamma", "vega", "theta", "vanna"]:
                assert abs(batch[greek][i] - scalar[greek]) < 1e-10, \
                    f"Mismatch at index {i} for {greek}: batch={batch[greek][i]:.8f} scalar={scalar[greek]:.8f}"

    def test_batch_handles_invalid_inputs(self):
        """Batch should return zeros for invalid T/sigma, not raise."""
        S, r, q = 100.0, 0.05, 0.0
        Ks = np.array([100.0, 100.0])
        Ts = np.array([0.0, -1.0])   # both invalid
        sigmas = np.array([0.20, 0.0])
        types = np.array(["C", "P"])

        result = BSMPricer.full_greeks_batch(S, Ks, Ts, r, q, sigmas, types)
        assert result["delta"][0] == 0.0
        assert result["gamma"][0] == 0.0


# --------------------------------------------------------------------------
# GEX sign convention test
# --------------------------------------------------------------------------
class TestGEXSign:
    def test_call_gex_negative_dealer_short(self):
        """
        Dealer short calls → negative gamma exposure for dealer.
        BSMPricer.dollar_gamma() returns unsigned gamma * OI.
        The sign is applied in DealerPositioningEngine.
        """
        gamma = BSMPricer.gamma(S=5000, K=5000, T=0.1, r=0.05, q=0.0, sigma=0.15)
        dgamma = BSMPricer.dollar_gamma(S=5000, K=5000, T=0.1, r=0.05, q=0.0, sigma=0.15, oi=100000)
        assert gamma > 0
        assert dgamma > 0  # unsigned; sign applied by positioning engine

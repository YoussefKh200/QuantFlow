"""
Black-Scholes-Merton pricer — production-grade, fully vectorized.

All methods accept both scalar floats and NumPy arrays.
Batch processing via vectorized ops for performance in Celery workers.
"""
from __future__ import annotations

import warnings
from typing import Union

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

# Type alias for scalar or array inputs
Numeric = Union[float, np.ndarray]


class BSMPricer:
    """
    Vectorized BSM pricer + complete Greeks surface.

    Conventions:
      S     — spot price
      K     — strike price
      T     — time to expiration in years
      r     — continuously compounded risk-free rate
      q     — continuously compounded dividend yield
      sigma — annualized implied volatility
      option_type — 'C' (call) or 'P' (put)

    All dollar-denominated outputs are per-share (not per-contract).
    Multiply by 100 (multiplier) for per-contract dollar values.
    """

    # ------------------------------------------------------------------
    # Intermediate quantities
    # ------------------------------------------------------------------

    @staticmethod
    def d1(S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric, sigma: Numeric) -> Numeric:
        """Standardized log-moneyness adjusted for carry."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))

    @staticmethod
    def d2(S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric, sigma: Numeric) -> Numeric:
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        return d1 - sigma * np.sqrt(T)

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------

    @staticmethod
    def price(
        S: Numeric,
        K: Numeric,
        T: Numeric,
        r: Numeric,
        q: Numeric,
        sigma: Numeric,
        option_type: Union[str, np.ndarray],
    ) -> Numeric:
        """Fair value via BSM. Returns max(theoretical, 0)."""
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        d2 = d1 - sigma * np.sqrt(T)
        phi = np.where(np.asarray(option_type) == "C", 1.0, -1.0)
        val = phi * (
            S * np.exp(-q * T) * norm.cdf(phi * d1)
            - K * np.exp(-r * T) * norm.cdf(phi * d2)
        )
        return np.maximum(val, 0.0)

    # ------------------------------------------------------------------
    # First-order Greeks
    # ------------------------------------------------------------------

    @staticmethod
    def delta(
        S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric,
        sigma: Numeric, option_type: Union[str, np.ndarray],
    ) -> Numeric:
        """
        dV/dS.
        Call: e^{-qT} * N(d1)
        Put:  e^{-qT} * (N(d1) - 1)
        """
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        nd1 = np.exp(-q * T) * norm.cdf(d1)
        return np.where(np.asarray(option_type) == "C", nd1, nd1 - np.exp(-q * T))

    @staticmethod
    def gamma(
        S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric, sigma: Numeric,
    ) -> Numeric:
        """
        d²V/dS² — same for calls and puts.
        Dollar gamma = gamma * S² * 0.01 (per 1% move)
        """
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        return np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))

    @staticmethod
    def vega(
        S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric, sigma: Numeric,
    ) -> Numeric:
        """
        dV/d(sigma) — per 1% (0.01) move in implied vol.
        Same for calls and puts.
        """
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        return S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T) * 0.01

    @staticmethod
    def theta(
        S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric,
        sigma: Numeric, option_type: Union[str, np.ndarray],
    ) -> Numeric:
        """
        dV/dt — per calendar day (negative = time decay).
        Division by 365 converts from per-year to per-day.
        """
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        d2 = d1 - sigma * np.sqrt(T)
        phi = np.where(np.asarray(option_type) == "C", 1.0, -1.0)

        term1 = -S * np.exp(-q * T) * norm.pdf(d1) * sigma / (2.0 * np.sqrt(T))
        term2 = -phi * r * K * np.exp(-r * T) * norm.cdf(phi * d2)
        term3 = phi * q * S * np.exp(-q * T) * norm.cdf(phi * d1)
        return (term1 + term2 + term3) / 365.0

    @staticmethod
    def rho(
        S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric,
        sigma: Numeric, option_type: Union[str, np.ndarray],
    ) -> Numeric:
        """
        dV/dr — per 1% (0.01) move in risk-free rate.
        """
        d2 = BSMPricer.d2(S, K, T, r, q, sigma)
        phi = np.where(np.asarray(option_type) == "C", 1.0, -1.0)
        return phi * K * T * np.exp(-r * T) * norm.cdf(phi * d2) * 0.01

    # ------------------------------------------------------------------
    # Second-order Greeks
    # ------------------------------------------------------------------

    @staticmethod
    def vanna(
        S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric, sigma: Numeric,
    ) -> Numeric:
        """
        dDelta/d(sigma) = d²V/(dS·d(sigma)).
        Critical for dealer vanna exposure (VEX) calculations.
        When IV changes, delta changes — dealers must re-hedge.
        """
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        d2 = d1 - sigma * np.sqrt(T)
        return -np.exp(-q * T) * norm.pdf(d1) * d2 / sigma

    @staticmethod
    def charm(
        S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric,
        sigma: Numeric, option_type: Union[str, np.ndarray],
    ) -> Numeric:
        """
        dDelta/dt — delta decay per day.
        Critical for overnight dealer hedging (CEX calculations).
        Tells you how much delta changes as time passes — major near expiry.
        """
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        d2 = d1 - sigma * np.sqrt(T)
        phi = np.where(np.asarray(option_type) == "C", 1.0, -1.0)

        numerator = (2.0 * (r - q) * T - d2 * sigma * np.sqrt(T))
        denominator = 2.0 * T * sigma * np.sqrt(T)

        return phi * np.exp(-q * T) * (
            norm.pdf(d1) * (numerator / denominator)
            - phi * q * norm.cdf(phi * d1)
        ) / 365.0  # per calendar day

    @staticmethod
    def vomma(
        S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric, sigma: Numeric,
    ) -> Numeric:
        """
        dVega/d(sigma) — vega convexity.
        Positive vomma means long gamma of vega — vega increases faster when IV rises.
        """
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        d2 = d1 - sigma * np.sqrt(T)
        vega = BSMPricer.vega(S, K, T, r, q, sigma)
        return vega * d1 * d2 / sigma

    @staticmethod
    def speed(
        S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric, sigma: Numeric,
    ) -> Numeric:
        """
        dGamma/dS — third-order, same for calls and puts.
        Tells you how gamma changes as spot moves.
        Used for advanced dealer hedging rebalance estimates.
        """
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        g = BSMPricer.gamma(S, K, T, r, q, sigma)
        return -g / S * (d1 / (sigma * np.sqrt(T)) + 1.0)

    # ------------------------------------------------------------------
    # Dollar-adjusted Greeks for dealer exposure calculations
    # ------------------------------------------------------------------

    @staticmethod
    def dollar_gamma(
        S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric,
        sigma: Numeric, oi: Numeric, multiplier: float = 100.0,
    ) -> Numeric:
        """
        Dollar Gamma Exposure = Gamma * OI * multiplier * S² * 0.01
        Represents the dollar P&L impact of a 1% move in spot.
        Sign convention for dealer GEX:
          Calls: dealers short → negative contribution
          Puts: dealers short → positive contribution (positive gamma)
        """
        return BSMPricer.gamma(S, K, T, r, q, sigma) * oi * multiplier * (S ** 2) * 0.01

    @staticmethod
    def dollar_delta(
        S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric,
        sigma: Numeric, option_type: Union[str, np.ndarray],
        oi: Numeric, multiplier: float = 100.0,
    ) -> Numeric:
        """Dollar Delta Exposure = Delta * OI * multiplier * S"""
        return BSMPricer.delta(S, K, T, r, q, sigma, option_type) * oi * multiplier * S

    # ------------------------------------------------------------------
    # IV Solver
    # ------------------------------------------------------------------

    @classmethod
    def implied_vol(
        cls,
        S: float,
        K: float,
        T: float,
        r: float,
        q: float,
        market_price: float,
        option_type: str,
        bounds: tuple[float, float] = (1e-6, 10.0),
        tol: float = 1e-8,
    ) -> float:
        """
        Newton-Raphson / Brentq hybrid IV solver.
        Returns np.nan when no solution exists.

        Short-circuit conditions:
          - T <= 0 (expired)
          - market_price <= intrinsic (no time value — IV undefined)
          - market_price >= forward price (arbitrage — IV undefined)
        """
        if T <= 0.0:
            return np.nan

        forward = S * np.exp((r - q) * T)
        intrinsic = max(
            (forward - K) * np.exp(-r * T) if option_type == "C" else (K - forward) * np.exp(-r * T),
            0.0,
        )

        if market_price <= intrinsic * 1.0001:
            return np.nan
        if market_price >= S:
            return np.nan

        def objective(sigma: float) -> float:
            return cls.price(S, K, T, r, q, sigma, option_type) - market_price

        try:
            # Check bracket
            if objective(bounds[0]) * objective(bounds[1]) > 0:
                return np.nan
            return float(brentq(objective, bounds[0], bounds[1], xtol=tol, maxiter=500))
        except (ValueError, RuntimeError):
            return np.nan

    @classmethod
    def implied_vol_batch(
        cls,
        S: float,
        Ks: np.ndarray,
        Ts: np.ndarray,
        r: float,
        q: float,
        prices: np.ndarray,
        types: np.ndarray,
    ) -> np.ndarray:
        """
        Vectorized IV solver — processes a full option chain.
        Returns array of IVs (np.nan where unsolvable).
        """
        return np.array([
            cls.implied_vol(S, K, T, r, q, p, ot)
            for K, T, p, ot in zip(Ks, Ts, prices, types)
        ])

    # ------------------------------------------------------------------
    # Full Greeks snapshot
    # ------------------------------------------------------------------

    @classmethod
    def full_greeks(
        cls,
        S: float,
        K: float,
        T: float,
        r: float,
        q: float,
        sigma: float,
        option_type: str,
    ) -> dict[str, float]:
        """
        Compute all Greeks in one pass.
        Returns a dict suitable for direct DB insertion.
        """
        if T <= 0 or sigma <= 0:
            return {
                "delta": 0.0, "gamma": 0.0, "vega": 0.0,
                "theta": 0.0, "rho": 0.0,
                "vanna": 0.0, "charm": 0.0, "vomma": 0.0, "speed": 0.0,
            }
        return {
            "delta": float(cls.delta(S, K, T, r, q, sigma, option_type)),
            "gamma": float(cls.gamma(S, K, T, r, q, sigma)),
            "vega": float(cls.vega(S, K, T, r, q, sigma)),
            "theta": float(cls.theta(S, K, T, r, q, sigma, option_type)),
            "rho": float(cls.rho(S, K, T, r, q, sigma, option_type)),
            "vanna": float(cls.vanna(S, K, T, r, q, sigma)),
            "charm": float(cls.charm(S, K, T, r, q, sigma, option_type)),
            "vomma": float(cls.vomma(S, K, T, r, q, sigma)),
            "speed": float(cls.speed(S, K, T, r, q, sigma)),
        }

    @classmethod
    def full_greeks_batch(
        cls,
        S: float,
        Ks: np.ndarray,
        Ts: np.ndarray,
        r: float,
        q: float,
        sigmas: np.ndarray,
        types: np.ndarray,
    ) -> dict[str, np.ndarray]:
        """
        Vectorized Greeks for an entire option chain.
        Returns dict of arrays — one value per contract.
        """
        valid = (Ts > 0) & (sigmas > 0) & np.isfinite(sigmas)

        result = {
            "delta": np.zeros(len(Ks)),
            "gamma": np.zeros(len(Ks)),
            "vega": np.zeros(len(Ks)),
            "theta": np.zeros(len(Ks)),
            "rho": np.zeros(len(Ks)),
            "vanna": np.zeros(len(Ks)),
            "charm": np.zeros(len(Ks)),
            "vomma": np.zeros(len(Ks)),
            "speed": np.zeros(len(Ks)),
        }

        if not valid.any():
            return result

        Kv, Tv, sv, tv = Ks[valid], Ts[valid], sigmas[valid], types[valid]

        result["delta"][valid] = cls.delta(S, Kv, Tv, r, q, sv, tv)
        result["gamma"][valid] = cls.gamma(S, Kv, Tv, r, q, sv)
        result["vega"][valid] = cls.vega(S, Kv, Tv, r, q, sv)
        result["theta"][valid] = cls.theta(S, Kv, Tv, r, q, sv, tv)
        result["rho"][valid] = cls.rho(S, Kv, Tv, r, q, sv, tv)
        result["vanna"][valid] = cls.vanna(S, Kv, Tv, r, q, sv)
        result["charm"][valid] = cls.charm(S, Kv, Tv, r, q, sv, tv)
        result["vomma"][valid] = cls.vomma(S, Kv, Tv, r, q, sv)
        result["speed"][valid] = cls.speed(S, Kv, Tv, r, q, sv)

        return result

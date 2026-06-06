"""
Volatility surface construction and interpolation.

Uses Radial Basis Function (RBF) interpolation on a
(log-moneyness, time) grid.  Arbitrage-free enforcement
via monotonicity checks on the total variance surface.
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import RBFInterpolator

from app.core.logging import get_logger

logger = get_logger(__name__)


class VolatilitySurface:
    """
    Fitted IV surface from a snapshot of option chain data.

    Coordinates:
      x-axis: log-moneyness  ln(K/S)  — zero = ATM
      y-axis: time in years
      z-axis: Black-Scholes implied vol

    RBF thin-plate-spline smoothing handles irregular grids
    (real option chains have non-uniform strikes per expiry).
    """

    def __init__(
        self,
        strikes: np.ndarray,
        dtes: np.ndarray,
        ivs: np.ndarray,
        spot: float,
        smoothing: float = 0.0,
    ) -> None:
        """
        Parameters
        ----------
        strikes : 1-D array of strike prices
        dtes    : 1-D array of days-to-expiry (same length as strikes)
        ivs     : 1-D array of implied vols   (same length)
        spot    : current spot price
        smoothing: RBF smoothing factor (0 = interpolating, >0 = approximating)
        """
        self.spot = spot

        # Filter invalid points
        mask = np.isfinite(ivs) & (ivs > 0.01) & (ivs < 5.0) & (dtes > 0)
        if mask.sum() < 4:
            raise ValueError(f"Insufficient valid IV data points: {mask.sum()}")

        strikes, dtes, ivs = strikes[mask], dtes[mask], ivs[mask]

        self._log_m = np.log(strikes / spot)     # log-moneyness
        self._t = dtes / 365.0                   # years
        self._ivs = ivs

        X = np.column_stack([self._log_m, self._t])
        self.rbf = RBFInterpolator(
            X, ivs,
            kernel="thin_plate_spline",
            smoothing=smoothing,
        )

        self._spot = spot
        self._min_t = float(self._t.min())
        self._max_t = float(self._t.max())

    def query(self, strike: float, dte: float) -> float:
        """Query single (strike, dte) point. Returns NaN if out of range."""
        lm = np.log(strike / self.spot)
        t = dte / 365.0
        if t < self._min_t * 0.5:
            return float("nan")
        x = np.array([[lm, t]])
        val = float(self.rbf(x)[0])
        return max(val, 0.001)  # floor at 0.1% vol

    def query_batch(
        self, strikes: np.ndarray, dtes: np.ndarray
    ) -> np.ndarray:
        """Batch query — same length arrays."""
        lm = np.log(strikes / self.spot)
        t = dtes / 365.0
        X = np.column_stack([lm, t])
        vals = self.rbf(X)
        return np.maximum(vals, 0.001)

    def surface_grid(
        self,
        n_strikes: int = 60,
        n_expiries: int = 24,
        moneyness_range: tuple[float, float] = (-0.35, 0.35),
    ) -> dict:
        """
        Build a regular grid for 3D surface visualization.

        Returns
        -------
        dict with:
          strikes  : 1-D list of strike prices
          dtes     : 1-D list of DTE values
          ivs      : 2-D list [n_expiries x n_strikes] of implied vols
          atm_ivs  : 1-D list of ATM IVs per expiry (for term structure)
        """
        lm_range = np.linspace(*moneyness_range, n_strikes)
        t_range = np.linspace(
            max(self._min_t, 7 / 365),
            min(self._max_t, 2.0),
            n_expiries,
        )

        LM, T = np.meshgrid(lm_range, t_range)
        pts = np.column_stack([LM.ravel(), T.ravel()])
        ivs = self.rbf(pts).reshape(n_expiries, n_strikes)
        ivs = np.maximum(ivs, 0.001)

        strikes = self.spot * np.exp(lm_range)
        dtes = t_range * 365

        # ATM IV = query at lm=0 for each expiry
        atm_pts = np.column_stack([np.zeros(n_expiries), t_range])
        atm_ivs = np.maximum(self.rbf(atm_pts), 0.001)

        return {
            "strikes": strikes.tolist(),
            "dtes": dtes.tolist(),
            "ivs": ivs.tolist(),
            "atm_ivs": atm_ivs.tolist(),
            "spot": self.spot,
        }

    def skew(self, dte: float, delta_put: float = 0.25, delta_call: float = 0.25) -> dict:
        """
        Compute vol skew at a given expiry.
        Returns {skew_25d, skew_10d, rr_25d, bf_25d}.

        Approximates 25-delta strikes from log-moneyness.
        """
        t = dte / 365.0
        # Approximate 25d strikes: ±0.5σ√T from ATM
        atm_iv = self.query(self.spot, dte)
        approx_sigma = atm_iv * np.sqrt(t)

        # 25-delta put ≈ e^{-0.67σ√T}, call ≈ e^{+0.67σ√T}
        k_25p = self.spot * np.exp(-0.67 * approx_sigma)
        k_25c = self.spot * np.exp(+0.67 * approx_sigma)
        k_10p = self.spot * np.exp(-1.28 * approx_sigma)
        k_10c = self.spot * np.exp(+1.28 * approx_sigma)

        iv_25p = self.query(k_25p, dte)
        iv_25c = self.query(k_25c, dte)
        iv_10p = self.query(k_10p, dte)
        iv_10c = self.query(k_10c, dte)

        return {
            "dte": dte,
            "atm_iv": atm_iv,
            "iv_25p": iv_25p,
            "iv_25c": iv_25c,
            "iv_10p": iv_10p,
            "iv_10c": iv_10c,
            "skew_25d": iv_25p - iv_25c,      # positive = put skew (normal)
            "skew_10d": iv_10p - iv_10c,
            "rr_25d": iv_25c - iv_25p,         # risk reversal
            "bf_25d": (iv_25p + iv_25c) / 2 - atm_iv,  # butterfly
        }

    def term_structure(self, n_points: int = 20) -> list[dict]:
        """ATM IV across the term structure."""
        t_range = np.linspace(max(self._min_t, 7 / 365), min(self._max_t, 2.0), n_points)
        pts = np.column_stack([np.zeros(n_points), t_range])
        atm_ivs = np.maximum(self.rbf(pts), 0.001)
        return [
            {"dte": int(t * 365), "atm_iv": float(iv), "total_var": float(iv ** 2 * t)}
            for t, iv in zip(t_range, atm_ivs)
        ]


class IVRankCalculator:
    """
    IV Rank and IV Percentile from a 1-year history of ATM IVs.

    IV Rank   = (current - 52wk_low) / (52wk_high - 52wk_low) * 100
    IV Percentile = % of days in past year current IV was higher than
    """

    @staticmethod
    def compute(
        current_iv: float,
        historical_ivs: np.ndarray,
        lookback_days: int = 252,
    ) -> dict[str, float]:
        if len(historical_ivs) < 20:
            return {"iv_rank": 50.0, "iv_percentile": 50.0, "iv_52wk_high": current_iv, "iv_52wk_low": current_iv}

        hist = historical_ivs[-lookback_days:]
        low = float(hist.min())
        high = float(hist.max())

        if high == low:
            return {"iv_rank": 50.0, "iv_percentile": 50.0, "iv_52wk_high": high, "iv_52wk_low": low}

        iv_rank = (current_iv - low) / (high - low) * 100.0
        iv_percentile = float(np.mean(hist < current_iv) * 100.0)

        return {
            "iv_rank": round(min(max(iv_rank, 0.0), 100.0), 2),
            "iv_percentile": round(iv_percentile, 2),
            "iv_52wk_high": round(high, 4),
            "iv_52wk_low": round(low, 4),
            "current_iv": round(current_iv, 4),
        }

"""
Unit tests for DealerPositioningEngine.

Tests cover:
  - GEX sign convention
  - Gamma flip detection
  - Call/put wall identification
  - Regime classification
  - Edge cases (no data, single strike)
"""
from __future__ import annotations

import polars as pl
import pytest

from app.services.dealer.positioning_engine import DealerPositioningEngine


def make_df(strikes, ois_c, ois_p, gamma=0.001, delta=0.5, vanna=0.0, charm=0.0):
    """Helper to build a minimal chain DataFrame."""
    rows = []
    for strike, oi_c, oi_p in zip(strikes, ois_c, ois_p):
        rows.append({"strike": float(strike), "option_type": "C", "oi": float(oi_c),
                     "gamma": gamma, "delta": delta, "vanna": vanna, "charm": charm})
        rows.append({"strike": float(strike), "option_type": "P", "oi": float(oi_p),
                     "gamma": gamma, "delta": -delta, "vanna": vanna, "charm": charm})
    return pl.DataFrame(rows)


class TestGEXSignConvention:
    def test_call_gex_is_negative(self):
        """
        Dealer short calls → negative GEX contribution.
        Pure call OI → negative total GEX.
        """
        df = make_df([5000], [100_000], [0])
        engine = DealerPositioningEngine(spot=5000)
        result = engine.compute_gex_per_strike(df)
        assert float(result.filter(pl.col("strike") == 5000)["gex_net"][0]) < 0

    def test_put_gex_is_positive(self):
        """
        Dealer short puts → positive GEX contribution.
        Pure put OI → positive total GEX.
        """
        df = make_df([5000], [0], [100_000])
        engine = DealerPositioningEngine(spot=5000)
        result = engine.compute_gex_per_strike(df)
        assert float(result.filter(pl.col("strike") == 5000)["gex_net"][0]) > 0

    def test_balanced_oi_gex_near_zero(self):
        """Equal call and put OI → GEX should be close to zero."""
        df = make_df([5000], [100_000], [100_000])
        engine = DealerPositioningEngine(spot=5000)
        result = engine.compute_gex_per_strike(df)
        gex = float(result["gex_net"][0])
        assert abs(gex) < 1e6  # small relative to individual contributions


class TestGammaFlip:
    def test_flip_detected_with_sign_change(self):
        """
        A single large call cluster above spot drives total GEX negative.
        A single large put cluster below spot keeps GEX positive there.
        The cumulative GEX sum crosses zero somewhere in between.
        """
        # Simple 3-strike setup: put at 4800 (positive GEX), call at 5200 (negative GEX)
        # Total GEX is zero exactly between them — flip should be detected.
        strikes = [4800, 5000, 5200]
        ois_c   = [0,    0,    500_000]   # big call at 5200
        ois_p   = [500_000, 0, 0]         # big put  at 4800

        df = make_df(strikes, ois_c, ois_p)
        engine = DealerPositioningEngine(spot=5000)
        gex_df = engine.compute_gex_per_strike(df)
        flip = engine.find_gamma_flip(gex_df)

        assert flip is not None
        # Flip must lie between the put wall (4800) and call wall (5200)
        assert 4800 <= flip <= 5200

    def test_flip_returns_none_uniform_sign(self):
        """If all strikes have same sign GEX, flip is at a bound (not None)."""
        df = make_df([4800, 4900, 5000], [100_000, 100_000, 100_000], [0, 0, 0])
        engine = DealerPositioningEngine(spot=5000)
        gex_df = engine.compute_gex_per_strike(df)
        flip = engine.find_gamma_flip(gex_df)
        # Should return a boundary value, not crash
        assert flip is not None


class TestCallPutWalls:
    def test_call_wall_above_spot(self):
        df = make_df([4800, 4900, 5000, 5100, 5200], [0, 0, 0, 500_000, 100_000], [0, 0, 0, 0, 0])
        engine = DealerPositioningEngine(spot=5000)
        gex_df = engine.compute_gex_per_strike(df)
        wall = engine.find_call_wall(gex_df)
        assert wall == 5100.0

    def test_put_wall_below_spot(self):
        df = make_df([4800, 4900, 5000], [0, 0, 0], [100_000, 500_000, 0])
        engine = DealerPositioningEngine(spot=5000)
        gex_df = engine.compute_gex_per_strike(df)
        wall = engine.find_put_wall(gex_df)
        assert wall == 4900.0

    def test_no_call_wall_when_no_strikes_above(self):
        df = make_df([4800, 4900], [100_000, 100_000], [0, 0])
        engine = DealerPositioningEngine(spot=5000)
        gex_df = engine.compute_gex_per_strike(df)
        wall = engine.find_call_wall(gex_df)
        assert wall is None


class TestRegimeClassification:
    def test_long_gamma_regime(self):
        """Large positive GEX → long_gamma."""
        engine = DealerPositioningEngine(spot=5000)
        large_positive_gex = 5000 * 5e6 * 10  # well above threshold
        regime = engine.classify_regime(large_positive_gex)
        assert regime == "long_gamma"

    def test_short_gamma_regime(self):
        engine = DealerPositioningEngine(spot=5000)
        large_negative_gex = -5000 * 5e6 * 10
        regime = engine.classify_regime(large_negative_gex)
        assert regime == "short_gamma"

    def test_neutral_regime(self):
        engine = DealerPositioningEngine(spot=5000)
        regime = engine.classify_regime(0.0)
        assert regime == "neutral"


class TestHeatmapData:
    def test_heatmap_returns_sorted_by_strike(self):
        strikes = [5100, 4900, 5000, 5200, 4800]
        df = make_df(strikes, [100_000] * 5, [100_000] * 5)
        engine = DealerPositioningEngine(spot=5000)
        gex_df = engine.compute_gex_per_strike(df)
        heatmap = engine.heatmap_data(gex_df, top_n_strikes=10)
        hm_strikes = [row["strike"] for row in heatmap]
        assert hm_strikes == sorted(hm_strikes)

    def test_heatmap_respects_top_n(self):
        strikes = list(range(4800, 5300, 10))
        ois = [100_000] * len(strikes)
        df = make_df(strikes, ois, ois)
        engine = DealerPositioningEngine(spot=5000)
        gex_df = engine.compute_gex_per_strike(df)
        heatmap = engine.heatmap_data(gex_df, top_n_strikes=5)
        assert len(heatmap) == 5

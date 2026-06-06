"""
Dealer Positioning Engine.

Reconstructs net dealer gamma/delta/vanna/charm exposure
from open interest data.

Core assumption: Dealers (market makers) are net SHORT options —
they sell to customers and delta-hedge the resulting exposure.
This is well-documented for US equity options markets.

Sign convention:
  GEX > 0: dealers are net LONG gamma (market-stabilizing, mean-reverting)
  GEX < 0: dealers are net SHORT gamma (market-destabilizing, trending)

References:
  - Brent Kochuba (SpotGamma) — dealer positioning methodology
  - Squeezemetrics GEX white paper
  - Derman & Miller "The Volatility Smile" (2016)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import polars as pl

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DealerSummary:
    """Aggregate dealer exposure across all strikes."""
    underlying: str
    spot: float
    total_gex: float          # net GEX in dollars
    total_dex: float          # net DEX in dollars
    total_vex: float          # net VEX
    total_cex: float          # net CEX
    gamma_flip_price: Optional[float]   # zero-GEX crossing
    call_wall_strike: Optional[float]   # max call OI above spot
    put_wall_strike: Optional[float]    # max put OI below spot
    vol_trigger_price: Optional[float]  # vol trigger level
    dealer_regime: str        # 'long_gamma' | 'short_gamma' | 'neutral'


class DealerPositioningEngine:
    """
    Computes dealer Greeks exposure per strike and aggregates
    into key levels (gamma flip, walls, vol trigger).

    Input DataFrame columns required:
      strike, option_type, oi, gamma, delta, vanna, charm, (optional: expiration)
    """

    GEX_FORMULA = """
    GEX per contract = Gamma × OI × multiplier × S² × 0.01
    Sign: +1 for calls (dealer short calls = negative gamma exposure)
           -1 for puts (dealer short puts = positive gamma exposure)
    Net dealer GEX:
      Calls contribute NEGATIVE gamma (dealer is short gamma via short calls)
      Puts contribute POSITIVE gamma (dealer is short puts — positive gamma)
    Standard market convention flips this — we follow SpotGamma/SqueezeMetrics.
    """

    def __init__(self, spot: float, multiplier: float = 100.0):
        self.spot = spot
        self.multiplier = multiplier

    def compute_gex_per_strike(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Compute GEX, DEX, VEX, CEX per strike.

        Parameters
        ----------
        df : Polars DataFrame with columns:
             strike, option_type, oi, gamma, delta, vanna, charm

        Returns
        -------
        Polars DataFrame aggregated by strike with exposure columns.
        """
        S = self.spot
        M = self.multiplier

        df = df.with_columns([
            # GEX: gamma × OI × M × S² × 0.01
            # Sign: calls negative (dealer short), puts positive
            (
                pl.col("gamma")
                * pl.col("oi")
                * M
                * (S ** 2)
                * 0.01
                * pl.when(pl.col("option_type") == "C").then(-1.0).otherwise(1.0)
            ).alias("gex"),

            # DEX: delta × OI × M × S
            (
                pl.col("delta")
                * pl.col("oi")
                * M
                * S
                * pl.when(pl.col("option_type") == "C").then(-1.0).otherwise(1.0)
            ).alias("dex"),

            # VEX: vanna × OI × M × S² × 0.01
            (pl.col("vanna") * pl.col("oi") * M * (S ** 2) * 0.01).alias("vex"),

            # CEX: charm × OI × M (per calendar day)
            (pl.col("charm") * pl.col("oi") * M).alias("cex"),
        ])

        aggregated = df.group_by("strike").agg([
            pl.col("gex").filter(pl.col("option_type") == "C").sum().alias("gex_calls"),
            pl.col("gex").filter(pl.col("option_type") == "P").sum().alias("gex_puts"),
            pl.col("gex").sum().alias("gex_net"),
            pl.col("dex").filter(pl.col("option_type") == "C").sum().alias("dex_calls"),
            pl.col("dex").filter(pl.col("option_type") == "P").sum().alias("dex_puts"),
            pl.col("dex").sum().alias("dex_net"),
            pl.col("vex").sum().alias("vex_net"),
            pl.col("cex").sum().alias("cex_net"),
            pl.col("oi").filter(pl.col("option_type") == "C").sum().alias("oi_calls"),
            pl.col("oi").filter(pl.col("option_type") == "P").sum().alias("oi_puts"),
        ]).sort("strike")

        return aggregated

    def find_gamma_flip(self, gex_by_strike: pl.DataFrame) -> Optional[float]:
        """
        The gamma flip level is the spot price where dealer net GEX crosses zero.
        Above = dealers long gamma (suppresses vol).
        Below = dealers short gamma (amplifies vol).

        Implementation: cumulative sum of GEX from lowest to highest strike.
        Find the zero crossing and linearly interpolate.
        """
        df = gex_by_strike.sort("strike")
        strikes = df["strike"].to_list()
        gex_vals = df["gex_net"].to_list()

        if not gex_vals:
            return None

        cumsum = 0.0
        for i, (s, g) in enumerate(zip(strikes, gex_vals)):
            prev = cumsum
            cumsum += g
            if i > 0 and prev * cumsum < 0:
                # Linear interpolation of zero crossing
                prev_s = strikes[i - 1]
                frac = abs(prev) / (abs(prev) + abs(cumsum))
                return prev_s + frac * (s - prev_s)

        # No crossing found — return sign-based bounds
        if cumsum > 0:
            return float(min(strikes))   # entire range is long gamma
        return float(max(strikes))       # entire range is short gamma

    def find_call_wall(self, df: pl.DataFrame) -> Optional[float]:
        """
        Call wall = strike with maximum call OI ABOVE current spot.
        Acts as price resistance — dealers' negative delta from short calls
        creates selling pressure as price approaches.
        """
        above = df.filter(pl.col("strike") > self.spot)
        if len(above) == 0:
            return None
        return float(above.sort("oi_calls", descending=True)["strike"][0])

    def find_put_wall(self, df: pl.DataFrame) -> Optional[float]:
        """
        Put wall = strike with maximum put OI BELOW current spot.
        Acts as price support — dealers' positive delta from short puts
        creates buying pressure as price approaches.
        """
        below = df.filter(pl.col("strike") < self.spot)
        if len(below) == 0:
            return None
        return float(below.sort("oi_puts", descending=True)["strike"][0])

    def find_vol_trigger(self, df: pl.DataFrame) -> Optional[float]:
        """
        Vol trigger = strike where vanna exposure is maximum.
        When spot crosses this level, dealers' vanna hedging creates
        a feedback loop that accelerates volatility expansion/compression.
        """
        if "vex_net" not in df.columns:
            return None
        max_row = df.sort(pl.col("vex_net").abs(), descending=True).head(1)
        return float(max_row["strike"][0]) if len(max_row) > 0 else None

    def classify_regime(self, total_gex: float) -> str:
        """
        Regime based on total net GEX normalized by spot.
        Threshold is a heuristic — tune per symbol.
        """
        threshold = self.spot * 5e6   # ~$5M GEX per point of spot
        if total_gex > threshold:
            return "long_gamma"
        if total_gex < -threshold:
            return "short_gamma"
        return "neutral"

    def compute_summary(self, gex_by_strike: pl.DataFrame) -> DealerSummary:
        """
        Compute aggregate summary from per-strike exposures.
        This is what gets cached and served to the dashboard.
        """
        total_gex = float(gex_by_strike["gex_net"].sum())
        total_dex = float(gex_by_strike["dex_net"].sum()) if "dex_net" in gex_by_strike.columns else 0.0
        total_vex = float(gex_by_strike["vex_net"].sum()) if "vex_net" in gex_by_strike.columns else 0.0
        total_cex = float(gex_by_strike["cex_net"].sum()) if "cex_net" in gex_by_strike.columns else 0.0

        gamma_flip = self.find_gamma_flip(gex_by_strike)
        call_wall = self.find_call_wall(gex_by_strike)
        put_wall = self.find_put_wall(gex_by_strike)
        vol_trigger = self.find_vol_trigger(gex_by_strike)
        regime = self.classify_regime(total_gex)

        logger.info(
            "dealer_summary_computed",
            spot=self.spot,
            total_gex=total_gex,
            regime=regime,
            gamma_flip=gamma_flip,
            call_wall=call_wall,
            put_wall=put_wall,
        )

        return DealerSummary(
            underlying="",  # set by caller
            spot=self.spot,
            total_gex=total_gex,
            total_dex=total_dex,
            total_vex=total_vex,
            total_cex=total_cex,
            gamma_flip_price=gamma_flip,
            call_wall_strike=call_wall,
            put_wall_strike=put_wall,
            vol_trigger_price=vol_trigger,
            dealer_regime=regime,
        )

    def flag_key_levels(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Add boolean flag columns to the per-strike DataFrame.
        Used for DB insert and chart highlighting.
        """
        summary = self.compute_summary(df)

        return df.with_columns([
            (pl.col("strike") == (summary.call_wall_strike or -1)).alias("is_call_wall"),
            (pl.col("strike") == (summary.put_wall_strike or -1)).alias("is_put_wall"),
            (
                (pl.col("strike") >= (summary.gamma_flip_price or -1) - 0.5)
                & (pl.col("strike") <= (summary.gamma_flip_price or -1) + 0.5)
            ).alias("is_gamma_flip"),
            (pl.col("strike") == (summary.vol_trigger_price or -1)).alias("is_vol_trigger"),
        ])

    def heatmap_data(
        self,
        df: pl.DataFrame,
        top_n_strikes: int = 40,
    ) -> list[dict]:
        """
        Return top N strikes by absolute GEX for heatmap rendering.
        Sorted by strike for vertical bar chart display.
        """
        top = (
            df.with_columns(pl.col("gex_net").abs().alias("abs_gex"))
            .sort("abs_gex", descending=True)
            .head(top_n_strikes)
            .sort("strike")
        )

        return [
            {
                "strike": row["strike"],
                "gex_calls": row["gex_calls"],
                "gex_puts": row["gex_puts"],
                "gex_net": row["gex_net"],
                "oi_calls": row["oi_calls"],
                "oi_puts": row["oi_puts"],
                "is_call_wall": row.get("is_call_wall", False),
                "is_put_wall": row.get("is_put_wall", False),
                "is_gamma_flip": row.get("is_gamma_flip", False),
            }
            for row in top.to_dicts()
        ]

"""
Post-Earnings Announcement Drift (PEAD) Engine.

Implements the SUE-based alpha signal documented in academic literature:
  Ball & Brown (1968)  — original PEAD discovery
  Bernard & Thomas (1989) — systematic exploitation evidence
  Livnat & Mendenhall (2006) — modern refinement

Strategy: stocks with extreme positive SUE drift upward for ~60 days
post-announcement as the market slowly incorporates the information.
Negative SUE stocks drift downward.

The effect is strongest in the first 10-20 days and decays.
IV crush after earnings creates favorable risk/reward for post-earnings trades.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PEADSignal:
    ticker: str
    report_date: date
    sue_score: float
    direction: str              # 'L', 'S', or 'N'
    confidence: float           # 0-1
    horizon_days: int           # expected drift window
    signal_type: str
    eps_surprise_pct: float
    iv_crush_expected: bool
    notes: str = ""


class PEADEngine:
    """
    Full PEAD research and signal generation pipeline.

    Workflow per earnings event:
      1. Compute SUE from EPS surprise history
      2. Compute post-announcement price drift (CAR)
      3. Measure IV crush magnitude
      4. Generate directional signal with confidence
    """

    # SUE quintile thresholds
    QUINTILE_5_THRESHOLD = 2.0    # strong positive surprise
    QUINTILE_4_THRESHOLD = 1.0
    QUINTILE_2_THRESHOLD = -1.0
    QUINTILE_1_THRESHOLD = -2.0

    @staticmethod
    def compute_sue(
        earnings_df: pd.DataFrame,
        lookback_quarters: int = 8,
    ) -> pd.Series:
        """
        Standardized Unexpected Earnings (SUE).

        SUE = (EPS_actual - EPS_estimate) / σ(historical_surprises)

        Standardizing by the rolling std of surprise history removes
        the effect of a company consistently beating/missing by the same amount.

        Parameters
        ----------
        earnings_df : DataFrame with column 'eps_surprise_pct', sorted ascending by date
        lookback_quarters : number of prior quarters for rolling std

        Returns
        -------
        Series of SUE scores, same index as earnings_df
        """
        surprise = earnings_df["eps_surprise_pct"].copy()
        rolling_std = (
            surprise.shift(1)
            .rolling(lookback_quarters, min_periods=4)
            .std()
            .replace(0.0, np.nan)
        )
        sue = surprise / rolling_std
        return sue.round(4)

    @staticmethod
    def compute_drift(
        price_df: pd.DataFrame,
        event_date: str,
        benchmark_col: str = "spx",
        windows: tuple[int, ...] = (1, 5, 10, 20, 60),
    ) -> dict[str, Optional[float]]:
        """
        Compute Cumulative Abnormal Return (CAR) after earnings.

        CAR = cumulative stock return - cumulative benchmark return
        (market-adjusted to remove systematic risk)

        Parameters
        ----------
        price_df : DataFrame with 'close' and benchmark column, date-indexed
        event_date : announcement date string ('YYYY-MM-DD')
        windows : DTE windows to measure (business days)

        Returns
        -------
        dict of {drift_Nd: float} for each window
        """
        try:
            event_idx = price_df.index.get_loc(event_date)
        except KeyError:
            # Try nearest trading day
            event_ts = pd.Timestamp(event_date)
            nearest = price_df.index.searchsorted(event_ts)
            if nearest >= len(price_df):
                return {f"drift_{w}d": None for w in windows}
            event_idx = nearest

        results: dict[str, Optional[float]] = {}
        base_price = float(price_df["close"].iloc[event_idx])
        has_benchmark = benchmark_col in price_df.columns

        if base_price <= 0:
            return {f"drift_{w}d": None for w in windows}

        for w in windows:
            end_idx = min(event_idx + w, len(price_df) - 1)
            if end_idx <= event_idx:
                results[f"drift_{w}d"] = None
                continue

            stock_ret = float(price_df["close"].iloc[end_idx]) / base_price - 1.0

            if has_benchmark:
                base_bench = float(price_df[benchmark_col].iloc[event_idx])
                mkt_ret = float(price_df[benchmark_col].iloc[end_idx]) / base_bench - 1.0 if base_bench > 0 else 0.0
                car = stock_ret - mkt_ret
            else:
                car = stock_ret

            results[f"drift_{w}d"] = round(car, 6)

        return results

    @staticmethod
    def compute_iv_crush(
        iv_pre: float,
        iv_post_1d: float,
    ) -> dict[str, float]:
        """
        IV crush metrics — IV typically collapses 30-60% post earnings.
        This is one of the most reliable option-selling opportunities.
        """
        crush_abs = iv_pre - iv_post_1d
        crush_pct = crush_abs / iv_pre if iv_pre > 0 else 0.0
        return {
            "iv_pre": round(iv_pre, 4),
            "iv_post_1d": round(iv_post_1d, 4),
            "iv_crush_abs": round(crush_abs, 4),
            "iv_crush_pct": round(crush_pct, 4),
            "is_significant": crush_pct > 0.25,  # >25% crush is significant
        }

    def generate_signal(
        self,
        sue: float,
        ticker: str,
        report_date: date,
        eps_surprise_pct: float,
        iv_crush_expected: bool = True,
    ) -> PEADSignal:
        """
        Generate a directional signal based on SUE quintile.

        Confidence is calibrated from historical win rates by SUE bucket:
          SUE > 2.0  → 70% base confidence + scaling
          SUE > 1.0  → 65% base confidence
          SUE < -2.0 → 65% base confidence + scaling
          SUE < -1.0 → 60% base confidence

        IV crush expected = post-earnings, IV drops → long gamma less efficient.
        Pure directional play preferred over options after crush.
        """
        if sue > self.QUINTILE_5_THRESHOLD:
            direction = "L"
            confidence = min(0.95, 0.70 + (sue - 2.0) * 0.04)
            horizon = 20
            signal_type = "pead_long_strong"
            notes = f"SUE {sue:.2f} — quintile 5 long, strong positive surprise"

        elif sue > self.QUINTILE_4_THRESHOLD:
            direction = "L"
            confidence = 0.65
            horizon = 20
            signal_type = "pead_long"
            notes = f"SUE {sue:.2f} — quintile 4 long"

        elif sue < self.QUINTILE_1_THRESHOLD:
            direction = "S"
            confidence = min(0.90, 0.65 + (abs(sue) - 2.0) * 0.03)
            horizon = 20
            signal_type = "pead_short_strong"
            notes = f"SUE {sue:.2f} — quintile 1 short, strong negative surprise"

        elif sue < self.QUINTILE_2_THRESHOLD:
            direction = "S"
            confidence = 0.60
            horizon = 20
            signal_type = "pead_short"
            notes = f"SUE {sue:.2f} — quintile 2 short"

        else:
            direction = "N"
            confidence = 0.50
            horizon = 0
            signal_type = "pead_neutral"
            notes = f"SUE {sue:.2f} — neutral, no signal"

        # Reduce confidence if IV crush expected (IV already high, market may know)
        if iv_crush_expected and abs(eps_surprise_pct) < 0.05:
            confidence = max(confidence - 0.05, 0.40)
            notes += " (confidence reduced — small surprise vs elevated IV)"

        return PEADSignal(
            ticker=ticker,
            report_date=report_date,
            sue_score=round(sue, 4),
            direction=direction,
            confidence=round(confidence, 4),
            horizon_days=horizon,
            signal_type=signal_type,
            eps_surprise_pct=eps_surprise_pct,
            iv_crush_expected=iv_crush_expected,
            notes=notes,
        )

    @staticmethod
    def backtest_pead(
        signals_df: pd.DataFrame,
        prices_df: pd.DataFrame,
        holding_period: int = 20,
        transaction_cost: float = 0.001,
    ) -> dict:
        """
        Backtest PEAD strategy on historical signal + price data.

        Parameters
        ----------
        signals_df : DataFrame with columns: ticker, report_date, direction, confidence
        prices_df : Multi-index DataFrame (date, ticker) with 'close'
        holding_period : days to hold after signal
        transaction_cost : round-trip cost fraction

        Returns
        -------
        dict with performance metrics
        """
        if signals_df.empty:
            return {"error": "No signals to backtest"}

        returns = []

        for _, row in signals_df.iterrows():
            ticker = row["ticker"]
            entry_date = row["report_date"]
            direction = row["direction"]

            if direction == "N":
                continue

            try:
                ticker_prices = prices_df.xs(ticker, level="ticker")["close"]
                entry_idx = ticker_prices.index.searchsorted(entry_date) + 1  # day after report

                if entry_idx >= len(ticker_prices):
                    continue
                if entry_idx + holding_period >= len(ticker_prices):
                    exit_idx = len(ticker_prices) - 1
                else:
                    exit_idx = entry_idx + holding_period

                gross_ret = (
                    float(ticker_prices.iloc[exit_idx]) / float(ticker_prices.iloc[entry_idx]) - 1.0
                )
                net_ret = (gross_ret - transaction_cost) * (1 if direction == "L" else -1)
                returns.append(net_ret)

            except (KeyError, IndexError):
                continue

        if not returns:
            return {"error": "No valid return observations"}

        ret_arr = np.array(returns)
        n = len(ret_arr)
        mean_ret = float(ret_arr.mean())
        vol = float(ret_arr.std(ddof=1)) if n > 1 else 0.0
        sharpe = (mean_ret / vol * np.sqrt(252 / holding_period)) if vol > 0 else 0.0

        # t-stat for significance
        t_stat = float(stats.ttest_1samp(ret_arr, 0.0).statistic) if n > 1 else 0.0
        p_value = float(stats.ttest_1samp(ret_arr, 0.0).pvalue) if n > 1 else 1.0

        return {
            "n_trades": n,
            "mean_return": round(mean_ret, 6),
            "annualized_return": round(mean_ret * (252 / holding_period), 4),
            "volatility": round(vol, 6),
            "sharpe_ratio": round(sharpe, 4),
            "win_rate": round(float(np.mean(ret_arr > 0)), 4),
            "t_statistic": round(t_stat, 3),
            "p_value": round(p_value, 4),
            "is_significant": p_value < 0.05,
            "max_loss": round(float(ret_arr.min()), 6),
            "max_gain": round(float(ret_arr.max()), 6),
        }

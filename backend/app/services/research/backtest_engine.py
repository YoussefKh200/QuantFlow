"""
Research Lab — Backtesting Engine.

Supports:
  - Event-driven vectorized backtesting
  - Walk-forward optimization (WFO)
  - Monte Carlo permutation testing for significance
  - Full performance metrics suite

Design philosophy: vectorized first, readable second.
NumPy/Pandas throughout — no loops over individual bars.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd
from scipy import stats

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BacktestResult:
    """Complete backtest performance report."""
    strategy_name: str
    start_date: str
    end_date: str
    n_trades: int

    # Returns
    total_return: float
    annualized_return: float
    annualized_vol: float

    # Risk-adjusted
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # Drawdown
    max_drawdown: float
    avg_drawdown: float
    max_drawdown_duration_days: int

    # Trade stats
    win_rate: float
    profit_factor: float
    avg_trade_return: float
    best_trade: float
    worst_trade: float

    # Time series
    equity_curve: list[float] = field(default_factory=list)
    drawdown_series: list[float] = field(default_factory=list)
    trade_log: list[dict] = field(default_factory=list)

    # Significance
    t_statistic: float = 0.0
    p_value: float = 1.0
    is_significant: bool = False

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "n_trades": self.n_trades,
            "total_return": round(self.total_return, 4),
            "annualized_return": round(self.annualized_return, 4),
            "annualized_vol": round(self.annualized_vol, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "calmar_ratio": round(self.calmar_ratio, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 4),
            "avg_trade_return": round(self.avg_trade_return, 6),
            "best_trade": round(self.best_trade, 4),
            "worst_trade": round(self.worst_trade, 4),
            "t_statistic": round(self.t_statistic, 3),
            "p_value": round(self.p_value, 4),
            "is_significant": self.is_significant,
        }


class PerformanceCalculator:
    """
    Standalone performance metrics from a returns series.
    All inputs/outputs are daily return fractions (not percentages).
    """

    TRADING_DAYS = 252

    @staticmethod
    def from_returns(
        returns: np.ndarray,
        strategy_name: str = "strategy",
        start_date: str = "",
        end_date: str = "",
        trade_returns: Optional[np.ndarray] = None,
    ) -> BacktestResult:
        """
        Compute the full performance suite from a daily returns series.

        Parameters
        ----------
        returns       : daily strategy returns (fraction), shape (n_days,)
        trade_returns : per-trade returns (for trade stats). If None,
                        non-zero daily returns are used as a proxy.
        """
        n = len(returns)
        if n < 2:
            raise ValueError("Need at least 2 return observations")

        TD = PerformanceCalculator.TRADING_DAYS

        # --- Equity curve ---
        equity = np.cumprod(1 + returns)
        total_return = float(equity[-1] - 1.0)
        ann_return = float((equity[-1]) ** (TD / n) - 1.0)
        ann_vol = float(returns.std(ddof=1) * np.sqrt(TD))

        # --- Sharpe ---
        sharpe = ann_return / ann_vol if ann_vol > 0 else 0.0

        # --- Sortino (downside deviation) ---
        downside = returns[returns < 0]
        downside_dev = float(downside.std(ddof=1) * np.sqrt(TD)) if len(downside) > 1 else ann_vol
        sortino = ann_return / downside_dev if downside_dev > 0 else 0.0

        # --- Drawdown ---
        rolling_max = np.maximum.accumulate(equity)
        drawdown = (equity - rolling_max) / rolling_max
        max_dd = float(drawdown.min())
        avg_dd = float(drawdown[drawdown < 0].mean()) if (drawdown < 0).any() else 0.0

        # Drawdown duration
        in_dd = drawdown < 0
        max_dd_dur = _max_consecutive_true(in_dd)

        # --- Calmar ---
        calmar = ann_return / abs(max_dd) if max_dd != 0 else 0.0

        # --- Trade stats ---
        if trade_returns is None:
            trade_returns = returns[returns != 0]

        n_trades = len(trade_returns)
        if n_trades > 0:
            win_rate = float(np.mean(trade_returns > 0))
            wins = trade_returns[trade_returns > 0]
            losses = trade_returns[trade_returns < 0]
            profit_factor = (
                float(wins.sum() / abs(losses.sum()))
                if len(losses) > 0 and losses.sum() != 0
                else float("inf")
            )
            avg_tr = float(trade_returns.mean())
            best = float(trade_returns.max())
            worst = float(trade_returns.min())
        else:
            win_rate = profit_factor = avg_tr = best = worst = 0.0

        # --- Statistical significance (t-test vs zero) ---
        if n_trades > 1:
            t_stat, p_val = stats.ttest_1samp(trade_returns, 0.0)
        else:
            t_stat, p_val = 0.0, 1.0

        return BacktestResult(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            n_trades=n_trades,
            total_return=total_return,
            annualized_return=ann_return,
            annualized_vol=ann_vol,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_dd,
            avg_drawdown=avg_dd,
            max_drawdown_duration_days=int(max_dd_dur),
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_trade_return=avg_tr,
            best_trade=best,
            worst_trade=worst,
            equity_curve=equity.tolist(),
            drawdown_series=drawdown.tolist(),
            t_statistic=float(t_stat),
            p_value=float(p_val),
            is_significant=float(p_val) < 0.05,
        )


class WalkForwardOptimizer:
    """
    Walk-Forward Optimization (WFO).

    Avoids in-sample overfitting by:
      1. Train on a rolling in-sample window
      2. Evaluate on out-of-sample (OOS) window
      3. Slide forward and repeat
      4. Report OOS-only performance

    The ratio of OOS Sharpe to IS Sharpe measures robustness.
    A healthy strategy has OOS/IS ratio > 0.6.
    """

    def __init__(
        self,
        in_sample_days: int = 252,
        out_of_sample_days: int = 63,
        min_trades: int = 10,
    ):
        self.is_days = in_sample_days
        self.oos_days = out_of_sample_days
        self.min_trades = min_trades

    def run(
        self,
        prices: pd.DataFrame,
        strategy_fn: Callable[[pd.DataFrame, dict], np.ndarray],
        param_grid: list[dict],
        metric: str = "sharpe_ratio",
    ) -> dict:
        """
        Run walk-forward optimization.

        Parameters
        ----------
        prices      : DataFrame with price data, date-indexed
        strategy_fn : function(prices_slice, params) → daily_returns array
        param_grid  : list of parameter dicts to evaluate in-sample
        metric      : metric to optimize in-sample ('sharpe_ratio', 'total_return')

        Returns
        -------
        dict with OOS results, best params per window, robustness metrics
        """
        n = len(prices)
        window = self.is_days + self.oos_days
        n_windows = (n - window) // self.oos_days

        if n_windows < 2:
            raise ValueError(
                f"Insufficient data: need {window * 2} days, have {n}"
            )

        oos_returns_all: list[float] = []
        is_sharpes: list[float] = []
        oos_sharpes: list[float] = []
        best_params_per_window: list[dict] = []

        for i in range(n_windows):
            is_start = i * self.oos_days
            is_end = is_start + self.is_days
            oos_end = is_end + self.oos_days

            is_prices = prices.iloc[is_start:is_end]
            oos_prices = prices.iloc[is_end:oos_end]

            # --- In-sample optimization ---
            best_metric = -np.inf
            best_params: dict = {}

            for params in param_grid:
                try:
                    is_returns = strategy_fn(is_prices, params)
                    if len(is_returns) < self.min_trades:
                        continue
                    result = PerformanceCalculator.from_returns(is_returns)
                    m = getattr(result, metric, result.sharpe_ratio)
                    if m > best_metric:
                        best_metric = m
                        best_params = params
                except Exception:
                    continue

            if not best_params:
                continue

            # --- Out-of-sample evaluation ---
            try:
                oos_returns = strategy_fn(oos_prices, best_params)
                oos_result = PerformanceCalculator.from_returns(oos_returns)

                is_sharpes.append(best_metric)
                oos_sharpes.append(oos_result.sharpe_ratio)
                oos_returns_all.extend(oos_returns.tolist())
                best_params_per_window.append({
                    "window": i,
                    "is_start": str(is_prices.index[0].date()),
                    "oos_end": str(oos_prices.index[-1].date()),
                    "best_params": best_params,
                    "is_sharpe": round(best_metric, 3),
                    "oos_sharpe": round(oos_result.sharpe_ratio, 3),
                })
            except Exception as e:
                logger.warning("wfo_oos_failed", window=i, error=str(e))

        if not oos_returns_all:
            return {"error": "No valid WFO windows"}

        oos_arr = np.array(oos_returns_all)
        oos_overall = PerformanceCalculator.from_returns(oos_arr, "wfo_oos_combined")
        is_avg = float(np.mean(is_sharpes)) if is_sharpes else 0.0
        oos_avg = float(np.mean(oos_sharpes)) if oos_sharpes else 0.0
        robustness = oos_avg / is_avg if is_avg > 0 else 0.0

        return {
            "n_windows": len(best_params_per_window),
            "oos_performance": oos_overall.to_dict(),
            "is_avg_sharpe": round(is_avg, 3),
            "oos_avg_sharpe": round(oos_avg, 3),
            "robustness_ratio": round(robustness, 3),
            "is_robust": robustness >= 0.60,
            "windows": best_params_per_window,
        }


class MonteCarloSimulator:
    """
    Monte Carlo significance testing via strategy permutation.

    Tests whether observed Sharpe ratio could occur by random chance
    by randomly shuffling the signal and re-running the strategy N times.
    p-value = fraction of shuffled runs with Sharpe ≥ observed.
    """

    def __init__(self, n_simulations: int = 1000, seed: int = 42):
        self.n_sims = n_simulations
        self.rng = np.random.default_rng(seed)

    def permutation_test(
        self,
        signal: np.ndarray,
        returns: np.ndarray,
        observed_sharpe: float,
    ) -> dict:
        """
        Permutation test for strategy significance.

        Parameters
        ----------
        signal          : daily signal array (e.g., +1/-1/0)
        returns         : underlying daily return series
        observed_sharpe : Sharpe ratio of actual strategy

        Returns
        -------
        dict with p_value, distribution stats, conclusion
        """
        sim_sharpes = []
        n = min(len(signal), len(returns))
        signal, returns = signal[:n], returns[:n]

        for _ in range(self.n_sims):
            shuffled = self.rng.permutation(signal)
            sim_returns = shuffled * returns
            if sim_returns.std() > 0:
                ann_ret = sim_returns.mean() * 252
                ann_vol = sim_returns.std() * np.sqrt(252)
                sim_sharpes.append(ann_ret / ann_vol)

        sim_arr = np.array(sim_sharpes)
        p_value = float(np.mean(sim_arr >= observed_sharpe))

        return {
            "observed_sharpe": round(observed_sharpe, 4),
            "p_value": round(p_value, 4),
            "is_significant": p_value < 0.05,
            "n_simulations": len(sim_sharpes),
            "sim_sharpe_mean": round(float(sim_arr.mean()), 4),
            "sim_sharpe_std": round(float(sim_arr.std()), 4),
            "sim_sharpe_95th": round(float(np.percentile(sim_arr, 95)), 4),
            "percentile_rank": round(float(np.mean(sim_arr < observed_sharpe)) * 100, 1),
            "distribution": {
                "p5": round(float(np.percentile(sim_arr, 5)), 4),
                "p25": round(float(np.percentile(sim_arr, 25)), 4),
                "p50": round(float(np.percentile(sim_arr, 50)), 4),
                "p75": round(float(np.percentile(sim_arr, 75)), 4),
                "p95": round(float(np.percentile(sim_arr, 95)), 4),
            },
        }

    def equity_curve_fan(
        self,
        returns: np.ndarray,
        n_paths: int = 500,
    ) -> dict:
        """
        Bootstrap equity curve fan chart.
        Resample daily returns with replacement and compound.
        """
        n = len(returns)
        paths = []
        for _ in range(n_paths):
            sampled = self.rng.choice(returns, size=n, replace=True)
            equity = np.cumprod(1 + sampled).tolist()
            paths.append(equity)

        paths_arr = np.array(paths)
        return {
            "n_paths": n_paths,
            "p5":  np.percentile(paths_arr, 5,  axis=0).tolist(),
            "p25": np.percentile(paths_arr, 25, axis=0).tolist(),
            "p50": np.percentile(paths_arr, 50, axis=0).tolist(),
            "p75": np.percentile(paths_arr, 75, axis=0).tolist(),
            "p95": np.percentile(paths_arr, 95, axis=0).tolist(),
        }


# ------------------------------------------------------------------
# Utility
# ------------------------------------------------------------------

def _max_consecutive_true(arr: np.ndarray) -> int:
    """Return the length of the longest consecutive True run."""
    if not arr.any():
        return 0
    max_run = cur_run = 0
    for v in arr:
        if v:
            cur_run += 1
            max_run = max(max_run, cur_run)
        else:
            cur_run = 0
    return max_run

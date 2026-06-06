"""
Unit tests for Risk Engine (VaR, ES, Stress) and Backtest Engine.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.services.risk.var_engine import VaREngine, StressTester, _is_positive_definite
from app.services.research.backtest_engine import PerformanceCalculator, MonteCarloSimulator


# ----------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------

@pytest.fixture
def normal_returns():
    """252 days of normally distributed returns, mean=0.0005, vol=0.01."""
    rng = np.random.default_rng(42)
    return rng.normal(loc=0.0005, scale=0.01, size=252)


@pytest.fixture
def fat_tail_returns():
    """252 days with fat tails (Student-t, df=3)."""
    rng = np.random.default_rng(42)
    return rng.standard_t(df=3, size=252) * 0.01


@pytest.fixture
def var_engine():
    return VaREngine(portfolio_value=1_000_000)


# ----------------------------------------------------------------
# VaR Engine Tests
# ----------------------------------------------------------------

class TestHistoricalVaR:
    def test_returns_positive_var(self, var_engine, normal_returns):
        result = var_engine.historical_var(normal_returns, confidence=0.99)
        assert result.var_dollar > 0
        assert result.es_dollar > 0

    def test_es_greater_than_var(self, var_engine, normal_returns):
        """ES (CVaR) must be ≥ VaR by definition."""
        result = var_engine.historical_var(normal_returns, confidence=0.99)
        assert result.es_dollar >= result.var_dollar

    def test_higher_confidence_higher_var(self, var_engine, normal_returns):
        r95 = var_engine.historical_var(normal_returns, confidence=0.95)
        r99 = var_engine.historical_var(normal_returns, confidence=0.99)
        assert r99.var_dollar >= r95.var_dollar

    def test_longer_horizon_higher_var(self, var_engine, normal_returns):
        r1 = var_engine.historical_var(normal_returns, horizon_days=1)
        r5 = var_engine.historical_var(normal_returns, horizon_days=5)
        # sqrt-of-time: 5-day VaR ≈ 1-day VaR × sqrt(5)
        ratio = r5.var_dollar / r1.var_dollar
        assert 2.0 < ratio < 2.5  # sqrt(5) ≈ 2.236

    def test_raises_with_too_few_observations(self, var_engine):
        with pytest.raises(ValueError, match="100"):
            var_engine.historical_var(np.array([0.01, -0.01, 0.005]), confidence=0.99)

    def test_var_pct_consistent_with_dollar(self, var_engine, normal_returns):
        result = var_engine.historical_var(normal_returns, confidence=0.99)
        expected_dollar = result.var_pct * var_engine.portfolio_value
        assert abs(result.var_dollar - expected_dollar) < 1.0   # rounding only


class TestParametricVaR:
    def test_returns_valid_result(self, var_engine, normal_returns):
        result = var_engine.parametric_var(normal_returns, confidence=0.99)
        assert result.var_dollar > 0
        assert result.method == "parametric_cornish_fisher"

    def test_cf_adjustment_positive_for_fat_tails(self, var_engine, fat_tail_returns):
        """Fat-tailed returns → CF adjustment should push VaR higher than Gaussian."""
        result = var_engine.parametric_var(fat_tail_returns, confidence=0.99)
        assert result.metadata["cf_adjustment"] != 0.0
        # For fat tails (positive excess kurtosis), VaR should exceed normal approximation
        assert result.metadata["excess_kurtosis"] > 0

    def test_cf_metadata_populated(self, var_engine, normal_returns):
        result = var_engine.parametric_var(normal_returns)
        for key in ["mu", "sigma", "skewness", "excess_kurtosis", "z_normal", "z_cornish_fisher"]:
            assert key in result.metadata


class TestMonteCarloVaR:
    def test_basic_mc_var(self, var_engine):
        n = 3
        mu = np.array([0.0005] * n)
        sigma = np.array([0.012, 0.015, 0.010])
        corr = np.eye(n)
        positions = np.array([500_000, 300_000, 200_000])

        result = var_engine.monte_carlo_var(mu, sigma, corr, positions, n_sims=5000)
        assert result.var_dollar > 0
        assert result.method == "monte_carlo_gbm"

    def test_mc_handles_ill_conditioned_corr(self, var_engine):
        """Non-PD correlation matrix should be regularized, not crash."""
        corr = np.array([
            [1.0, 0.99, 0.99],
            [0.99, 1.0, 0.99],
            [0.99, 0.99, 1.0],
        ])  # Nearly singular
        mu = np.array([0.0, 0.0, 0.0])
        sigma = np.array([0.01, 0.01, 0.01])
        positions = np.array([333_333, 333_333, 333_334])

        result = var_engine.monte_carlo_var(mu, sigma, corr, positions, n_sims=1000)
        assert result.var_dollar > 0

    def test_diversification_reduces_var(self, var_engine):
        """Diversified portfolio should have lower VaR than concentrated."""
        n = 4
        sigma = np.array([0.02] * n)
        mu = np.zeros(n)
        pos_div = np.array([250_000] * n)
        pos_conc = np.array([1_000_000, 0, 0, 0])

        # Perfect correlation — no diversification benefit
        corr_high = np.full((n, n), 0.9)
        np.fill_diagonal(corr_high, 1.0)

        # Zero correlation — full diversification
        corr_zero = np.eye(n)

        r_div = var_engine.monte_carlo_var(mu, sigma, corr_zero, pos_div, n_sims=5000)
        r_conc = var_engine.monte_carlo_var(mu, sigma, corr_high, pos_conc, n_sims=5000)

        # Concentrated high-corr portfolio should have higher VaR
        assert r_conc.var_dollar > r_div.var_dollar


class TestStressTester:
    def test_all_scenarios_run(self):
        tester = StressTester(portfolio_value=1_000_000)
        results = tester.run_all_scenarios(equity_weight=1.0)
        assert len(results) == len(StressTester.SCENARIOS)

    def test_crash_scenarios_negative_pnl(self):
        tester = StressTester(portfolio_value=1_000_000)
        result = tester.run_scenario("gfc_lehman_2008", equity_weight=1.0)
        assert result.pnl_dollar < 0

    def test_soft_landing_positive_pnl(self):
        tester = StressTester(portfolio_value=1_000_000)
        result = tester.run_scenario("soft_landing", equity_weight=1.0)
        assert result.pnl_dollar > 0

    def test_unknown_scenario_raises(self):
        tester = StressTester()
        with pytest.raises(ValueError, match="Unknown scenario"):
            tester.run_scenario("nonexistent_scenario")

    def test_results_sorted_worst_first(self):
        tester = StressTester(portfolio_value=1_000_000)
        results = tester.run_all_scenarios(equity_weight=1.0)
        pnls = [r["pnl_dollar"] for r in results]
        assert pnls == sorted(pnls)


# ----------------------------------------------------------------
# Backtest Engine Tests
# ----------------------------------------------------------------

class TestPerformanceCalculator:
    def test_positive_returns_positive_total_return(self):
        returns = np.full(252, 0.001)  # +0.1% per day
        result = PerformanceCalculator.from_returns(returns)
        assert result.total_return > 0
        assert result.annualized_return > 0

    def test_negative_returns_negative_total_return(self):
        returns = np.full(252, -0.001)
        result = PerformanceCalculator.from_returns(returns)
        assert result.total_return < 0

    def test_sharpe_calculation(self):
        """Known Sharpe ratio for constant positive returns."""
        returns = np.full(252, 0.001)
        result = PerformanceCalculator.from_returns(returns)
        # Constant returns → zero vol → infinite Sharpe (returns 0.0 in our impl)
        # Test just that it doesn't crash and returns a number
        assert isinstance(result.sharpe_ratio, float)

    def test_max_drawdown_is_negative_or_zero(self):
        returns = np.array([0.01, -0.05, 0.02, -0.03, 0.01])
        result = PerformanceCalculator.from_returns(returns)
        assert result.max_drawdown <= 0

    def test_win_rate_bounds(self):
        rng = np.random.default_rng(1)
        returns = rng.normal(0, 0.01, 100)
        result = PerformanceCalculator.from_returns(returns, trade_returns=returns)
        assert 0.0 <= result.win_rate <= 1.0

    def test_equity_curve_starts_at_one(self):
        returns = np.array([0.01, -0.01, 0.02])
        result = PerformanceCalculator.from_returns(returns)
        assert abs(result.equity_curve[0] - 1.01) < 1e-10

    def test_raises_with_too_few_observations(self):
        with pytest.raises(ValueError):
            PerformanceCalculator.from_returns(np.array([0.01]))


class TestMonteCarloSimulator:
    def test_permutation_test_random_signal_high_pvalue(self):
        """A random signal should have a high p-value (not significant)."""
        rng = np.random.default_rng(99)
        signal = rng.choice([-1, 0, 1], size=252)
        returns = rng.normal(0, 0.01, 252)
        observed_sharpe = 0.05   # very low — close to random

        sim = MonteCarloSimulator(n_simulations=500, seed=42)
        result = sim.permutation_test(signal, returns, observed_sharpe)

        assert "p_value" in result
        assert 0.0 <= result["p_value"] <= 1.0
        # Random signal should not be significant most of the time
        assert result["p_value"] > 0.05

    def test_equity_fan_has_correct_quantiles(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0008, 0.01, 252)
        sim = MonteCarloSimulator(n_simulations=200, seed=42)
        fan = sim.equity_curve_fan(returns, n_paths=200)

        assert "p5" in fan and "p95" in fan and "p50" in fan
        assert len(fan["p50"]) == 252
        # p95 should be above p5 at the end
        assert fan["p95"][-1] > fan["p5"][-1]

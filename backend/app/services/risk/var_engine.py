"""
Risk Engine — VaR, Expected Shortfall, Stress Testing.

Three VaR methodologies:
  1. Historical Simulation    — non-parametric, 1000-day lookback
  2. Parametric (Cornish-Fisher) — accounts for skewness + kurtosis
  3. Monte Carlo              — GBM with full correlation structure

All methods return both VaR and ES (Expected Shortfall / CVaR).
ES is the mean loss beyond the VaR threshold — more informative
for tail risk and required under Basel III.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy import stats

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VaRResult:
    method: str
    confidence: float
    horizon_days: int
    var_dollar: float          # 1-day VaR in dollars (positive = loss)
    es_dollar: float           # Expected Shortfall in dollars
    var_pct: float             # VaR as % of portfolio
    es_pct: float
    n_scenarios: int
    metadata: dict = field(default_factory=dict)


@dataclass
class StressResult:
    scenario: str
    shock_description: str
    pnl_dollar: float
    pnl_pct: float
    worst_position: str
    worst_position_pnl: float


class VaREngine:
    """
    Portfolio Value-at-Risk engine.

    Inputs:
      returns       — np.ndarray of daily P&L returns (NOT prices), shape (n_days,)
                      for multi-asset: shape (n_days, n_assets)
      portfolio_value — current dollar value of portfolio
    """

    def __init__(self, portfolio_value: float = 1_000_000.0):
        self.portfolio_value = portfolio_value

    # ------------------------------------------------------------------
    # 1. Historical Simulation VaR
    # ------------------------------------------------------------------

    def historical_var(
        self,
        returns: np.ndarray,
        confidence: float = 0.99,
        horizon_days: int = 1,
    ) -> VaRResult:
        """
        Historical simulation VaR.

        Scales to multi-day horizon via square-root-of-time rule.
        No distributional assumptions — purely empirical.
        Requires at least 250 observations for 99% VaR reliability.
        """
        if len(returns) < 100:
            raise ValueError(f"Need ≥100 return observations, got {len(returns)}")

        # Scale to horizon
        if horizon_days > 1:
            scaled = returns * np.sqrt(horizon_days)
        else:
            scaled = returns

        var_pct = float(-np.percentile(scaled, (1 - confidence) * 100))
        # ES = mean of losses beyond VaR threshold
        tail = scaled[scaled <= -var_pct]
        es_pct = float(-tail.mean()) if len(tail) > 0 else var_pct * 1.2

        return VaRResult(
            method="historical_simulation",
            confidence=confidence,
            horizon_days=horizon_days,
            var_dollar=round(var_pct * self.portfolio_value, 2),
            es_dollar=round(es_pct * self.portfolio_value, 2),
            var_pct=round(var_pct, 6),
            es_pct=round(es_pct, 6),
            n_scenarios=len(returns),
            metadata={
                "lookback_days": len(returns),
                "tail_observations": len(tail),
            },
        )

    # ------------------------------------------------------------------
    # 2. Parametric VaR (Cornish-Fisher Expansion)
    # ------------------------------------------------------------------

    def parametric_var(
        self,
        returns: np.ndarray,
        confidence: float = 0.99,
        horizon_days: int = 1,
    ) -> VaRResult:
        """
        Parametric VaR with Cornish-Fisher expansion.

        Standard parametric VaR assumes normality — CF expansion
        adjusts the normal quantile for observed skewness and excess kurtosis.

        CF adjustment:
          z_cf = z + (z²-1)·S/6 + (z³-3z)·K/24 - (2z³-5z)·S²/36

        where z = normal quantile, S = skewness, K = excess kurtosis.
        """
        mu = float(returns.mean())
        sigma = float(returns.std(ddof=1))
        skew = float(stats.skew(returns))
        kurt = float(stats.kurtosis(returns))  # excess kurtosis

        z = float(stats.norm.ppf(1 - confidence))

        # Cornish-Fisher adjusted quantile
        z_cf = (
            z
            + (z ** 2 - 1) * skew / 6
            + (z ** 3 - 3 * z) * kurt / 24
            - (2 * z ** 3 - 5 * z) * skew ** 2 / 36
        )

        var_pct = float(-(mu + z_cf * sigma)) * np.sqrt(horizon_days)
        var_pct = max(var_pct, 0.0)

        # ES via numerical integration for CF
        # Approximate: ES ≈ VaR × (1 + adjustment_factor)
        phi_z = float(stats.norm.pdf(z))
        es_normal = phi_z / (1 - confidence) * sigma
        skew_adj = 1 + (z ** 2 - 1) * skew / 6 + (z ** 3 - 3 * z) * kurt / 24
        es_pct = float((-mu + es_normal * skew_adj)) * np.sqrt(horizon_days)
        es_pct = max(es_pct, var_pct)

        return VaRResult(
            method="parametric_cornish_fisher",
            confidence=confidence,
            horizon_days=horizon_days,
            var_dollar=round(var_pct * self.portfolio_value, 2),
            es_dollar=round(es_pct * self.portfolio_value, 2),
            var_pct=round(var_pct, 6),
            es_pct=round(es_pct, 6),
            n_scenarios=len(returns),
            metadata={
                "mu": round(mu, 6),
                "sigma": round(sigma, 6),
                "skewness": round(skew, 4),
                "excess_kurtosis": round(kurt, 4),
                "z_normal": round(z, 4),
                "z_cornish_fisher": round(z_cf, 4),
                "cf_adjustment": round(z_cf - z, 4),
            },
        )

    # ------------------------------------------------------------------
    # 3. Monte Carlo VaR
    # ------------------------------------------------------------------

    def monte_carlo_var(
        self,
        mu: np.ndarray,
        sigma: np.ndarray,
        corr_matrix: np.ndarray,
        positions: np.ndarray,
        confidence: float = 0.99,
        horizon_days: int = 1,
        n_sims: int = 10_000,
        seed: Optional[int] = 42,
    ) -> VaRResult:
        """
        Full Monte Carlo VaR with Cholesky-decomposed correlation structure.

        Parameters
        ----------
        mu          : (n_assets,) expected daily returns
        sigma       : (n_assets,) daily return volatilities
        corr_matrix : (n_assets, n_assets) correlation matrix
        positions   : (n_assets,) dollar position sizes (signed)
        confidence  : VaR confidence level
        horizon_days: holding period
        n_sims      : number of Monte Carlo paths
        seed        : random seed for reproducibility
        """
        n_assets = len(positions)
        rng = np.random.default_rng(seed)

        # Cholesky decomposition of correlation matrix
        try:
            L = np.linalg.cholesky(corr_matrix)
        except np.linalg.LinAlgError:
            # Matrix not positive definite — regularize
            corr_matrix = _nearest_positive_definite(corr_matrix)
            L = np.linalg.cholesky(corr_matrix)

        dt = horizon_days / 252.0

        # Simulate correlated returns: Z ~ N(0, Σ)
        Z = rng.standard_normal((n_sims, n_assets))
        corr_Z = Z @ L.T                                   # shape (n_sims, n_assets)

        # GBM returns: r_i = (μ_i - σ_i²/2)dt + σ_i√dt·Z_i
        drift = (mu - 0.5 * sigma ** 2) * dt
        diffusion = sigma * np.sqrt(dt) * corr_Z
        returns_sim = drift + diffusion                    # (n_sims, n_assets)

        # Portfolio P&L per simulation
        pnl = (returns_sim * positions).sum(axis=1)        # (n_sims,)

        var_dollar = float(-np.percentile(pnl, (1 - confidence) * 100))
        tail = pnl[pnl <= -var_dollar]
        es_dollar = float(-tail.mean()) if len(tail) > 0 else var_dollar * 1.25

        return VaRResult(
            method="monte_carlo_gbm",
            confidence=confidence,
            horizon_days=horizon_days,
            var_dollar=round(var_dollar, 2),
            es_dollar=round(es_dollar, 2),
            var_pct=round(var_dollar / self.portfolio_value, 6),
            es_pct=round(es_dollar / self.portfolio_value, 6),
            n_scenarios=n_sims,
            metadata={
                "n_assets": n_assets,
                "horizon_days": horizon_days,
                "tail_observations": len(tail),
            },
        )

    # ------------------------------------------------------------------
    # Comparison — run all three methods
    # ------------------------------------------------------------------

    def full_var_report(
        self,
        returns: np.ndarray,
        confidence: float = 0.99,
        horizon_days: int = 1,
    ) -> dict:
        """
        Run all three VaR methods and return side-by-side results.
        Useful for model validation and reporting.
        """
        results = {}

        try:
            hist = self.historical_var(returns, confidence, horizon_days)
            results["historical"] = {
                "var": hist.var_dollar,
                "es": hist.es_dollar,
                "var_pct": hist.var_pct,
            }
        except Exception as e:
            results["historical"] = {"error": str(e)}

        try:
            param = self.parametric_var(returns, confidence, horizon_days)
            results["parametric_cf"] = {
                "var": param.var_dollar,
                "es": param.es_dollar,
                "var_pct": param.var_pct,
                "skewness": param.metadata.get("skewness"),
                "excess_kurtosis": param.metadata.get("excess_kurtosis"),
                "cf_adjustment": param.metadata.get("cf_adjustment"),
            }
        except Exception as e:
            results["parametric_cf"] = {"error": str(e)}

        results["confidence"] = confidence
        results["horizon_days"] = horizon_days
        results["portfolio_value"] = self.portfolio_value
        return results


class StressTester:
    """
    Historical and hypothetical stress testing.

    Applies predefined shock scenarios to a portfolio
    and computes the expected P&L impact.
    """

    # Historical stress scenarios — daily return shocks
    SCENARIOS: dict[str, dict[str, float]] = {
        "covid_crash_march2020": {
            "description": "COVID crash — S&P -34% peak-to-trough (Feb–Mar 2020)",
            "equity_shock": -0.12,       # single worst day: -12%
            "vol_shock": +1.50,          # VIX spike
            "credit_shock": -0.05,
            "gold_shock": +0.02,
        },
        "gfc_lehman_2008": {
            "description": "Lehman Brothers bankruptcy week (Sep 15, 2008)",
            "equity_shock": -0.045,
            "vol_shock": +0.80,
            "credit_shock": -0.08,
            "gold_shock": +0.04,
        },
        "flash_crash_2010": {
            "description": "May 6, 2010 Flash Crash — Dow -9% intraday",
            "equity_shock": -0.09,
            "vol_shock": +0.45,
            "credit_shock": -0.02,
            "gold_shock": +0.01,
        },
        "taper_tantrum_2013": {
            "description": "Fed taper tantrum — rates spike, equities sell off",
            "equity_shock": -0.06,
            "vol_shock": +0.35,
            "credit_shock": -0.04,
            "gold_shock": -0.05,
        },
        "ukraine_invasion_2022": {
            "description": "Russia–Ukraine invasion Feb 24, 2022",
            "equity_shock": -0.027,
            "vol_shock": +0.40,
            "credit_shock": -0.03,
            "gold_shock": +0.03,
        },
        "rate_shock_plus200bps": {
            "description": "Hypothetical: +200bps overnight rate shock",
            "equity_shock": -0.10,
            "vol_shock": +0.60,
            "credit_shock": -0.06,
            "gold_shock": -0.02,
        },
        "vol_spike_vix80": {
            "description": "Hypothetical: VIX spikes to 80 (COVID peak was 82.7)",
            "equity_shock": -0.15,
            "vol_shock": +2.00,
            "credit_shock": -0.08,
            "gold_shock": +0.03,
        },
        "soft_landing": {
            "description": "Hypothetical: benign soft landing — vol compression",
            "equity_shock": +0.03,
            "vol_shock": -0.30,
            "credit_shock": +0.01,
            "gold_shock": -0.01,
        },
    }

    def __init__(self, portfolio_value: float = 1_000_000.0):
        self.portfolio_value = portfolio_value

    def run_scenario(
        self,
        scenario_name: str,
        equity_weight: float = 1.0,
        vol_sensitivity: float = 0.0,  # vega * $ notional
        credit_weight: float = 0.0,
        gold_weight: float = 0.0,
        positions: Optional[dict[str, float]] = None,
    ) -> StressResult:
        """
        Apply a named stress scenario to the portfolio.

        Parameters
        ----------
        equity_weight    : fraction of portfolio in equities
        vol_sensitivity  : dollar vega (positive = long vol)
        credit_weight    : fraction in credit/bonds
        gold_weight      : fraction in gold
        """
        if scenario_name not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_name}. Valid: {list(self.SCENARIOS)}")

        sc = self.SCENARIOS[scenario_name]

        pnl_equity = equity_weight * self.portfolio_value * sc["equity_shock"]
        pnl_vol = vol_sensitivity * sc["vol_shock"]
        pnl_credit = credit_weight * self.portfolio_value * sc["credit_shock"]
        pnl_gold = gold_weight * self.portfolio_value * sc["gold_shock"]

        total_pnl = pnl_equity + pnl_vol + pnl_credit + pnl_gold

        # Identify worst position
        components = {
            "equity": pnl_equity,
            "volatility": pnl_vol,
            "credit": pnl_credit,
            "gold": pnl_gold,
        }
        worst = min(components, key=lambda k: components[k])

        return StressResult(
            scenario=scenario_name,
            shock_description=sc["description"],
            pnl_dollar=round(total_pnl, 2),
            pnl_pct=round(total_pnl / self.portfolio_value, 6),
            worst_position=worst,
            worst_position_pnl=round(components[worst], 2),
        )

    def run_all_scenarios(self, **kwargs) -> list[dict]:
        """Run all scenarios and return sorted by severity (worst first)."""
        results = []
        for name in self.SCENARIOS:
            try:
                result = self.run_scenario(name, **kwargs)
                results.append({
                    "scenario": result.scenario,
                    "description": result.shock_description,
                    "pnl_dollar": result.pnl_dollar,
                    "pnl_pct": round(result.pnl_pct * 100, 2),
                    "worst_position": result.worst_position,
                })
            except Exception as e:
                logger.warning("stress_scenario_failed", scenario=name, error=str(e))

        return sorted(results, key=lambda r: r["pnl_dollar"])

    def sensitivity_analysis(
        self,
        base_returns: np.ndarray,
        confidence_levels: tuple[float, ...] = (0.90, 0.95, 0.99),
        horizons: tuple[int, ...] = (1, 5, 10, 21),
    ) -> dict:
        """
        VaR sensitivity table across confidence levels and horizons.
        Returns a 2D dict [confidence][horizon] → VaR %.
        """
        engine = VaREngine(self.portfolio_value)
        table = {}
        for conf in confidence_levels:
            table[str(conf)] = {}
            for h in horizons:
                try:
                    result = engine.historical_var(base_returns, conf, h)
                    table[str(conf)][str(h)] = {
                        "var_pct": result.var_pct,
                        "var_dollar": result.var_dollar,
                        "es_dollar": result.es_dollar,
                    }
                except Exception:
                    table[str(conf)][str(h)] = None
        return table


# ------------------------------------------------------------------
# Utility
# ------------------------------------------------------------------

def _nearest_positive_definite(A: np.ndarray) -> np.ndarray:
    """
    Find the nearest positive definite matrix to A.
    Used to regularize ill-conditioned correlation matrices.
    Higham (1988) algorithm.
    """
    B = (A + A.T) / 2
    _, s, V = np.linalg.svd(B)
    H = V.T @ np.diag(s) @ V
    A2 = (B + H) / 2
    A3 = (A2 + A2.T) / 2

    if _is_positive_definite(A3):
        return A3

    spacing = np.spacing(np.linalg.norm(A))
    k = 1
    while not _is_positive_definite(A3):
        min_eig = np.min(np.real(np.linalg.eigvals(A3)))
        A3 += np.eye(A.shape[0]) * (-min_eig * k ** 2 + spacing)
        k += 1

    return A3


def _is_positive_definite(A: np.ndarray) -> bool:
    try:
        np.linalg.cholesky(A)
        return True
    except np.linalg.LinAlgError:
        return False

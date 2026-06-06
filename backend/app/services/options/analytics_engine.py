"""
Options Analytics Engine.

Orchestrates BSM pricer, IV solver, and surface fitting
for a complete option chain snapshot.
Called by both the API layer and Celery workers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Optional

import numpy as np

from app.core.logging import get_logger
from app.services.options.bsm import BSMPricer
from app.services.options.iv_surface import IVRankCalculator, VolatilitySurface

logger = get_logger(__name__)


@dataclass
class ContractInput:
    """Raw market data for a single option contract."""
    contract_id: str
    underlying: str
    strike: float
    expiration: date
    option_type: str          # 'C' or 'P'
    bid: float
    ask: float
    open_interest: int
    volume: int
    spot_price: float
    dte: int                  # days to expiration
    multiplier: float = 100.0


@dataclass
class GreeksOutput:
    """Computed Greeks + IV for a single contract."""
    contract_id: str
    underlying: str
    spot_price: float
    iv: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    vanna: float
    charm: float
    vomma: float
    speed: float
    iv_bid: float
    iv_ask: float
    dollar_gamma: float       # GEX contribution = gamma * OI * multiplier * S² * 0.01
    dollar_delta: float       # DEX contribution


class OptionsAnalyticsEngine:
    """
    Full-chain analytics pipeline.

    1. Solve IV from market mid-prices (batch Brentq)
    2. Compute all Greeks vectorized (NumPy)
    3. Fit volatility surface (RBF)
    4. Return structured output ready for DB insert
    """

    def __init__(self, risk_free_rate: float = 0.0525, dividend_yield: float = 0.0):
        self.r = risk_free_rate
        self.q = dividend_yield

    def compute_chain_greeks(
        self,
        contracts: list[ContractInput],
        timestamp: Optional[datetime] = None,
    ) -> list[GreeksOutput]:
        """
        Main entry point — process a full option chain snapshot.

        Parameters
        ----------
        contracts : list of ContractInput with market data
        timestamp : snapshot time (defaults to now)

        Returns
        -------
        list of GreeksOutput — one per contract
        """
        if not contracts:
            return []

        ts = timestamp or datetime.now(tz=timezone.utc)
        spot = contracts[0].spot_price

        # ---- Vectorize inputs ----
        n = len(contracts)
        Ks = np.array([c.strike for c in contracts])
        Ts = np.array([c.dte / 365.0 for c in contracts])
        mids = np.array([(c.bid + c.ask) / 2.0 for c in contracts])
        bids = np.array([c.bid for c in contracts])
        asks = np.array([c.ask for c in contracts])
        types = np.array([c.option_type for c in contracts])
        ois = np.array([c.open_interest for c in contracts], dtype=float)
        mults = np.array([c.multiplier for c in contracts])

        # ---- Solve IV batch ----
        logger.debug("solving_iv_batch", n_contracts=n, symbol=contracts[0].underlying)
        iv_mid = BSMPricer.implied_vol_batch(spot, Ks, Ts, self.r, self.q, mids, types)
        iv_bid = BSMPricer.implied_vol_batch(spot, Ks, Ts, self.r, self.q, bids, types)
        iv_ask = BSMPricer.implied_vol_batch(spot, Ks, Ts, self.r, self.q, asks, types)

        # ---- Fill NaN IVs with surface interpolation where possible ----
        valid_mask = np.isfinite(iv_mid)
        if valid_mask.sum() > 4:
            try:
                surface = VolatilitySurface(Ks[valid_mask], Ts[valid_mask] * 365, iv_mid[valid_mask], spot)
                nan_mask = ~valid_mask
                if nan_mask.any():
                    iv_mid[nan_mask] = surface.query_batch(Ks[nan_mask], Ts[nan_mask] * 365)
            except Exception as e:
                logger.warning("surface_fill_failed", error=str(e))

        # ---- Compute Greeks vectorized ----
        greeks = BSMPricer.full_greeks_batch(spot, Ks, Ts, self.r, self.q, iv_mid, types)

        # ---- Dollar exposures ----
        sign = np.where(types == "C", 1.0, -1.0)
        dgamma = greeks["gamma"] * ois * mults * (spot ** 2) * 0.01 * sign
        ddelta = greeks["delta"] * ois * mults * spot

        # ---- Build output ----
        results: list[GreeksOutput] = []
        for i, c in enumerate(contracts):
            results.append(GreeksOutput(
                contract_id=c.contract_id,
                underlying=c.underlying,
                spot_price=spot,
                iv=float(iv_mid[i]) if np.isfinite(iv_mid[i]) else 0.0,
                iv_bid=float(iv_bid[i]) if np.isfinite(iv_bid[i]) else 0.0,
                iv_ask=float(iv_ask[i]) if np.isfinite(iv_ask[i]) else 0.0,
                delta=float(greeks["delta"][i]),
                gamma=float(greeks["gamma"][i]),
                vega=float(greeks["vega"][i]),
                theta=float(greeks["theta"][i]),
                rho=float(greeks["rho"][i]),
                vanna=float(greeks["vanna"][i]),
                charm=float(greeks["charm"][i]),
                vomma=float(greeks["vomma"][i]),
                speed=float(greeks["speed"][i]),
                dollar_gamma=float(dgamma[i]),
                dollar_delta=float(ddelta[i]),
            ))

        logger.info(
            "chain_greeks_computed",
            symbol=contracts[0].underlying,
            n_contracts=n,
            n_valid_iv=int(valid_mask.sum()),
        )
        return results

    def build_surface(
        self,
        contracts: list[ContractInput],
        iv_values: Optional[list[float]] = None,
    ) -> Optional[VolatilitySurface]:
        """
        Fit a volatility surface from chain data + pre-computed IVs.
        Returns None if insufficient data.
        """
        if len(contracts) < 10:
            return None

        spot = contracts[0].spot_price
        Ks = np.array([c.strike for c in contracts])
        Ds = np.array([c.dte for c in contracts], dtype=float)

        if iv_values is not None:
            ivs = np.array(iv_values)
        else:
            Ts = Ds / 365.0
            mids = np.array([(c.bid + c.ask) / 2.0 for c in contracts])
            types = np.array([c.option_type for c in contracts])
            ivs = BSMPricer.implied_vol_batch(spot, Ks, Ts, self.r, self.q, mids, types)

        try:
            return VolatilitySurface(Ks, Ds, ivs, spot)
        except ValueError as e:
            logger.warning("surface_build_failed", error=str(e))
            return None

    def compute_iv_rank(
        self,
        current_atm_iv: float,
        historical_ivs: np.ndarray,
    ) -> dict:
        return IVRankCalculator.compute(current_atm_iv, historical_ivs)

"""
Greeks Calculator Celery Task.

Runs every minute during market hours.
Pulls latest chain data, computes Greeks + IV, persists to TimescaleDB.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)

# Market hours gate — Eastern Time
_MARKET_OPEN_HOUR = 9
_MARKET_OPEN_MIN = 30
_MARKET_CLOSE_HOUR = 16


def _is_market_hours() -> bool:
    """Simple market hours check (ET). TODO: handle holidays."""
    import zoneinfo
    now_et = datetime.now(tz=zoneinfo.ZoneInfo("America/New_York"))
    if now_et.weekday() >= 5:  # Saturday/Sunday
        return False
    t = (now_et.hour, now_et.minute)
    market_open = (_MARKET_OPEN_HOUR, _MARKET_OPEN_MIN)
    market_close = (_MARKET_CLOSE_HOUR, 0)
    return market_open <= t <= market_close


@celery_app.task(
    name="app.tasks.greeks_calculator.compute_all_greeks",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    soft_time_limit=55,       # must finish within 55s (before next 1-min tick)
    time_limit=60,
)
def compute_all_greeks(self, symbols: list[str]) -> dict:
    """
    Compute Greeks for all active option contracts.

    1. Pull latest chain snapshot from DB / cache
    2. Run analytics engine (vectorized BSM)
    3. Bulk-insert into greeks hypertable
    4. Update Redis cache per symbol
    """
    if not _is_market_hours():
        return {"status": "skipped", "reason": "outside_market_hours"}

    try:
        result = asyncio.run(_compute_greeks_async(symbols))
        return result
    except Exception as exc:
        logger.exception("greeks_task_failed", symbols=symbols)
        raise self.retry(exc=exc)


async def _compute_greeks_async(symbols: list[str]) -> dict:
    from app.core.database import AsyncSessionFactory
    from app.core.cache import Cache, CacheKey, CacheTTL, get_redis
    from app.services.options.analytics_engine import OptionsAnalyticsEngine, ContractInput
    from app.models.option_contract import OptionContract
    from app.models.option_chain import OptionChain
    from app.models.greeks import Greeks
    from sqlalchemy import select, and_
    from datetime import date

    engine = OptionsAnalyticsEngine()
    cache = Cache(get_redis())
    total_computed = 0
    errors = []

    async with AsyncSessionFactory() as session:
        for symbol in symbols:
            try:
                # Fetch latest chain snapshot from DB
                result = await session.execute(
                    select(OptionChain, OptionContract)
                    .join(OptionContract, OptionChain.contract_id == OptionContract.id)
                    .where(
                        and_(
                            OptionChain.underlying == symbol,
                            OptionContract.expiration >= date.today(),
                        )
                    )
                    .order_by(OptionChain.time.desc())
                    .limit(2000)  # max contracts per symbol
                )
                rows = result.all()

                if not rows:
                    continue

                spot = rows[0].OptionChain.spot_price or 0.0
                if spot <= 0:
                    continue

                # Build ContractInput list
                contracts = [
                    ContractInput(
                        contract_id=str(row.OptionChain.contract_id),
                        underlying=symbol,
                        strike=float(row.OptionContract.strike),
                        expiration=row.OptionContract.expiration,
                        option_type=row.OptionContract.option_type,
                        bid=float(row.OptionChain.bid or 0),
                        ask=float(row.OptionChain.ask or 0),
                        open_interest=int(row.OptionChain.open_interest or 0),
                        volume=int(row.OptionChain.volume or 0),
                        spot_price=spot,
                        dte=int(row.OptionChain.dte or 0),
                        multiplier=float(row.OptionContract.multiplier or 100.0),
                    )
                    for row in rows
                ]

                # Compute Greeks
                greeks_outputs = engine.compute_chain_greeks(contracts)

                # Bulk insert
                now = datetime.now(tz=timezone.utc)
                greek_rows = [
                    Greeks(
                        time=now,
                        contract_id=g.contract_id,
                        underlying=symbol,
                        spot_price=g.spot_price,
                        iv=g.iv,
                        iv_bid=g.iv_bid,
                        iv_ask=g.iv_ask,
                        delta=g.delta,
                        gamma=g.gamma,
                        vega=g.vega,
                        theta=g.theta,
                        rho=g.rho,
                        vanna=g.vanna,
                        charm=g.charm,
                        vomma=g.vomma,
                        speed=g.speed,
                    )
                    for g in greeks_outputs
                ]

                session.add_all(greek_rows)
                total_computed += len(greek_rows)

                # Cache summary
                summary = {
                    "symbol": symbol,
                    "spot": spot,
                    "n_contracts": len(greek_rows),
                    "timestamp": now.isoformat(),
                    "atm_iv": _estimate_atm_iv(greeks_outputs, spot),
                }
                await cache.set(CacheKey.greeks(symbol), summary, CacheTTL.GREEKS)

            except Exception as e:
                errors.append({"symbol": symbol, "error": str(e)})
                logger.error("greeks_symbol_failed", symbol=symbol, error=str(e))

        await session.commit()

    logger.info("greeks_task_complete", total=total_computed, errors=len(errors))
    return {"status": "ok", "computed": total_computed, "errors": errors}


def _estimate_atm_iv(outputs, spot: float) -> Optional[float]:
    """Find the contract closest to ATM and return its IV."""
    if not outputs:
        return None
    atm = min(outputs, key=lambda g: abs(g.dollar_gamma))  # proxy
    return atm.iv if atm.iv > 0 else None

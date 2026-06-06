"""
Dealer Positioning Snapshot Task.

Runs every 5 minutes. Aggregates latest Greeks into GEX/DEX/VEX/CEX
per strike and persists the dealer positioning snapshot.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import polars as pl

from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.dealer_snapshot.take_snapshot",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=280,
    time_limit=300,
)
def take_snapshot(self, symbols: list[str]) -> dict:
    """Compute and persist dealer positioning for all symbols."""
    try:
        return asyncio.run(_snapshot_async(symbols))
    except Exception as exc:
        logger.exception("dealer_snapshot_failed")
        raise self.retry(exc=exc)


async def _snapshot_async(symbols: list[str]) -> dict:
    from app.core.database import AsyncSessionFactory
    from app.core.cache import Cache, CacheKey, CacheTTL, get_redis
    from app.services.dealer.positioning_engine import DealerPositioningEngine
    from app.models.dealer_positioning import DealerPositioning
    from app.models.greeks import Greeks
    from app.models.option_contract import OptionContract
    from sqlalchemy import select, and_, func

    cache = Cache(get_redis())
    results = {}

    async with AsyncSessionFactory() as session:
        for symbol in symbols:
            try:
                # Pull most recent Greeks snapshot
                latest_time_q = (
                    select(func.max(Greeks.time))
                    .where(Greeks.underlying == symbol)
                )
                latest_time = (await session.execute(latest_time_q)).scalar()

                if not latest_time:
                    continue

                rows = await session.execute(
                    select(Greeks, OptionContract)
                    .join(OptionContract, Greeks.contract_id == OptionContract.id)
                    .where(
                        and_(
                            Greeks.underlying == symbol,
                            Greeks.time == latest_time,
                        )
                    )
                )
                data = rows.all()

                if not data:
                    continue

                spot = data[0].Greeks.spot_price or 0.0
                if spot <= 0:
                    continue

                # Build Polars DataFrame for fast aggregation
                df = pl.DataFrame({
                    "strike": [float(r.OptionContract.strike) for r in data],
                    "option_type": [r.OptionContract.option_type for r in data],
                    "oi": [float(r.Greeks.gamma or 0) * 0 + (r.OptionContract.multiplier or 100) for r in data],
                    "gamma": [float(r.Greeks.gamma or 0) for r in data],
                    "delta": [float(r.Greeks.delta or 0) for r in data],
                    "vanna": [float(r.Greeks.vanna or 0) for r in data],
                    "charm": [float(r.Greeks.charm or 0) for r in data],
                    # OI from latest chain — we join separately for production
                    # For now use a proxy
                })

                # Need actual OI — fetch from option_chains
                from app.models.option_chain import OptionChain
                chain_rows = await session.execute(
                    select(OptionContract.strike, OptionContract.option_type, OptionChain.open_interest)
                    .join(OptionChain, OptionContract.id == OptionChain.contract_id)
                    .where(
                        and_(
                            OptionChain.underlying == symbol,
                            OptionChain.time == latest_time,
                        )
                    )
                )
                oi_data = chain_rows.all()
                oi_map = {(float(r.strike), r.option_type): int(r.open_interest or 0) for r in oi_data}

                # Rebuild df with real OI
                df = pl.DataFrame({
                    "strike": [float(r.OptionContract.strike) for r in data],
                    "option_type": [r.OptionContract.option_type for r in data],
                    "oi": [float(oi_map.get((float(r.OptionContract.strike), r.OptionContract.option_type), 0)) for r in data],
                    "gamma": [float(r.Greeks.gamma or 0) for r in data],
                    "delta": [float(r.Greeks.delta or 0) for r in data],
                    "vanna": [float(r.Greeks.vanna or 0) for r in data],
                    "charm": [float(r.Greeks.charm or 0) for r in data],
                })

                engine = DealerPositioningEngine(spot=spot)
                gex_df = engine.compute_gex_per_strike(df)
                gex_df = engine.flag_key_levels(gex_df)
                summary = engine.compute_summary(gex_df)
                summary.underlying = symbol

                # Persist per-strike rows
                now = datetime.now(tz=timezone.utc)
                positioning_rows = [
                    DealerPositioning(
                        time=now,
                        underlying=symbol,
                        strike=row["strike"],
                        gex_calls=row.get("gex_calls"),
                        gex_puts=row.get("gex_puts"),
                        gex_net=row.get("gex_net"),
                        dex_calls=row.get("dex_calls"),
                        dex_puts=row.get("dex_puts"),
                        dex_net=row.get("dex_net"),
                        vex_net=row.get("vex_net"),
                        cex_net=row.get("cex_net"),
                        oi_calls=row.get("oi_calls"),
                        oi_puts=row.get("oi_puts"),
                        is_call_wall=row.get("is_call_wall", False),
                        is_put_wall=row.get("is_put_wall", False),
                        is_gamma_flip=row.get("is_gamma_flip", False),
                        is_vol_trigger=row.get("is_vol_trigger", False),
                    )
                    for row in gex_df.to_dicts()
                ]
                session.add_all(positioning_rows)

                # Cache summary for API
                summary_dict = {
                    "underlying": symbol,
                    "spot": spot,
                    "total_gex": summary.total_gex,
                    "total_dex": summary.total_dex,
                    "total_vex": summary.total_vex,
                    "total_cex": summary.total_cex,
                    "gamma_flip_price": summary.gamma_flip_price,
                    "call_wall_strike": summary.call_wall_strike,
                    "put_wall_strike": summary.put_wall_strike,
                    "vol_trigger_price": summary.vol_trigger_price,
                    "dealer_regime": summary.dealer_regime,
                    "timestamp": now.isoformat(),
                    "heatmap": engine.heatmap_data(gex_df),
                }
                await cache.set(CacheKey.gex(symbol), summary_dict, CacheTTL.GEX_SUMMARY)
                results[symbol] = {"status": "ok", "regime": summary.dealer_regime}

            except Exception as e:
                logger.error("dealer_snapshot_symbol_failed", symbol=symbol, error=str(e))
                results[symbol] = {"status": "error", "error": str(e)}

        await session.commit()

    return {"status": "ok", "results": results}

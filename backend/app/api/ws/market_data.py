"""
WebSocket endpoints.

All channels authenticate via ?token=<JWT> query param
(Bearer header not supported in browser WebSocket API).

Channels:
  /ws/market-data/{symbol}  — OHLCV ticks (1s interval)
  /ws/greeks/{symbol}       — Greeks stream (10s interval)
  /ws/dealer/{symbol}       — Dealer positioning (30s interval)
  /ws/flow                  — Global flow scanner (real-time)
  /ws/alerts/{user_id}      — User alert stream (push)
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.api.ws.manager import manager
from app.core.cache import Cache, CacheKey, get_redis
from app.core.logging import get_logger
from app.core.security import jwt_manager

logger = get_logger(__name__)

ws_router = APIRouter()


# ------------------------------------------------------------------
# Auth helper
# ------------------------------------------------------------------

async def _authenticate_ws(token: str) -> dict | None:
    """Validate JWT from query param. Returns payload or None."""
    try:
        return jwt_manager.verify_token(token, expected_type="access")
    except jwt.InvalidTokenError:
        return None


# ------------------------------------------------------------------
# Channels
# ------------------------------------------------------------------

@ws_router.websocket("/market-data/{symbol}")
async def ws_market_data(
    websocket: WebSocket,
    symbol: str,
    token: str = Query(...),
):
    """Real-time OHLCV ticks — pushes every second from Polygon WS feed."""
    payload = await _authenticate_ws(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    channel = f"market:{symbol.upper()}"
    await manager.connect(websocket, channel, user_id=payload["sub"])

    try:
        while True:
            # Keep connection alive — actual data pushed by market data ingestor
            # via manager.broadcast(channel, data)
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Handle client ping
                if msg == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send server-side heartbeat
                await websocket.send_json({"type": "heartbeat", "ts": datetime.now(tz=timezone.utc).isoformat()})
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@ws_router.websocket("/greeks/{symbol}")
async def ws_greeks(
    websocket: WebSocket,
    symbol: str,
    token: str = Query(...),
):
    """Live Greeks stream — pushes cached data every 10 seconds."""
    payload = await _authenticate_ws(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    channel = f"greeks:{symbol.upper()}"
    sym = symbol.upper()
    cache = Cache(get_redis())

    await manager.connect(websocket, channel, user_id=payload["sub"])

    try:
        while True:
            # Push latest Greeks from cache
            data = await cache.get(CacheKey.greeks(sym))
            if data:
                await websocket.send_json({
                    "type": "greeks_update",
                    "symbol": sym,
                    "data": data,
                    "ts": datetime.now(tz=timezone.utc).isoformat(),
                })

            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
                if msg == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                pass  # normal — just loop and push again

    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@ws_router.websocket("/dealer/{symbol}")
async def ws_dealer(
    websocket: WebSocket,
    symbol: str,
    token: str = Query(...),
):
    """Dealer positioning stream — pushes GEX snapshot every 30 seconds."""
    payload = await _authenticate_ws(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    channel = f"dealer:{symbol.upper()}"
    sym = symbol.upper()
    cache = Cache(get_redis())

    await manager.connect(websocket, channel, user_id=payload["sub"])

    try:
        while True:
            data = await cache.get(CacheKey.gex(sym))
            if data:
                await websocket.send_json({
                    "type": "dealer_update",
                    "symbol": sym,
                    "data": data,
                    "ts": datetime.now(tz=timezone.utc).isoformat(),
                })

            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if msg == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@ws_router.websocket("/flow")
async def ws_flow(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    Global flow scanner stream.
    Pushes new unusual flow events as they arrive.
    Events are published here by the flow scanner service
    via manager.broadcast('flow', event).
    """
    payload = await _authenticate_ws(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    channel = "flow"
    cache = Cache(get_redis())

    await manager.connect(websocket, channel, user_id=payload["sub"])

    try:
        # Send recent flow on connect
        recent = await cache.get(CacheKey.flow_scanner())
        if recent:
            await websocket.send_json({
                "type": "flow_snapshot",
                "data": recent,
                "ts": datetime.now(tz=timezone.utc).isoformat(),
            })

        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                if msg == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat",
                    "ts": datetime.now(tz=timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@ws_router.websocket("/alerts/{user_id}")
async def ws_alerts(
    websocket: WebSocket,
    user_id: str,
    token: str = Query(...),
):
    """
    Private per-user alert stream.
    Only accessible if JWT sub matches user_id.
    """
    payload = await _authenticate_ws(token)
    if not payload or payload["sub"] != user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    channel = f"alerts:{user_id}"
    await manager.connect(websocket, channel, user_id=user_id)

    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                if msg == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)


@ws_router.websocket("/status")
async def ws_status(websocket: WebSocket, token: str = Query(...)):
    """Connection stats — admin only."""
    payload = await _authenticate_ws(token)
    if not payload or payload.get("role") != "admin":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    try:
        while True:
            stats = {
                "type": "ws_stats",
                "total_connections": manager.total_connections(),
                "channels": manager.channel_stats(),
                "ts": datetime.now(tz=timezone.utc).isoformat(),
            }
            await websocket.send_json(stats)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass

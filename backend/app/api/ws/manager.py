"""
WebSocket Connection Manager.

Manages per-channel rooms of connected clients.
Supports:
  - Multiple subscribers per channel (e.g. all users watching SPX dealer)
  - Per-user private channels (alerts)
  - Heartbeat / ping-pong to detect dead connections
  - Graceful disconnect cleanup

Channel naming convention:
  market:{symbol}    — OHLCV ticks
  greeks:{symbol}    — live Greeks stream
  dealer:{symbol}    — positioning stream
  flow               — global flow scanner
  alerts:{user_id}   — user alert stream
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Thread-safe WebSocket connection manager.
    Backed by asyncio — safe for FastAPI's single event loop.
    """

    HEARTBEAT_INTERVAL = 30   # seconds
    HEARTBEAT_TIMEOUT = 10    # seconds to wait for pong

    def __init__(self) -> None:
        # channel_id → set of WebSocket connections
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        # WebSocket → set of subscribed channel ids
        self._socket_channels: dict[WebSocket, set[str]] = defaultdict(set)
        # WebSocket → user_id (optional, set after auth)
        self._socket_users: dict[WebSocket, str] = {}

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(
        self,
        websocket: WebSocket,
        channel: str,
        user_id: str | None = None,
    ) -> None:
        await websocket.accept()
        self._channels[channel].add(websocket)
        self._socket_channels[websocket].add(channel)
        if user_id:
            self._socket_users[websocket] = user_id

        logger.info(
            "ws_connected",
            channel=channel,
            user_id=user_id,
            total_in_channel=len(self._channels[channel]),
        )

        # Send welcome frame
        await self._send_json(websocket, {
            "type": "connected",
            "channel": channel,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        })

    async def disconnect(self, websocket: WebSocket, channel: str | None = None) -> None:
        """Remove connection from one or all channels."""
        if channel:
            self._channels[channel].discard(websocket)
            self._socket_channels[websocket].discard(channel)
        else:
            # Remove from all channels
            for ch in list(self._socket_channels.get(websocket, set())):
                self._channels[ch].discard(websocket)
            self._socket_channels.pop(websocket, None)
            self._socket_users.pop(websocket, None)

        logger.info("ws_disconnected", channel=channel)

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def broadcast(self, channel: str, data: dict[str, Any]) -> int:
        """
        Broadcast message to all subscribers of a channel.
        Returns count of successfully sent messages.
        Silently removes dead connections.
        """
        if channel not in self._channels:
            return 0

        payload = json.dumps(data, default=str)
        dead: list[WebSocket] = []
        sent = 0

        for ws in list(self._channels[channel]):
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(payload)
                    sent += 1
                else:
                    dead.append(ws)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)

        return sent

    async def send_to_user(self, user_id: str, data: dict[str, Any]) -> bool:
        """Send to the private alert channel for a specific user."""
        channel = f"alerts:{user_id}"
        count = await self.broadcast(channel, data)
        return count > 0

    async def _send_json(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        try:
            await websocket.send_json(data)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def channel_count(self, channel: str) -> int:
        return len(self._channels.get(channel, set()))

    def total_connections(self) -> int:
        return len(self._socket_channels)

    def channel_stats(self) -> dict[str, int]:
        return {ch: len(sockets) for ch, sockets in self._channels.items() if sockets}


# Singleton — shared across all WebSocket routes
manager = ConnectionManager()

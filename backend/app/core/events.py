"""
RabbitMQ event bus.
Provides async publish/subscribe for inter-service messaging.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Coroutine

import aio_pika
from aio_pika import ExchangeType, Message
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractExchange

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_connection: AbstractConnection | None = None
_channel: AbstractChannel | None = None
_exchange: AbstractExchange | None = None

EXCHANGE_NAME = "quantflow.events"


async def init_rabbitmq() -> AbstractConnection:
    global _connection, _channel, _exchange

    _connection = await aio_pika.connect_robust(
        settings.RABBITMQ_URL,
        client_properties={"connection_name": "quantflow-backend"},
    )
    _channel = await _connection.channel()
    await _channel.set_qos(prefetch_count=10)

    _exchange = await _channel.declare_exchange(
        EXCHANGE_NAME,
        ExchangeType.TOPIC,
        durable=True,
    )

    logger.info("rabbitmq_connected", exchange=EXCHANGE_NAME)
    return _connection


async def publish(routing_key: str, payload: dict[str, Any]) -> None:
    """
    Publish a JSON message to the topic exchange.

    routing_key examples:
      "market.options.chain.SPX"
      "dealer.snapshot.SPY"
      "alerts.triggered.user123"
    """
    if _exchange is None:
        raise RuntimeError("RabbitMQ not initialized")

    message = Message(
        body=json.dumps(payload).encode(),
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )

    await _exchange.publish(message, routing_key=routing_key)
    logger.debug("event_published", routing_key=routing_key)


async def subscribe(
    queue_name: str,
    routing_key: str,
    handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    durable: bool = True,
) -> None:
    """Declare a queue, bind it, and start consuming."""
    if _channel is None or _exchange is None:
        raise RuntimeError("RabbitMQ not initialized")

    queue = await _channel.declare_queue(queue_name, durable=durable)
    await queue.bind(_exchange, routing_key=routing_key)

    async def _on_message(message: aio_pika.IncomingMessage) -> None:
        async with message.process():
            try:
                payload = json.loads(message.body)
                await handler(payload)
            except Exception:
                logger.exception("event_handler_error", queue=queue_name)

    await queue.consume(_on_message)
    logger.info("subscribed", queue=queue_name, routing_key=routing_key)


async def close_rabbitmq() -> None:
    if _connection:
        await _connection.close()

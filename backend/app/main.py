"""
QuantFlow Terminal — FastAPI Application Factory.

Startup order:
  1. Configure logging
  2. Initialize DB pool (asyncpg)
  3. Initialize Redis
  4. Initialize RabbitMQ
  5. Mount routers
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import orjson
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.cache import init_redis
from app.core.database import create_db_pool
from app.core.events import close_rabbitmq, init_rabbitmq
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


class ORJSONResponse(JSONResponse):
    """Faster JSON responses using orjson."""
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return orjson.dumps(content, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup and shutdown."""
    configure_logging()
    logger.info("quantflow_starting", env=settings.APP_ENV, version=settings.APP_VERSION)

    # Startup
    app.state.db = await create_db_pool()
    logger.info("database_connected")

    app.state.redis = await init_redis()
    logger.info("redis_connected")

    try:
        app.state.mq = await init_rabbitmq()
        logger.info("rabbitmq_connected")
    except Exception as e:
        # RabbitMQ failure is non-fatal in dev
        logger.warning("rabbitmq_unavailable", error=str(e))
        app.state.mq = None

    logger.info("quantflow_ready")
    yield

    # Shutdown
    logger.info("quantflow_shutting_down")
    if app.state.mq:
        await close_rabbitmq()
    await app.state.redis.close()
    await app.state.db.dispose()
    logger.info("quantflow_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="QuantFlow Terminal API",
        description="Institutional-grade options analytics, dealer positioning, and quantitative research platform.",
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        default_response_class=ORJSONResponse,
        # Disable automatic trailing slash redirects
        redirect_slashes=False,
    )

    # ----------------------------------------------------------------
    # Middleware (order matters — outermost = first to process)
    # ----------------------------------------------------------------
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
    )

    # ----------------------------------------------------------------
    # Routers
    # ----------------------------------------------------------------
    from app.api.v1.router import v1_router
    app.include_router(v1_router, prefix="/api/v1")

    # ----------------------------------------------------------------
    # Health endpoints (no auth)
    # ----------------------------------------------------------------
    @app.get("/health", tags=["system"], include_in_schema=False)
    async def health_check(request: Request):
        checks: dict[str, str] = {"status": "ok", "version": settings.APP_VERSION}

        # DB check
        try:
            from sqlalchemy import text
            async with request.app.state.db.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"
            checks["status"] = "degraded"

        # Redis check
        try:
            await request.app.state.redis.ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "error"
            checks["status"] = "degraded"

        http_status = status.HTTP_200_OK if checks["status"] == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
        return ORJSONResponse(content=checks, status_code=http_status)

    @app.get("/api/v1/ping", tags=["system"])
    async def ping():
        return {"pong": True}

    # ----------------------------------------------------------------
    # Global exception handlers
    # ----------------------------------------------------------------
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled_exception", path=request.url.path, method=request.method)
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_server_error", "detail": "An unexpected error occurred"},
        )

    return app


app = create_app()

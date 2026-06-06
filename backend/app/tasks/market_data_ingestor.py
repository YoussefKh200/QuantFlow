"""Market data ingestion heartbeat."""
from __future__ import annotations
from app.core.logging import get_logger
from app.tasks.celery_app import celery_app
logger = get_logger(__name__)

@celery_app.task(name="app.tasks.market_data_ingestor.heartbeat", bind=True)
def heartbeat(self) -> dict:
    """Check market data connections are alive."""
    return {"status": "ok"}

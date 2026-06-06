"""Nightly regime classification task."""
from __future__ import annotations
from app.core.logging import get_logger
from app.tasks.celery_app import celery_app
logger = get_logger(__name__)

@celery_app.task(name="app.tasks.regime_updater.run_classification", bind=True, max_retries=2, soft_time_limit=600)
def run_classification(self, symbols: list[str]) -> dict:
    """Train/update HMM classifier and classify current regime for each symbol."""
    logger.debug("regime_classification_stub", symbols=symbols)
    return {"status": "stub"}

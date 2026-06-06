"""AI daily report generation task."""
from __future__ import annotations
from app.core.logging import get_logger
from app.tasks.celery_app import celery_app
logger = get_logger(__name__)

@celery_app.task(name="app.tasks.report_generator.generate_daily", bind=True, max_retries=1, soft_time_limit=300)
def generate_daily(self) -> dict:
    """Generate pre-market AI research report and push to users."""
    logger.debug("report_generator_stub")
    return {"status": "stub"}

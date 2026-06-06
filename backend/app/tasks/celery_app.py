"""
Celery application factory.

Queues:
  options   — chain updates + Greeks computation  (high priority, every 1 min)
  dealer    — positioning snapshots               (every 5 min)
  flow      — flow scanner events                 (real-time)
  research  — backtests, monte carlo, reports     (low priority, long-running)
  earnings  — PEAD signal computation             (daily)
  default   — everything else
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import settings


def create_celery_app() -> Celery:
    app = Celery("quantflow")

    app.conf.update(
        # --- Broker / Backend ---
        broker_url=settings.CELERY_BROKER_URL,
        result_backend=settings.CELERY_RESULT_BACKEND,

        # --- Serialization ---
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="America/New_York",
        enable_utc=True,

        # --- Task routing ---
        task_routes={
            "app.tasks.options_chain_updater.*":  {"queue": "options"},
            "app.tasks.greeks_calculator.*":       {"queue": "options"},
            "app.tasks.dealer_snapshot.*":         {"queue": "dealer"},
            "app.tasks.earnings_tracker.*":        {"queue": "earnings"},
            "app.tasks.regime_updater.*":          {"queue": "research"},
            "app.tasks.report_generator.*":        {"queue": "research"},
            "app.tasks.market_data_ingestor.*":    {"queue": "default"},
        },

        # --- Worker settings ---
        worker_prefetch_multiplier=1,   # one task at a time per worker process
        task_acks_late=True,            # ack after completion (not receipt) — safer
        task_reject_on_worker_lost=True,
        worker_max_tasks_per_child=500, # restart worker after 500 tasks (memory leak prevention)

        # --- Result TTL ---
        result_expires=3600,            # 1 hour

        # --- Retry defaults ---
        task_default_retry_delay=30,
        task_max_retries=3,

        # --- Beat schedule ---
        beat_schedule=_build_beat_schedule(),
    )

    # Auto-discover tasks in app.tasks.*
    app.autodiscover_tasks(["app.tasks"])

    return app


def _build_beat_schedule() -> dict:
    """
    Returns the Celery Beat schedule.
    All tasks are gated on market hours in the task itself.
    """
    CORE_SYMBOLS = ["SPX", "SPY", "QQQ", "NDX", "IWM", "TSLA", "NVDA", "AAPL", "META", "MSFT"]

    return {
        # ---- Options chain updates — every 1 minute ----
        "update-option-chains": {
            "task": "app.tasks.options_chain_updater.update_all_chains",
            "schedule": crontab(minute="*/1"),
            "kwargs": {"symbols": CORE_SYMBOLS},
            "options": {"queue": "options"},
        },

        # ---- Greeks computation — every 1 minute ----
        "compute-greeks": {
            "task": "app.tasks.greeks_calculator.compute_all_greeks",
            "schedule": crontab(minute="*/1"),
            "kwargs": {"symbols": CORE_SYMBOLS},
            "options": {"queue": "options"},
        },

        # ---- Dealer snapshots — every 5 minutes ----
        "dealer-snapshot": {
            "task": "app.tasks.dealer_snapshot.take_snapshot",
            "schedule": crontab(minute="*/5"),
            "kwargs": {"symbols": CORE_SYMBOLS},
            "options": {"queue": "dealer"},
        },

        # ---- IV surface update — hourly ----
        "update-iv-surface": {
            "task": "app.tasks.options_chain_updater.update_iv_surfaces",
            "schedule": crontab(minute=0),
            "kwargs": {"symbols": CORE_SYMBOLS},
            "options": {"queue": "options"},
        },

        # ---- PEAD signal computation — after market close ----
        "pead-signals": {
            "task": "app.tasks.earnings_tracker.compute_pead_signals",
            "schedule": crontab(hour=16, minute=30),
            "options": {"queue": "earnings"},
        },

        # ---- Earnings calendar update — daily at 7 AM ----
        "earnings-calendar": {
            "task": "app.tasks.earnings_tracker.update_earnings_calendar",
            "schedule": crontab(hour=7, minute=0),
            "options": {"queue": "earnings"},
        },

        # ---- Regime classification — nightly ----
        "regime-classification": {
            "task": "app.tasks.regime_updater.run_classification",
            "schedule": crontab(hour=23, minute=0),
            "kwargs": {"symbols": CORE_SYMBOLS},
            "options": {"queue": "research"},
        },

        # ---- AI daily report — 5 AM pre-market ----
        "ai-daily-report": {
            "task": "app.tasks.report_generator.generate_daily",
            "schedule": crontab(hour=5, minute=0),
            "options": {"queue": "research"},
        },

        # ---- Market data heartbeat — every 10 min ----
        "market-data-heartbeat": {
            "task": "app.tasks.market_data_ingestor.heartbeat",
            "schedule": crontab(minute="*/10"),
            "options": {"queue": "default"},
        },
    }


# Create the singleton app instance
celery_app = create_celery_app()

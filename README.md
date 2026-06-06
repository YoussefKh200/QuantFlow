# QuantFlow Terminal — Complete Codebase Guide

> Every file, every decision, every algorithm explained.
> Written for engineers joining the project or auditing the implementation.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Layout](#2-repository-layout)
3. [Infrastructure & Docker](#3-infrastructure--docker)
4. [Database Layer](#4-database-layer)
5. [Backend Core](#5-backend-core)
6. [API Layer](#6-api-layer)
7. [WebSocket Layer](#7-websocket-layer)
8. [Service Layer — Quant Engines](#8-service-layer--quant-engines)
9. [Celery Task Layer](#9-celery-task-layer)
10. [Frontend Architecture](#10-frontend-architecture)
11. [Testing](#11-testing)
12. [Kubernetes & Production](#12-kubernetes--production)
13. [Security Model](#13-security-model)
14. [Data Flow Diagrams](#14-data-flow-diagrams)
15. [Key Design Decisions](#15-key-design-decisions)
16. [Development Runbook](#16-development-runbook)

---

## Screenshots

Below are quick visual references for the main modules and architecture. Add the corresponding PNGs into the `img/` folder using the filenames shown below so they render here.

### Options Analytics
![Options Analytics](img/options-analytics.png)

### Liquidity Map
![Liquidity Map](img/liquidity-map.png)

### Dealer Positioning
![Dealer Positioning](img/dealer-positioning.png)

### Futures Flow
![Futures Flow](img/futures-flow.png)

### Earnings Alpha
![Earnings Alpha](img/earnings-alpha.png)

### Vol Regime
![Vol Regime](img/vol-regime.png)

### Flow Analyzer
![Flow Analyzer](img/flow-analyzer.png)

### AI Research
![AI Research](img/ai-research.png)

### Research Lab
![Research Lab](img/research-lab.png)

### Gold Analytics
![Gold Analytics](img/gold-analytics.png)

### Architecture Diagram
![Architecture](img/architecture.png)

## 1. Project Overview

QuantFlow Terminal is a production-grade institutional trading and research platform built for options analytics, dealer positioning, volatility regime detection, and quantitative research.

### What it does

The platform ingests real-time options chain data, computes the full Greeks surface (including second-order Greeks: vanna, charm, vomma, speed), reconstructs dealer net exposure from open interest, classifies market volatility regimes using a Hidden Markov Model, detects unusual options flow, and generates post-earnings momentum signals using the academic PEAD anomaly.

### Technology stack

| Layer | Technology | Why |
|---|---|---|
| API framework | FastAPI 0.111 | Async-native, fastest Python framework, auto-generates OpenAPI |
| Database | PostgreSQL 16 + TimescaleDB | Native time-series hypertables, continuous aggregates, retention policies |
| ORM | SQLAlchemy 2.0 async | Type-safe, async-first, works with TimescaleDB |
| Migrations | Alembic | Industry standard, autogenerate, version-controlled DDL |
| Cache | Redis 7 | Sub-millisecond reads for hot Greeks/GEX data |
| Task queue | Celery 5 + RabbitMQ | Durable task scheduling, per-queue concurrency |
| Numerical | NumPy 1.26 + SciPy 1.13 | Vectorized BSM computations over full option chains |
| DataFrame | Polars 0.20 | Faster than Pandas for GEX aggregation (zero-copy, Rust-backed) |
| ML | hmmlearn 0.3 + scikit-learn | HMM regime classifier |
| Frontend | Next.js 14 App Router | RSC, streaming, file-based routing |
| State | Zustand + Immer | Minimal, type-safe, no boilerplate |
| Charts | ECharts 5 + Plotly.js | ECharts for bar/heat maps; Plotly for 3D WebGL surface |
| WebSocket | Native browser WS + FastAPI | No additional library needed; custom reconnect hook |
| Auth | JWT RS256 + Argon2 | Asymmetric JWT (can verify without private key); Argon2 is PHC winner |
| Infra | Docker Compose + Kubernetes | Compose for dev, K8s for prod with HPA |

---

## 2. Repository Layout

```
quantflow/
├── .env.example              # All environment variables with documentation
├── .gitignore
├── README.md                 # Quick-start guide
├── docker-compose.yml        # Full development stack
│
├── backend/                  # Python FastAPI application
│   ├── pyproject.toml        # Dependencies + tooling config (ruff, mypy, pytest)
│   ├── alembic.ini           # Alembic config pointing to DATABASE_URL
│   ├── alembic/
│   │   ├── env.py            # Async migration runner with TimescaleDB extension setup
│   │   └── versions/
│   │       └── 001_initial_schema.py  # All 16 tables + 8 hypertables
│   └── app/
│       ├── main.py           # FastAPI factory, lifespan, middleware
│       ├── config.py         # Pydantic BaseSettings — all env vars
│       ├── dependencies.py   # FastAPI DI: session, cache, auth, RBAC
│       ├── api/
│       │   ├── v1/           # REST endpoints
│       │   └── ws/           # WebSocket channels
│       ├── core/             # Infrastructure wrappers
│       ├── models/           # SQLAlchemy ORM models
│       ├── schemas/          # Pydantic request/response schemas
│       ├── services/         # Business logic and quant engines
│       └── tasks/            # Celery async tasks
│
├── frontend/                 # Next.js 14 application
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts    # Dark terminal color palette
│   ├── tsconfig.json
│   └── src/
│       ├── app/              # App Router pages
│       ├── components/       # Reusable UI components
│       ├── hooks/            # Custom React hooks
│       ├── lib/              # API client, formatters, utilities
│       ├── store/            # Zustand global state
│       └── types/            # TypeScript type definitions
│
├── infra/
│   ├── docker/               # Dockerfiles + nginx config
│   └── k8s/                  # Kubernetes manifests
│
├── scripts/
│   ├── init-db.sql           # PostgreSQL extensions + tuning (runs on first boot)
│   ├── migrate.sh            # Migration helper (Docker or local)
│   └── seed_symbols.py       # Seed symbols + admin user
│
└── docs/
    └── CODEBASE_GUIDE.md     # This file
```

---

## 3. Infrastructure & Docker

### 3.1 docker-compose.yml

The dev stack declares seven services connected on a shared `quantflow-network` bridge network.

**postgres** — `timescale/timescaledb:latest-pg16`

TimescaleDB is a PostgreSQL extension that adds time-series superpowers. The image ships with both PostgreSQL 16 and the TimescaleDB extension pre-installed. On first boot, Docker mounts `scripts/init-db.sql` into the container's `docker-entrypoint-initdb.d/` directory, which PostgreSQL automatically executes. That SQL file creates the three required extensions (`timescaledb`, `uuid-ossp`, `pg_stat_statements`) and applies recommended PostgreSQL tuning parameters for a mixed OLTP + time-series workload.

A healthcheck using `pg_isready` gates all services that depend on the database — they won't start until Postgres is accepting connections.

**redis** — `redis:7-alpine`

Configured with `--appendonly yes` (AOF persistence so data survives restarts), `--maxmemory 512mb`, and `--maxmemory-policy allkeys-lru` (evicts least-recently-used keys when memory is full). The password is injected from the environment. A healthcheck runs `redis-cli ping` every 5 seconds.

**rabbitmq** — `rabbitmq:3.13-management`

RabbitMQ is used as the Celery broker (durable task queuing) and as the event bus (inter-service pub/sub via aio-pika). The management UI is exposed on port 15672 for debugging. Queue declarations are done programmatically by the application at startup, not in the Docker config.

**backend** — multi-stage build from `infra/docker/backend.Dockerfile`

In development mode the container mounts `./backend:/app` as a volume and runs uvicorn with `--reload`, so code changes take effect instantly without rebuilding. Ports 8000 (API) and 9090 (Prometheus metrics) are forwarded.

**celery-worker** — same image as backend, different command

Runs `celery worker` with four concurrent processes (`--concurrency=4`) listening on six queues: `options`, `dealer`, `research`, `flow`, `earnings`, `default`. Multiple workers can run simultaneously and Celery distributes tasks across them.

**celery-beat** — same image, `celery beat` command

Beat is the scheduler. It reads the `beat_schedule` dict from `celery_app.py` and fires tasks at the right times. **Only one Beat instance should ever run** — multiple beats would fire duplicate tasks. In Kubernetes this is enforced by `replicas: 1`.

**flower** — Celery monitoring UI on port 5555. Shows task history, queue depths, worker status, and failure rates.

**frontend** — `infra/docker/frontend.Dockerfile`, Next.js dev server on port 3000.

**nginx** — only starts with `docker compose --profile proxy up`. Provides a single entry point on port 80 that proxies `/api/` to the backend, `/ws/` to the backend with WebSocket upgrade headers, and everything else to the frontend.

### 3.2 backend.Dockerfile

Three build stages:

**base** — Python 3.11 slim + system dependencies (`build-essential`, `libpq-dev`). Sets `PYTHONDONTWRITEBYTECODE=1` to skip `.pyc` files and `PYTHONUNBUFFERED=1` so log output appears immediately.

**deps** — installs all Python dependencies from `pyproject.toml`. Pinned to exact versions for reproducibility.

**development** — extends `deps`, just exposes ports and sets the uvicorn hot-reload command.

**builder** — compiles all Python files with `compileall` for faster startup in production.

**production** — starts from a fresh slim Python image, copies only the compiled app and installed packages from `builder`. Creates a dedicated non-root `quantflow` user and runs as that user. Includes a `HEALTHCHECK` that hits `/health` every 30 seconds.

### 3.3 frontend.Dockerfile

Three stages: `deps` (npm ci), `development` (dev server), `builder` (next build with `output: "standalone"`), `production` (copies the standalone output which bundles all dependencies into a single directory — no `node_modules` needed at runtime).

### 3.4 nginx.conf

Key configuration decisions:

- Two rate limit zones using `limit_req_zone` with `$binary_remote_addr` (IP-based): `api` at 100 requests/minute and `auth` at 10 requests/minute (brute-force protection for login).
- WebSocket proxying for `/ws/` requires `proxy_http_version 1.1` and the `Upgrade`/`Connection` headers. `proxy_read_timeout 86400s` keeps connections open for 24 hours.
- Security headers on every response: `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy`.
- Gzip compression for text content.

---

## 4. Database Layer

### 4.1 Design Philosophy

The schema separates concerns into three categories:

**Static/reference tables** — `symbols`, `option_contracts`, `users`. These use UUID primary keys (via `uuid-ossp` extension), have standard B-tree indexes, and are queried by the application server.

**Snapshot hypertables** — `option_chains`, `greeks`, `dealer_positioning`, `dealer_summary`, `volatility_metrics`, `flow_events`, `market_regimes`. These are TimescaleDB hypertables partitioned by `time` with 1-day chunks. They receive high-frequency writes and are queried using time-range filters.

**Derived/analytical tables** — `earnings`, `earnings_pead`, `signals`, `backtests`, `alerts`, `research_results`. These are standard PostgreSQL tables with JSONB columns for flexible result storage.

### 4.2 TimescaleDB Hypertables

A hypertable is a PostgreSQL table that TimescaleDB automatically partitions into time-based "chunks". Each chunk is a separate physical table covering a time interval (configured as 1 day for all hypertables in this project).

Benefits:
- Queries with time filters only scan the relevant chunks, not the entire table.
- Old data can be dropped by dropping old chunks — extremely fast compared to `DELETE`.
- Continuous aggregates can materialise hourly/daily summaries without scanning raw data.
- Compression can be applied per-chunk to reduce storage by 10–20x for historical data.

The migration creates hypertables using `create_hypertable('table_name', 'time', chunk_time_interval => INTERVAL '1 day')`. A retention policy is added to `option_chains` to automatically drop data older than 2 years.

### 4.3 All Tables Explained

**symbols** — master list of tradeable instruments. `asset_class` is a CHECK constraint enum: `equity`, `etf`, `index`, `future`, `forex`, `commodity`. `has_options` gates which symbols get options chain updates. `multiplier` defaults to 1.0 but is 50 for ES (E-mini S&P 500 futures) and 100 for equity options.

**option_contracts** — one row per listed option contract. `osi_symbol` is the OCC (Options Clearing Corporation) standardised ticker, e.g. `AAPL  240119C00150000`. This is unique across all contracts and is the canonical identifier. `style` is `american` or `european` (index options like SPX are European — cannot be exercised early). `multiplier` is always 100 for equity options (one contract covers 100 shares).

**option_chains** (hypertable) — one row per (time, contract) snapshot. Stores the market data: bid, ask, mid, last, volume, open interest, implied vol, DTE. The `time` + `contract_id` composite primary key means you can store multiple snapshots of the same contract per day.

**greeks** (hypertable) — one row per (time, contract) snapshot. Stores all computed Greeks: delta, gamma, vega, theta, rho (first-order) and vanna, charm, vomma, speed (second-order). Separated from `option_chains` because Greeks are computed asynchronously by the Celery worker, not at ingestion time.

**dealer_positioning** (hypertable) — one row per (time, underlying, strike). Aggregated GEX/DEX/VEX/CEX by strike across all expirations. The boolean flags (`is_call_wall`, `is_put_wall`, `is_gamma_flip`, `is_vol_trigger`) are set by the positioning engine and drive chart highlighting.

**dealer_summary** (hypertable) — one row per (time, underlying). The aggregate totals (total_gex, total_dex, etc.) and key levels (gamma_flip_price, call_wall_strike, etc.) that the dashboard displays. This is the table the API reads for the summary endpoint — much faster than re-aggregating `dealer_positioning` on every request.

**volatility_metrics** (hypertable) — realized vol (5d/10d/21d/63d), implied vol (ATM 30d/60d), IV rank, IV percentile, skew metrics, term structure slope. Updated nightly by the regime updater task.

**flow_events** (hypertable) — one row per options trade. `trade_type` is `sweep`, `block`, or `split`. `aggressor` is `BUYER` or `SELLER` (inferred from fill price relative to bid/ask). `flow_score` is the composite conviction metric (0–1). `is_unusual` flags trades where size exceeds 5% of open interest or the premium exceeds $250k on a block trade.

**market_regimes** (hypertable) — one row per (time, underlying). The HMM-classified regime plus the gamma regime (derived from dealer_summary) and trend regime. `composite_regime` combines all three.

**earnings** — one row per earnings report. `report_time` is `BMO` (before market open) or `AMC` (after market close). `guidance_raised` is a boolean that tracks whether management raised forward guidance — this has incremental alpha beyond the EPS beat.

**earnings_pead** — post-event analysis keyed to an earnings report. SUE score (Standardized Unexpected Earnings), price drift at 1/5/10/20/60 day windows, and IV crush metrics. Populated by the PEAD engine after each report.

**signals** — trading signals generated by any of the research engines. The `signal_type` field identifies the source: `pead_long`, `pead_short`, `gex_flip`, `vol_regime_change`, etc. `direction` is L (long), S (short), or N (neutral). `actual_return` is backfilled when the position closes.

**backtests** — stores backtest results. `parameters` is JSONB for flexible parameter storage. `equity_curve` and `trade_log` are compressed JSONB arrays — the equity curve is a list of daily NAV values, the trade log lists each trade with entry/exit/return.

**users** — standard auth table. `hashed_password` stores the Argon2 hash (never the plaintext). `role` is a CHECK constraint: `admin`, `trader`, `analyst`, `viewer`.

**alerts** — user-defined alert conditions. `condition` is a JSONB object describing the trigger logic: `{"metric": "gex_net", "symbol": "SPX", "operator": "<", "threshold": -500000000}`. The alert engine evaluates these conditions periodically.

**research_results** — flexible storage for research lab outputs. `research_type` identifies the analysis: `factor`, `pead`, `stat_arb`, `momentum`. `charts` stores S3 keys for chart images.

### 4.4 Alembic Migration: `001_initial_schema.py`

The migration creates all 16 tables in dependency order (parent tables before child tables that reference them via foreign keys). It uses raw `op.execute()` calls for TimescaleDB-specific SQL because Alembic doesn't have native TimescaleDB support.

The `env.py` migration environment is async-aware. It uses `async_engine_from_config` and runs the synchronous Alembic operations via `connection.run_sync()`. Before running migrations, it executes the three `CREATE EXTENSION IF NOT EXISTS` commands to ensure the extensions are available.

The `include_object` filter excludes TimescaleDB internal tables (named `_timescaledb_*`) from autogenerate, preventing Alembic from treating them as untracked tables.

### 4.5 scripts/init-db.sql

This SQL runs automatically when the PostgreSQL container first starts (via the `docker-entrypoint-initdb.d/` mechanism). It creates the three extensions and applies `ALTER SYSTEM SET` tuning parameters optimised for a mixed OLTP + time-series workload:

- `shared_buffers = 512MB` — PostgreSQL's main memory cache. Recommended as 25% of RAM for dedicated servers.
- `effective_cache_size = 1536MB` — hint to the query planner about how much OS page cache is available.
- `random_page_cost = 1.1` — tells the planner SSDs are being used (default is 4.0 for spinning disks), making index scans more attractive.
- `effective_io_concurrency = 200` — allows more simultaneous I/O requests for bitmap heap scans.
- `jit = off` — JIT compilation in PostgreSQL can slow down OLTP queries. Disabled via the asyncpg connection arg `"jit": "off"`.

---

## 5. Backend Core

### 5.1 app/config.py — Pydantic BaseSettings

All configuration is read from environment variables (or a `.env` file). Pydantic validates types and raises at startup if required values are missing.

The `model_validator(mode="after")` decorators auto-build compound URLs from their components. If `DATABASE_URL` is set explicitly in the environment, it's used as-is. If not, it's constructed from `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`. This makes the config work in both scenarios: full URL (common in cloud platforms like Heroku/Railway) and individual components (common in Kubernetes with secrets mounted as env vars).

The `@lru_cache(maxsize=1)` on `get_settings()` means the settings object is only constructed once per process — environment variables are read once at startup, not on every request.

### 5.2 app/main.py — Application Factory

The factory pattern (`create_app()`) rather than a module-level `app = FastAPI()` makes the application testable — tests can call `create_app()` with different settings.

**Lifespan context manager** replaces the deprecated `on_event("startup")` / `on_event("shutdown")` pattern. Resources are created in order: logging → database pool → Redis → RabbitMQ. RabbitMQ failure is caught and logged as a warning (non-fatal) because in development the queue is optional.

**ORJSONResponse** replaces the default `JSONResponse`. orjson is 2-6x faster than the standard `json` module, handles `datetime` objects natively, and can serialize NumPy arrays directly (important for returning Greeks data without manual conversion).

**Middleware order** matters in ASGI: the outermost middleware processes requests first. The order here is GzipMiddleware (outermost) → CORSMiddleware. CORS must be inner because Gzip compresses the response body, and CORS adds headers — the CORS headers must survive Gzip wrapping.

**Global exception handler** catches unhandled exceptions at the application boundary, logs them with full traceback via structlog, and returns a clean 500 JSON response instead of leaking stack traces to clients.

### 5.3 app/core/database.py — Async SQLAlchemy

Uses `asyncpg` driver (pure Python async PostgreSQL client, fastest available). The `create_async_engine` creates a connection pool.

Pool configuration:
- `pool_size=20` — 20 persistent connections kept alive.
- `max_overflow=40` — up to 40 additional temporary connections when the pool is exhausted.
- `pool_pre_ping=True` — before using a connection from the pool, sends `SELECT 1` to check it's still alive. Handles database restarts transparently.
- `pool_recycle=3600` — force-replace connections older than 1 hour to prevent "connection closed by server" errors on long-running processes.
- `server_settings: {"jit": "off"}` — disables JIT for this connection session (belt and suspenders alongside the `ALTER SYSTEM SET`).

Two session factories are provided:
- `get_session()` — commits on success, rolls back on exception. Used for all write endpoints.
- `get_session_no_commit()` — read-only, no commit. Slightly faster for GET endpoints.

### 5.4 app/core/cache.py — Redis Layer

The Redis client is initialised at startup with `from_url()` using the connection URL (which includes password auth). `decode_responses=True` means all values are decoded to Python strings automatically.

The `CacheTTL` class documents the intended freshness of each data type. These values encode business requirements: option chains at 10 seconds (near real-time), earnings calendar at 1 hour (changes rarely), flow scanner at 5 seconds (high-priority real-time feed).

The `CacheKey` class provides a namespaced key builder: `qf:v1:gex:SPX`. The `v1` prefix allows cache-busting during major schema changes by bumping the version.

The `Cache` class wraps the raw Redis client with typed helpers that automatically JSON-serialize/deserialize values using `json.dumps` with `default=str` (handles datetime objects by converting to ISO string).

### 5.5 app/core/security.py — JWT + Argon2

**JWT RS256** uses asymmetric RSA-2048 cryptography. The private key signs tokens (kept secret on the server), and the public key verifies them (can be distributed to other services that need to verify tokens without being able to issue new ones). This is important for microservices architectures.

Access tokens expire in 15 minutes. Refresh tokens expire in 7 days. When a refresh token is used to obtain a new access token, the old refresh token is immediately added to the Redis blacklist with TTL matching its remaining lifetime. This provides one-time-use refresh tokens without a database round-trip.

The `jti` (JWT ID) claim in refresh tokens is a `secrets.token_urlsafe(32)` random value — 192 bits of entropy, completely unguessable.

**Argon2** password hashing uses `passlib` which handles salting, iteration counts, and algorithm versioning automatically. Argon2 won the Password Hashing Competition in 2015 and is the current recommended standard — it's memory-hard (resistant to GPU cracking) and time-hard (resistant to brute force).

### 5.6 app/core/rate_limiter.py — Sliding Window

Uses a Redis sorted set (ZSET) per (user, endpoint) pair. Each request is stored as a member with score = current timestamp in milliseconds. The window is implemented by:

1. Removing entries older than `now - window_ms` using `ZREMRANGEBYSCORE`.
2. Counting remaining entries using `ZCARD`.
3. Adding the current request using `ZADD`.
4. Setting expiry using `EXPIRE`.

All four operations run in a single Redis pipeline (atomic multi-command). Time complexity is O(log N) for the ZRANGEBYSCORE and ZADD operations.

The sliding window is more accurate than fixed windows (which can allow 2× the limit at window boundaries) without the complexity of token bucket algorithms.

Different limits apply to different endpoint prefixes. The `/auth` prefix has a strict 10 req/min limit to prevent brute-force password attacks. Research backtests are limited to 10 per hour because they're computationally expensive.

### 5.7 app/core/events.py — RabbitMQ

Uses `aio-pika`, an async wrapper around the `pika` RabbitMQ client. Declares a single topic exchange (`quantflow.events`). All messages are published with `DeliveryMode.PERSISTENT` so they survive broker restarts.

Routing keys follow a dot-separated hierarchy:
- `market.options.chain.SPX` — option chain update for SPX
- `dealer.snapshot.SPY` — dealer snapshot for SPY
- `alerts.triggered.user-uuid` — alert triggered for a specific user

Consumers bind queues to the exchange with routing key patterns (using `*` and `#` wildcards). The `prefetch_count=10` limit prevents a slow consumer from being overwhelmed with unprocessed messages.

### 5.8 app/core/logging.py — Structured Logging

Uses `structlog` which adds context-aware structured logging on top of the standard library. In production, all log output is JSON (one line per event with timestamp, level, message, and any key-value context). In development, colored console output is used for readability.

The `configure_logging()` function is called exactly once during the lifespan startup. The `cache_logger_on_first_use=True` setting caches the logger chain after first use, eliminating overhead on subsequent calls.

Noisy libraries (uvicorn access log, SQLAlchemy engine, asyncio) are set to WARNING level to reduce log volume.

### 5.9 app/dependencies.py — FastAPI DI

FastAPI's dependency injection system is used throughout. All dependencies are declared as async generator functions (using `yield`) or regular functions.

**`get_session()`** — yields an async database session, commits on success, rolls back on exception, closes always. Because it uses `yield`, FastAPI ensures the cleanup code runs after the response is sent.

**`get_current_user()`** — extracts the Bearer token from the `Authorization` header, verifies it with `jwt_manager`, checks the Redis blacklist for revoked tokens, and loads the User from the database. Returns the User object. Any failure raises a 401.

**`require_role(*roles)`** is a factory function that returns a dependency. Usage: `Depends(require_role("admin", "trader"))`. Returns the user if their role is in the allowed list, raises 403 otherwise.

The `AdminOnly`, `TraderOrAbove`, `AnalystOrAbove` constants are pre-built role dependencies for the most common access patterns.

---

## 6. API Layer

### 6.1 app/api/v1/auth.py

Four endpoints implementing the full JWT auth lifecycle:

**POST /auth/login** — validates credentials, updates `last_login`, issues access + refresh token pair. The access token contains the user's `id` and `role` in the payload. No password is ever returned.

**POST /auth/refresh** — validates the refresh token, checks the blacklist, loads the user, issues a new access token and new refresh token, and blacklists the old refresh token. The old token's Redis TTL matches its remaining JWT lifetime so the blacklist entry auto-expires.

**POST /auth/logout** — decodes (without verifying) the refresh token to extract the `jti`, then blacklists it. Returns 204 regardless of whether the token was valid — logout should always appear to succeed from the client's perspective.

**GET /auth/me** — protected by `CurrentUser` dependency, returns the user profile.

**POST /auth/register** — creates a new account. In production this endpoint should be gated behind admin authentication to prevent public self-registration. The password is hashed with Argon2 before storage.

### 6.2 Options, Dealer, Volatility, Flow, Earnings, Alerts Endpoints

All endpoints are currently implemented as stubs returning `{"status": "stub"}`. The routing structure, authentication dependencies, and URL patterns are fully implemented. The stub bodies will be replaced as each service is completed.

The pattern for every endpoint is:
1. Protected by `CurrentUser` dependency (handles auth)
2. Accept `SessionDep` for DB access if needed
3. Accept `CacheDep` for cache reads
4. Check cache first, fall back to DB query, set cache on miss

---

## 7. WebSocket Layer

### 7.1 app/api/ws/manager.py — Connection Manager

The `ConnectionManager` maintains two dictionaries:
- `_channels: dict[str, set[WebSocket]]` — maps channel names to sets of connected WebSocket objects
- `_socket_channels: dict[WebSocket, set[str]]` — inverse map for cleanup (remove a socket from all its channels when it disconnects)

**Broadcasting** iterates the channel's socket set, sends to each, and silently removes dead sockets (those where `client_state != CONNECTED` or where `send_text()` raises). This prevents dead connections from accumulating.

The manager is a singleton (`manager = ConnectionManager()`) shared across all WebSocket routes. Because FastAPI runs on a single asyncio event loop, there are no concurrency issues — all operations are single-threaded from Python's perspective.

### 7.2 app/api/ws/market_data.py — Channel Handlers

All channels authenticate via `?token=<JWT>` query parameter. The standard `Authorization: Bearer` header is not supported by the browser's WebSocket API, so query-param auth is the correct approach.

Authentication is handled by `_authenticate_ws()` which calls `jwt_manager.verify_token()`. A failed verification closes the WebSocket with code `1008` (Policy Violation) before accepting the connection.

**Channel patterns:**

`/ws/market-data/{symbol}` — listens for messages from the client (ping/pong heartbeat only). Actual OHLCV data is pushed into this channel by the market data ingestor task calling `manager.broadcast("market:SPX", data)`.

`/ws/greeks/{symbol}` — polls the Redis cache every 10 seconds and pushes the latest Greeks snapshot to all subscribers. This is a server-initiated push pattern: the server controls the push cadence.

`/ws/dealer/{symbol}` — same pattern as greeks, polls every 30 seconds.

`/ws/flow` — waits for events pushed by the flow scanner via `manager.broadcast("flow", event)`. On connect, sends the last cached snapshot.

`/ws/alerts/{user_id}` — private channel. JWT must contain `sub == user_id`. Alert events are pushed by the alert engine via `manager.send_to_user(user_id, alert)`.

**Reconnection**: all channels use `asyncio.wait_for(receive_text(), timeout=N)` to detect disconnections. When the client sends no messages for `N` seconds, the server sends a heartbeat. If the socket closes (`WebSocketDisconnect`), the handler exits gracefully and calls `manager.disconnect()` for cleanup.

---

## 8. Service Layer — Quant Engines

### 8.1 BSM Pricer — `app/services/options/bsm.py`

The Black-Scholes-Merton model prices European options using the log-normal stock price assumption. All methods are implemented as static methods on `BSMPricer` and accept both scalar floats and NumPy arrays (vectorised).

**Core inputs:**
- `S` — current spot price
- `K` — option strike price
- `T` — time to expiration in years (e.g. 30 days = 30/365 ≈ 0.0822)
- `r` — continuously compounded risk-free rate (e.g. 5.25% = 0.0525)
- `q` — continuously compounded dividend yield
- `sigma` — annualised implied volatility (e.g. 20% = 0.20)

**d1 and d2** are intermediate quantities that appear in every BSM formula:
```
d1 = [ln(S/K) + (r - q + σ²/2) × T] / (σ√T)
d2 = d1 - σ√T
```
`ln(S/K)` is the log-moneyness — how far the option is in or out of the money. `(r - q + σ²/2) × T` is the expected drift. `σ√T` is the diffusion over the option's remaining life.

**Pricing formula:**
```
Call = S × e^(-qT) × N(d1) - K × e^(-rT) × N(d2)
Put  = K × e^(-rT) × N(-d2) - S × e^(-qT) × N(-d1)
```
where `N()` is the standard normal CDF. `e^(-qT)` discounts the stock for dividends paid during the option's life. `e^(-rT)` discounts the strike to present value.

**Delta** — rate of change of option price with respect to spot price.
- Call delta ∈ (0, 1). Deep ITM call delta → 1 (moves dollar-for-dollar with stock). Deep OTM call delta → 0.
- Put delta ∈ (-1, 0). Call delta - Put delta = e^(-qT) by put-call parity.

**Gamma** — rate of change of delta with respect to spot price (same for calls and puts). Gamma is maximum at-the-money and decreases for ITM/OTM options. High gamma means delta changes rapidly — short-gamma dealers must re-hedge frequently.

**Vega** — sensitivity to a 1% change in implied vol. Scaled by 0.01 so it represents actual dollar change per 1 vol point (not per 100%). Vega is always positive for long options.

**Theta** — time decay per calendar day. Negative for long options (you lose money as time passes). Divided by 365 to convert from per-year to per-day. Near expiry, theta accelerates dramatically (pins to zero value).

**Vanna** (`dDelta/dSigma`) — how much delta changes when volatility changes. Critical for dealer hedging because when IV moves (e.g. during a selloff), dealers' deltas shift and they must re-hedge. The VEX (Vanna Exposure) calculation uses this to estimate the hedging flow from IV changes.

**Charm** (`dDelta/dTime`) — how much delta changes per calendar day. Critical for overnight positioning: as each day passes, dealers' deltas shift purely from time decay, requiring rebalancing. The CEX (Charm Exposure) calculation captures this.

**Vomma** (`dVega/dSigma`) — convexity of vega. Positive vomma means vega increases as IV rises — you benefit more from large IV moves than small ones. Options with high vomma are preferred in volatile regimes.

**Speed** (`dGamma/dS`) — third-order Greek. How much gamma changes as spot moves. Used for advanced delta-hedging strategies that anticipate gamma profile changes across spot levels.

**IV Solver** — uses the Brentq root-finding algorithm from SciPy. The objective function is `BSM_price(S, K, T, r, q, sigma, type) - market_price = 0`. Brentq is guaranteed to converge if the function changes sign within the bracket [1e-6, 10.0] (0.0001% to 1000% vol). Returns `nan` if no solution exists:
- `T <= 0` — expired option, IV is undefined
- `market_price <= intrinsic` — no time value, IV is undefined
- `market_price >= S` — absurd price, no solution

**Batch Greeks** — the `full_greeks_batch()` method processes an entire option chain in vectorised form. It builds a validity mask `(T > 0) & (sigma > 0) & isfinite(sigma)` and only computes Greeks for valid contracts, leaving zeros for invalid ones. This avoids NaN propagation through the NumPy operations.

### 8.2 Volatility Surface — `app/services/options/iv_surface.py`

**VolatilitySurface** fits a Radial Basis Function (RBF) interpolator to scattered IV data points. RBF interpolation fits a function of the form:

```
f(x) = Σ w_i × φ(||x - x_i||)
```

where `φ` is the thin-plate-spline kernel: `φ(r) = r² × ln(r)`. The weights `w_i` are solved by a linear system. The thin-plate-spline minimises the "bending energy" of the surface — it finds the smoothest possible surface that passes through all data points.

The coordinate system uses `(log-moneyness, time_in_years)` rather than `(strike, DTE)`. Log-moneyness `ln(K/S)` centers the ATM strike at zero regardless of the absolute spot level, making the surface comparisons across different underlying prices meaningful.

The **volatility smile** shows a characteristic "smirk" shape: puts with low strikes have higher IV than calls with high strikes (because investors pay more for downside protection). The RBF surface captures this non-linear shape.

**IVRankCalculator** computes two distinct metrics:
- **IV Rank** — where the current IV falls within its own 1-year range: `(current - low) / (high - low) × 100`. An IV rank of 80 means current IV is at the 80th percentile of its range.
- **IV Percentile** — fraction of days in the past year where IV was *below* the current level. An IV percentile of 70 means IV was lower than today on 70% of trading days.

IV rank and percentile can diverge significantly. If IV spiked to 100% once during a crash but has been low most of the year, the rank might be 10 (not far from lows) while the percentile is also low — useful signals are different.

### 8.3 Options Analytics Engine — `app/services/options/analytics_engine.py`

Orchestrates the BSM pricer and surface fitter for a complete chain update cycle:

1. Accept `list[ContractInput]` — market data for every contract (bid, ask, OI, DTE, etc.)
2. Build NumPy arrays from the list (vectorised)
3. Solve IV for mid prices in batch
4. Fill NaN IVs using surface interpolation (contracts where bid=0 or spread too wide)
5. Compute all Greeks in vectorised form
6. Compute dollar exposures (GEX/DEX contributions per contract)
7. Return `list[GreeksOutput]` ready for database insertion

The `GreeksOutput` dataclass includes `dollar_gamma` and `dollar_delta` — the signed dollar exposure contribution of each contract assuming the dealer is short. These feed directly into the dealer positioning engine.

### 8.4 Dealer Positioning Engine — `app/services/dealer/positioning_engine.py`

**Core assumption**: In the US equity options market, dealers (market makers) are systematically net short options — they sell to customers who are predominantly buyers of options for hedging or speculation. Dealers then delta-hedge the resulting exposure by trading the underlying stock or futures.

**GEX (Gamma Exposure)** is the dollar change in the dealer's delta hedge required for a 1% move in the underlying:

```
GEX per contract = Gamma × OI × Multiplier × S² × 0.01
```

Sign convention (following SpotGamma/SqueezeMetrics industry standard):
- **Calls**: dealers are short calls → they are short gamma → call GEX is **negative**
- **Puts**: dealers are short puts → they are long gamma (short puts have positive gamma) → put GEX is **positive**

When total net GEX is **positive** (put-heavy), dealers must **buy** the underlying as it falls (to maintain delta-neutral) and **sell** as it rises. This is a stabilising, mean-reverting force — the "long gamma" regime.

When total net GEX is **negative** (call-heavy), dealers must **sell** the underlying as it falls and **buy** as it rises. This is a destabilising, momentum-amplifying force — the "short gamma" regime. This is why markets tend to be more volatile when GEX is negative.

**DEX (Delta Exposure)** = Delta × OI × Multiplier × S. Total DEX indicates the aggregate directional exposure dealers must hedge via the underlying. Large positive DEX means dealers are net short delta (lots of short call OI) and must be long the underlying.

**VEX (Vanna Exposure)** = Vanna × OI × Multiplier × S² × 0.01. When implied volatility changes, dealers' deltas shift by the vanna amount. High VEX means an IV spike or collapse will trigger large delta re-hedging flows.

**CEX (Charm Exposure)** = Charm × OI × Multiplier. Purely time-based delta decay. This manifests as dealer re-hedging flows on Monday morning (Friday close → Monday open has three days of charm decay).

**Gamma Flip** is the spot level where the running cumulative sum of GEX (sorted by strike, low to high) changes sign. Below the flip: dealers are long gamma. Above: dealers are short gamma. The flip acts as a volatility regime boundary — markets tend to compress above it and expand below it.

**Call Wall** is the strike with maximum call open interest above the current spot. It acts as resistance because as spot approaches the call wall, the negative GEX from those short calls increases, requiring dealers to sell more underlying — creating selling pressure.

**Put Wall** is the mirror image below spot — acts as support.

**Polars** is used for the aggregation step rather than Pandas. The `group_by().agg()` pattern in Polars is 3-10x faster than the Pandas equivalent because Polars uses Rust-native parallelism and avoids Python GIL overhead.

### 8.5 Volatility Regime Classifier — `app/services/volatility/regime_classifier.py`

**Hidden Markov Model** is a statistical model where the system transitions between hidden states (the "regime") and emits observable outputs (the market data features) according to state-specific probability distributions.

The model has 4 hidden states representing volatility regimes. States are not labelled a priori — the HMM discovers them from data. After training, states are sorted by their mean ATM IV (column index 2 of the feature matrix) to assign labels: low vol, normal vol, high vol, expansion.

**Feature vector** per day: `[log_return, rv_21d, atm_iv_30d, iv_rank_norm, skew_25d]`

Each feature captures a different aspect of the vol environment:
- Log return captures recent directional momentum (large negative returns → high vol)
- RV 21d is backward-looking realised vol
- ATM IV 30d is forward-looking implied vol
- IV rank normalised to [0,1] captures where we are in the vol cycle
- 25-delta skew captures put demand (fear/hedging intensity)

**Covariance type `full`** means each state has its own full covariance matrix for the 5-dimensional feature space. This allows the model to capture correlations between features within each regime.

**1000 iterations** for EM (Expectation-Maximisation) convergence. The HMM is retrained nightly with the most recent 252 days of data (1 year).

**Heuristic overlays** override the HMM classification in specific cases:
- `IV/RV < 0.80` → **compression** regime (IV below realised vol — very unusual, precedes spikes)
- `IV/RV > 1.60` AND already in a high-vol HMM state → **expansion** regime

The fallback classifier (used when insufficient training data) uses simple thresholds: IV < 12% → low, IV > 35% → high, IV/RV < 0.8 → compression.

### 8.6 PEAD Engine — `app/services/earnings/pead_engine.py`

**Post-Earnings Announcement Drift** is one of the most well-documented anomalies in academic finance. First documented by Ball & Brown (1968) and confirmed by Bernard & Thomas (1989): stocks continue to drift in the direction of their earnings surprise for 60 days after the announcement.

**SUE (Standardized Unexpected Earnings)** normalises the surprise by historical volatility of surprises:
```
SUE = (EPS_actual - EPS_estimate) / σ(past_surprises)
```
Dividing by `σ` removes the effect of companies that consistently beat by the same amount (analyst anchoring). A SUE of 2.0 means the surprise was 2 standard deviations above expectations — truly unexpected.

The `lookback_quarters=8` (2 years) rolling window for the standard deviation is a balance: too short gives noisy estimates, too long fails to capture changing forecast accuracy.

**Drift computation** uses Cumulative Abnormal Return (CAR) — the stock's return minus the benchmark (S&P 500) return over the holding period. This removes market-wide moves that happen to coincide with the announcement.

**Signal generation** maps SUE quintiles to signals:
- SUE > 2.0: strong long, base confidence 70% (scales up with SUE magnitude)
- SUE 1.0–2.0: moderate long, 65% confidence
- SUE -1.0 to -2.0: moderate short, 60% confidence
- SUE < -2.0: strong short, base confidence 65%

Confidence is the backtested historical win rate for each quintile bucket.

**IV crush** — implied vol typically drops 30-60% after earnings because the "event uncertainty" is resolved. When `iv_crush_expected=True` and the surprise is small, confidence is reduced by 5% — the market may have already priced in the surprise through high pre-earnings IV.

### 8.7 Flow Scanner — `app/services/flow/scanner.py`

**Trade classification** uses three signals:

**Exchange count** — if a single order fills across 3+ exchanges simultaneously, it's a sweep. The order routing system is sending aggressive market orders to every exchange at once, indicating urgency and directional conviction. Sweeps are the most bullish/bearish signal.

**Fill price vs. bid/ask** — if `trade_price >= ask × 0.98`, the buyer paid at or near the ask — an "aggressive buyer." If `trade_price <= bid × 1.02`, the seller hit the bid — an "aggressive seller." The aggressor direction is the key signal: buying calls at the ask is bullish, selling puts at the bid is also bullish.

**Sentiment matrix:**
```
             | BUY (aggressive) | SELL (aggressive) |
Call options |    Bullish       |    Bearish        |
Put options  |    Bearish       |    Bullish        |
```

**Flow Score** composite metric (0-1):
- Size score (20%) — log-normalized trade size. 1 contract scores near zero, 5000 contracts scores near 1.
- Premium score (30%) — log-normalized total premium paid. $1k near zero, $10M near 1.
- OI ratio score (20%) — size relative to open interest. Buying 5% of OI is very significant.
- Type score (20%) — sweep=1.0, block=0.7, split=0.3.
- Aggressiveness (10%) — how close to ask/bid the fill was.

The premium score has the highest weight because it filters out "lottery ticket" small trades and focuses on real money commitment.

**Unusual flag** requires any of: size ≥ 5% of OI, sweep type, or block trade ≥ $250k premium. These are the trades that institutions, hedge funds, and informed traders execute — they require action because someone is putting real money behind a directional view.

### 8.8 VaR Engine — `app/services/risk/var_engine.py`

Three complementary approaches to Value-at-Risk:

**Historical Simulation** — sort the last 252+ daily P&L returns and find the 1st percentile (for 99% VaR). No distributional assumption. The strength is realism: it captures actual fat tails, skewness, and volatility clustering from the data. The weakness is that it assumes history repeats.

Horizon scaling uses the square-root-of-time rule: 5-day VaR = 1-day VaR × √5. This assumes i.i.d. returns (no autocorrelation), which is an approximation.

**Parametric (Cornish-Fisher)** — computes VaR from the empirical mean and standard deviation, but adjusts the normal quantile using the Cornish-Fisher expansion for observed skewness and kurtosis:
```
z_CF = z + (z²-1)S/6 + (z³-3z)K/24 - (2z³-5z)S²/36
```
where z is the normal quantile, S is skewness, K is excess kurtosis. For fat-tailed distributions (S<0, K>0), this gives a larger (more conservative) VaR than the pure normal assumption.

**Monte Carlo** — simulates 10,000 portfolio scenarios using correlated Geometric Brownian Motion. The Cholesky decomposition `L = chol(Σ)` decomposes the correlation matrix, then correlated random returns are generated as `Z @ L.T` where Z is i.i.d. normal. This correctly preserves the specified correlation structure between assets.

If the correlation matrix is not positive definite (e.g., estimated from limited history or with near-collinear assets), the `_nearest_positive_definite()` function regularises it using Higham's (1988) algorithm before Cholesky decomposition.

**Expected Shortfall (ES)** — also called CVaR (Conditional Value-at-Risk). It's the average loss in the tail beyond the VaR threshold. ES is more informative than VaR for risk management because it characterises the severity of tail losses, not just the threshold. Required under Basel III for market risk capital.

**Stress Testing** — 8 named scenarios from historical market events (COVID crash, GFC Lehman, Flash Crash, Taper Tantrum, Ukraine invasion) and 3 hypothetical scenarios (rate shock, VIX spike to 80, soft landing). Each scenario defines shocks to equity, volatility, credit, and gold positions.

### 8.9 Backtest Engine — `app/services/research/backtest_engine.py`

**Performance metrics suite** computed from daily returns:
- **Sharpe ratio**: `annualised_return / annualised_vol`. Measures risk-adjusted return. Above 1.0 is good, above 2.0 is exceptional.
- **Sortino ratio**: uses downside deviation (standard deviation of negative returns only) in the denominator. Penalises only downside volatility, which is what investors actually care about.
- **Calmar ratio**: `annualised_return / |max_drawdown|`. Measures return per unit of worst observed drawdown.
- **Max drawdown**: maximum peak-to-trough decline. Computed on the equity curve as `(equity - running_max) / running_max`.
- **Max drawdown duration**: longest consecutive period in drawdown (the `_max_consecutive_true()` utility counts the longest run of True values in the boolean drawdown mask).
- **Profit factor**: `sum(winning_trades) / |sum(losing_trades)|`. Above 1.5 indicates a viable strategy.

**Walk-Forward Optimization (WFO)** is the gold standard for avoiding in-sample curve-fitting. The implementation slides a window across the data:
1. Train (optimise parameters) on 252-day in-sample window
2. Test on 63-day out-of-sample window (no re-optimisation)
3. Slide forward 63 days and repeat

The **robustness ratio** = OOS Sharpe / IS Sharpe. A healthy strategy has ratio > 0.60. If the ratio is 0.1, the strategy is heavily overfit — it works great in-sample but fails out-of-sample.

**Monte Carlo permutation test** tests whether the observed Sharpe ratio could occur by chance. The signal array is randomly shuffled 1000 times, and the resulting "random" strategy's Sharpe ratio is recorded. The p-value is the fraction of random shuffles that produced a Sharpe ≥ the observed value. p < 0.05 means the result is unlikely to be random chance.

The **equity curve fan chart** bootstraps 500 equity paths by sampling daily returns with replacement (allows the same day to be drawn multiple times). The 5th-50th-95th percentiles of these paths visualise the range of possible outcomes.

---

## 9. Celery Task Layer

### 9.1 app/tasks/celery_app.py — Task Router and Beat Schedule

Celery connects to RabbitMQ as the broker and Redis as the result backend.

**Task routing** assigns tasks to specific queues based on their module path pattern. This allows workers to specialise: a worker that handles only the `options` queue can be tuned for high-frequency, low-latency chain updates, while a `research` queue worker can be given more memory for backtesting.

**Beat schedule** — all tasks are scheduled using `crontab` objects. The schedule is compiled into a dict where keys are human-readable names (used in Flower monitoring). All market-hours gating is done inside the task itself (not the schedule) for flexibility.

Schedule cadence:
- **Every minute**: option chain updates and Greeks computation — near-real-time during market hours
- **Every 5 minutes**: dealer positioning snapshots — allows 5-minute GEX charts
- **Every hour**: IV surface refitting — computationally expensive, doesn't need to be more frequent
- **4:30 PM ET daily**: PEAD signal computation — runs after market close when final prices are confirmed
- **7:00 AM ET daily**: earnings calendar update — pre-market preparation
- **11:00 PM ET nightly**: regime classification — uses full day's data, trains HMM
- **5:00 AM ET daily**: AI report generation — pre-market, catches overnight news

### 9.2 app/tasks/greeks_calculator.py

The task is market-hours gated using a simple check against Eastern Time. It:
1. Queries the latest `OptionChain` + `OptionContract` rows for each symbol (up to 2000 contracts)
2. Builds `ContractInput` objects
3. Calls `OptionsAnalyticsEngine.compute_chain_greeks()`
4. Bulk-inserts `Greeks` rows using `session.add_all()`
5. Caches the ATM IV summary in Redis

`soft_time_limit=55` means Celery sends a `SoftTimeLimitExceeded` exception at 55 seconds. This allows graceful cleanup. `time_limit=60` sends `SIGKILL` at 60 seconds. Together they ensure the task always finishes before the next 1-minute tick.

### 9.3 app/tasks/dealer_snapshot.py

Joins `Greeks` and `OptionChain` tables on the most recent timestamp to get OI alongside Greeks. Builds a Polars DataFrame and runs the dealer positioning engine. Persists per-strike `DealerPositioning` rows and caches the full summary (including the heatmap array) in Redis for the API to serve.

---

## 10. Frontend Architecture

### 10.1 Next.js 14 App Router

The App Router uses the `app/` directory with a segment-based routing system. Layout files (`layout.tsx`) wrap child pages and persist across navigation within their route segment.

**Route groups** use parentheses: `(auth)` and `(platform)`. These group related routes without adding URL segments. `(auth)/login/page.tsx` is served at `/login`, not `/(auth)/login`. The groups allow different root layouts: auth pages get a centered card layout, platform pages get the sidebar+topbar shell.

**Server Components vs Client Components**: all components use `"use client"` in this implementation because they involve real-time data, browser APIs (WebSocket, localStorage), and interactive state. In a future iteration, route pages could be Server Components that fetch initial data server-side and pass it to Client Components as props.

### 10.2 Tailwind Configuration — Dark Terminal Palette

Custom colors in `tailwind.config.ts`:

```
terminal-bg:       #0a0a0f  — deepest background (page background)
terminal-surface:  #0f0f17  — card/panel background (slightly lighter)
terminal-elevated: #14141e  — hover states, elevated panels
terminal-border:   #1e1e2e  — all borders and dividers
terminal-muted:    #2a2a3e  — progress bars, input backgrounds
```

The palette uses a blue-tinged near-black rather than pure grey (#101010) to give a subtle "terminal" feel without being harsh.

```
bull: #22c55e  — green-500 for positive values, long signals
bear: #ef4444  — red-500 for negative values, short signals
warn: #f59e0b  — amber-500 for warnings, neutral signals
brand: #6366f1 — indigo-500 for interactive elements, highlights
```

### 10.3 src/lib/api.ts — Axios Client

**Token refresh interceptor** handles the 401 → refresh → retry cycle transparently. When a request returns 401:
1. The interceptor fires and sets `_isRefreshing = true`
2. Any other in-flight requests that also get 401 are queued in `_refreshQueue`
3. The refresh call is made once
4. On success, all queued requests are retried with the new token

Without the queue mechanism, a burst of 401s (e.g., five simultaneous requests with an expired token) would trigger five parallel refresh calls, causing race conditions.

**Typed API helpers** (`authApi`, `optionsApi`, `dealerApi`, etc.) wrap the raw Axios calls with named, typed functions. This improves IDE completion and makes it easier to grep for all callers of a specific endpoint.

### 10.4 src/hooks/useWebSocket.ts — Reconnect Hook

**Exponential backoff** starts at 500ms and doubles on each reconnect failure: 500ms → 1s → 2s → 4s → ... → 30s (max). This prevents thundering-herd reconnect storms when a backend restarts under load.

The `mountedRef` pattern prevents state updates after unmount. When the component unmounts, `mountedRef.current = false` is set, and all async callbacks check this before calling `setState`. Without this, React would log "Can't perform a state update on an unmounted component" warnings.

**Ping/pong heartbeat** sends `"ping"` every 20 seconds. The server responds with `"pong"` (or a heartbeat JSON frame). This keeps the connection alive through proxies and load balancers that close idle TCP connections.

### 10.5 src/store/index.ts — Zustand Stores

Four stores with Immer middleware (enables direct mutation syntax):

**authStore** — `user`, `token`, `isAuthenticated`. Token is initialised from `localStorage` on store creation (handles page refresh). `setTokens()` persists to both localStorage and store.

**marketStore** — `activeSymbol` (the symbol the whole UI is focused on), `spotPrices` (live prices by symbol). Setting `activeSymbol` triggers re-renders in all components that subscribe to it, allowing the entire dashboard to switch instruments.

**dealerStore** — `summaries` per symbol (keyed by ticker). Stores the full dealer summary including heatmap data. `lastUpdated` tracks freshness for staleness warnings.

**alertStore** — live alert feed with `unreadCount`. `addAlert()` prepends to the array and trims to 100 entries. `markAllRead()` resets the badge count.

### 10.6 src/types/market.ts

All domain types are defined in one file. TypeScript union types (`DealerRegime`, `VolRegime`, `Sentiment`) are string literal unions — they provide autocomplete and prevent typos while remaining serialisable as JSON.

`WsMessage<T>` is a discriminated union type where the `type` field discriminates between message kinds. TypeScript narrows the type automatically in `if (msg.type === "dealer_update")` branches.

### 10.7 src/lib/formatters.ts

All display formatting in one place:
- `fmtGEX()` — formats large dollar numbers with B/M/K suffixes and sign: `+$2.4B`, `-$847M`
- `fmtIV()` — multiplies by 100 and appends `%`: `0.20 → "20.0%"`
- `fmtIVRank()` — shows two decimal places for the 0–100 scale: `82.45`
- `bullBearColor()` — returns Tailwind class name: `text-bull`, `text-bear`, or `text-text-secondary`
- `fmtTimeAgo()` — human-friendly relative time: `"3m ago"`, `"2h ago"`

All functions handle `null` and `undefined` gracefully, returning `"—"` rather than crashing.

### 10.8 Component Architecture

**GexHeatmap.tsx** — uses ECharts 5 with the React wrapper. The chart is imperatively constructed (not declaratively via JSX) because ECharts uses its own virtual DOM. The `useEffect` hook that calls `chart.setOption(option, true)` runs whenever `data` or `summary` changes. The `true` parameter clears the old option before applying the new one, preventing stale series data.

Per-bar colors are set via `itemStyle` in each data point object, allowing the call wall and put wall strikes to glow brighter. The `markLine` feature draws horizontal annotation lines for the gamma flip and spot price.

The tooltip `formatter` returns an HTML string — ECharts supports rich HTML tooltips that display a mini-grid of metrics for each strike.

**VolSurface3D.tsx** — uses `react-plotly.js` loaded via `dynamic(() => import(...), { ssr: false })`. Plotly is a browser-only library (it uses `window` and `document`) so it cannot run during Next.js server-side rendering. The `dynamic` import with `ssr: false` defers it to the client.

The surface uses a Plotly `surface` trace with a custom colorscale mapping low IV (dark blue-black) to high IV (amber). The ATM spine is overlaid as a `scatter3d` trace with `mode: "lines"` — this highlights the term structure curve across the surface.

---

## 11. Testing

### 11.1 Test Structure

```
tests/
├── unit/
│   ├── test_bsm.py           # 27 tests for BSM pricer
│   ├── test_dealer.py        # 13 tests for positioning engine
│   └── test_risk_backtest.py # 26 tests for VaR + backtest
└── integration/              # placeholder (requires running DB)
```

All 66 unit tests pass in under 10 seconds with no external dependencies.

### 11.2 BSM Tests (27 tests)

**Put-call parity** is the most fundamental check. For any set of inputs, the relation `C - P = S × e^(-qT) - K × e^(-rT)` must hold to within floating-point precision (< 1e-8 absolute error). A bug in any of the pricing components will break this identity.

**Delta bounds** verify the mathematical constraints: call delta ∈ (0, 1), put delta ∈ (-1, 0). Deep ITM calls must have delta > 0.95. The relationship `call_delta - put_delta = e^(-qT)` is a stronger test than just checking bounds.

**IV round-trip**: `price(iv) → market_price → solve_iv(market_price) → should_equal_iv`. Any error in the solver propagates through the chain. The test checks to within 1e-6 relative accuracy.

**Batch consistency**: for every contract, `full_greeks_batch()` result must match `full_greeks()` scalar result to within 1e-10. This verifies vectorisation doesn't introduce numerical errors.

### 11.3 Dealer Tests (13 tests)

**GEX sign convention** is business-critical — wrong signs would flip bull/bear signals. The test verifies:
- Pure call OI → negative net GEX (dealer short calls = short gamma)
- Pure put OI → positive net GEX (dealer short puts = positive gamma)

**Gamma flip** test uses a three-strike setup: large put at 4800, nothing at 5000, large call at 5200. The cumulative GEX sum must cross zero somewhere between these strikes.

**Heatmap sorting** verifies results are always returned in ascending strike order (required for the chart to render correctly).

### 11.4 Risk & Backtest Tests (26 tests)

**ES ≥ VaR** is a mathematical requirement. Expected Shortfall is the average of all losses beyond the VaR threshold, so it must always be at least as large as VaR.

**Higher confidence → higher VaR**: 99% VaR must exceed 95% VaR. Larger confidence intervals always capture more extreme events.

**Sqrt-of-time scaling**: 5-day VaR should be approximately √5 ≈ 2.236× the 1-day VaR. The test checks the ratio falls in [2.0, 2.5].

**Diversification**: a 4-asset portfolio with zero correlation must have lower VaR than a single-asset concentrated portfolio with high inter-asset correlation.

**Stress scenario ordering**: `run_all_scenarios()` must return results sorted by severity (worst first). This is required for the UI to show scenarios in the right order.

**Permutation test**: a random signal (shuffled) should produce a p-value > 0.05, confirming the test correctly identifies non-significant results.

---

## 12. Kubernetes & Production

### 12.1 Namespace

All resources are in the `quantflow` namespace for isolation. Namespace-scoped RBAC policies, resource quotas, and network policies can be applied to this namespace without affecting other workloads.

### 12.2 Backend Deployment

**3 replicas minimum** (set in `spec.replicas`) ensures zero downtime during rolling updates. `maxSurge: 2` allows 2 extra pods during updates (so 5 total at peak). `maxUnavailable: 0` means never remove a pod until a new one is healthy.

**Pod anti-affinity** uses `preferredDuringSchedulingIgnoredDuringExecution` to spread pods across different Kubernetes nodes. If 3 pods are all on the same node and that node fails, all 3 go down simultaneously — anti-affinity reduces this risk.

**Resource limits**: `requests` tell Kubernetes how much to reserve when scheduling. `limits` cap what the container can consume. Setting `limits.cpu = 2000m` (2 cores) prevents a runaway task from starving other pods on the same node.

**JWT keys** are mounted from a Kubernetes Secret as a volume at `/run/secrets`. Secrets are base64-encoded in etcd and can be encrypted at rest. The application reads them from the filesystem (not environment variables) because private keys are sensitive and long.

### 12.3 Celery Worker Deployment

Workers have `terminationGracePeriodSeconds: 60` to allow in-progress tasks to complete before the pod is terminated. The liveness probe runs `celery inspect ping` to verify the worker process is responsive (not just alive but actually processing).

### 12.4 HPA (Horizontal Pod Autoscaler)

Backend scales from 3 to 20 replicas based on CPU (scale up at 60%) and memory (scale up at 70%).

Scale-up stabilisation window is 30 seconds — allows fast scaling during market open when load spikes. Scale-down window is 300 seconds (5 minutes) — prevents thrashing when load oscillates.

Scale-up policy: add up to 4 pods per 60-second period. Scale-down policy: remove up to 2 pods per 120-second period.

### 12.5 Ingress

The NGINX ingress controller handles SSL termination (Let's Encrypt via cert-manager), rate limiting, and WebSocket protocol upgrade. The `proxy-read-timeout: 86400` annotation keeps WebSocket connections alive for up to 24 hours.

The `configuration-snippet` annotation injects the WebSocket upgrade headers into the NGINX config for `/ws/` paths.

---

## 13. Security Model

### 13.1 Authentication Flow

```
Client                    Backend                   Redis
  |                          |                         |
  |-- POST /auth/login ----→ |                         |
  |                          |-- verify password       |
  |                          |-- create access token   |
  |                          |-- create refresh token  |
  |←-- {access, refresh} --- |                         |
  |                          |                         |
  |-- GET /api/* (access) → |                         |
  |                          |-- verify JWT RS256      |
  |                          |-- check blacklist ----→ |
  |                          |←-- not blacklisted ---- |
  |                          |-- load user from DB     |
  |←-- 200 OK -------------- |                         |
  |                          |                         |
  |-- POST /auth/refresh --→ |                         |
  |    (refresh token)       |-- verify refresh JWT    |
  |                          |-- check blacklist ----→ |
  |                          |-- blacklist old jti --→ |
  |                          |-- issue new pair        |
  |←-- {new_access, new_refresh}                       |
```

### 13.2 RBAC

Four roles in ascending privilege order:
- **viewer** — read-only access to all analytics data
- **analyst** — viewer + can create backtests, research runs, and alerts
- **trader** — analyst + can access live flow scanner and manage signals
- **admin** — full access including user management

Role is embedded in the JWT access token payload. The `require_role()` dependency checks it on every request without a database round-trip.

### 13.3 Rate Limiting

Per-user, per-endpoint sliding window. The key is `rl:{user_id}:{path_prefix}`. Using user_id (not IP) means authenticated users have separate budgets regardless of shared NAT. Tight limits on `/auth` prevent brute-force attacks.

### 13.4 Input Validation

Pydantic v2 validates all request bodies at the API boundary. Invalid inputs are rejected with 422 before reaching the business logic layer. The `email-validator` library ensures email addresses are syntactically valid and the domain exists (optional DNS check).

### 13.5 Secret Management

In development: secrets are in `.env` (gitignored).
In Kubernetes: secrets are stored as K8s Secrets, mounted as environment variables or files. The JWT private key is mounted as a file (never as an env var) because private keys can contain special characters that corrupt env var parsing.

---

## 14. Data Flow Diagrams

### 14.1 Option Chain Update Cycle (every 1 minute)

```
Polygon.io WebSocket
    │
    ▼
options_chain_updater task (Celery, options queue)
    │  Fetch bid/ask/OI/volume for all listed contracts
    ▼
option_chains table (TimescaleDB hypertable)
    │
    ▼
greeks_calculator task (Celery, options queue)
    │  Pull option_chains, run BSM IV solver + Greeks
    ▼
greeks table (TimescaleDB hypertable)
    │
    ├─→ Redis cache (CacheKey.greeks("SPX"), TTL=10s)
    │       │
    │       └─→ WebSocket /ws/greeks/SPX (push every 10s)
    │               └─→ Frontend GreeksTable component
    │
    └─→ dealer_snapshot task (every 5 min)
            │  Pull greeks + OI, compute GEX/DEX/VEX/CEX
            ▼
        dealer_positioning table + dealer_summary table
            │
            ├─→ Redis cache (CacheKey.gex("SPX"), TTL=30s)
            │       │
            │       └─→ WebSocket /ws/dealer/SPX (push every 30s)
            │               └─→ Frontend GexHeatmap component
            │
            └─→ GET /api/v1/dealer/summary/SPX
                    └─→ Returns cached data instantly
```

### 14.2 Earnings PEAD Signal Cycle (daily at 4:30 PM ET)

```
Earnings data provider (Earnings Whispers / FactSet)
    │
    ▼
update_earnings_calendar task (7 AM daily)
    │  Fetch upcoming reports, upsert to earnings table
    ▼
earnings table
    │
    ▼ (after market close, 4:30 PM)
compute_pead_signals task
    │  For each recent report:
    │    1. Compute SUE from EPS surprise history
    │    2. Compute post-announcement drift (CAR)
    │    3. Measure IV crush
    │    4. Generate directional signal
    ▼
earnings_pead table (drift stats)
signals table (active trading signals)
    │
    └─→ GET /api/v1/earnings/signals
            └─→ Frontend Overview page signals panel
```

### 14.3 Volatility Regime Cycle (nightly at 11 PM)

```
volatility_metrics table (daily ATM IV, HV, IV rank)
    │
    ▼
run_classification task (Celery, research queue)
    │  For each symbol:
    │    1. Fetch 252 days of vol metrics
    │    2. Build feature matrix [log_ret, rv, iv, rank, skew]
    │    3. Train 4-state Gaussian HMM
    │    4. Classify current state
    │    5. Apply heuristic overlays (compression/expansion)
    ▼
market_regimes table
    │
    ├─→ Redis cache (CacheKey.regime("SPX"), TTL=60s)
    │
    └─→ GET /api/v1/volatility/regime/SPX
            └─→ Frontend Volatility page regime banner
```

---

## 15. Key Design Decisions

### Why TimescaleDB instead of InfluxDB or ClickHouse?

TimescaleDB is an extension to PostgreSQL — it retains full SQL compatibility, transactions, joins, foreign keys, and all PostgreSQL features. The options data model has significant relational structure (contracts reference symbols, chains reference contracts, Greeks reference contracts). Managing this relational integrity in a pure time-series database like InfluxDB would require application-level joins and lose foreign key enforcement. ClickHouse is excellent for analytics but poor for transactional writes. TimescaleDB gives the best of both worlds.

### Why Polars instead of Pandas for GEX aggregation?

The GEX computation runs every 5 minutes for all symbols. For SPX, which can have 50,000+ option contracts across all expirations, a Pandas `groupby().agg()` takes roughly 200-400ms. Polars completes the same operation in 20-50ms because it uses Rust-native parallelism, avoids Python GIL overhead, and uses memory-efficient Apache Arrow format internally. For a task that runs 288 times per day, this matters.

### Why RabbitMQ instead of just Redis for task queuing?

Redis-based Celery works (and is simpler), but has important limitations: Redis can't guarantee message durability across restarts without AOF, it lacks message acknowledgement semantics (a crashed worker loses its task), and it doesn't support sophisticated routing. RabbitMQ provides durable queues (messages survive broker restart), proper ACK/NACK semantics (failed tasks are re-queued), topic-based routing (the event bus uses pub/sub patterns), and the management UI gives visibility into queue depths and consumer counts.

### Why async/await throughout instead of sync FastAPI?

Options chain updates involve 2000+ database inserts per symbol every minute. Each insert requires a round-trip to PostgreSQL. With synchronous code, each request blocks a thread while waiting for I/O. With async/await and asyncpg, the Python process can handle thousands of concurrent I/O operations using a single thread — the event loop switches between coroutines while they're waiting for I/O. This is why we can handle 10 symbols × 2000 contracts = 20,000 DB writes per minute on modest hardware.

### Why RBF surface fitting instead of SVI (Stochastic Volatility Inspired)?

SVI is the industry standard for parametric vol surface fitting and guarantees no butterfly arbitrage. However, SVI requires non-linear optimisation for each expiry slice, is sensitive to initial parameter choices, and requires careful calibration for short-dated options near expiry. RBF interpolation is non-parametric, fits any shape automatically, and is extremely fast (`O(n³)` for fitting, `O(n)` for queries after fitting). For the latency requirements of this platform (surface must update every hour), RBF is the right trade-off. An SVI fitter would be the natural upgrade for a production arbitrage desk.

### Why JWT RS256 instead of HS256?

HS256 uses a single symmetric key for both signing and verification. Any service that needs to verify tokens must have the secret key — and if that key is compromised anywhere, attackers can issue tokens. RS256 uses asymmetric RSA: the private key signs tokens (held only by the auth server), and the public key verifies them (can be distributed freely). Future microservices can verify tokens without ever seeing the private key.

### Why Cornish-Fisher VaR instead of just normal VaR?

Financial returns are not normally distributed — they have fat tails (more extreme events than normal) and negative skewness (large crashes are more likely than large rallies). Pure parametric VaR using the normal distribution systematically underestimates tail risk. The Cornish-Fisher expansion corrects for both effects using the observed skewness and excess kurtosis, without requiring Monte Carlo simulation. It's more accurate than normal VaR and faster than Monte Carlo.

---

## 16. Development Runbook

### First-time setup

```bash
# 1. Clone and enter the repository
git clone <repo> && cd quantflow

# 2. Generate RSA keys for JWT
mkdir -p secrets
openssl genrsa -out secrets/jwt_private.pem 2048
openssl rsa -in secrets/jwt_private.pem -pubout -out secrets/jwt_public.pem

# 3. Copy environment config
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, REDIS_PASSWORD, POLYGON_API_KEY

# 4. Start the full stack
docker compose up -d

# 5. Wait for services to be healthy (watch status)
docker compose ps

# 6. Run database migrations
./scripts/migrate.sh up

# 7. Seed symbols and admin user
docker compose exec backend python scripts/seed_symbols.py

# 8. Open the app
open http://localhost:3000
# Login: admin@quantflow.io / ChangeMe123!
```

### Common development tasks

```bash
# View live logs for a service
docker compose logs -f backend

# Run backend tests
docker compose exec backend pytest tests/unit/ -v

# Open a Python shell inside the backend container
docker compose exec backend python

# Apply new migrations after schema changes
./scripts/migrate.sh up

# Create a new migration from model changes
./scripts/migrate.sh revision "add_gold_analytics_table"

# Restart only the backend (after code changes, without --reload)
docker compose restart backend

# Inspect the Celery task queue
docker compose exec celery-worker celery -A app.tasks.celery_app inspect active

# Clear Redis cache
docker compose exec redis redis-cli -a $REDIS_PASSWORD FLUSHDB

# Connect to PostgreSQL
docker compose exec postgres psql -U quantflow quantflow
```

### Environment variables reference

| Variable | Required | Description |
|---|---|---|
| `APP_ENV` | No | `development` / `staging` / `production` |
| `POSTGRES_PASSWORD` | **Yes** | PostgreSQL password |
| `REDIS_PASSWORD` | No | Redis password (empty = no auth) |
| `RABBITMQ_PASSWORD` | **Yes** | RabbitMQ password |
| `JWT_PRIVATE_KEY_PATH` | **Yes** | Path to RSA private key PEM file |
| `JWT_PUBLIC_KEY_PATH` | **Yes** | Path to RSA public key PEM file |
| `POLYGON_API_KEY` | **Yes** | Polygon.io API key for market data |
| `FRED_API_KEY` | No | FRED API for Treasury yields |
| `ALPACA_API_KEY` | No | Alpaca fallback data source |
| `APP_SECRET_KEY` | **Yes** | 32+ char random string |

### Adding a new quant module

1. Create `app/services/{module_name}/engine.py` with the core logic
2. Add the ORM model in `app/models/{module_name}.py`
3. Add migration via `./scripts/migrate.sh revision "add_{module_name}"`
4. Add API endpoints in `app/api/v1/{module_name}.py`
5. Register the router in `app/api/v1/router.py`
6. Add a Celery task in `app/tasks/{module_name}_updater.py`
7. Add the task to the beat schedule in `celery_app.py`
8. Add unit tests in `tests/unit/test_{module_name}.py`
9. Add a frontend page in `frontend/src/app/(platform)/{module_name}/page.tsx`

### Performance tuning

**High Greeks latency**: increase `DB_POOL_SIZE`, add a read replica, or cache more aggressively.

**Slow GEX aggregation**: increase Celery worker concurrency (`--concurrency=8`), or shard symbols across multiple beat schedules.

**Redis memory pressure**: reduce `CacheTTL` values or add more specific cache invalidation (currently TTL-based expiry only).

**Frontend bundle size**: use `dynamic(() => import(...))` for heavy chart libraries (Plotly is already dynamic-loaded). ECharts should be lazy-loaded per-page.

---

*Document generated from QuantFlow Terminal implementation. Last updated: 2026-06-06.*
*Total codebase: 120 files, ~8,500 lines of production code, 66 unit tests.*
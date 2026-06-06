# QUANTFLOW TERMINAL
## Production-Grade Institutional Trading & Research Platform
### Complete Implementation Specification

---

## TABLE OF CONTENTS
1. Folder Structure
2. Database Schema (PostgreSQL + TimescaleDB)
3. API Architecture (FastAPI)
4. Module Specifications (10 Modules)
5. Service Architecture
6. Data Pipeline Architecture
7. Frontend Architecture
8. Infrastructure & Deployment
9. Security Architecture
10. Development Roadmap

---

## 1. FOLDER STRUCTURE

```
quantflow/
├── backend/
│   ├── pyproject.toml
│   ├── alembic/
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                          # FastAPI application factory
│   │   ├── config.py                        # Pydantic BaseSettings
│   │   ├── dependencies.py                  # DI: db, redis, auth
│   │   │
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── router.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── options.py
│   │   │   │   ├── dealer.py
│   │   │   │   ├── liquidity.py
│   │   │   │   ├── futures.py
│   │   │   │   ├── earnings.py
│   │   │   │   ├── volatility.py
│   │   │   │   ├── flow.py
│   │   │   │   ├── research.py
│   │   │   │   ├── gold.py
│   │   │   │   ├── risk.py
│   │   │   │   ├── alerts.py
│   │   │   │   └── portfolio.py
│   │   │   └── ws/
│   │   │       ├── manager.py               # WebSocket connection manager
│   │   │       ├── market_data.py
│   │   │       └── alerts.py
│   │   │
│   │   ├── core/
│   │   │   ├── security.py                  # JWT, password hashing
│   │   │   ├── cache.py                     # Redis wrapper
│   │   │   ├── database.py                  # SQLAlchemy async engine
│   │   │   ├── events.py                    # RabbitMQ publisher/consumer
│   │   │   ├── rate_limiter.py              # Redis-backed sliding window
│   │   │   └── logging.py                   # Structured JSON logging
│   │   │
│   │   ├── models/                          # SQLAlchemy ORM models
│   │   │   ├── base.py
│   │   │   ├── symbol.py
│   │   │   ├── option_contract.py
│   │   │   ├── option_chain.py
│   │   │   ├── greeks.py
│   │   │   ├── dealer_positioning.py
│   │   │   ├── earnings.py
│   │   │   ├── volatility_metric.py
│   │   │   ├── flow_event.py
│   │   │   ├── market_regime.py
│   │   │   ├── signal.py
│   │   │   ├── backtest.py
│   │   │   ├── alert.py
│   │   │   ├── user.py
│   │   │   └── research_result.py
│   │   │
│   │   ├── schemas/                         # Pydantic v2 schemas
│   │   │   ├── options.py
│   │   │   ├── dealer.py
│   │   │   ├── liquidity.py
│   │   │   ├── futures.py
│   │   │   ├── earnings.py
│   │   │   ├── volatility.py
│   │   │   ├── flow.py
│   │   │   ├── research.py
│   │   │   ├── gold.py
│   │   │   ├── risk.py
│   │   │   ├── alerts.py
│   │   │   └── auth.py
│   │   │
│   │   ├── services/                        # Business logic layer
│   │   │   ├── options/
│   │   │   │   ├── analytics_engine.py      # Core Greeks computation
│   │   │   │   ├── iv_surface.py            # Vol surface fitting
│   │   │   │   ├── iv_smile.py
│   │   │   │   ├── term_structure.py
│   │   │   │   └── bsm.py                   # Black-Scholes-Merton
│   │   │   ├── dealer/
│   │   │   │   ├── positioning_engine.py    # GEX/DEX/VEX/CEX
│   │   │   │   ├── gamma_flip.py
│   │   │   │   ├── call_wall.py
│   │   │   │   └── heatmap_builder.py
│   │   │   ├── liquidity/
│   │   │   │   ├── map_engine.py
│   │   │   │   ├── oi_aggregator.py
│   │   │   │   └── magnet_detector.py
│   │   │   ├── futures/
│   │   │   │   ├── flow_engine.py
│   │   │   │   ├── hedge_estimator.py
│   │   │   │   └── impact_scorer.py
│   │   │   ├── earnings/
│   │   │   │   ├── pead_engine.py
│   │   │   │   ├── surprise_calculator.py
│   │   │   │   └── drift_analyzer.py
│   │   │   ├── volatility/
│   │   │   │   ├── regime_classifier.py
│   │   │   │   ├── hmm_model.py
│   │   │   │   ├── iv_rank.py
│   │   │   │   └── realized_vol.py
│   │   │   ├── flow/
│   │   │   │   ├── scanner.py
│   │   │   │   ├── sweep_detector.py
│   │   │   │   └── sentiment_scorer.py
│   │   │   ├── research/
│   │   │   │   ├── backtest_engine.py
│   │   │   │   ├── walk_forward.py
│   │   │   │   ├── monte_carlo.py
│   │   │   │   ├── factor_model.py
│   │   │   │   └── stat_arb.py
│   │   │   ├── gold/
│   │   │   │   ├── analytics.py
│   │   │   │   └── correlation_engine.py
│   │   │   ├── risk/
│   │   │   │   ├── var_engine.py
│   │   │   │   ├── stress_tester.py
│   │   │   │   └── portfolio_risk.py
│   │   │   └── ai/
│   │   │       ├── research_assistant.py
│   │   │       ├── report_generator.py
│   │   │       └── trade_idea_engine.py
│   │   │
│   │   └── tasks/                           # Celery async tasks
│   │       ├── celery_app.py
│   │       ├── market_data_ingestor.py
│   │       ├── options_chain_updater.py
│   │       ├── greeks_calculator.py
│   │       ├── dealer_snapshot.py
│   │       ├── earnings_tracker.py
│   │       ├── regime_updater.py
│   │       └── report_generator.py
│   │
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── fixtures/
│
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── app/                             # Next.js 14 App Router
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx                     # Overview dashboard
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── layout.tsx
│   │   │   ├── (platform)/
│   │   │   │   ├── layout.tsx               # Sidebar + top nav
│   │   │   │   ├── volatility/page.tsx
│   │   │   │   ├── dealer/page.tsx
│   │   │   │   ├── gamma/page.tsx
│   │   │   │   ├── vanna/page.tsx
│   │   │   │   ├── charm/page.tsx
│   │   │   │   ├── liquidity/page.tsx
│   │   │   │   ├── flow/page.tsx
│   │   │   │   ├── research/page.tsx
│   │   │   │   ├── earnings/page.tsx
│   │   │   │   ├── gold/page.tsx
│   │   │   │   ├── portfolio/page.tsx
│   │   │   │   └── settings/page.tsx
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   │   ├── GammaCurve.tsx           # TradingView Lightweight
│   │   │   │   ├── VolSurface3D.tsx         # Plotly 3D surface
│   │   │   │   ├── GexHeatmap.tsx           # ECharts heatmap
│   │   │   │   ├── StrikeLadder.tsx
│   │   │   │   ├── RegimeChart.tsx
│   │   │   │   ├── FlowChart.tsx
│   │   │   │   └── TermStructure.tsx
│   │   │   ├── dealer/
│   │   │   │   ├── GexBar.tsx
│   │   │   │   ├── DealerMap.tsx
│   │   │   │   ├── CallPutWall.tsx
│   │   │   │   └── GammaFlipIndicator.tsx
│   │   │   ├── options/
│   │   │   │   ├── GreeksTable.tsx
│   │   │   │   ├── IVRankBadge.tsx
│   │   │   │   └── ChainViewer.tsx
│   │   │   ├── flow/
│   │   │   │   ├── FlowScanner.tsx
│   │   │   │   ├── SweepAlert.tsx
│   │   │   │   └── FlowSentiment.tsx
│   │   │   ├── research/
│   │   │   │   ├── BacktestChart.tsx
│   │   │   │   ├── FactorTable.tsx
│   │   │   │   └── MonteCarloChart.tsx
│   │   │   └── shared/
│   │   │       ├── DataTable.tsx
│   │   │       ├── MetricCard.tsx
│   │   │       ├── AlertBanner.tsx
│   │   │       ├── WsProvider.tsx
│   │   │       └── TradingLayout.tsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useGex.ts
│   │   │   ├── useVolSurface.ts
│   │   │   ├── useFlowScanner.ts
│   │   │   └── useRealtimeAlerts.ts
│   │   ├── store/                           # Zustand stores
│   │   │   ├── marketStore.ts
│   │   │   ├── dealerStore.ts
│   │   │   └── alertStore.ts
│   │   ├── lib/
│   │   │   ├── api.ts                       # Axios client factory
│   │   │   ├── auth.ts                      # NextAuth config
│   │   │   └── formatters.ts
│   │   └── types/
│   │       ├── options.ts
│   │       ├── dealer.ts
│   │       └── market.ts
│
├── infra/
│   ├── docker/
│   │   ├── backend.Dockerfile
│   │   ├── frontend.Dockerfile
│   │   └── nginx/
│   │       └── nginx.conf
│   ├── docker-compose.yml                   # Dev stack
│   ├── docker-compose.prod.yml
│   ├── k8s/
│   │   ├── namespace.yaml
│   │   ├── deployments/
│   │   │   ├── backend.yaml
│   │   │   ├── frontend.yaml
│   │   │   ├── celery-worker.yaml
│   │   │   └── celery-beat.yaml
│   │   ├── services/
│   │   ├── configmaps/
│   │   ├── secrets/
│   │   ├── hpa/
│   │   └── ingress.yaml
│   └── helm/
│       └── quantflow/
│
├── scripts/
│   ├── seed_symbols.py
│   ├── backfill_options.py
│   └── migrate.sh
│
└── docs/
    ├── architecture/
    ├── api/
    └── runbooks/
```

---

## 2. DATABASE SCHEMA (PostgreSQL 16 + TimescaleDB)

### 2.1 Core Schema — DDL

```sql
-- ============================================================
-- EXTENSIONS
-- ============================================================
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- ============================================================
-- SYMBOLS
-- ============================================================
CREATE TABLE symbols (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker          VARCHAR(20) NOT NULL UNIQUE,
    name            TEXT,
    asset_class     VARCHAR(20) NOT NULL CHECK (asset_class IN ('equity','etf','index','future','forex','commodity')),
    exchange        VARCHAR(20),
    currency        CHAR(3) DEFAULT 'USD',
    multiplier      NUMERIC(12,4) DEFAULT 1.0,
    is_active       BOOLEAN DEFAULT TRUE,
    has_options     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_symbols_ticker ON symbols(ticker);
CREATE INDEX idx_symbols_asset_class ON symbols(asset_class);

-- ============================================================
-- OPTION CONTRACTS
-- ============================================================
CREATE TABLE option_contracts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol_id       UUID NOT NULL REFERENCES symbols(id),
    osi_symbol      VARCHAR(25) NOT NULL UNIQUE,  -- OCC standard
    underlying      VARCHAR(20) NOT NULL,
    expiration      DATE NOT NULL,
    strike          NUMERIC(12,2) NOT NULL,
    option_type     CHAR(1) NOT NULL CHECK (option_type IN ('C','P')),
    multiplier      NUMERIC(8,2) DEFAULT 100.0,
    style           VARCHAR(10) DEFAULT 'american' CHECK (style IN ('american','european')),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_oc_underlying_exp ON option_contracts(underlying, expiration);
CREATE INDEX idx_oc_underlying_strike ON option_contracts(underlying, strike, option_type);
CREATE INDEX idx_oc_expiration ON option_contracts(expiration);

-- ============================================================
-- OPTION CHAINS (snapshot per timestamp — hypertable)
-- ============================================================
CREATE TABLE option_chains (
    time            TIMESTAMPTZ NOT NULL,
    contract_id     UUID NOT NULL REFERENCES option_contracts(id),
    underlying      VARCHAR(20) NOT NULL,
    spot_price      NUMERIC(12,4),
    bid             NUMERIC(12,4),
    ask             NUMERIC(12,4),
    mid             NUMERIC(12,4),
    last            NUMERIC(12,4),
    volume          BIGINT DEFAULT 0,
    open_interest   BIGINT DEFAULT 0,
    iv              NUMERIC(10,6),         -- implied vol (annualized)
    intrinsic       NUMERIC(12,4),
    extrinsic       NUMERIC(12,4),
    dte             SMALLINT,              -- days to expiration
    PRIMARY KEY (time, contract_id)
);
SELECT create_hypertable('option_chains', 'time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_chains_underlying ON option_chains(underlying, time DESC);
SELECT add_retention_policy('option_chains', INTERVAL '2 years');

-- ============================================================
-- GREEKS (per contract per snapshot — hypertable)
-- ============================================================
CREATE TABLE greeks (
    time            TIMESTAMPTZ NOT NULL,
    contract_id     UUID NOT NULL REFERENCES option_contracts(id),
    underlying      VARCHAR(20) NOT NULL,
    spot_price      NUMERIC(12,4),
    -- First-order
    delta           NUMERIC(10,8),
    gamma           NUMERIC(14,10),
    vega            NUMERIC(12,8),
    theta           NUMERIC(12,8),
    rho             NUMERIC(12,8),
    -- Second-order
    vanna           NUMERIC(14,10),
    charm           NUMERIC(14,10),
    vomma           NUMERIC(14,10),
    speed           NUMERIC(16,12),
    -- Vol metrics
    iv              NUMERIC(10,6),
    iv_bid          NUMERIC(10,6),
    iv_ask          NUMERIC(10,6),
    PRIMARY KEY (time, contract_id)
);
SELECT create_hypertable('greeks', 'time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_greeks_underlying ON greeks(underlying, time DESC);

-- ============================================================
-- DEALER POSITIONING (aggregate per strike — hypertable)
-- ============================================================
CREATE TABLE dealer_positioning (
    time                TIMESTAMPTZ NOT NULL,
    underlying          VARCHAR(20) NOT NULL,
    strike              NUMERIC(12,2) NOT NULL,
    expiration          DATE,
    -- Exposures (dollar-adjusted, per strike)
    gex_calls           NUMERIC(20,2),    -- Gamma Exposure calls
    gex_puts            NUMERIC(20,2),    -- Gamma Exposure puts
    gex_net             NUMERIC(20,2),    -- Net GEX
    dex_calls           NUMERIC(20,2),    -- Delta Exposure calls
    dex_puts            NUMERIC(20,2),
    dex_net             NUMERIC(20,2),
    vex_net             NUMERIC(20,2),    -- Vanna Exposure
    cex_net             NUMERIC(20,2),    -- Charm Exposure
    -- Open interest
    oi_calls            BIGINT,
    oi_puts             BIGINT,
    -- Aggregate flags
    is_call_wall        BOOLEAN DEFAULT FALSE,
    is_put_wall         BOOLEAN DEFAULT FALSE,
    is_gamma_flip       BOOLEAN DEFAULT FALSE,
    is_vol_trigger      BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (time, underlying, strike)
);
SELECT create_hypertable('dealer_positioning', 'time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_dp_underlying ON dealer_positioning(underlying, time DESC);
CREATE INDEX idx_dp_gex ON dealer_positioning(underlying, gex_net DESC);

-- ============================================================
-- DEALER SUMMARY (aggregate totals — hypertable)
-- ============================================================
CREATE TABLE dealer_summary (
    time                TIMESTAMPTZ NOT NULL,
    underlying          VARCHAR(20) NOT NULL,
    total_gex           NUMERIC(22,2),
    total_dex           NUMERIC(22,2),
    total_vex           NUMERIC(22,2),
    total_cex           NUMERIC(22,2),
    gamma_flip_price    NUMERIC(12,4),
    call_wall_strike    NUMERIC(12,2),
    put_wall_strike     NUMERIC(12,2),
    vol_trigger_price   NUMERIC(12,4),
    dealer_regime       VARCHAR(20),     -- 'long_gamma','short_gamma','neutral'
    PRIMARY KEY (time, underlying)
);
SELECT create_hypertable('dealer_summary', 'time', chunk_time_interval => INTERVAL '1 day');

-- ============================================================
-- VOLATILITY METRICS (per symbol per time — hypertable)
-- ============================================================
CREATE TABLE volatility_metrics (
    time                TIMESTAMPTZ NOT NULL,
    underlying          VARCHAR(20) NOT NULL,
    -- Realized
    hv_5d               NUMERIC(10,6),
    hv_10d              NUMERIC(10,6),
    hv_21d              NUMERIC(10,6),
    hv_63d              NUMERIC(10,6),
    -- Implied
    atm_iv_30d          NUMERIC(10,6),
    atm_iv_60d          NUMERIC(10,6),
    vix_term            NUMERIC(10,6),
    -- Rank / Percentile (1-year lookback)
    iv_rank             NUMERIC(6,4),    -- 0-100
    iv_percentile       NUMERIC(6,4),    -- 0-100
    -- Skew
    skew_25d            NUMERIC(10,6),   -- 25d put/call skew
    skew_10d            NUMERIC(10,6),
    -- Term structure
    ts_30_60            NUMERIC(10,6),   -- 30d vs 60d
    ts_slope            NUMERIC(10,6),
    -- Regime
    vol_regime          VARCHAR(20),     -- low/normal/high/compression/expansion
    PRIMARY KEY (time, underlying)
);
SELECT create_hypertable('volatility_metrics', 'time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_vm_underlying ON volatility_metrics(underlying, time DESC);

-- ============================================================
-- EARNINGS (fundamental data)
-- ============================================================
CREATE TABLE earnings (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol_id           UUID NOT NULL REFERENCES symbols(id),
    ticker              VARCHAR(20) NOT NULL,
    fiscal_period       VARCHAR(10),     -- 'Q1 2025'
    report_date         DATE NOT NULL,
    report_time         VARCHAR(5),      -- 'BMO' before mkt, 'AMC' after
    eps_actual          NUMERIC(12,4),
    eps_estimate        NUMERIC(12,4),
    eps_surprise        NUMERIC(12,4),
    eps_surprise_pct    NUMERIC(10,6),
    revenue_actual      NUMERIC(20,2),
    revenue_estimate    NUMERIC(20,2),
    revenue_surprise    NUMERIC(20,2),
    guidance_raised     BOOLEAN,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_earnings_ticker ON earnings(ticker, report_date DESC);
CREATE INDEX idx_earnings_date ON earnings(report_date);

-- ============================================================
-- EARNINGS SURPRISES / PEAD (post-event analysis)
-- ============================================================
CREATE TABLE earnings_pead (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    earnings_id         UUID NOT NULL REFERENCES earnings(id),
    ticker              VARCHAR(20) NOT NULL,
    report_date         DATE NOT NULL,
    -- Standardized Unexpected Earnings (SUE)
    sue_score           NUMERIC(10,6),
    -- Price on report day
    price_at_close      NUMERIC(12,4),
    price_day_before    NUMERIC(12,4),
    -- Drift windows
    drift_1d            NUMERIC(10,6),
    drift_5d            NUMERIC(10,6),
    drift_10d           NUMERIC(10,6),
    drift_20d           NUMERIC(10,6),
    drift_60d           NUMERIC(10,6),
    -- IV crush
    iv_pre              NUMERIC(10,6),
    iv_post_1d          NUMERIC(10,6),
    iv_crush_pct        NUMERIC(10,6),
    -- Signal
    signal_direction    CHAR(1),         -- 'L' long, 'S' short
    signal_confidence   NUMERIC(6,4),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_pead_ticker ON earnings_pead(ticker, report_date DESC);
CREATE INDEX idx_pead_sue ON earnings_pead(sue_score DESC);

-- ============================================================
-- FLOW EVENTS (options order flow — hypertable)
-- ============================================================
CREATE TABLE flow_events (
    time                TIMESTAMPTZ NOT NULL,
    contract_id         UUID NOT NULL REFERENCES option_contracts(id),
    underlying          VARCHAR(20) NOT NULL,
    strike              NUMERIC(12,2),
    expiration          DATE,
    option_type         CHAR(1),
    -- Trade details
    trade_size          INTEGER,
    trade_price         NUMERIC(12,4),
    trade_side          VARCHAR(5),      -- 'BUY','SELL'
    aggressor           VARCHAR(5),      -- 'BUYER','SELLER'
    trade_type          VARCHAR(10),     -- 'sweep','block','split'
    premium_total       NUMERIC(16,2),   -- size * price * 100
    -- Classification
    sentiment           VARCHAR(10),     -- 'bullish','bearish','neutral'
    is_unusual          BOOLEAN DEFAULT FALSE,
    is_institutional    BOOLEAN DEFAULT FALSE,
    flow_score          NUMERIC(6,4),    -- 0-1 confidence
    exchange            VARCHAR(10),
    conditions          TEXT[],
    PRIMARY KEY (time, contract_id, trade_size, trade_price)
);
SELECT create_hypertable('flow_events', 'time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_flow_underlying ON flow_events(underlying, time DESC);
CREATE INDEX idx_flow_unusual ON flow_events(is_unusual, time DESC);

-- ============================================================
-- MARKET REGIMES (classified states — hypertable)
-- ============================================================
CREATE TABLE market_regimes (
    time                TIMESTAMPTZ NOT NULL,
    underlying          VARCHAR(20) NOT NULL,
    -- Volatility regime
    vol_regime          VARCHAR(20) NOT NULL,
    vol_state           NUMERIC(6,4),    -- HMM state probability
    -- Gamma regime
    gamma_regime        VARCHAR(20) NOT NULL,  -- 'positive','negative','neutral'
    gex_level           NUMERIC(22,2),
    -- Trend regime
    trend_regime        VARCHAR(20),     -- 'trending','mean_reverting','choppy'
    trend_probability   NUMERIC(6,4),
    -- Overall
    composite_regime    VARCHAR(30),
    regime_confidence   NUMERIC(6,4),
    PRIMARY KEY (time, underlying)
);
SELECT create_hypertable('market_regimes', 'time', chunk_time_interval => INTERVAL '1 day');

-- ============================================================
-- SIGNALS (trading signals)
-- ============================================================
CREATE TABLE signals (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    underlying          VARCHAR(20) NOT NULL,
    signal_type         VARCHAR(30) NOT NULL,  -- 'pead_long','gex_flip','vol_regime_change'
    direction           CHAR(1) CHECK (direction IN ('L','S','N')),
    confidence          NUMERIC(6,4),
    expected_return     NUMERIC(10,6),
    expected_vol        NUMERIC(10,6),
    sharpe_estimate     NUMERIC(8,4),
    entry_price         NUMERIC(12,4),
    target_price        NUMERIC(12,4),
    stop_price          NUMERIC(12,4),
    horizon_days        SMALLINT,
    metadata            JSONB,
    is_active           BOOLEAN DEFAULT TRUE,
    closed_at           TIMESTAMPTZ,
    actual_return       NUMERIC(10,6)
);
CREATE INDEX idx_signals_underlying ON signals(underlying, created_at DESC);
CREATE INDEX idx_signals_type ON signals(signal_type, created_at DESC);
CREATE INDEX idx_signals_active ON signals(is_active, created_at DESC);

-- ============================================================
-- BACKTESTS
-- ============================================================
CREATE TABLE backtests (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(100),
    strategy_name       VARCHAR(50) NOT NULL,
    parameters          JSONB NOT NULL,
    universe            TEXT[],
    start_date          DATE NOT NULL,
    end_date            DATE NOT NULL,
    -- Performance
    total_return        NUMERIC(10,6),
    annualized_return   NUMERIC(10,6),
    annualized_vol      NUMERIC(10,6),
    sharpe_ratio        NUMERIC(8,4),
    sortino_ratio       NUMERIC(8,4),
    calmar_ratio        NUMERIC(8,4),
    max_drawdown        NUMERIC(10,6),
    win_rate            NUMERIC(6,4),
    profit_factor       NUMERIC(8,4),
    num_trades          INTEGER,
    avg_trade_return    NUMERIC(10,6),
    -- Results artifact
    equity_curve        JSONB,           -- compressed time series
    trade_log           JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    created_by          UUID REFERENCES users(id)
);
CREATE INDEX idx_backtests_strategy ON backtests(strategy_name, created_at DESC);

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email               VARCHAR(255) UNIQUE NOT NULL,
    hashed_password     VARCHAR(255) NOT NULL,
    full_name           TEXT,
    role                VARCHAR(20) DEFAULT 'analyst' CHECK (role IN ('admin','trader','analyst','viewer')),
    is_active           BOOLEAN DEFAULT TRUE,
    last_login          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ALERTS
-- ============================================================
CREATE TABLE alerts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID REFERENCES users(id),
    alert_type          VARCHAR(30) NOT NULL,
    underlying          VARCHAR(20),
    condition           JSONB NOT NULL,
    message             TEXT,
    severity            VARCHAR(10) DEFAULT 'info' CHECK (severity IN ('info','warning','critical')),
    is_triggered        BOOLEAN DEFAULT FALSE,
    triggered_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_alerts_user ON alerts(user_id, created_at DESC);
CREATE INDEX idx_alerts_triggered ON alerts(is_triggered, triggered_at DESC);

-- ============================================================
-- RESEARCH RESULTS (lab outputs)
-- ============================================================
CREATE TABLE research_results (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    research_type       VARCHAR(30) NOT NULL,   -- 'factor','pead','stat_arb','momentum'
    title               TEXT,
    parameters          JSONB,
    results             JSONB NOT NULL,
    charts              JSONB,                  -- S3 artifact keys
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    created_by          UUID REFERENCES users(id)
);
```

---

## 3. API ARCHITECTURE (FastAPI)

### 3.1 Application Factory — `app/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.core.database import create_db_pool
from app.core.cache import init_redis
from app.core.events import init_rabbitmq
from app.core.logging import configure_logging
from app.api.v1.router import v1_router
from app.api.ws.manager import ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    app.state.db = await create_db_pool()
    app.state.redis = await init_redis()
    app.state.mq = await init_rabbitmq()
    yield
    await app.state.db.close()
    await app.state.redis.close()
    await app.state.mq.close()

def create_app() -> FastAPI:
    app = FastAPI(
        title="QuantFlow Terminal API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(CORSMiddleware,
        allow_origins=["https://quantflow.io"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(v1_router, prefix="/api/v1")
    app.include_router(ws_router, prefix="/ws")
    return app

app = create_app()
```

### 3.2 Complete API Endpoints

#### Authentication
```
POST   /api/v1/auth/login          — JWT token issuance
POST   /api/v1/auth/refresh        — Token refresh
POST   /api/v1/auth/logout         — Token revocation (Redis blacklist)
GET    /api/v1/auth/me             — Current user profile
```

#### Options Analytics
```
GET    /api/v1/options/chain/{symbol}           — Full option chain
GET    /api/v1/options/chain/{symbol}/{expiry}  — Chain by expiry
GET    /api/v1/options/greeks/{symbol}          — All Greeks for symbol
GET    /api/v1/options/iv-surface/{symbol}      — Vol surface data (3D)
GET    /api/v1/options/iv-smile/{symbol}        — Smile by expiry
GET    /api/v1/options/term-structure/{symbol}  — Term structure curve
GET    /api/v1/options/iv-rank/{symbol}         — IV rank + percentile
GET    /api/v1/options/skew/{symbol}            — Vol skew metrics
POST   /api/v1/options/price                   — Single contract pricer
```

#### Dealer Positioning
```
GET    /api/v1/dealer/gex/{symbol}              — GEX per strike
GET    /api/v1/dealer/dex/{symbol}              — DEX per strike
GET    /api/v1/dealer/vex/{symbol}              — Vanna exposure
GET    /api/v1/dealer/cex/{symbol}              — Charm exposure
GET    /api/v1/dealer/summary/{symbol}          — Aggregate positioning
GET    /api/v1/dealer/heatmap/{symbol}          — Heatmap data
GET    /api/v1/dealer/levels/{symbol}           — Call wall, put wall, flip
GET    /api/v1/dealer/history/{symbol}          — Historical GEX
```

#### Volatility Regime
```
GET    /api/v1/volatility/regime/{symbol}       — Current regime
GET    /api/v1/volatility/history/{symbol}      — Regime time series
GET    /api/v1/volatility/metrics/{symbol}      — HV, IV, rank, percentile
GET    /api/v1/volatility/skew/{symbol}         — Skew metrics
```

#### Futures Flow
```
GET    /api/v1/futures/flow/{symbol}            — Net flow estimate
GET    /api/v1/futures/hedge-requirements       — Dealer hedge calc
GET    /api/v1/futures/impact-score/{symbol}    — Market impact score
GET    /api/v1/futures/trend-probability        — Trend vs mean revert
```

#### Earnings & PEAD
```
GET    /api/v1/earnings/calendar                — Upcoming earnings
GET    /api/v1/earnings/history/{symbol}        — Historical earnings
GET    /api/v1/earnings/pead/{symbol}           — PEAD drift stats
GET    /api/v1/earnings/signals                 — Active PEAD signals
GET    /api/v1/earnings/alpha-score/{symbol}    — Alpha opportunity score
```

#### Flow Analyzer
```
GET    /api/v1/flow/scanner                     — Live flow feed
GET    /api/v1/flow/unusual                     — Unusual activity
GET    /api/v1/flow/blocks                      — Block trades
GET    /api/v1/flow/sweeps                      — Sweep orders
GET    /api/v1/flow/sentiment/{symbol}          — Bull/bear flow score
GET    /api/v1/flow/institutional/{symbol}      — Institutional activity
```

#### Research Lab
```
POST   /api/v1/research/backtest               — Submit backtest job
GET    /api/v1/research/backtest/{id}          — Get results
GET    /api/v1/research/backtests             — List backtests
POST   /api/v1/research/walk-forward          — Walk-forward analysis
POST   /api/v1/research/monte-carlo           — Monte Carlo run
GET    /api/v1/research/factors/{symbol}       — Factor exposures
GET    /api/v1/research/results               — Research results
```

#### Alerts
```
POST   /api/v1/alerts                          — Create alert
GET    /api/v1/alerts                          — List alerts
DELETE /api/v1/alerts/{id}                     — Delete alert
GET    /api/v1/alerts/triggered               — Recent triggers
```

#### WebSocket Channels
```
WS     /ws/market-data/{symbol}               — Real-time OHLCV ticks
WS     /ws/greeks/{symbol}                    — Live Greeks stream
WS     /ws/dealer/{symbol}                    — Dealer positioning stream
WS     /ws/flow                               — Global flow scanner stream
WS     /ws/alerts/{user_id}                   — User alert stream
```

### 3.3 Caching Strategy

```python
CACHE_TTL = {
    "option_chain":      10,      # seconds — near real-time
    "greeks":            10,
    "gex_summary":       30,
    "vol_surface":       60,
    "iv_rank":           300,
    "earnings_calendar": 3600,
    "pead_signals":      300,
    "regime":            60,
    "flow_scanner":      5,
}

# Cache key pattern: "qf:{version}:{endpoint}:{symbol}:{params_hash}"
# Example: "qf:v1:gex:SPX:a1b2c3d4"
```

---

## 4. MODULE SPECIFICATIONS

---

### MODULE 1: OPTIONS ANALYTICS ENGINE

**Purpose**: Compute complete Greeks profile for every listed option contract in real time.

**Core Algorithms**:

#### Black-Scholes-Merton Pricer (`services/options/bsm.py`)

```python
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq

class BSMPricer:
    """
    Vectorized BSM implementation for production Greeks calculation.
    All inputs should be NumPy arrays for batch processing.
    """

    @staticmethod
    def d1(S, K, T, r, q, sigma):
        return (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

    @staticmethod
    def d2(S, K, T, r, q, sigma):
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        return d1 - sigma * np.sqrt(T)

    @staticmethod
    def price(S, K, T, r, q, sigma, option_type):
        """
        S: spot price
        K: strike
        T: time to expiration (years)
        r: risk-free rate
        q: dividend yield
        sigma: implied volatility (annualized)
        """
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        d2 = BSMPricer.d2(S, K, T, r, q, sigma)
        phi = np.where(option_type == 'C', 1, -1)
        price = phi * (
            S * np.exp(-q * T) * norm.cdf(phi * d1)
            - K * np.exp(-r * T) * norm.cdf(phi * d2)
        )
        return np.maximum(price, 0)

    @staticmethod
    def delta(S, K, T, r, q, sigma, option_type):
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        if option_type == 'C':
            return np.exp(-q * T) * norm.cdf(d1)
        return -np.exp(-q * T) * norm.cdf(-d1)

    @staticmethod
    def gamma(S, K, T, r, q, sigma):
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        return np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))

    @staticmethod
    def vega(S, K, T, r, q, sigma):
        # Returns per 1% move in IV
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        return S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T) * 0.01

    @staticmethod
    def theta(S, K, T, r, q, sigma, option_type):
        # Returns per calendar day
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        d2 = d1 - sigma * np.sqrt(T)
        phi = np.where(option_type == 'C', 1, -1)
        term1 = -S * np.exp(-q * T) * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
        term2 = -phi * r * K * np.exp(-r * T) * norm.cdf(phi * d2)
        term3 = phi * q * S * np.exp(-q * T) * norm.cdf(phi * d1)
        return (term1 + term2 + term3) / 365

    @staticmethod
    def vanna(S, K, T, r, q, sigma):
        """dDelta/dVol — important for dealer hedging"""
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        d2 = d1 - sigma * np.sqrt(T)
        return -np.exp(-q * T) * norm.pdf(d1) * d2 / sigma

    @staticmethod
    def charm(S, K, T, r, q, sigma, option_type):
        """dDelta/dTime — critical for overnight positioning"""
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        d2 = d1 - sigma * np.sqrt(T)
        phi = np.where(option_type == 'C', 1, -1)
        return phi * np.exp(-q * T) * (
            norm.pdf(d1) * (q - (r - q + (2 * d1 - d2) * sigma / (2 * np.sqrt(T))) / (sigma * np.sqrt(T)))
            - phi * q * norm.cdf(phi * d1)
        )

    @staticmethod
    def vomma(S, K, T, r, q, sigma):
        """dVega/dVol — convexity of vega"""
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        d2 = d1 - sigma * np.sqrt(T)
        vega = BSMPricer.vega(S, K, T, r, q, sigma)
        return vega * d1 * d2 / sigma

    @staticmethod
    def speed(S, K, T, r, q, sigma):
        """dGamma/dS — third order"""
        d1 = BSMPricer.d1(S, K, T, r, q, sigma)
        gamma = BSMPricer.gamma(S, K, T, r, q, sigma)
        return -gamma / S * (d1 / (sigma * np.sqrt(T)) + 1)

    @classmethod
    def implied_vol(cls, S, K, T, r, q, market_price, option_type,
                    bounds=(1e-6, 10.0), tol=1e-8):
        """
        Newton-Raphson / Brentq hybrid IV solver.
        Returns NaN if no solution found.
        """
        intrinsic = max(
            (S - K) if option_type == 'C' else (K - S),
            0
        )
        if market_price <= intrinsic or T <= 0:
            return np.nan

        def objective(sigma):
            return cls.price(S, K, T, r, q, sigma, option_type) - market_price

        try:
            return brentq(objective, *bounds, xtol=tol, full_output=False)
        except (ValueError, RuntimeError):
            return np.nan
```

#### Vol Surface Fitting (`services/options/iv_surface.py`)

```python
import numpy as np
from scipy.interpolate import RBFInterpolator
from typing import Tuple

class VolatilitySurface:
    """
    Interpolated volatility surface using Radial Basis Functions.
    Inputs: (log-moneyness, DTE) grid -> IV.
    """

    def __init__(self, strikes, dtes, ivs, spot):
        """
        strikes: 1D array of strikes
        dtes: 1D array of days-to-expiration
        ivs: 1D array of implied vols (same length)
        spot: current spot price
        """
        self.spot = spot
        log_m = np.log(strikes / spot)  # log-moneyness
        t = dtes / 365.0                # years
        X = np.column_stack([log_m, t])
        self.rbf = RBFInterpolator(X, ivs, kernel='thin_plate_spline')
        self._raw = (log_m, t, ivs)

    def query(self, strike: float, dte: float) -> float:
        x = np.array([[np.log(strike / self.spot), dte / 365.0]])
        return float(self.rbf(x)[0])

    def surface_grid(self, n_strikes=50, n_expiries=20) -> dict:
        log_m_range = np.linspace(-0.3, 0.3, n_strikes)
        t_range = np.linspace(7/365, 2.0, n_expiries)
        LM, T = np.meshgrid(log_m_range, t_range)
        pts = np.column_stack([LM.ravel(), T.ravel()])
        ivs = self.rbf(pts).reshape(n_expiries, n_strikes)
        strikes = self.spot * np.exp(log_m_range)
        dtes = t_range * 365
        return {"strikes": strikes.tolist(), "dtes": dtes.tolist(), "ivs": ivs.tolist()}
```

**Database tables used**: `option_contracts`, `option_chains`, `greeks`, `volatility_metrics`

**API endpoints**: `/api/v1/options/*`

**Scalability**: Greeks computed in Celery workers using vectorized NumPy. One worker per symbol batch of 1000 contracts. Cached in Redis for 10s TTL. TimescaleDB continuous aggregates for historical queries.

---

### MODULE 2: DEALER POSITIONING ENGINE

**Purpose**: Reconstruct dealer gamma/delta/vanna/charm exposure from open interest data.

**Core Algorithm** (`services/dealer/positioning_engine.py`):

```python
import polars as pl
import numpy as np
from typing import Optional

class DealerPositioningEngine:
    """
    Market maker / dealer net exposure estimation.

    ASSUMPTION: Dealers are short options (sell to customers) 
    and must delta-hedge. This is a well-documented structural 
    feature of US equity options markets.

    GEX formula (per strike per expiry):
      GEX = Gamma * OI * multiplier * spot^2 * 0.01
      (sign: +1 for calls, -1 for puts — dealer is short)
    
    DEX formula:
      DEX = Delta * OI * multiplier * spot
    
    VEX formula:
      VEX = Vanna * OI * multiplier * spot^2 * 0.01
    
    CEX formula:
      CEX = Charm * OI * multiplier
    """

    def __init__(self, spot: float, multiplier: float = 100.0):
        self.spot = spot
        self.multiplier = multiplier

    def compute_gex_per_strike(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        df must have columns:
          strike, option_type, oi, gamma, delta, vanna, charm
        """
        # Sign convention: calls positive (dealer short = negative gamma),
        # puts negative (dealer short puts = positive gamma)
        # Industry standard: GEX positive means dealers long gamma
        df = df.with_columns([
            (pl.col("gamma")
             * pl.col("oi")
             * self.multiplier
             * (self.spot ** 2)
             * 0.01
             * pl.when(pl.col("option_type") == "C").then(1).otherwise(-1)
            ).alias("gex"),

            (pl.col("delta")
             * pl.col("oi")
             * self.multiplier
             * self.spot
             * pl.when(pl.col("option_type") == "C").then(1).otherwise(-1)
            ).alias("dex"),

            (pl.col("vanna")
             * pl.col("oi")
             * self.multiplier
             * (self.spot ** 2)
             * 0.01
            ).alias("vex"),

            (pl.col("charm")
             * pl.col("oi")
             * self.multiplier
            ).alias("cex"),
        ])

        return df.group_by("strike").agg([
            pl.col("gex").filter(pl.col("option_type") == "C").sum().alias("gex_calls"),
            pl.col("gex").filter(pl.col("option_type") == "P").sum().alias("gex_puts"),
            pl.col("gex").sum().alias("gex_net"),
            pl.col("dex").filter(pl.col("option_type") == "C").sum().alias("dex_calls"),
            pl.col("dex").filter(pl.col("option_type") == "P").sum().alias("dex_puts"),
            pl.col("dex").sum().alias("dex_net"),
            pl.col("vex").sum().alias("vex_net"),
            pl.col("cex").sum().alias("cex_net"),
            pl.col("oi").filter(pl.col("option_type") == "C").sum().alias("oi_calls"),
            pl.col("oi").filter(pl.col("option_type") == "P").sum().alias("oi_puts"),
        ]).sort("strike")

    def find_gamma_flip(self, gex_by_strike: pl.DataFrame) -> Optional[float]:
        """
        The gamma flip is where cumulative GEX crosses zero.
        Find the strike where running sum changes sign.
        """
        df = gex_by_strike.sort("strike")
        strikes = df["strike"].to_list()
        gex = df["gex_net"].to_list()
        cumsum = 0
        for i, (s, g) in enumerate(zip(strikes, gex)):
            prev = cumsum
            cumsum += g
            if prev * cumsum < 0:  # sign change
                # Linear interpolation
                frac = abs(prev) / (abs(prev) + abs(cumsum))
                return strikes[i-1] + frac * (s - strikes[i-1])
        return None

    def find_call_wall(self, df: pl.DataFrame) -> float:
        """Strike with maximum call OI above spot — acts as resistance."""
        above = df.filter(pl.col("strike") > self.spot)
        return float(above.sort("oi_calls", descending=True)["strike"][0])

    def find_put_wall(self, df: pl.DataFrame) -> float:
        """Strike with maximum put OI below spot — acts as support."""
        below = df.filter(pl.col("strike") < self.spot)
        return float(below.sort("oi_puts", descending=True)["strike"][0])

    def vol_trigger(self, gex_total: float, spot: float) -> str:
        """
        When GEX > 0 (dealers long gamma): market tends to mean-revert.
        When GEX < 0 (dealers short gamma): market tends to trend/be volatile.
        """
        threshold = spot * 1e7  # normalized
        if gex_total > threshold:
            return "long_gamma"
        elif gex_total < -threshold:
            return "short_gamma"
        return "neutral"
```

---

### MODULE 3: VOLATILITY REGIME ENGINE

**Core Algorithm** (`services/volatility/regime_classifier.py`):

```python
import numpy as np
import pandas as pd
from hmmlearn import hmm
from enum import Enum

class VolRegime(str, Enum):
    LOW = "low_volatility"
    NORMAL = "normal_volatility"
    HIGH = "high_volatility"
    COMPRESSION = "compression"
    EXPANSION = "expansion"
    EVENT = "event_driven"

class RegimeClassifier:
    """
    Hidden Markov Model-based volatility regime detection.
    4-state HMM trained on realized volatility + VIX + IV rank.
    """
    N_STATES = 4
    WINDOW = 252  # 1 year lookback for training

    def __init__(self):
        self.model = hmm.GaussianHMM(
            n_components=self.N_STATES,
            covariance_type="full",
            n_iter=1000,
            random_state=42,
        )
        self._trained = False

    def _build_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Feature vector: [log_return, rv_21d, iv_atm, iv_rank, skew_25d]
        """
        return np.column_stack([
            np.log(df["close"].pct_change().fillna(0) + 1),
            df["hv_21d"].fillna(method="ffill"),
            df["atm_iv_30d"].fillna(method="ffill"),
            df["iv_rank"].fillna(50) / 100,
            df["skew_25d"].fillna(0),
        ])

    def train(self, df: pd.DataFrame):
        X = self._build_features(df.tail(self.WINDOW))
        self.model.fit(X)
        self._trained = True
        # Sort states by mean volatility
        means = self.model.means_[:, 2]  # sort by IV mean
        self._state_order = np.argsort(means)

    def classify(self, df: pd.DataFrame) -> dict:
        if not self._trained:
            raise RuntimeError("Model not trained")
        X = self._build_features(df.tail(20))
        states = self.model.predict(X)
        proba = self.model.predict_proba(X)
        current_raw_state = states[-1]
        sorted_pos = np.where(self._state_order == current_raw_state)[0][0]
        regimes = [VolRegime.LOW, VolRegime.NORMAL, VolRegime.HIGH, VolRegime.EXPANSION]
        regime = regimes[sorted_pos]
        # Additional heuristics
        rv = df["hv_21d"].iloc[-1]
        iv = df["atm_iv_30d"].iloc[-1]
        if iv / rv < 0.85:
            regime = VolRegime.COMPRESSION
        elif iv / rv > 1.5 and sorted_pos >= 2:
            regime = VolRegime.EXPANSION
        return {
            "regime": regime.value,
            "state_probability": float(proba[-1, current_raw_state]),
            "rv_21d": float(rv),
            "atm_iv": float(iv),
            "iv_rv_ratio": float(iv / rv),
        }
```

---

### MODULE 4: EARNINGS ALPHA ENGINE (PEAD)

**Core Algorithm** (`services/earnings/pead_engine.py`):

```python
import pandas as pd
import numpy as np
from scipy import stats

class PEADEngine:
    """
    Post-Earnings Announcement Drift research engine.
    
    SUE = (EPS_actual - EPS_expected) / std_dev_of_surprise_history
    
    Academic literature (Ball & Brown 1968, Bernard & Thomas 1989)
    consistently shows stocks with extreme positive SUE continue
    to drift upward for 60 days. We exploit this systematically.
    """

    @staticmethod
    def compute_sue(ticker_earnings: pd.DataFrame, lookback: int = 8) -> pd.Series:
        """
        Standardized Unexpected Earnings.
        lookback: number of prior quarters for std dev.
        """
        surprise = ticker_earnings["eps_surprise_pct"]
        rolling_std = surprise.shift(1).rolling(lookback, min_periods=4).std()
        return surprise / rolling_std.replace(0, np.nan)

    @staticmethod
    def compute_drift(prices: pd.DataFrame, event_date: str, windows=(5, 10, 20, 60)):
        """
        Compute cumulative abnormal returns (CAR) after earnings.
        Uses market-adjusted returns (subtract SPX return).
        """
        event_idx = prices.index.get_loc(event_date)
        results = {}
        for w in windows:
            end_idx = min(event_idx + w, len(prices) - 1)
            if end_idx <= event_idx:
                results[f"drift_{w}d"] = np.nan
                continue
            cum_ret = (prices["close"].iloc[end_idx] / prices["close"].iloc[event_idx]) - 1
            mkt_ret = (prices["spx"].iloc[end_idx] / prices["spx"].iloc[event_idx]) - 1
            results[f"drift_{w}d"] = cum_ret - mkt_ret
        return results

    def generate_signal(self, sue: float, iv_crush_expected: bool = True) -> dict:
        """
        Signal generation based on SUE quintiles.
        Quintile 5 (SUE > 2.0): Strong long
        Quintile 4 (SUE 1.0-2.0): Moderate long
        Quintile 2 (SUE -1.0 to -2.0): Moderate short
        Quintile 1 (SUE < -2.0): Strong short
        """
        if sue > 2.0:
            direction, confidence = 'L', min(0.95, 0.7 + (sue - 2) * 0.05)
        elif sue > 1.0:
            direction, confidence = 'L', 0.65
        elif sue < -2.0:
            direction, confidence = 'S', min(0.90, 0.65 + (abs(sue) - 2) * 0.04)
        elif sue < -1.0:
            direction, confidence = 'S', 0.60
        else:
            direction, confidence = 'N', 0.5
        return {
            "direction": direction,
            "confidence": confidence,
            "sue": sue,
            "horizon_days": 20,
            "signal_type": "pead_long" if direction == 'L' else "pead_short",
        }
```

---

### MODULE 5: RISK ENGINE

```python
class VaREngine:
    """
    Multiple VaR methodologies:
    - Historical simulation (1000-day lookback)
    - Parametric (Cornish-Fisher expansion for non-normality)
    - Monte Carlo (10,000 paths, GBM + stochastic vol)
    """

    @staticmethod
    def historical_var(returns: np.ndarray, confidence: float = 0.99) -> dict:
        """1-day VaR at confidence level."""
        var = np.percentile(returns, (1 - confidence) * 100)
        es = returns[returns <= var].mean()
        return {"var": float(-var), "es": float(-es), "method": "historical"}

    @staticmethod
    def parametric_var(returns: np.ndarray, confidence: float = 0.99) -> dict:
        """Cornish-Fisher expansion accounts for skewness and kurtosis."""
        mu, sigma = returns.mean(), returns.std()
        skew = stats.skew(returns)
        kurt = stats.kurtosis(returns)
        z = stats.norm.ppf(1 - confidence)
        z_cf = (z + (z**2 - 1) * skew / 6
                + (z**3 - 3*z) * kurt / 24
                - (2*z**3 - 5*z) * skew**2 / 36)
        var = -(mu + z_cf * sigma)
        return {"var": float(var), "method": "parametric_cf"}

    @staticmethod
    def monte_carlo_var(portfolio_value: float, mu: float, sigma: float,
                        corr_matrix: np.ndarray, positions: np.ndarray,
                        n_sims: int = 10000, horizon: int = 1,
                        confidence: float = 0.99) -> dict:
        """Full Monte Carlo VaR with correlation structure."""
        L = np.linalg.cholesky(corr_matrix)
        Z = np.random.standard_normal((n_sims, len(positions)))
        corr_Z = Z @ L.T
        dt = horizon / 252
        returns = mu * dt + sigma * np.sqrt(dt) * corr_Z
        pnl = (returns * positions).sum(axis=1) * portfolio_value
        var = np.percentile(pnl, (1 - confidence) * 100)
        es = pnl[pnl <= var].mean()
        return {"var": float(-var), "es": float(-es), "method": "monte_carlo"}
```

---

## 5. DATA PIPELINE ARCHITECTURE

### 5.1 Market Data Ingestion Schedule (Celery Beat)

```python
CELERYBEAT_SCHEDULE = {
    # Every minute during market hours
    "update-option-chains": {
        "task": "tasks.options_chain_updater.update_all_chains",
        "schedule": crontab(minute="*/1"),
        "kwargs": {"symbols": ["SPX","SPY","QQQ","NDX","IWM","TSLA","NVDA","AAPL","META","MSFT"]},
    },
    # Every minute
    "compute-greeks": {
        "task": "tasks.greeks_calculator.compute_all_greeks",
        "schedule": crontab(minute="*/1"),
    },
    # Every 5 minutes
    "dealer-snapshot": {
        "task": "tasks.dealer_snapshot.take_snapshot",
        "schedule": crontab(minute="*/5"),
    },
    # Hourly
    "update-iv-surface": {
        "task": "tasks.iv_surface_updater.update_surfaces",
        "schedule": crontab(minute=0),
    },
    # After market close (4:30 PM ET)
    "pead-signals": {
        "task": "tasks.earnings_tracker.compute_pead_signals",
        "schedule": crontab(hour=16, minute=30),
    },
    # Nightly at 11 PM
    "regime-classification": {
        "task": "tasks.regime_updater.run_classification",
        "schedule": crontab(hour=23, minute=0),
    },
    # Nightly report
    "ai-daily-report": {
        "task": "tasks.report_generator.generate_daily",
        "schedule": crontab(hour=5, minute=0),
    },
}
```

### 5.2 Market Data Sources

| Data Type | Primary Source | Fallback | Frequency |
|---|---|---|---|
| Options chains | Polygon.io | CBOE datafeed | 1-minute |
| Stock prices | Polygon.io WebSocket | Alpaca | Real-time |
| Futures OHLCV | Interactive Brokers API | CME Group | 1-minute |
| VIX / vol indices | CBOE | Yahoo Finance | 1-minute |
| Earnings | Earnings Whispers | FactSet | Daily |
| Treasury yields | FRED API | Bloomberg | Daily |
| Gold spot | Polygon.io | Quandl | 1-minute |
| Macro data | FRED | World Bank | Weekly |

---

## 6. FRONTEND ARCHITECTURE

### 6.1 Key Component: Dealer Positioning Dashboard

```typescript
// components/dealer/DealerMap.tsx
import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { useGex } from '@/hooks/useGex';

interface StrikeLevelData {
  strike: number;
  gex_calls: number;
  gex_puts: number;
  gex_net: number;
  is_call_wall: boolean;
  is_put_wall: boolean;
  is_gamma_flip: boolean;
}

export const DealerMap: React.FC<{ symbol: string }> = ({ symbol }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const { data, gammaFlip, callWall, putWall } = useGex(symbol);

  useEffect(() => {
    if (!chartRef.current || !data) return;
    const chart = echarts.init(chartRef.current);

    const option = {
      backgroundColor: 'transparent',
      grid: { top: 40, bottom: 60, left: 80, right: 120 },
      xAxis: {
        type: 'value',
        name: 'GEX ($B)',
        nameTextStyle: { color: '#9ca3af' },
        axisLine: { lineStyle: { color: '#374151' } },
        splitLine: { lineStyle: { color: '#1f2937' } },
      },
      yAxis: {
        type: 'category',
        data: data.map((d: StrikeLevelData) => d.strike.toFixed(0)),
        axisLine: { lineStyle: { color: '#374151' } },
        axisLabel: { color: '#9ca3af', fontSize: 11 },
      },
      series: [
        {
          name: 'Call GEX',
          type: 'bar',
          stack: 'gex',
          data: data.map((d: StrikeLevelData) => ({
            value: d.gex_calls / 1e9,
            itemStyle: {
              color: d.is_call_wall ? '#22c55e' : '#16a34a',
              opacity: d.is_call_wall ? 1.0 : 0.75,
            }
          })),
        },
        {
          name: 'Put GEX',
          type: 'bar',
          stack: 'gex',
          data: data.map((d: StrikeLevelData) => ({
            value: d.gex_puts / 1e9,
            itemStyle: {
              color: d.is_put_wall ? '#ef4444' : '#dc2626',
              opacity: d.is_put_wall ? 1.0 : 0.75,
            }
          })),
        },
      ],
      markLine: {
        data: [
          { xAxis: 0, lineStyle: { color: '#f59e0b', width: 2, type: 'dashed' } },
          { yAxis: gammaFlip?.toString(), lineStyle: { color: '#6366f1', width: 2 } },
        ]
      },
    };

    chart.setOption(option);
    return () => chart.dispose();
  }, [data, gammaFlip]);

  return (
    <div className="relative">
      <div ref={chartRef} style={{ height: 600 }} />
      <div className="absolute top-2 right-2 flex flex-col gap-1 text-xs">
        <LevelBadge label="Gamma Flip" value={gammaFlip} color="indigo" />
        <LevelBadge label="Call Wall" value={callWall} color="green" />
        <LevelBadge label="Put Wall" value={putWall} color="red" />
      </div>
    </div>
  );
};
```

### 6.2 Real-time WebSocket Hook

```typescript
// hooks/useWebSocket.ts
import { useEffect, useRef, useCallback, useState } from 'react';
import { useAuthStore } from '@/store/authStore';

type WsMessage<T> = { type: string; data: T; timestamp: string };

export function useWebSocket<T>(channel: string) {
  const [data, setData] = useState<T | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const token = useAuthStore((s) => s.token);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    const url = `${process.env.NEXT_PUBLIC_WS_URL}/${channel}?token=${token}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      reconnectTimeout.current = setTimeout(connect, 2000);
    };
    ws.onmessage = (event) => {
      const msg: WsMessage<T> = JSON.parse(event.data);
      setData(msg.data);
    };
  }, [channel, token]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      clearTimeout(reconnectTimeout.current);
    };
  }, [connect]);

  return { data, connected };
}
```

---

## 7. INFRASTRUCTURE & DEPLOYMENT

### 7.1 Docker Compose (Development)

```yaml
version: '3.9'
services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: quantflow
      POSTGRES_USER: quantflow
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "quantflow"]
      interval: 5s

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redisdata:/data
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3.13-management
    environment:
      RABBITMQ_DEFAULT_USER: quantflow
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    ports:
      - "5672:5672"
      - "15672:15672"
    volumes:
      - rabbitmqdata:/var/lib/rabbitmq

  backend:
    build:
      context: ./backend
      dockerfile: ../infra/docker/backend.Dockerfile
    env_file: .env
    depends_on:
      - postgres
      - redis
      - rabbitmq
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  celery-worker:
    build:
      context: ./backend
      dockerfile: ../infra/docker/backend.Dockerfile
    env_file: .env
    depends_on:
      - postgres
      - redis
      - rabbitmq
    command: celery -A app.tasks.celery_app worker --loglevel=info -c 4 -Q options,dealer,research

  celery-beat:
    build:
      context: ./backend
      dockerfile: ../infra/docker/backend.Dockerfile
    env_file: .env
    depends_on:
      - celery-worker
    command: celery -A app.tasks.celery_app beat --loglevel=info

  frontend:
    build:
      context: ./frontend
      dockerfile: ../infra/docker/frontend.Dockerfile
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NEXT_PUBLIC_WS_URL: ws://localhost:8000/ws

volumes:
  pgdata:
  redisdata:
  rabbitmqdata:
```

### 7.2 Kubernetes HPA (Production)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: quantflow-backend-hpa
  namespace: quantflow
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: quantflow-backend
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 70
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
        - type: Pods
          value: 4
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
```

---

## 8. SECURITY ARCHITECTURE

### 8.1 JWT Implementation

```python
# core/security.py
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["argon2"], deprecated="auto")

class JWTManager:
    ALGORITHM = "RS256"       # RSA for production
    ACCESS_TTL = 15           # minutes
    REFRESH_TTL = 7 * 24 * 60 # 7 days in minutes

    def __init__(self, private_key: str, public_key: str):
        self.private_key = private_key
        self.public_key = public_key

    def create_access_token(self, user_id: str, role: str) -> str:
        payload = {
            "sub": user_id,
            "role": role,
            "exp": datetime.utcnow() + timedelta(minutes=self.ACCESS_TTL),
            "iat": datetime.utcnow(),
            "type": "access",
        }
        return jwt.encode(payload, self.private_key, algorithm=self.ALGORITHM)

    def create_refresh_token(self, user_id: str) -> str:
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(minutes=self.REFRESH_TTL),
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_urlsafe(32),  # unique token ID
        }
        return jwt.encode(payload, self.private_key, algorithm=self.ALGORITHM)

    def verify_token(self, token: str) -> dict:
        return jwt.decode(token, self.public_key,
                         algorithms=[self.ALGORITHM],
                         options={"require": ["exp", "iat", "sub"]})
```

### 8.2 Rate Limiting (Redis sliding window)

```python
# core/rate_limiter.py
import redis.asyncio as redis
from fastapi import HTTPException, Request

class SlidingWindowRateLimiter:
    """
    Per-user, per-endpoint sliding window rate limiter.
    Uses Redis sorted sets for O(log N) performance.
    """

    LIMITS = {
        "/api/v1/options": (100, 60),    # 100 req/min
        "/api/v1/dealer":  (200, 60),
        "/api/v1/research/backtest": (10, 3600),  # 10 backtests/hr
        "default":         (300, 60),
    }

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check(self, request: Request, user_id: str):
        path_prefix = "/" + "/".join(request.url.path.split("/")[:4])
        limit, window = self.LIMITS.get(path_prefix, self.LIMITS["default"])
        key = f"rl:{user_id}:{path_prefix}"
        now = int(time.time() * 1000)
        async with self.redis.pipeline() as pipe:
            pipe.zremrangebyscore(key, 0, now - window * 1000)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, window)
            _, count, _, _ = await pipe.execute()
        if count >= limit:
            raise HTTPException(429, detail=f"Rate limit exceeded: {limit} req/{window}s")
```

---

## 9. DEVELOPMENT ROADMAP

### Phase 1 — MVP (Weeks 1–6)
- [ ] Docker Compose dev stack
- [ ] PostgreSQL + TimescaleDB schema migrations
- [ ] Authentication (JWT)
- [ ] Polygon.io data ingestion
- [ ] BSM Options pricer + Greeks API
- [ ] GEX/DEX computation engine
- [ ] Next.js shell with 3 core pages (Overview, Dealer, Options)
- [ ] Basic TradingView chart integration

### Phase 2 — Core Platform (Weeks 7–12)
- [ ] Full options chain UI with real-time Greeks
- [ ] Volatility surface (3D Plotly)
- [ ] Dealer positioning heatmap (ECharts)
- [ ] Liquidity map engine
- [ ] Earnings calendar + PEAD research module
- [ ] Flow scanner with sweep detection
- [ ] WebSocket streaming for live updates
- [ ] Redis caching layer

### Phase 3 — Research & Intelligence (Weeks 13–18)
- [ ] Volatility regime HMM classifier
- [ ] Backtesting framework
- [ ] Monte Carlo VaR engine
- [ ] Futures flow analysis
- [ ] Gold analytics module
- [ ] Alert engine (email + WebSocket)
- [ ] AI daily report generation

### Phase 4 — Enterprise (Weeks 19–24)
- [ ] Kubernetes deployment + Helm charts
- [ ] Prometheus + Grafana monitoring
- [ ] Walk-forward optimization
- [ ] Factor research module
- [ ] Statistical arbitrage module
- [ ] Multi-user RBAC
- [ ] Audit logging
- [ ] SOC 2 compliance controls

---

## 10. TESTING STRATEGY

### Unit Tests
```python
# tests/unit/test_bsm.py
def test_put_call_parity():
    """Verify BSM put-call parity."""
    S, K, T, r, q, sigma = 100, 100, 0.25, 0.05, 0.02, 0.20
    call = BSMPricer.price(S, K, T, r, q, sigma, 'C')
    put  = BSMPricer.price(S, K, T, r, q, sigma, 'P')
    # C - P = S*e^{-qT} - K*e^{-rT}
    expected = S * np.exp(-q*T) - K * np.exp(-r*T)
    assert abs(call - put - expected) < 1e-8

def test_gex_sign_convention():
    """GEX should be positive when dealers are long gamma."""
    engine = DealerPositioningEngine(spot=5000)
    df = pl.DataFrame({"strike": [5000], "option_type": ["C"],
                       "oi": [100000], "gamma": [0.001],
                       "delta": [0.5], "vanna": [0.0], "charm": [0.0]})
    result = engine.compute_gex_per_strike(df)
    # Single call OI: dealer is short calls = negative gamma = negative GEX
    assert result["gex_net"][0] < 0
```

### Integration Tests
```python
# tests/integration/test_options_api.py
async def test_get_option_chain(client, seed_options_data):
    response = await client.get("/api/v1/options/chain/SPX")
    assert response.status_code == 200
    data = response.json()
    assert "calls" in data
    assert "puts" in data
    assert len(data["calls"]) > 0
    assert "delta" in data["calls"][0]
```

---

*End of QuantFlow Terminal Production Specification v1.0*
*Generated: 2026 | Architecture Team*
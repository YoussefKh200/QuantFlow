"""Initial schema — all tables + TimescaleDB hypertables.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-06-04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----------------------------------------------------------------
    # SYMBOLS
    # ----------------------------------------------------------------
    op.create_table(
        "symbols",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("name", sa.Text),
        sa.Column("asset_class", sa.String(20), nullable=False),
        sa.Column("exchange", sa.String(20)),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("multiplier", sa.Numeric(12, 4), server_default="1.0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("has_options", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("asset_class IN ('equity','etf','index','future','forex','commodity')", name="chk_symbols_asset_class"),
        sa.UniqueConstraint("ticker", name="uq_symbols_ticker"),
    )
    op.create_index("idx_symbols_ticker", "symbols", ["ticker"])
    op.create_index("idx_symbols_asset_class", "symbols", ["asset_class"])

    # ----------------------------------------------------------------
    # USERS
    # ----------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.Text),
        sa.Column("role", sa.String(20), server_default="analyst"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_login", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("role IN ('admin','trader','analyst','viewer')", name="chk_users_role"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # ----------------------------------------------------------------
    # OPTION CONTRACTS
    # ----------------------------------------------------------------
    op.create_table(
        "option_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("symbols.id"), nullable=False),
        sa.Column("osi_symbol", sa.String(25), nullable=False),
        sa.Column("underlying", sa.String(20), nullable=False),
        sa.Column("expiration", sa.Date, nullable=False),
        sa.Column("strike", sa.Numeric(12, 2), nullable=False),
        sa.Column("option_type", sa.String(1), nullable=False),
        sa.Column("multiplier", sa.Numeric(8, 2), server_default="100.0"),
        sa.Column("style", sa.String(10), server_default="american"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("option_type IN ('C','P')", name="chk_oc_option_type"),
        sa.CheckConstraint("style IN ('american','european')", name="chk_oc_style"),
        sa.UniqueConstraint("osi_symbol", name="uq_oc_osi_symbol"),
    )
    op.create_index("idx_oc_underlying_exp", "option_contracts", ["underlying", "expiration"])
    op.create_index("idx_oc_underlying_strike", "option_contracts", ["underlying", "strike", "option_type"])
    op.create_index("idx_oc_expiration", "option_contracts", ["expiration"])

    # ----------------------------------------------------------------
    # HYPERTABLES — created as regular tables first, then converted
    # ----------------------------------------------------------------

    # Option chains
    op.create_table(
        "option_chains",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("option_contracts.id"), nullable=False),
        sa.Column("underlying", sa.String(20), nullable=False),
        sa.Column("spot_price", sa.Numeric(12, 4)),
        sa.Column("bid", sa.Numeric(12, 4)),
        sa.Column("ask", sa.Numeric(12, 4)),
        sa.Column("mid", sa.Numeric(12, 4)),
        sa.Column("last", sa.Numeric(12, 4)),
        sa.Column("volume", sa.BigInteger, server_default="0"),
        sa.Column("open_interest", sa.BigInteger, server_default="0"),
        sa.Column("iv", sa.Numeric(10, 6)),
        sa.Column("intrinsic", sa.Numeric(12, 4)),
        sa.Column("extrinsic", sa.Numeric(12, 4)),
        sa.Column("dte", sa.SmallInteger),
        sa.PrimaryKeyConstraint("time", "contract_id"),
    )
    op.execute("SELECT create_hypertable('option_chains', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)")
    op.create_index("idx_chains_underlying", "option_chains", ["underlying", sa.text("time DESC")])
    op.execute("SELECT add_retention_policy('option_chains', INTERVAL '2 years', if_not_exists => TRUE)")

    # Greeks
    op.create_table(
        "greeks",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("option_contracts.id"), nullable=False),
        sa.Column("underlying", sa.String(20), nullable=False),
        sa.Column("spot_price", sa.Numeric(12, 4)),
        sa.Column("delta", sa.Numeric(10, 8)),
        sa.Column("gamma", sa.Numeric(14, 10)),
        sa.Column("vega", sa.Numeric(12, 8)),
        sa.Column("theta", sa.Numeric(12, 8)),
        sa.Column("rho", sa.Numeric(12, 8)),
        sa.Column("vanna", sa.Numeric(14, 10)),
        sa.Column("charm", sa.Numeric(14, 10)),
        sa.Column("vomma", sa.Numeric(14, 10)),
        sa.Column("speed", sa.Numeric(16, 12)),
        sa.Column("iv", sa.Numeric(10, 6)),
        sa.Column("iv_bid", sa.Numeric(10, 6)),
        sa.Column("iv_ask", sa.Numeric(10, 6)),
        sa.PrimaryKeyConstraint("time", "contract_id"),
    )
    op.execute("SELECT create_hypertable('greeks', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)")
    op.create_index("idx_greeks_underlying", "greeks", ["underlying", sa.text("time DESC")])

    # Dealer positioning
    op.create_table(
        "dealer_positioning",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("underlying", sa.String(20), nullable=False),
        sa.Column("strike", sa.Numeric(12, 2), nullable=False),
        sa.Column("expiration", sa.Date),
        sa.Column("gex_calls", sa.Numeric(20, 2)),
        sa.Column("gex_puts", sa.Numeric(20, 2)),
        sa.Column("gex_net", sa.Numeric(20, 2)),
        sa.Column("dex_calls", sa.Numeric(20, 2)),
        sa.Column("dex_puts", sa.Numeric(20, 2)),
        sa.Column("dex_net", sa.Numeric(20, 2)),
        sa.Column("vex_net", sa.Numeric(20, 2)),
        sa.Column("cex_net", sa.Numeric(20, 2)),
        sa.Column("oi_calls", sa.BigInteger),
        sa.Column("oi_puts", sa.BigInteger),
        sa.Column("is_call_wall", sa.Boolean, server_default="false"),
        sa.Column("is_put_wall", sa.Boolean, server_default="false"),
        sa.Column("is_gamma_flip", sa.Boolean, server_default="false"),
        sa.Column("is_vol_trigger", sa.Boolean, server_default="false"),
        sa.PrimaryKeyConstraint("time", "underlying", "strike"),
    )
    op.execute("SELECT create_hypertable('dealer_positioning', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)")
    op.create_index("idx_dp_underlying", "dealer_positioning", ["underlying", sa.text("time DESC")])
    op.create_index("idx_dp_gex", "dealer_positioning", ["underlying", sa.text("gex_net DESC")])

    # Dealer summary
    op.create_table(
        "dealer_summary",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("underlying", sa.String(20), nullable=False),
        sa.Column("total_gex", sa.Numeric(22, 2)),
        sa.Column("total_dex", sa.Numeric(22, 2)),
        sa.Column("total_vex", sa.Numeric(22, 2)),
        sa.Column("total_cex", sa.Numeric(22, 2)),
        sa.Column("gamma_flip_price", sa.Numeric(12, 4)),
        sa.Column("call_wall_strike", sa.Numeric(12, 2)),
        sa.Column("put_wall_strike", sa.Numeric(12, 2)),
        sa.Column("vol_trigger_price", sa.Numeric(12, 4)),
        sa.Column("dealer_regime", sa.String(20)),
        sa.PrimaryKeyConstraint("time", "underlying"),
    )
    op.execute("SELECT create_hypertable('dealer_summary', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)")

    # Volatility metrics
    op.create_table(
        "volatility_metrics",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("underlying", sa.String(20), nullable=False),
        sa.Column("hv_5d", sa.Numeric(10, 6)),
        sa.Column("hv_10d", sa.Numeric(10, 6)),
        sa.Column("hv_21d", sa.Numeric(10, 6)),
        sa.Column("hv_63d", sa.Numeric(10, 6)),
        sa.Column("atm_iv_30d", sa.Numeric(10, 6)),
        sa.Column("atm_iv_60d", sa.Numeric(10, 6)),
        sa.Column("vix_term", sa.Numeric(10, 6)),
        sa.Column("iv_rank", sa.Numeric(6, 4)),
        sa.Column("iv_percentile", sa.Numeric(6, 4)),
        sa.Column("skew_25d", sa.Numeric(10, 6)),
        sa.Column("skew_10d", sa.Numeric(10, 6)),
        sa.Column("ts_30_60", sa.Numeric(10, 6)),
        sa.Column("ts_slope", sa.Numeric(10, 6)),
        sa.Column("vol_regime", sa.String(20)),
        sa.PrimaryKeyConstraint("time", "underlying"),
    )
    op.execute("SELECT create_hypertable('volatility_metrics', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)")
    op.create_index("idx_vm_underlying", "volatility_metrics", ["underlying", sa.text("time DESC")])

    # Flow events
    op.create_table(
        "flow_events",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("option_contracts.id"), nullable=False),
        sa.Column("underlying", sa.String(20), nullable=False),
        sa.Column("strike", sa.Numeric(12, 2)),
        sa.Column("expiration", sa.Date),
        sa.Column("option_type", sa.String(1)),
        sa.Column("trade_size", sa.Integer),
        sa.Column("trade_price", sa.Numeric(12, 4)),
        sa.Column("trade_side", sa.String(5)),
        sa.Column("aggressor", sa.String(10)),
        sa.Column("trade_type", sa.String(10)),
        sa.Column("premium_total", sa.Numeric(16, 2)),
        sa.Column("sentiment", sa.String(10)),
        sa.Column("is_unusual", sa.Boolean, server_default="false"),
        sa.Column("is_institutional", sa.Boolean, server_default="false"),
        sa.Column("flow_score", sa.Numeric(6, 4)),
        sa.Column("exchange", sa.String(10)),
        sa.PrimaryKeyConstraint("time", "contract_id", "trade_size", "trade_price"),
    )
    op.execute("SELECT create_hypertable('flow_events', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)")
    op.create_index("idx_flow_underlying", "flow_events", ["underlying", sa.text("time DESC")])
    op.create_index("idx_flow_unusual", "flow_events", ["is_unusual", sa.text("time DESC")])

    # Market regimes
    op.create_table(
        "market_regimes",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("underlying", sa.String(20), nullable=False),
        sa.Column("vol_regime", sa.String(20), nullable=False),
        sa.Column("vol_state", sa.Numeric(6, 4)),
        sa.Column("gamma_regime", sa.String(20), nullable=False),
        sa.Column("gex_level", sa.Numeric(22, 2)),
        sa.Column("trend_regime", sa.String(20)),
        sa.Column("trend_probability", sa.Numeric(6, 4)),
        sa.Column("composite_regime", sa.String(30)),
        sa.Column("regime_confidence", sa.Numeric(6, 4)),
        sa.PrimaryKeyConstraint("time", "underlying"),
    )
    op.execute("SELECT create_hypertable('market_regimes', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)")

    # ----------------------------------------------------------------
    # EARNINGS
    # ----------------------------------------------------------------
    op.create_table(
        "earnings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("symbols.id")),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("fiscal_period", sa.String(10)),
        sa.Column("report_date", sa.Date, nullable=False),
        sa.Column("report_time", sa.String(5)),
        sa.Column("eps_actual", sa.Numeric(12, 4)),
        sa.Column("eps_estimate", sa.Numeric(12, 4)),
        sa.Column("eps_surprise", sa.Numeric(12, 4)),
        sa.Column("eps_surprise_pct", sa.Numeric(10, 6)),
        sa.Column("revenue_actual", sa.Numeric(20, 2)),
        sa.Column("revenue_estimate", sa.Numeric(20, 2)),
        sa.Column("revenue_surprise", sa.Numeric(20, 2)),
        sa.Column("guidance_raised", sa.Boolean),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_earnings_ticker", "earnings", ["ticker", sa.text("report_date DESC")])
    op.create_index("idx_earnings_date", "earnings", ["report_date"])

    op.create_table(
        "earnings_pead",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("earnings_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("earnings.id")),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("report_date", sa.Date, nullable=False),
        sa.Column("sue_score", sa.Numeric(10, 6)),
        sa.Column("price_at_close", sa.Numeric(12, 4)),
        sa.Column("price_day_before", sa.Numeric(12, 4)),
        sa.Column("drift_1d", sa.Numeric(10, 6)),
        sa.Column("drift_5d", sa.Numeric(10, 6)),
        sa.Column("drift_10d", sa.Numeric(10, 6)),
        sa.Column("drift_20d", sa.Numeric(10, 6)),
        sa.Column("drift_60d", sa.Numeric(10, 6)),
        sa.Column("iv_pre", sa.Numeric(10, 6)),
        sa.Column("iv_post_1d", sa.Numeric(10, 6)),
        sa.Column("iv_crush_pct", sa.Numeric(10, 6)),
        sa.Column("signal_direction", sa.String(1)),
        sa.Column("signal_confidence", sa.Numeric(6, 4)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_pead_ticker", "earnings_pead", ["ticker", sa.text("report_date DESC")])
    op.create_index("idx_pead_sue", "earnings_pead", [sa.text("sue_score DESC")])

    # ----------------------------------------------------------------
    # SIGNALS, BACKTESTS, ALERTS, RESEARCH RESULTS
    # ----------------------------------------------------------------
    op.create_table(
        "signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("underlying", sa.String(20), nullable=False),
        sa.Column("signal_type", sa.String(30), nullable=False),
        sa.Column("direction", sa.String(1)),
        sa.Column("confidence", sa.Numeric(6, 4)),
        sa.Column("expected_return", sa.Numeric(10, 6)),
        sa.Column("expected_vol", sa.Numeric(10, 6)),
        sa.Column("sharpe_estimate", sa.Numeric(8, 4)),
        sa.Column("entry_price", sa.Numeric(12, 4)),
        sa.Column("target_price", sa.Numeric(12, 4)),
        sa.Column("stop_price", sa.Numeric(12, 4)),
        sa.Column("horizon_days", sa.SmallInteger),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("actual_return", sa.Numeric(10, 6)),
        sa.CheckConstraint("direction IN ('L','S','N')", name="chk_signals_direction"),
    )
    op.create_index("idx_signals_underlying", "signals", ["underlying", sa.text("created_at DESC")])
    op.create_index("idx_signals_type", "signals", ["signal_type", sa.text("created_at DESC")])
    op.create_index("idx_signals_active", "signals", ["is_active", sa.text("created_at DESC")])

    op.create_table(
        "backtests",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("name", sa.String(100)),
        sa.Column("strategy_name", sa.String(50), nullable=False),
        sa.Column("parameters", postgresql.JSONB, nullable=False),
        sa.Column("universe", postgresql.ARRAY(sa.Text)),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("total_return", sa.Numeric(10, 6)),
        sa.Column("annualized_return", sa.Numeric(10, 6)),
        sa.Column("annualized_vol", sa.Numeric(10, 6)),
        sa.Column("sharpe_ratio", sa.Numeric(8, 4)),
        sa.Column("sortino_ratio", sa.Numeric(8, 4)),
        sa.Column("calmar_ratio", sa.Numeric(8, 4)),
        sa.Column("max_drawdown", sa.Numeric(10, 6)),
        sa.Column("win_rate", sa.Numeric(6, 4)),
        sa.Column("profit_factor", sa.Numeric(8, 4)),
        sa.Column("num_trades", sa.Integer),
        sa.Column("avg_trade_return", sa.Numeric(10, 6)),
        sa.Column("equity_curve", postgresql.JSONB),
        sa.Column("trade_log", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )
    op.create_index("idx_backtests_strategy", "backtests", ["strategy_name", sa.text("created_at DESC")])

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("alert_type", sa.String(30), nullable=False),
        sa.Column("underlying", sa.String(20)),
        sa.Column("condition", postgresql.JSONB, nullable=False),
        sa.Column("message", sa.Text),
        sa.Column("severity", sa.String(10), server_default="info"),
        sa.Column("is_triggered", sa.Boolean, server_default="false"),
        sa.Column("triggered_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("severity IN ('info','warning','critical')", name="chk_alerts_severity"),
    )
    op.create_index("idx_alerts_user", "alerts", ["user_id", sa.text("created_at DESC")])
    op.create_index("idx_alerts_triggered", "alerts", ["is_triggered", sa.text("triggered_at DESC")])

    op.create_table(
        "research_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("research_type", sa.String(30), nullable=False),
        sa.Column("title", sa.Text),
        sa.Column("parameters", postgresql.JSONB),
        sa.Column("results", postgresql.JSONB, nullable=False),
        sa.Column("charts", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("research_results")
    op.drop_table("alerts")
    op.drop_table("backtests")
    op.drop_table("signals")
    op.drop_table("earnings_pead")
    op.drop_table("earnings")
    op.drop_table("market_regimes")
    op.drop_table("flow_events")
    op.drop_table("volatility_metrics")
    op.drop_table("dealer_summary")
    op.drop_table("dealer_positioning")
    op.drop_table("greeks")
    op.drop_table("option_chains")
    op.drop_table("option_contracts")
    op.drop_table("users")
    op.drop_table("symbols")

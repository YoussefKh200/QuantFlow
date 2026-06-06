// ============================================================
// QuantFlow — Shared TypeScript Types
// ============================================================

export type AssetClass = "equity" | "etf" | "index" | "future" | "forex" | "commodity";
export type OptionType = "C" | "P";
export type Direction = "L" | "S" | "N";
export type Sentiment = "bullish" | "bearish" | "neutral";
export type DealerRegime = "long_gamma" | "short_gamma" | "neutral";
export type VolRegime =
  | "low_volatility"
  | "normal_volatility"
  | "high_volatility"
  | "compression"
  | "expansion"
  | "event_driven";

export interface Symbol {
  id: string;
  ticker: string;
  name: string | null;
  asset_class: AssetClass;
  exchange: string | null;
  currency: string;
  has_options: boolean;
}

export interface Greeks {
  contract_id: string;
  underlying: string;
  spot_price: number;
  iv: number;
  iv_bid: number;
  iv_ask: number;
  delta: number;
  gamma: number;
  vega: number;
  theta: number;
  rho: number;
  vanna: number;
  charm: number;
  vomma: number;
  speed: number;
}

export interface OptionContract {
  id: string;
  osi_symbol: string;
  underlying: string;
  expiration: string;
  strike: number;
  option_type: OptionType;
  multiplier: number;
  style: string;
}

export interface OptionChainRow extends OptionContract {
  bid: number;
  ask: number;
  mid: number;
  last: number;
  volume: number;
  open_interest: number;
  iv: number;
  dte: number;
  greeks: Greeks;
}

export interface DealerStrikeLevelData {
  strike: number;
  gex_calls: number;
  gex_puts: number;
  gex_net: number;
  dex_calls: number;
  dex_puts: number;
  dex_net: number;
  vex_net: number;
  cex_net: number;
  oi_calls: number;
  oi_puts: number;
  is_call_wall: boolean;
  is_put_wall: boolean;
  is_gamma_flip: boolean;
  is_vol_trigger: boolean;
}

export interface DealerSummary {
  underlying: string;
  spot: number;
  total_gex: number;
  total_dex: number;
  total_vex: number;
  total_cex: number;
  gamma_flip_price: number | null;
  call_wall_strike: number | null;
  put_wall_strike: number | null;
  vol_trigger_price: number | null;
  dealer_regime: DealerRegime;
  timestamp: string;
  heatmap: DealerStrikeLevelData[];
}

export interface VolatilityMetrics {
  underlying: string;
  hv_5d: number | null;
  hv_10d: number | null;
  hv_21d: number | null;
  hv_63d: number | null;
  atm_iv_30d: number | null;
  atm_iv_60d: number | null;
  iv_rank: number | null;
  iv_percentile: number | null;
  skew_25d: number | null;
  skew_10d: number | null;
  vol_regime: VolRegime | null;
  ts_slope: number | null;
}

export interface VolSurface {
  strikes: number[];
  dtes: number[];
  ivs: number[][];
  atm_ivs: number[];
  spot: number;
}

export interface FlowEvent {
  contract_id: string;
  underlying: string;
  strike: number;
  expiration: string;
  option_type: OptionType;
  trade_type: "sweep" | "block" | "split";
  trade_size: number;
  trade_price: number;
  trade_side: "BUY" | "SELL";
  aggressor: "BUYER" | "SELLER";
  premium_total: number;
  sentiment: Sentiment;
  is_unusual: boolean;
  is_institutional: boolean;
  flow_score: number;
  exchange: string;
  timestamp: string;
}

export interface FlowSentiment {
  sentiment_score: number;
  unusual_sentiment_score: number;
  bull_premium: number;
  bear_premium: number;
  total_premium: number;
  dominant: Sentiment;
  n_events: number;
  n_unusual: number;
  n_institutional: number;
}

export interface EarningsEvent {
  id: string;
  ticker: string;
  fiscal_period: string;
  report_date: string;
  report_time: "BMO" | "AMC";
  eps_actual: number | null;
  eps_estimate: number | null;
  eps_surprise_pct: number | null;
  guidance_raised: boolean | null;
}

export interface Signal {
  id: string;
  underlying: string;
  signal_type: string;
  direction: Direction;
  confidence: number;
  entry_price: number | null;
  target_price: number | null;
  stop_price: number | null;
  horizon_days: number;
  created_at: string;
  is_active: boolean;
}

export interface Alert {
  id: string;
  alert_type: string;
  underlying: string | null;
  severity: "info" | "warning" | "critical";
  message: string | null;
  is_triggered: boolean;
  triggered_at: string | null;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: "admin" | "trader" | "analyst" | "viewer";
  created_at: string;
}

// WebSocket message types
export type WsMessage<T = unknown> =
  | { type: "connected"; channel: string; timestamp: string }
  | { type: "heartbeat"; ts: string }
  | { type: "greeks_update"; symbol: string; data: T; ts: string }
  | { type: "dealer_update"; symbol: string; data: T; ts: string }
  | { type: "flow_snapshot"; data: T; ts: string }
  | { type: "alert_triggered"; data: T; ts: string };

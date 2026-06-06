"use client";

import useSWR from "swr";
import { TrendingUp, TrendingDown, Activity, Zap, Flame, BarChart2 } from "lucide-react";
import api, { dealerApi, volatilityApi, earningsApi } from "@/lib/api";
import {
  fmtGEX, fmtIV, fmtIVRank, fmtPct, fmtDateTime, regimeColor,
} from "@/lib/formatters";
import { useMarketStore } from "@/store";
import { useGEXStream } from "@/hooks/useWebSocket";
import { cn } from "@/lib/utils";
import type { DealerSummary, VolatilityMetrics } from "@/types/market";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

// ---- Small metric card ----
function MetricCard({
  label, value, sub, color, icon: Icon,
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
  icon?: React.ElementType;
}) {
  return (
    <div className="metric-card flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs text-text-muted uppercase tracking-wide">{label}</span>
        {Icon && <Icon className="w-3.5 h-3.5 text-text-muted" />}
      </div>
      <span className={cn("text-xl font-mono font-semibold", color ?? "text-text-primary")}>
        {value}
      </span>
      {sub && <span className="text-2xs text-text-muted">{sub}</span>}
    </div>
  );
}

// ---- Dealer regime badge ----
function RegimeBadge({ regime }: { regime: string | undefined }) {
  if (!regime) return null;
  const cls =
    regime === "long_gamma" ? "regime-long" :
    regime === "short_gamma" ? "regime-short" :
    "regime-neutral";
  const label =
    regime === "long_gamma" ? "Long Gamma" :
    regime === "short_gamma" ? "Short Gamma" :
    "Neutral";
  return <span className={cn("level-badge", cls)}>{label}</span>;
}

// ---- Key level row ----
function LevelRow({
  label, value, highlight,
}: {
  label: string; value: string | null; highlight?: string;
}) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-terminal-border/50 last:border-0">
      <span className="text-xs text-text-muted">{label}</span>
      <span className={cn("text-sm font-mono font-medium", highlight ?? "text-text-primary")}>
        {value ?? "—"}
      </span>
    </div>
  );
}

export default function OverviewPage() {
  const { activeSymbol } = useMarketStore();

  // REST data
  const { data: dealer } = useSWR<DealerSummary>(
    `/dealer/summary/${activeSymbol}`, fetcher, { refreshInterval: 30_000 }
  );
  const { data: vol } = useSWR<VolatilityMetrics>(
    `/volatility/metrics/${activeSymbol}`, fetcher, { refreshInterval: 60_000 }
  );
  const { data: signals } = useSWR("/earnings/signals", fetcher, { refreshInterval: 300_000 });
  const { data: calendar } = useSWR("/earnings/calendar", fetcher);

  // Live WebSocket GEX stream
  const { data: liveGex, status: wsStatus, lastTs } = useGEXStream(activeSymbol);
  const gex = (liveGex as DealerSummary | null) ?? dealer;

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">
            Market Overview
            <span className="ml-2 text-text-muted font-mono font-normal">
              {activeSymbol}
            </span>
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            {lastTs ? `Updated ${fmtDateTime(lastTs)}` : "Waiting for data…"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className={cn(
            "ws-dot",
            wsStatus === "connected" ? "ws-dot-connected" :
            wsStatus === "connecting" ? "ws-dot-connecting" :
            "ws-dot-disconnected"
          )} />
          <span className="text-xs text-text-muted capitalize">{wsStatus}</span>
        </div>
      </div>

      {/* Key metrics row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          label="Net GEX"
          value={fmtGEX(gex?.total_gex)}
          sub={gex?.dealer_regime?.replace("_", " ") ?? "—"}
          color={
            (gex?.total_gex ?? 0) > 0 ? "text-bull" :
            (gex?.total_gex ?? 0) < 0 ? "text-bear" : "text-text-primary"
          }
          icon={Zap}
        />
        <MetricCard
          label="ATM IV (30d)"
          value={fmtIV(vol?.atm_iv_30d)}
          sub={`IV Rank: ${fmtIVRank(vol?.iv_rank)}`}
          icon={Activity}
        />
        <MetricCard
          label="HV 21d"
          value={fmtIV(vol?.hv_21d)}
          sub={
            vol?.atm_iv_30d && vol?.hv_21d
              ? `IV/RV: ${(vol.atm_iv_30d / vol.hv_21d).toFixed(2)}x`
              : undefined
          }
          icon={BarChart2}
        />
        <MetricCard
          label="Skew (25d)"
          value={fmtIV(vol?.skew_25d)}
          sub={`10d: ${fmtIV(vol?.skew_10d)}`}
          icon={Flame}
        />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Dealer key levels */}
        <div className="metric-card space-y-2">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-medium text-text-primary">Dealer Levels</h2>
            <RegimeBadge regime={gex?.dealer_regime} />
          </div>
          <LevelRow
            label="Gamma Flip"
            value={gex?.gamma_flip_price?.toFixed(0) ?? null}
            highlight="text-brand-bright"
          />
          <LevelRow
            label="Call Wall"
            value={gex?.call_wall_strike?.toFixed(0) ?? null}
            highlight="text-bull"
          />
          <LevelRow
            label="Put Wall"
            value={gex?.put_wall_strike?.toFixed(0) ?? null}
            highlight="text-bear"
          />
          <LevelRow
            label="Vol Trigger"
            value={gex?.vol_trigger_price?.toFixed(0) ?? null}
            highlight="text-warn"
          />
          <LevelRow
            label="Total DEX"
            value={fmtGEX(gex?.total_dex)}
          />
        </div>

        {/* Volatility regime */}
        <div className="metric-card space-y-3">
          <h2 className="text-sm font-medium text-text-primary">Volatility Regime</h2>
          <div className="flex items-center gap-2">
            <span className={cn("text-base font-semibold", regimeColor(vol?.vol_regime))}>
              {vol?.vol_regime?.replace(/_/g, " ") ?? "Loading…"}
            </span>
          </div>
          <div className="space-y-1.5 text-xs">
            {[
              { label: "IV Rank", value: `${fmtIVRank(vol?.iv_rank)} / 100` },
              { label: "IV Percentile", value: `${fmtIVRank(vol?.iv_percentile)}%` },
              { label: "TS Slope", value: fmtPct(vol?.ts_slope, 2) },
              { label: "30/60d", value: fmtIV(vol?.atm_iv_60d) },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between border-b border-terminal-border/40 pb-1">
                <span className="text-text-muted">{label}</span>
                <span className="font-mono text-text-primary">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Active signals */}
        <div className="metric-card">
          <h2 className="text-sm font-medium text-text-primary mb-3">Active Signals</h2>
          {signals?.signals?.length === 0 && (
            <p className="text-xs text-text-muted">No active signals</p>
          )}
          <div className="space-y-2">
            {(signals?.signals ?? []).slice(0, 5).map((sig: any, i: number) => (
              <div
                key={i}
                className="flex items-center justify-between p-2 rounded bg-terminal-elevated"
              >
                <div>
                  <span className="text-xs font-mono font-medium text-text-primary">
                    {sig.underlying}
                  </span>
                  <span className="ml-2 text-2xs text-text-muted">
                    {sig.signal_type?.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {sig.direction === "L" ? (
                    <TrendingUp className="w-3.5 h-3.5 text-bull" />
                  ) : sig.direction === "S" ? (
                    <TrendingDown className="w-3.5 h-3.5 text-bear" />
                  ) : null}
                  <span className="text-xs font-mono text-text-secondary">
                    {fmtPct(sig.confidence)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Earnings calendar preview */}
      <div className="metric-card">
        <h2 className="text-sm font-medium text-text-primary mb-3">Earnings This Week</h2>
        {!calendar?.earnings?.length ? (
          <p className="text-xs text-text-muted">No upcoming earnings</p>
        ) : (
          <table className="terminal-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Date</th>
                <th>Time</th>
                <th>EPS Est.</th>
                <th>EPS Act.</th>
                <th>Surprise</th>
              </tr>
            </thead>
            <tbody>
              {calendar.earnings.slice(0, 8).map((e: any, i: number) => (
                <tr key={i}>
                  <td>
                    <span className="font-mono font-medium">{e.ticker}</span>
                  </td>
                  <td>{fmtDateTime(e.report_date)}</td>
                  <td>
                    <span className="text-2xs text-text-muted">{e.report_time}</span>
                  </td>
                  <td>${e.eps_estimate?.toFixed(2) ?? "—"}</td>
                  <td>{e.eps_actual != null ? `$${e.eps_actual.toFixed(2)}` : "—"}</td>
                  <td>
                    {e.eps_surprise_pct != null ? (
                      <span className={cn(
                        "font-medium",
                        e.eps_surprise_pct > 0 ? "text-bull" : "text-bear"
                      )}>
                        {fmtPct(e.eps_surprise_pct)}
                      </span>
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

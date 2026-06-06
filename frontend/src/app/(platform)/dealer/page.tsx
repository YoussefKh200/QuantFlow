"use client";

import { useState } from "react";
import useSWR from "swr";
import { RefreshCw, TrendingUp, TrendingDown, Minus } from "lucide-react";
import api from "@/lib/api";
import { GexHeatmap } from "@/components/charts/GexHeatmap";
import { fmtGEX, fmtPrice, fmtDateTime } from "@/lib/formatters";
import { useMarketStore } from "@/store";
import { useGEXStream } from "@/hooks/useWebSocket";
import { cn } from "@/lib/utils";
import type { DealerSummary } from "@/types/market";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

function ExposureBar({
  label, value, maxAbs, color,
}: { label: string; value: number; maxAbs: number; color: string }) {
  const pct = maxAbs > 0 ? Math.abs(value) / maxAbs : 0;
  const isPos = value >= 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-text-muted">{label}</span>
        <span className={cn("font-mono font-medium", isPos ? "text-bull" : "text-bear")}>
          {fmtGEX(value)}
        </span>
      </div>
      <div className="h-1.5 bg-terminal-muted rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-500", color)}
          style={{ width: `${Math.min(pct * 100, 100)}%` }}
        />
      </div>
    </div>
  );
}

function LevelChip({
  label, value, variant,
}: { label: string; value: string | null; variant: "green" | "red" | "indigo" | "amber" }) {
  const colors = {
    green:  "bg-bull/10 border-bull/25 text-bull",
    red:    "bg-bear/10 border-bear/25 text-bear",
    indigo: "bg-brand/10 border-brand/25 text-brand-bright",
    amber:  "bg-warn/10 border-warn/25 text-warn",
  };
  return (
    <div className={cn("level-badge flex-col items-start gap-0.5 px-3 py-2", colors[variant])}>
      <span className="text-2xs opacity-70 uppercase tracking-wide">{label}</span>
      <span className="text-sm font-mono font-semibold">{value ?? "—"}</span>
    </div>
  );
}

export default function DealerPage() {
  const { activeSymbol } = useMarketStore();
  const [tab, setTab] = useState<"gex" | "dex" | "vex">("gex");

  const { data: restData, mutate, isLoading } = useSWR<DealerSummary>(
    `/dealer/summary/${activeSymbol}`,
    fetcher,
    { refreshInterval: 30_000 }
  );

  // Live WebSocket overlay
  const { data: wsData, status: wsStatus, lastTs } = useGEXStream(activeSymbol);
  const summary: DealerSummary | null = (wsData as DealerSummary | null) ?? restData ?? null;

  const regimeIcon =
    summary?.dealer_regime === "long_gamma" ? <TrendingUp className="w-4 h-4 text-bull" /> :
    summary?.dealer_regime === "short_gamma" ? <TrendingDown className="w-4 h-4 text-bear" /> :
    <Minus className="w-4 h-4 text-warn" />;

  const regimeText =
    summary?.dealer_regime === "long_gamma" ? "Long Gamma" :
    summary?.dealer_regime === "short_gamma" ? "Short Gamma" : "Neutral";

  const regimeColor =
    summary?.dealer_regime === "long_gamma" ? "text-bull" :
    summary?.dealer_regime === "short_gamma" ? "text-bear" : "text-warn";

  const maxAbsExposure = Math.max(
    Math.abs(summary?.total_gex ?? 0),
    Math.abs(summary?.total_dex ?? 0),
    Math.abs(summary?.total_vex ?? 0),
    Math.abs(summary?.total_cex ?? 0),
    1,
  );

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">
            Dealer Positioning
            <span className="ml-2 font-mono font-normal text-text-muted">{activeSymbol}</span>
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            {lastTs ? `Live · ${fmtDateTime(lastTs)}` : "Connecting…"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div className={cn(
              "w-2 h-2 rounded-full",
              wsStatus === "connected" ? "bg-bull animate-pulse" : "bg-bear"
            )} />
            <span className="text-xs text-text-muted">WebSocket</span>
          </div>
          <button
            onClick={() => mutate()}
            className="p-1.5 rounded hover:bg-terminal-muted text-text-secondary"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", isLoading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Key level chips */}
      <div className="flex flex-wrap gap-2">
        <LevelChip label="Gamma Flip" value={summary?.gamma_flip_price?.toFixed(0) ?? null} variant="indigo" />
        <LevelChip label="Call Wall"  value={summary?.call_wall_strike?.toFixed(0) ?? null}  variant="green" />
        <LevelChip label="Put Wall"   value={summary?.put_wall_strike?.toFixed(0) ?? null}   variant="red" />
        <LevelChip label="Vol Trigger" value={summary?.vol_trigger_price?.toFixed(0) ?? null} variant="amber" />
        <div className="level-badge flex-col items-start gap-0.5 px-3 py-2 border-terminal-border">
          <span className="text-2xs text-text-muted opacity-70 uppercase tracking-wide">Regime</span>
          <div className="flex items-center gap-1">
            {regimeIcon}
            <span className={cn("text-sm font-semibold", regimeColor)}>{regimeText}</span>
          </div>
        </div>
      </div>

      {/* Exposure bars + chart */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Exposure summary — left column */}
        <div className="metric-card space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Net Exposure
          </h3>
          <ExposureBar
            label="GEX (Gamma)"
            value={summary?.total_gex ?? 0}
            maxAbs={maxAbsExposure}
            color={(summary?.total_gex ?? 0) >= 0 ? "bg-bull" : "bg-bear"}
          />
          <ExposureBar
            label="DEX (Delta)"
            value={summary?.total_dex ?? 0}
            maxAbs={maxAbsExposure}
            color={(summary?.total_dex ?? 0) >= 0 ? "bg-bull" : "bg-bear"}
          />
          <ExposureBar
            label="VEX (Vanna)"
            value={summary?.total_vex ?? 0}
            maxAbs={maxAbsExposure}
            color="bg-brand"
          />
          <ExposureBar
            label="CEX (Charm)"
            value={summary?.total_cex ?? 0}
            maxAbs={maxAbsExposure}
            color="bg-warn"
          />

          <div className="pt-2 border-t border-terminal-border space-y-1.5 text-xs">
            {[
              { label: "Total GEX", value: fmtGEX(summary?.total_gex) },
              { label: "Total DEX", value: fmtGEX(summary?.total_dex) },
              { label: "Total VEX", value: fmtGEX(summary?.total_vex) },
              { label: "Total CEX", value: fmtGEX(summary?.total_cex) },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between">
                <span className="text-text-muted">{label}</span>
                <span className="font-mono text-text-primary">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* GEX heatmap — right 3 columns */}
        <div className="lg:col-span-3 bg-terminal-surface border border-terminal-border rounded-lg p-3">
          {/* Tab bar */}
          <div className="flex gap-2 mb-3">
            {(["gex", "dex", "vex"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  "px-3 py-1 rounded text-xs font-medium uppercase tracking-wide transition-colors",
                  tab === t
                    ? "bg-brand/20 text-brand-bright border border-brand/30"
                    : "text-text-muted hover:text-text-secondary"
                )}
              >
                {t}
              </button>
            ))}
            <div className="flex-1" />
            <span className="text-xs text-text-muted self-center">
              {summary?.heatmap?.length ?? 0} strikes
            </span>
          </div>

          {summary?.heatmap?.length ? (
            <GexHeatmap
              data={summary.heatmap}
              summary={summary}
              spot={summary.spot}
              height={520}
            />
          ) : (
            <div className="flex items-center justify-center h-[520px]">
              <span className="text-sm text-text-muted">
                {isLoading ? "Loading GEX data…" : "No dealer data available"}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Strike table */}
      {summary?.heatmap && summary.heatmap.length > 0 && (
        <div className="metric-card overflow-auto max-h-72">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-text-muted mb-3">
            Top Strikes by Abs GEX
          </h3>
          <table className="terminal-table">
            <thead>
              <tr>
                <th>Strike</th>
                <th>Net GEX</th>
                <th>Call GEX</th>
                <th>Put GEX</th>
                <th>Call OI</th>
                <th>Put OI</th>
                <th>Flags</th>
              </tr>
            </thead>
            <tbody>
              {[...summary.heatmap]
                .sort((a, b) => Math.abs(b.gex_net) - Math.abs(a.gex_net))
                .slice(0, 20)
                .map((row) => (
                  <tr key={row.strike}>
                    <td>
                      <span className="font-mono font-medium">{row.strike.toFixed(0)}</span>
                    </td>
                    <td className={row.gex_net >= 0 ? "text-bull" : "text-bear"}>
                      {fmtGEX(row.gex_net)}
                    </td>
                    <td className="text-bull">{fmtGEX(row.gex_calls)}</td>
                    <td className="text-bear">{fmtGEX(row.gex_puts)}</td>
                    <td>{(row.oi_calls ?? 0).toLocaleString()}</td>
                    <td>{(row.oi_puts ?? 0).toLocaleString()}</td>
                    <td>
                      <div className="flex gap-1 justify-end">
                        {row.is_call_wall  && <span className="level-badge regime-long text-2xs">CW</span>}
                        {row.is_put_wall   && <span className="level-badge regime-short text-2xs">PW</span>}
                        {row.is_gamma_flip && <span className="level-badge bg-brand/10 border-brand/30 text-brand-bright text-2xs">γF</span>}
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

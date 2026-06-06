"use client";

import useSWR from "swr";
import { VolSurface3D } from "@/components/charts/VolSurface3D";
import {
  fmtIV, fmtIVRank, fmtPct, regimeColor,
} from "@/lib/formatters";
import { useMarketStore } from "@/store";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import type { VolatilityMetrics, VolSurface } from "@/types/market";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

function IVRankGauge({ rank }: { rank: number | null }) {
  if (rank == null) return null;
  const pct = Math.min(Math.max(rank, 0), 100);
  const color =
    pct < 20 ? "bg-bull" :
    pct > 80 ? "bg-bear" :
    pct > 50 ? "bg-warn" : "bg-info";
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs">
        <span className="text-text-muted">IV Rank</span>
        <span className="font-mono font-semibold text-text-primary">{rank.toFixed(1)} / 100</span>
      </div>
      <div className="h-2 bg-terminal-muted rounded-full overflow-hidden relative">
        <div
          className={cn("h-full rounded-full transition-all duration-700", color)}
          style={{ width: `${pct}%` }}
        />
        {/* Threshold markers */}
        {[20, 50, 80].map((m) => (
          <div
            key={m}
            className="absolute top-0 h-full w-px bg-terminal-border"
            style={{ left: `${m}%` }}
          />
        ))}
      </div>
      <div className="flex justify-between text-2xs text-text-muted">
        <span>Low (0–20)</span>
        <span>Normal</span>
        <span>High (80+)</span>
      </div>
    </div>
  );
}

function VolMetricRow({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-terminal-border/50 last:border-0">
      <div>
        <span className="text-xs text-text-muted">{label}</span>
        {sub && <span className="block text-2xs text-text-muted/60">{sub}</span>}
      </div>
      <span className="text-sm font-mono font-medium text-text-primary">{value}</span>
    </div>
  );
}

export default function VolatilityPage() {
  const { activeSymbol } = useMarketStore();

  const { data: metrics } = useSWR<VolatilityMetrics>(
    `/volatility/metrics/${activeSymbol}`,
    fetcher,
    { refreshInterval: 60_000 }
  );
  const { data: regime } = useSWR(
    `/volatility/regime/${activeSymbol}`,
    fetcher,
    { refreshInterval: 60_000 }
  );
  const { data: surface } = useSWR<VolSurface>(
    `/options/iv-surface/${activeSymbol}`,
    fetcher,
    { refreshInterval: 300_000 }
  );

  const currentRegime = regime?.regime ?? metrics?.vol_regime;

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-lg font-semibold text-text-primary">
          Volatility Regime
          <span className="ml-2 font-mono font-normal text-text-muted">{activeSymbol}</span>
        </h1>
        <p className="text-xs text-text-muted mt-0.5">
          HMM classification · updated nightly · IV rank updated real-time
        </p>
      </div>

      {/* Regime banner */}
      <div className="metric-card flex items-center gap-4">
        <div>
          <p className="text-xs text-text-muted uppercase tracking-wide mb-1">Current Regime</p>
          <p className={cn("text-2xl font-bold capitalize", regimeColor(currentRegime))}>
            {currentRegime?.replace(/_/g, " ") ?? "—"}
          </p>
        </div>
        {regime?.state_probability != null && (
          <div className="border-l border-terminal-border pl-4">
            <p className="text-xs text-text-muted">Confidence</p>
            <p className="text-lg font-mono font-semibold text-text-primary">
              {fmtPct(regime.state_probability)}
            </p>
          </div>
        )}
        {regime?.iv_rv_ratio != null && (
          <div className="border-l border-terminal-border pl-4">
            <p className="text-xs text-text-muted">IV / RV Ratio</p>
            <p className={cn(
              "text-lg font-mono font-semibold",
              regime.iv_rv_ratio < 0.85 ? "text-bear" :
              regime.iv_rv_ratio > 1.5 ? "text-bull" : "text-text-primary"
            )}>
              {regime.iv_rv_ratio.toFixed(2)}x
            </p>
          </div>
        )}
        {regime?.is_compression && (
          <span className="level-badge bg-bear/10 border-bear/25 text-bear ml-auto">
            IV Compression
          </span>
        )}
        {regime?.is_expansion && (
          <span className="level-badge bg-bull/10 border-bull/25 text-bull ml-auto">
            Vol Expansion
          </span>
        )}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Metrics panel */}
        <div className="metric-card space-y-4">
          <h2 className="text-sm font-medium text-text-primary">Volatility Metrics</h2>

          <IVRankGauge rank={metrics?.iv_rank ?? null} />

          <div className="space-y-0">
            <VolMetricRow label="ATM IV (30d)"    value={fmtIV(metrics?.atm_iv_30d)} />
            <VolMetricRow label="ATM IV (60d)"    value={fmtIV(metrics?.atm_iv_60d)} />
            <VolMetricRow label="HV 5d"           value={fmtIV(metrics?.hv_5d)} />
            <VolMetricRow label="HV 10d"          value={fmtIV(metrics?.hv_10d)} />
            <VolMetricRow label="HV 21d"          value={fmtIV(metrics?.hv_21d)} />
            <VolMetricRow label="HV 63d"          value={fmtIV(metrics?.hv_63d)} />
            <VolMetricRow
              label="IV Rank"
              value={fmtIVRank(metrics?.iv_rank)}
              sub="1-year lookback, 0–100"
            />
            <VolMetricRow
              label="IV Percentile"
              value={`${fmtIVRank(metrics?.iv_percentile)}%`}
              sub="% of days below current IV"
            />
          </div>
        </div>

        {/* Skew panel */}
        <div className="metric-card space-y-4">
          <h2 className="text-sm font-medium text-text-primary">Skew & Term Structure</h2>

          <div className="space-y-0">
            <VolMetricRow
              label="25Δ Skew"
              value={fmtIV(metrics?.skew_25d)}
              sub="25d put IV − 25d call IV"
            />
            <VolMetricRow
              label="10Δ Skew"
              value={fmtIV(metrics?.skew_10d)}
              sub="10d put IV − 10d call IV"
            />
            <VolMetricRow
              label="TS Slope"
              value={fmtPct(metrics?.ts_slope, 2)}
              sub="Term structure slope"
            />
          </div>

          <div className="pt-2 border-t border-terminal-border">
            <h3 className="text-xs text-text-muted mb-3">Regime Interpretation</h3>
            <div className="space-y-2 text-xs">
              {currentRegime === "low_volatility" && (
                <p className="text-text-secondary">
                  Low IV environment. Cheap options — consider long vega strategies.
                  Mean reversion expected with positive GEX.
                </p>
              )}
              {currentRegime === "high_volatility" && (
                <p className="text-text-secondary">
                  Elevated IV. Expensive options — consider short vega / premium selling.
                  Trend continuation likely with negative GEX.
                </p>
              )}
              {currentRegime === "compression" && (
                <p className="text-text-secondary">
                  IV below realized vol — unusual compression.
                  Vol spike risk elevated. Consider long straddles.
                </p>
              )}
              {currentRegime === "expansion" && (
                <p className="text-text-secondary">
                  Vol expansion regime. Fear premium elevated.
                  Watch for vol mean reversion after catalyst passes.
                </p>
              )}
              {currentRegime === "normal_volatility" && (
                <p className="text-text-secondary">
                  Normal vol environment. Standard risk/reward for options.
                  Directional trades preferred over pure vol plays.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Term structure summary */}
        <div className="metric-card space-y-3">
          <h2 className="text-sm font-medium text-text-primary">ATM Term Structure</h2>
          {surface?.atm_ivs && surface.dtes ? (
            <div className="space-y-1.5">
              {surface.dtes
                .filter((_, i) => i % Math.ceil(surface.dtes.length / 10) === 0)
                .map((dte, i) => {
                  const ivIdx = Math.round(i * (surface.dtes.length - 1) / 9);
                  const iv = surface.atm_ivs[ivIdx] ?? 0;
                  const maxIV = Math.max(...surface.atm_ivs);
                  return (
                    <div key={dte} className="flex items-center gap-2">
                      <span className="text-xs font-mono text-text-muted w-12 text-right">
                        {Math.round(dte)}d
                      </span>
                      <div className="flex-1 h-1.5 bg-terminal-muted rounded overflow-hidden">
                        <div
                          className="h-full bg-brand rounded"
                          style={{ width: `${(iv / maxIV) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-text-primary w-12">
                        {fmtIV(iv)}
                      </span>
                    </div>
                  );
                })}
            </div>
          ) : (
            <p className="text-xs text-text-muted">Loading term structure…</p>
          )}
        </div>
      </div>

      {/* Vol Surface 3D */}
      <div className="metric-card p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-terminal-border">
          <h2 className="text-sm font-medium text-text-primary">
            Implied Volatility Surface
            <span className="ml-2 text-xs text-text-muted font-normal">
              RBF interpolation · rotate with mouse
            </span>
          </h2>
        </div>
        <div className="p-4">
          <VolSurface3D surface={surface ?? null} height={500} />
        </div>
      </div>
    </div>
  );
}

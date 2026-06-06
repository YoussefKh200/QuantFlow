"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { ECharts } from "echarts";
import { fmtGEX } from "@/lib/formatters";
import type { DealerStrikeLevelData, DealerSummary } from "@/types/market";
import { cn } from "@/lib/utils";

interface GexHeatmapProps {
  data: DealerStrikeLevelData[];
  summary: DealerSummary | null;
  spot?: number;
  height?: number;
}

// Colour tokens that match the Tailwind palette
const COLORS = {
  callGex:     "#16a34a",   // green-700
  callWall:    "#22c55e",   // green-500 (brighter for wall)
  putGex:      "#dc2626",   // red-600
  putWall:     "#ef4444",   // red-500
  gammaFlip:   "#6366f1",   // indigo-500
  volTrigger:  "#f59e0b",   // amber-500
  spot:        "#e2e8f0",   // text-primary
  gridLine:    "#1e1e2e",   // terminal-border
  axisLabel:   "#94a3b8",   // text-secondary
  zero:        "#334155",   // slate-700
  tooltip:     "#14141e",
};

export function GexHeatmap({ data, summary, spot, height = 580 }: GexHeatmapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ECharts | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    chartRef.current = echarts.init(containerRef.current, "dark");

    const handleResize = () => chartRef.current?.resize();
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chartRef.current?.dispose();
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current || !data.length) return;

    // Sort strikes ascending (y-axis top = highest strike in echarts category)
    const sorted = [...data].sort((a, b) => a.strike - b.strike);
    const strikes = sorted.map((d) => d.strike.toFixed(0));

    // Build series data with per-bar styling
    const callData = sorted.map((d) => ({
      value: d.gex_calls / 1e9,
      itemStyle: {
        color: d.is_call_wall ? COLORS.callWall : COLORS.callGex,
        opacity: d.is_call_wall ? 1.0 : 0.72,
        borderRadius: [0, 3, 3, 0],
      },
    }));

    const putData = sorted.map((d) => ({
      value: d.gex_puts / 1e9,
      itemStyle: {
        color: d.is_put_wall ? COLORS.putWall : COLORS.putGex,
        opacity: d.is_put_wall ? 1.0 : 0.72,
        borderRadius: [3, 0, 0, 3],
      },
    }));

    // Spot price y-index (closest strike)
    const spotIdx = spot
      ? sorted.reduce(
          (best, d, i) =>
            Math.abs(d.strike - spot) < Math.abs(sorted[best].strike - spot) ? i : best,
          0
        )
      : null;

    // Gamma flip y-axis value
    const gammaFlipStrike = summary?.gamma_flip_price?.toFixed(0) ?? null;

    const option: echarts.EChartsOption = {
      backgroundColor: "transparent",
      animation: false,
      grid: { top: 10, bottom: 44, left: 64, right: 110 },

      xAxis: {
        type: "value",
        name: "GEX ($B)",
        nameLocation: "middle",
        nameGap: 28,
        nameTextStyle: { color: COLORS.axisLabel, fontSize: 11 },
        axisLine: { lineStyle: { color: COLORS.gridLine } },
        splitLine: { lineStyle: { color: COLORS.gridLine } },
        axisLabel: {
          color: COLORS.axisLabel,
          fontSize: 10,
          formatter: (v: number) => fmtGEX(v * 1e9),
        },
      },

      yAxis: {
        type: "category",
        data: strikes,
        inverse: true,
        axisLine: { lineStyle: { color: COLORS.gridLine } },
        axisTick: { show: false },
        axisLabel: {
          color: COLORS.axisLabel,
          fontSize: 10,
          fontFamily: "JetBrains Mono, monospace",
          formatter: (v: string) => {
            const strike = parseFloat(v);
            const isGammaFlip = gammaFlipStrike && Math.abs(strike - parseFloat(gammaFlipStrike)) < 1;
            return isGammaFlip ? `{flip|${v}}` : v;
          },
          rich: {
            flip: {
              color: COLORS.gammaFlip,
              fontWeight: "bold",
            },
          },
        },
      },

      series: [
        {
          name: "Call GEX",
          type: "bar",
          stack: "gex",
          data: callData,
          barMaxWidth: 18,
          emphasis: { focus: "series" },
          markLine: {
            silent: true,
            symbol: "none",
            data: [
              // Zero line
              {
                xAxis: 0,
                lineStyle: { color: COLORS.zero, width: 1, type: "solid" },
              },
              // Gamma flip horizontal line
              ...(gammaFlipStrike
                ? [{
                    yAxis: gammaFlipStrike,
                    lineStyle: { color: COLORS.gammaFlip, width: 1.5, type: "dashed" as const },
                    label: {
                      show: true,
                      position: "insideEndTop" as const,
                      formatter: "γ flip",
                      color: COLORS.gammaFlip,
                      fontSize: 10,
                    },
                  }]
                : []),
              // Spot price line
              ...(spotIdx !== null
                ? [{
                    yAxis: strikes[spotIdx],
                    lineStyle: { color: COLORS.spot, width: 1.5, type: "dotted" as const },
                    label: {
                      show: true,
                      position: "insideStartTop" as const,
                      formatter: "SPOT",
                      color: COLORS.spot,
                      fontSize: 10,
                    },
                  }]
                : []),
            ],
          },
        },
        {
          name: "Put GEX",
          type: "bar",
          stack: "gex",
          data: putData,
          barMaxWidth: 18,
          emphasis: { focus: "series" },
        },
      ],

      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: COLORS.tooltip,
        borderColor: "#1e1e2e",
        textStyle: { color: "#e2e8f0", fontSize: 12 },
        formatter: (params: any) => {
          const idx = params[0]?.dataIndex ?? 0;
          const d = sorted[idx];
          const isSpecial = d.is_call_wall || d.is_put_wall || d.is_gamma_flip;

          return `
            <div style="font-family: JetBrains Mono, monospace;">
              <div style="font-size:13px;font-weight:600;margin-bottom:6px">
                Strike ${d.strike.toFixed(0)}
                ${isSpecial ? `<span style="color:#6366f1;font-size:10px;margin-left:6px">
                  ${d.is_gamma_flip ? "γ FLIP " : ""}
                  ${d.is_call_wall ? "CALL WALL " : ""}
                  ${d.is_put_wall ? "PUT WALL" : ""}
                </span>` : ""}
              </div>
              <div style="display:grid;grid-template-columns:auto auto;gap:2px 16px;font-size:11px">
                <span style="color:#94a3b8">Net GEX</span>
                <span style="color:${d.gex_net >= 0 ? COLORS.callWall : COLORS.putWall}">
                  ${fmtGEX(d.gex_net)}
                </span>
                <span style="color:#94a3b8">Call GEX</span>
                <span style="color:${COLORS.callGex}">${fmtGEX(d.gex_calls)}</span>
                <span style="color:#94a3b8">Put GEX</span>
                <span style="color:${COLORS.putGex}">${fmtGEX(d.gex_puts)}</span>
                <span style="color:#94a3b8">Call OI</span>
                <span>${(d.oi_calls ?? 0).toLocaleString()}</span>
                <span style="color:#94a3b8">Put OI</span>
                <span>${(d.oi_puts ?? 0).toLocaleString()}</span>
              </div>
            </div>
          `;
        },
      },

      legend: {
        data: ["Call GEX", "Put GEX"],
        bottom: 4,
        textStyle: { color: COLORS.axisLabel, fontSize: 11 },
        itemWidth: 12,
        itemHeight: 8,
      },
    };

    chartRef.current.setOption(option, true);
  }, [data, summary, spot]);

  return <div ref={containerRef} style={{ height }} className="w-full" />;
}

"use client";

import dynamic from "next/dynamic";
import type { VolSurface } from "@/types/market";

// Plotly is SSR-incompatible — dynamic import with no SSR
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface VolSurface3DProps {
  surface: VolSurface | null;
  height?: number;
}

export function VolSurface3D({ surface, height = 480 }: VolSurface3DProps) {
  if (!surface) {
    return (
      <div
        className="flex items-center justify-center bg-terminal-surface rounded-lg border border-terminal-border"
        style={{ height }}
      >
        <span className="text-sm text-text-muted">Loading surface…</span>
      </div>
    );
  }

  const { strikes, dtes, ivs } = surface;
  // ivs is [n_expiries × n_strikes], z-axis = iv * 100 (%)
  const zData = ivs.map((row) => row.map((v) => v * 100));

  const data: Plotly.Data[] = [
    {
      type: "surface" as const,
      x: strikes,
      y: dtes,
      z: zData,
      colorscale: [
        [0.0,  "#0f172a"],
        [0.15, "#1e3a5f"],
        [0.30, "#1d4ed8"],
        [0.50, "#6366f1"],
        [0.65, "#a855f7"],
        [0.80, "#ec4899"],
        [0.90, "#ef4444"],
        [1.0,  "#fbbf24"],
      ],
      showscale: true,
      colorbar: {
        title: { text: "IV (%)", font: { color: "#94a3b8", size: 11 } },
        tickfont: { color: "#94a3b8", size: 10 },
        thickness: 12,
        len: 0.7,
        x: 1.02,
      },
      opacity: 0.92,
      contours: {
        z: {
          show: true,
          usecolormap: true,
          highlightcolor: "#818cf8",
          project: { z: false },
        },
      },
      hovertemplate:
        "Strike: <b>%{x:.0f}</b><br>" +
        "DTE: <b>%{y:.0f}d</b><br>" +
        "IV: <b>%{z:.1f}%</b><extra></extra>",
    },
    // ATM spine
    {
      type: "scatter3d" as const,
      x: Array(dtes.length).fill(surface.spot),
      y: dtes,
      z: surface.atm_ivs.map((v) => v * 100),
      mode: "lines",
      line: { color: "#f59e0b", width: 4 },
      name: "ATM Term Structure",
      hoverinfo: "skip",
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    paper_bgcolor: "transparent",
    plot_bgcolor:  "transparent",
    height,
    margin: { l: 0, r: 0, t: 0, b: 0 },
    scene: {
      xaxis: {
        title: { text: "Strike", font: { color: "#94a3b8", size: 11 } },
        tickfont: { color: "#94a3b8", size: 9 },
        gridcolor: "#1e1e2e",
        zerolinecolor: "#334155",
        backgroundcolor: "transparent",
        showbackground: false,
      },
      yaxis: {
        title: { text: "DTE (days)", font: { color: "#94a3b8", size: 11 } },
        tickfont: { color: "#94a3b8", size: 9 },
        gridcolor: "#1e1e2e",
        zerolinecolor: "#334155",
        showbackground: false,
      },
      zaxis: {
        title: { text: "IV (%)", font: { color: "#94a3b8", size: 11 } },
        tickfont: { color: "#94a3b8", size: 9 },
        gridcolor: "#1e1e2e",
        zerolinecolor: "#334155",
        showbackground: false,
        ticksuffix: "%",
      },
      camera: {
        eye: { x: 1.6, y: -1.4, z: 0.9 },
        up: { x: 0, y: 0, z: 1 },
      },
      bgcolor: "transparent",
      aspectmode: "manual",
      aspectratio: { x: 1.6, y: 1.0, z: 0.7 },
    },
    legend: {
      font: { color: "#94a3b8", size: 11 },
      bgcolor: "transparent",
    },
  };

  const config: Partial<Plotly.Config> = {
    displayModeBar: true,
    modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
    displaylogo: false,
    responsive: true,
  };

  return (
    <div className="w-full rounded-lg overflow-hidden border border-terminal-border">
      <Plot
        data={data}
        layout={layout}
        config={config}
        style={{ width: "100%", height }}
        useResizeHandler
      />
    </div>
  );
}

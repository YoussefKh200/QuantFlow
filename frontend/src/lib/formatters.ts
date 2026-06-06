/**
 * QuantFlow display formatters.
 * All formatting for prices, Greeks, percentages, and large numbers.
 */

// ----------------------------------------------------------------
// Price / currency
// ----------------------------------------------------------------
export const fmtPrice = (v: number | null | undefined, decimals = 2): string => {
  if (v == null || !isFinite(v)) return "—";
  return v.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

export const fmtDollar = (v: number | null | undefined, compact = false): string => {
  if (v == null || !isFinite(v)) return "—";
  if (compact) return fmtCompact(v, "$");
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);
};

// ----------------------------------------------------------------
// Greeks
// ----------------------------------------------------------------
export const fmtDelta = (v: number | null | undefined): string => {
  if (v == null || !isFinite(v)) return "—";
  const s = (v >= 0 ? "+" : "") + v.toFixed(4);
  return s;
};

export const fmtGamma = (v: number | null | undefined): string => {
  if (v == null || !isFinite(v)) return "—";
  return v.toFixed(6);
};

export const fmtVega = (v: number | null | undefined): string => {
  if (v == null || !isFinite(v)) return "—";
  return v.toFixed(4);
};

export const fmtTheta = (v: number | null | undefined): string => {
  if (v == null || !isFinite(v)) return "—";
  return (v >= 0 ? "+" : "") + v.toFixed(4);
};

// ----------------------------------------------------------------
// Percentages / volatility
// ----------------------------------------------------------------
export const fmtPct = (v: number | null | undefined, decimals = 1): string => {
  if (v == null || !isFinite(v)) return "—";
  return (v * 100).toFixed(decimals) + "%";
};

export const fmtIV = (v: number | null | undefined): string => {
  if (v == null || !isFinite(v)) return "—";
  return (v * 100).toFixed(1) + "%";
};

export const fmtIVRank = (v: number | null | undefined): string => {
  if (v == null || !isFinite(v)) return "—";
  return v.toFixed(1);
};

// ----------------------------------------------------------------
// GEX / large numbers
// ----------------------------------------------------------------
export const fmtGEX = (v: number | null | undefined): string => {
  if (v == null || !isFinite(v)) return "—";
  const abs = Math.abs(v);
  const sign = v < 0 ? "-" : "+";
  if (abs >= 1e9) return sign + (abs / 1e9).toFixed(2) + "B";
  if (abs >= 1e6) return sign + (abs / 1e6).toFixed(1) + "M";
  if (abs >= 1e3) return sign + (abs / 1e3).toFixed(0) + "K";
  return sign + abs.toFixed(0);
};

export const fmtCompact = (v: number, prefix = ""): string => {
  const abs = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  if (abs >= 1e12) return sign + prefix + (abs / 1e12).toFixed(2) + "T";
  if (abs >= 1e9)  return sign + prefix + (abs / 1e9).toFixed(2) + "B";
  if (abs >= 1e6)  return sign + prefix + (abs / 1e6).toFixed(1) + "M";
  if (abs >= 1e3)  return sign + prefix + (abs / 1e3).toFixed(0) + "K";
  return sign + prefix + abs.toFixed(0);
};

export const fmtOI = (v: number | null | undefined): string => {
  if (v == null) return "—";
  return fmtCompact(v);
};

// ----------------------------------------------------------------
// Dates
// ----------------------------------------------------------------
export const fmtDate = (s: string | null | undefined): string => {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return s;
  }
};

export const fmtExpiry = (s: string | null | undefined): string => {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  } catch {
    return s;
  }
};

export const fmtDateTime = (s: string | null | undefined): string => {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return s;
  }
};

export const fmtTimeAgo = (s: string | null | undefined): string => {
  if (!s) return "—";
  const diff = (Date.now() - new Date(s).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return fmtDate(s);
};

// ----------------------------------------------------------------
// Color helpers (for className conditionals)
// ----------------------------------------------------------------
export const bullBearColor = (v: number | null | undefined): string => {
  if (v == null) return "text-text-secondary";
  if (v > 0) return "text-bull";
  if (v < 0) return "text-bear";
  return "text-text-secondary";
};

export const sentimentColor = (s: string): string => {
  if (s === "bullish") return "text-bull";
  if (s === "bearish") return "text-bear";
  return "text-text-secondary";
};

export const regimeColor = (r: string | null | undefined): string => {
  if (!r) return "text-text-secondary";
  if (r.includes("low") || r === "compression") return "text-bull";
  if (r.includes("high") || r === "expansion") return "text-bear";
  if (r === "long_gamma") return "text-bull";
  if (r === "short_gamma") return "text-bear";
  return "text-warn";
};

"use client";

import { useState, useEffect, useRef } from "react";
import useSWR from "swr";
import { Flame, Filter, TrendingUp, TrendingDown } from "lucide-react";
import api from "@/lib/api";
import { useFlowStream } from "@/hooks/useWebSocket";
import {
  fmtPrice, fmtCompact, fmtExpiry, fmtTimeAgo, sentimentColor,
} from "@/lib/formatters";
import { cn } from "@/lib/utils";
import type { FlowEvent, FlowSentiment } from "@/types/market";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

function TradeBadge({ type }: { type: string }) {
  const cls =
    type === "sweep" ? "badge-sweep" :
    type === "block" ? "badge-block" :
    "badge-split";
  return <span className={cn("level-badge", cls)}>{type}</span>;
}

function SentimentDot({ s }: { s: string }) {
  return (
    <div className={cn(
      "w-1.5 h-1.5 rounded-full flex-shrink-0",
      s === "bullish" ? "bg-bull" : s === "bearish" ? "bg-bear" : "bg-text-muted"
    )} />
  );
}

function FlowRow({ event, isNew }: { event: FlowEvent; isNew?: boolean }) {
  return (
    <tr className={cn(
      "transition-colors duration-500",
      isNew && "bg-brand/5",
      "hover:bg-terminal-elevated"
    )}>
      <td>
        <div className="flex items-center gap-1.5">
          <SentimentDot s={event.sentiment} />
          <span className="font-mono font-semibold">{event.underlying}</span>
        </div>
      </td>
      <td>{event.strike.toFixed(0)}</td>
      <td>
        <span className={cn(
          "font-medium",
          event.option_type === "C" ? "text-bull" : "text-bear"
        )}>
          {event.option_type === "C" ? "Call" : "Put"}
        </span>
      </td>
      <td>{fmtExpiry(event.expiration)}</td>
      <td className="font-mono">${fmtPrice(event.trade_price, 2)}</td>
      <td className="font-mono">{event.trade_size.toLocaleString()}</td>
      <td className="font-mono font-medium">
        ${fmtCompact(event.premium_total)}
      </td>
      <td>
        <TradeBadge type={event.trade_type} />
      </td>
      <td>
        <span className={cn("font-medium text-xs", sentimentColor(event.sentiment))}>
          {event.sentiment}
        </span>
      </td>
      <td>
        <div className="flex items-center gap-1 justify-end">
          <div className="h-1 bg-terminal-muted rounded w-14 overflow-hidden">
            <div
              className="h-full bg-brand rounded"
              style={{ width: `${event.flow_score * 100}%` }}
            />
          </div>
          <span className="text-2xs font-mono text-text-muted w-8">
            {(event.flow_score * 100).toFixed(0)}
          </span>
        </div>
      </td>
      <td className="text-text-muted">{fmtTimeAgo(event.timestamp)}</td>
    </tr>
  );
}

function SentimentBar({ sentiment }: { sentiment: FlowSentiment | null }) {
  if (!sentiment) return null;
  const total = sentiment.bull_premium + sentiment.bear_premium;
  const bullPct = total > 0 ? (sentiment.bull_premium / total) * 100 : 50;

  return (
    <div className="metric-card space-y-2">
      <div className="flex justify-between text-xs">
        <div className="flex items-center gap-1.5 text-bull">
          <TrendingUp className="w-3 h-3" />
          <span>Bull ${fmtCompact(sentiment.bull_premium)}</span>
        </div>
        <div className="text-center">
          <span className={cn(
            "font-semibold text-sm",
            sentiment.sentiment_score > 0.2 ? "text-bull" :
            sentiment.sentiment_score < -0.2 ? "text-bear" : "text-warn"
          )}>
            {sentiment.dominant}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-bear">
          <span>Bear ${fmtCompact(sentiment.bear_premium)}</span>
          <TrendingDown className="w-3 h-3" />
        </div>
      </div>
      <div className="h-2 bg-bear/30 rounded-full overflow-hidden">
        <div
          className="h-full bg-bull rounded-full transition-all duration-500"
          style={{ width: `${bullPct}%` }}
        />
      </div>
      <div className="flex justify-between text-2xs text-text-muted">
        <span>{sentiment.n_unusual} unusual</span>
        <span>{sentiment.n_institutional} institutional</span>
        <span>{sentiment.n_events} trades</span>
      </div>
    </div>
  );
}

export default function FlowPage() {
  const [filter, setFilter] = useState<"all" | "unusual" | "sweep" | "block">("all");
  const [events, setEvents] = useState<FlowEvent[]>([]);
  const [newEventIds, setNewEventIds] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  // REST snapshot
  const { data: restData } = useSWR("/flow/unusual", fetcher, { refreshInterval: 10_000 });
  const { data: sentiment } = useSWR<FlowSentiment>("/flow/sentiment/SPX", fetcher, {
    refreshInterval: 30_000,
  });

  // Live WebSocket stream
  const { data: wsData, status } = useFlowStream();

  // Merge REST + WS events
  useEffect(() => {
    if (restData?.flows) {
      setEvents(restData.flows);
    }
  }, [restData]);

  useEffect(() => {
    if (!wsData) return;
    const newEvents: FlowEvent[] = (wsData as any)?.flows ?? [];
    if (!newEvents.length) return;

    const newIds = new Set(newEvents.map((e) => e.contract_id + e.timestamp));
    setNewEventIds(newIds);
    setEvents((prev) => [...newEvents, ...prev].slice(0, 200));
    setTimeout(() => setNewEventIds(new Set()), 2000);
  }, [wsData]);

  const filtered = events.filter((e) => {
    if (filter === "unusual") return e.is_unusual;
    if (filter === "sweep")   return e.trade_type === "sweep";
    if (filter === "block")   return e.trade_type === "block";
    return true;
  });

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Flame className="w-5 h-5 text-warn" />
          <h1 className="text-lg font-semibold text-text-primary">Flow Scanner</h1>
          <div className={cn(
            "w-2 h-2 rounded-full ml-1",
            status === "connected" ? "bg-bull animate-pulse" : "bg-bear"
          )} />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-text-muted" />
          {(["all", "unusual", "sweep", "block"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                "px-3 py-1 rounded text-xs font-medium capitalize transition-colors",
                filter === f
                  ? "bg-brand/20 text-brand-bright border border-brand/30"
                  : "text-text-muted hover:text-text-secondary"
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Sentiment bar */}
      <SentimentBar sentiment={sentiment ?? null} />

      {/* Flow table */}
      <div
        ref={scrollRef}
        className="bg-terminal-surface border border-terminal-border rounded-lg overflow-auto max-h-[calc(100vh-280px)]"
      >
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 gap-2">
            <Flame className="w-8 h-8 text-text-muted/30" />
            <p className="text-sm text-text-muted">
              {status === "connected" ? "Waiting for flow events…" : "Connecting to flow scanner…"}
            </p>
          </div>
        ) : (
          <table className="terminal-table">
            <thead className="sticky top-0 bg-terminal-surface z-10">
              <tr>
                <th>Symbol</th>
                <th>Strike</th>
                <th>Type</th>
                <th>Expiry</th>
                <th>Price</th>
                <th>Size</th>
                <th>Premium</th>
                <th>Trade</th>
                <th>Sentiment</th>
                <th>Score</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((event) => {
                const id = event.contract_id + event.timestamp;
                return (
                  <FlowRow
                    key={id}
                    event={event}
                    isNew={newEventIds.has(id)}
                  />
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <p className="text-xs text-text-muted text-center">
        Showing {filtered.length} of {events.length} events · Last 200 trades
      </p>
    </div>
  );
}

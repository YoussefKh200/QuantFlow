/**
 * useWebSocket — typed WebSocket hook with automatic reconnection.
 *
 * Features:
 *   - Exponential backoff reconnect (max 30s)
 *   - Ping/pong heartbeat
 *   - Message type discrimination
 *   - Cleanup on unmount
 */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/store";
import type { WsMessage } from "@/types/market";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";
const MAX_BACKOFF_MS = 30_000;
const INITIAL_BACKOFF_MS = 500;

type WsStatus = "connecting" | "connected" | "disconnected" | "error";

interface UseWebSocketOptions<T> {
  onMessage?: (msg: WsMessage<T>) => void;
  enabled?: boolean;
}

interface UseWebSocketReturn<T> {
  data: T | null;
  status: WsStatus;
  lastTs: string | null;
  send: (msg: string) => void;
}

export function useWebSocket<T = unknown>(
  channel: string,
  options: UseWebSocketOptions<T> = {}
): UseWebSocketReturn<T> {
  const { onMessage, enabled = true } = options;
  const token = useAuthStore((s) => s.token);

  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<WsStatus>("disconnected");
  const [lastTs, setLastTs] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(INITIAL_BACKOFF_MS);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const pingTimer = useRef<ReturnType<typeof setInterval>>();
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!enabled || !token || !mountedRef.current) return;

    const url = `${WS_BASE}/${channel}?token=${token}`;
    setStatus("connecting");

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) { ws.close(); return; }
        setStatus("connected");
        backoffRef.current = INITIAL_BACKOFF_MS;

        // Heartbeat ping every 20s
        pingTimer.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send("ping");
        }, 20_000);
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const msg: WsMessage<T> = JSON.parse(event.data);
          if (msg.type === "heartbeat") return;
          if ("data" in msg) setData(msg.data as T);
          if ("ts" in msg) setLastTs(msg.ts);
          onMessage?.(msg);
        } catch {
          // ignore malformed messages
        }
      };

      ws.onerror = () => {
        if (mountedRef.current) setStatus("error");
      };

      ws.onclose = () => {
        clearInterval(pingTimer.current);
        if (!mountedRef.current) return;
        setStatus("disconnected");
        // Exponential backoff reconnect
        const delay = Math.min(backoffRef.current, MAX_BACKOFF_MS);
        backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS);
        reconnectTimer.current = setTimeout(connect, delay);
      };
    } catch {
      setStatus("error");
    }
  }, [channel, token, enabled, onMessage]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectTimer.current);
      clearInterval(pingTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((msg: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(msg);
    }
  }, []);

  return { data, status, lastTs, send };
}

// ----------------------------------------------------------------
// Convenience hooks
// ----------------------------------------------------------------
export function useGEXStream(symbol: string) {
  return useWebSocket(`dealer/${symbol}`);
}

export function useGreeksStream(symbol: string) {
  return useWebSocket(`greeks/${symbol}`);
}

export function useFlowStream() {
  return useWebSocket("flow");
}

export function useAlertStream(userId: string | null) {
  return useWebSocket(userId ? `alerts/${userId}` : "", {
    enabled: !!userId,
  });
}

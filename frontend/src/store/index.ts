/**
 * QuantFlow Zustand stores.
 * Auth, market data, dealer, and alert state management.
 */
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { tokenStorage } from "@/lib/api";
import type { DealerSummary, Alert, User, Signal } from "@/types/market";

// ----------------------------------------------------------------
// Auth Store
// ----------------------------------------------------------------
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setUser: (user: User) => void;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  immer((set) => ({
    user: null,
    token: typeof window !== "undefined" ? tokenStorage.getAccess() : null,
    isAuthenticated: typeof window !== "undefined" ? !!tokenStorage.getAccess() : false,

    setUser: (user) =>
      set((s) => {
        s.user = user;
        s.isAuthenticated = true;
      }),

    setTokens: (access, refresh) => {
      tokenStorage.set(access, refresh);
      set((s) => {
        s.token = access;
        s.isAuthenticated = true;
      });
    },

    logout: () => {
      tokenStorage.clear();
      set((s) => {
        s.user = null;
        s.token = null;
        s.isAuthenticated = false;
      });
    },
  }))
);

// ----------------------------------------------------------------
// Market Store — active symbol + spot prices
// ----------------------------------------------------------------
interface MarketState {
  activeSymbol: string;
  spotPrices: Record<string, number>;
  setActiveSymbol: (symbol: string) => void;
  updateSpot: (symbol: string, price: number) => void;
}

export const useMarketStore = create<MarketState>()(
  immer((set) => ({
    activeSymbol: "SPX",
    spotPrices: {},

    setActiveSymbol: (symbol) =>
      set((s) => {
        s.activeSymbol = symbol;
      }),

    updateSpot: (symbol, price) =>
      set((s) => {
        s.spotPrices[symbol] = price;
      }),
  }))
);

// ----------------------------------------------------------------
// Dealer Store — cached GEX data per symbol
// ----------------------------------------------------------------
interface DealerState {
  summaries: Record<string, DealerSummary>;
  lastUpdated: Record<string, number>;
  updateSummary: (symbol: string, data: DealerSummary) => void;
}

export const useDealerStore = create<DealerState>()(
  immer((set) => ({
    summaries: {},
    lastUpdated: {},

    updateSummary: (symbol, data) =>
      set((s) => {
        s.summaries[symbol] = data;
        s.lastUpdated[symbol] = Date.now();
      }),
  }))
);

// ----------------------------------------------------------------
// Alert Store — live alert feed
// ----------------------------------------------------------------
interface AlertState {
  alerts: Alert[];
  unreadCount: number;
  addAlert: (alert: Alert) => void;
  markAllRead: () => void;
  clearAll: () => void;
}

export const useAlertStore = create<AlertState>()(
  immer((set) => ({
    alerts: [],
    unreadCount: 0,

    addAlert: (alert) =>
      set((s) => {
        s.alerts.unshift(alert);
        if (s.alerts.length > 100) s.alerts.pop();
        s.unreadCount += 1;
      }),

    markAllRead: () =>
      set((s) => {
        s.unreadCount = 0;
      }),

    clearAll: () =>
      set((s) => {
        s.alerts = [];
        s.unreadCount = 0;
      }),
  }))
);

// ----------------------------------------------------------------
// Signal Store — active trading signals
// ----------------------------------------------------------------
interface SignalState {
  signals: Signal[];
  setSignals: (signals: Signal[]) => void;
}

export const useSignalStore = create<SignalState>()(
  immer((set) => ({
    signals: [],
    setSignals: (signals) =>
      set((s) => {
        s.signals = signals;
      }),
  }))
);

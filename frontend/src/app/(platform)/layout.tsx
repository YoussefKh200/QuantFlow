"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity, BarChart2, Bell, BookOpen, ChevronDown,
  Cpu, Flame, Layers, LineChart, Settings, Shield,
  TrendingUp, Zap, LogOut, Search,
} from "lucide-react";
import { useAuthStore, useAlertStore, useMarketStore } from "@/store";
import { cn } from "@/lib/utils";

const NAV_SECTIONS = [
  {
    label: "Market Intelligence",
    items: [
      { href: "/",          icon: Activity,   label: "Overview" },
      { href: "/dealer",    icon: Layers,     label: "Dealer Positioning" },
      { href: "/gamma",     icon: Zap,        label: "Gamma Exposure" },
      { href: "/vanna",     icon: TrendingUp, label: "Vanna / Charm" },
      { href: "/liquidity", icon: BarChart2,  label: "Liquidity Map" },
    ],
  },
  {
    label: "Options Analytics",
    items: [
      { href: "/volatility", icon: LineChart, label: "Volatility Regime" },
      { href: "/flow",       icon: Flame,     label: "Flow Scanner" },
      { href: "/earnings",   icon: Cpu,       label: "Earnings / PEAD" },
      { href: "/gold",       icon: Shield,    label: "Gold Analytics" },
    ],
  },
  {
    label: "Research",
    items: [
      { href: "/research",  icon: BookOpen,   label: "Research Lab" },
      { href: "/portfolio", icon: Shield,     label: "Portfolio Risk" },
    ],
  },
];

const SYMBOLS = ["SPX", "SPY", "QQQ", "NDX", "IWM", "TSLA", "NVDA", "AAPL", "META", "MSFT"];

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const { unreadCount } = useAlertStore();
  const { activeSymbol, setActiveSymbol } = useMarketStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="flex h-screen overflow-hidden bg-terminal-bg">
      {/* ---- Sidebar ---- */}
      <aside
        className={cn(
          "flex flex-col border-r border-terminal-border bg-terminal-surface transition-all duration-200",
          sidebarOpen ? "w-56" : "w-14"
        )}
      >
        {/* Logo */}
        <div className="flex items-center gap-2 px-4 py-4 border-b border-terminal-border">
          <div className="w-7 h-7 rounded bg-brand flex items-center justify-center flex-shrink-0">
            <span className="text-white font-bold text-xs">QF</span>
          </div>
          {sidebarOpen && (
            <span className="font-semibold text-text-primary text-sm tracking-wide">
              QuantFlow
            </span>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-4">
          {NAV_SECTIONS.map((section) => (
            <div key={section.label}>
              {sidebarOpen && (
                <p className="px-2 mb-1 text-2xs font-semibold uppercase tracking-widest text-text-muted">
                  {section.label}
                </p>
              )}
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const active = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "nav-item",
                        active && "nav-item-active",
                        !sidebarOpen && "justify-center px-2"
                      )}
                      title={!sidebarOpen ? item.label : undefined}
                    >
                      <Icon className="w-4 h-4 flex-shrink-0" />
                      {sidebarOpen && <span>{item.label}</span>}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Bottom — settings + user */}
        <div className="border-t border-terminal-border p-2 space-y-0.5">
          <Link
            href="/settings"
            className={cn("nav-item", !sidebarOpen && "justify-center px-2")}
          >
            <Settings className="w-4 h-4 flex-shrink-0" />
            {sidebarOpen && <span>Settings</span>}
          </Link>
          <button
            onClick={logout}
            className={cn("nav-item w-full", !sidebarOpen && "justify-center px-2")}
          >
            <LogOut className="w-4 h-4 flex-shrink-0" />
            {sidebarOpen && <span>Sign out</span>}
          </button>
        </div>
      </aside>

      {/* ---- Main ---- */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Topbar */}
        <header className="flex items-center gap-3 px-4 py-2 border-b border-terminal-border bg-terminal-surface">
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="p-1.5 rounded hover:bg-terminal-muted text-text-secondary"
          >
            <Layers className="w-4 h-4" />
          </button>

          {/* Symbol selector */}
          <div className="flex items-center gap-1 bg-terminal-bg border border-terminal-border rounded-md px-2 py-1">
            <Search className="w-3 h-3 text-text-muted" />
            <select
              value={activeSymbol}
              onChange={(e) => setActiveSymbol(e.target.value)}
              className="bg-transparent border-none text-text-primary text-sm font-mono
                         focus:outline-none focus:ring-0 cursor-pointer pr-6"
            >
              {SYMBOLS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="flex-1" />

          {/* Alerts bell */}
          <button className="relative p-1.5 rounded hover:bg-terminal-muted text-text-secondary">
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-bear
                               text-white text-2xs flex items-center justify-center font-bold">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>

          {/* User avatar */}
          <div className="flex items-center gap-2 pl-2 border-l border-terminal-border">
            <div className="w-7 h-7 rounded-full bg-brand/20 border border-brand/40
                            flex items-center justify-center text-brand text-xs font-semibold">
              {user?.email?.[0]?.toUpperCase() ?? "U"}
            </div>
            {sidebarOpen && (
              <span className="text-xs text-text-secondary truncate max-w-24">
                {user?.email}
              </span>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-4">
          {children}
        </main>
      </div>
    </div>
  );
}

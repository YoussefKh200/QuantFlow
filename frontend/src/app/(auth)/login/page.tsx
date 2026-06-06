"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi, tokenStorage } from "@/lib/api";
import { useAuthStore } from "@/store";
import { cn } from "@/lib/utils";
import toast from "react-hot-toast";

export default function LoginPage() {
  const router = useRouter();
  const { setTokens, setUser } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    setLoading(true);

    try {
      const { data } = await authApi.login(email, password);
      setTokens(data.access_token, data.refresh_token);

      // Fetch user profile
      const { data: user } = await authApi.me();
      setUser(user);

      toast.success("Welcome back");
      router.replace("/");
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? "Login failed";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-terminal-bg px-4">
      <div className="w-full max-w-sm space-y-8">
        {/* Logo */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-xl bg-brand mx-auto flex items-center justify-center">
            <span className="text-white font-bold text-lg">QF</span>
          </div>
          <h1 className="text-xl font-semibold text-text-primary">QuantFlow Terminal</h1>
          <p className="text-sm text-text-muted">Institutional options analytics platform</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs text-text-muted font-medium uppercase tracking-wide">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="trader@firm.com"
              autoComplete="email"
              required
              className="w-full px-3 py-2.5 text-sm"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-text-muted font-medium uppercase tracking-wide">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
              className="w-full px-3 py-2.5 text-sm"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className={cn(
              "w-full py-2.5 rounded-lg text-sm font-medium transition-all",
              "bg-brand text-white hover:bg-brand-dim",
              "focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 focus:ring-offset-terminal-bg",
              loading && "opacity-60 cursor-not-allowed"
            )}
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="text-center text-xs text-text-muted">
          QuantFlow Terminal · Institutional Access Only
        </p>
      </div>
    </div>
  );
}

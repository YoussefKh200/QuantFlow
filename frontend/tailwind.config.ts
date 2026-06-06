import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark terminal palette
        terminal: {
          bg:       "#0a0a0f",      // deepest background
          surface:  "#0f0f17",      // card/panel background
          elevated: "#14141e",      // elevated panels
          border:   "#1e1e2e",      // borders
          muted:    "#2a2a3e",      // muted surfaces
        },
        // Brand colors
        brand: {
          DEFAULT:  "#6366f1",      // indigo-500
          dim:      "#4338ca",
          bright:   "#818cf8",
        },
        // Semantic
        bull:   "#22c55e",          // green-500
        bear:   "#ef4444",          // red-500
        warn:   "#f59e0b",          // amber-500
        info:   "#3b82f6",          // blue-500
        // Text
        text: {
          primary:   "#e2e8f0",
          secondary: "#94a3b8",
          muted:     "#475569",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      fontSize: {
        "2xs": ["0.65rem", { lineHeight: "1rem" }],
      },
      animation: {
        "pulse-fast":  "pulse 0.8s cubic-bezier(0.4,0,0.6,1) infinite",
        "fade-in":     "fadeIn 0.2s ease-out",
        "slide-up":    "slideUp 0.3s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%":   { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      boxShadow: {
        "glow-green":  "0 0 12px rgba(34,197,94,0.25)",
        "glow-red":    "0 0 12px rgba(239,68,68,0.25)",
        "glow-indigo": "0 0 12px rgba(99,102,241,0.25)",
      },
    },
  },
  plugins: [],
};

export default config;

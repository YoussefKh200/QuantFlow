import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "react-hot-toast";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "QuantFlow Terminal",
  description: "Institutional-grade options analytics and research platform",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans bg-terminal-bg text-text-primary antialiased`}>
        {children}
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: "#14141e",
              color: "#e2e8f0",
              border: "1px solid #1e1e2e",
              borderRadius: "8px",
              fontSize: "13px",
            },
            success: { iconTheme: { primary: "#22c55e", secondary: "#0a0a0f" } },
            error:   { iconTheme: { primary: "#ef4444", secondary: "#0a0a0f" } },
          }}
        />
      </body>
    </html>
  );
}

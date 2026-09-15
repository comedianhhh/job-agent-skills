import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

import { AuthGate, SignOutButton } from "@/components/AuthGate";

export const metadata: Metadata = {
  title: "Pipeline · job-agent-skills",
  description: "Kanban over career/tracker.md plus jobs-mcp scans.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-canvas text-ink">
        <header className="border-b border-line bg-panel">
          <nav className="mx-auto flex max-w-[1600px] items-center gap-6 px-4 py-2.5 text-sm">
            <span className="font-semibold tracking-tight">job-agent-skills</span>
            <Link href="/" className="text-muted hover:text-ink">
              Board
            </Link>
            <Link href="/scan" className="text-muted hover:text-ink">
              Scan
            </Link>
            <span className="ml-auto font-mono text-xs text-muted">career/tracker.md is the record</span>
            <SignOutButton />
          </nav>
        </header>
        <main className="mx-auto w-full max-w-[1600px] flex-1 px-4 py-4">
          <AuthGate>{children}</AuthGate>
        </main>
      </body>
    </html>
  );
}

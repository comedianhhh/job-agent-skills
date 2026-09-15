import type { Status } from "@/lib/api";

const TONE: Record<Status, string> = {
  DRAFT: "bg-line text-ink",
  BLOCKED: "bg-danger-soft text-danger",
  APPLIED: "bg-accent-soft text-accent",
  SCREEN: "bg-warn-soft text-warn",
  OA: "bg-warn-soft text-warn",
  TECH: "bg-warn-soft text-warn",
  ONSITE: "bg-warn-soft text-warn",
  OFFER: "bg-ok-soft text-ok",
  REJECTED: "bg-danger-soft text-danger",
  GHOSTED: "bg-line text-muted",
  WITHDRAWN: "bg-line text-muted",
};

export function StatusBadge({ status, raw }: { status: Status | null; raw?: string }) {
  const tone = status ? TONE[status] : "bg-line text-muted";
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 font-mono text-[11px] font-medium ${tone}`}>
      {status ?? raw?.replace(/`/g, "") ?? "—"}
    </span>
  );
}

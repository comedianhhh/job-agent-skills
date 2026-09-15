// Thin typed client for tracker-api. Every call goes to the FastAPI service, which is the only
// thing that touches career/tracker.md — the UI never parses markdown.
//
// Requests are same-origin: next.config.ts rewrites /api/* to the API. Set NEXT_PUBLIC_API_URL
// only if you want the browser to hit the API directly.

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

const TOKEN_KEY = "tracker_token";
export const UNAUTHORIZED_EVENT = "tracker:unauthorized";

export function getToken(): string | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private mode) — the token just lives for this page load */
  }
}

export type Status =
  | "DRAFT"
  | "BLOCKED"
  | "APPLIED"
  | "SCREEN"
  | "OA"
  | "TECH"
  | "ONSITE"
  | "OFFER"
  | "REJECTED"
  | "GHOSTED"
  | "WITHDRAWN";

export const STATUSES: Status[] = [
  "DRAFT",
  "BLOCKED",
  "APPLIED",
  "SCREEN",
  "OA",
  "TECH",
  "ONSITE",
  "OFFER",
  "REJECTED",
  "GHOSTED",
  "WITHDRAWN",
];

export interface Row {
  id: string;
  company: string;
  role: string;
  req: string;
  location: string;
  applied: string;
  applied_on: string | null;
  status: Status | null;
  status_raw: string;
  next_step: string;
  folder_text: string;
  folder_href: string;
  days_since_applied: number | null;
  follow_up_due: boolean;
  ghost_candidate: boolean;
}

export interface TrackerResponse {
  statuses: Status[];
  rows: Row[];
  path: string;
}

export interface Event {
  id: number;
  row_id: string;
  from_status: string | null;
  to_status: string;
  note: string;
  at: string;
}

export interface Scan {
  id: number;
  started_at: string;
  finished_at: string | null;
  params: Record<string, unknown>;
  scanned: number;
  matched: number;
  new: number;
  errors: string[];
}

export type Triage = "new" | "shortlisted" | "dismissed" | "tracked";

export interface Posting {
  id: number;
  source: string;
  board: string;
  external_id: string;
  title: string;
  company: string;
  location: string;
  url: string;
  posted_at: string | null;
  first_seen: string;
  last_seen: string;
  times_seen: number;
  triage: Triage;
  note: string;
  tracker_row_id: string | null;
  scan_id: number | null;
}

export interface Targets {
  boards: string[];
  linkedin: Record<string, string | number | boolean>[];
  filters: Record<string, string | number>;
  path: string;
  effective: Record<string, unknown>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (res.status === 401 && typeof window !== "undefined") {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => call<{ ok: boolean; career_dir: string; tracker_exists: boolean; auth: boolean }>("/api/health"),
  auth: () => call<{ ok: boolean }>("/api/auth"),
  tracker: () => call<TrackerResponse>("/api/tracker"),
  patchRow: (
    id: string,
    body: Partial<Pick<Row, "status" | "next_step" | "applied" | "location" | "req">> & { note?: string },
  ) => call<Row>(`/api/tracker/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  createRow: (body: { company: string; role: string; req?: string; location?: string; next_step?: string }) =>
    call<Row>("/api/tracker", { method: "POST", body: JSON.stringify(body) }),
  rowEvents: (id: string) => call<Event[]>(`/api/tracker/${id}/events`),
  events: (limit = 50) => call<Event[]>(`/api/events?limit=${limit}`),
  targets: () => call<Targets>("/api/targets"),
  scans: () => call<Scan[]>("/api/scans"),
  runScan: (body: { hours?: number; write_scan_file?: boolean }) =>
    call<Scan>("/api/scans", { method: "POST", body: JSON.stringify(body) }),
  postings: (q: { triage?: Triage; scan_id?: number } = {}) => {
    const p = new URLSearchParams();
    if (q.triage) p.set("triage", q.triage);
    if (q.scan_id != null) p.set("scan_id", String(q.scan_id));
    const qs = p.toString();
    return call<Posting[]>(`/api/postings${qs ? `?${qs}` : ""}`);
  },
  patchPosting: (id: number, body: { triage?: Triage; note?: string }) =>
    call<Posting>(`/api/postings/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  trackPosting: (id: number) => call<Row>(`/api/postings/${id}/track`, { method: "POST" }),
};

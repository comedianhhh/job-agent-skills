"use client";

import { useEffect, useState } from "react";

import { api, ApiError, type Posting, type Scan, type Targets, type Triage } from "@/lib/api";
import { fmtDate } from "@/lib/md";

const TRIAGE_TABS: { id: Triage | "all"; label: string }[] = [
  { id: "new", label: "New" },
  { id: "shortlisted", label: "Shortlisted" },
  { id: "tracked", label: "Tracked" },
  { id: "dismissed", label: "Dismissed" },
  { id: "all", label: "All" },
];

export function ScanPanel() {
  const [targets, setTargets] = useState<Targets | null>(null);
  const [scans, setScans] = useState<Scan[]>([]);
  const [postings, setPostings] = useState<Posting[]>([]);
  const [tab, setTab] = useState<Triage | "all">("new");
  const [hours, setHours] = useState<number | "">("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [last, setLast] = useState<Scan | null>(null);

  const [refresh, setRefresh] = useState(0); // bump to refetch for the current tab

  useEffect(() => {
    let alive = true;
    Promise.all([api.targets(), api.scans(), api.postings(tab === "all" ? {} : { triage: tab })])
      .then(([t, s, p]) => {
        if (!alive) return;
        setTargets(t);
        setScans(s);
        setPostings(p);
        setError(null);
      })
      .catch((e) => alive && setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e)));
    return () => {
      alive = false;
    };
  }, [tab, refresh]);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const s = await api.runScan(hours === "" ? {} : { hours: Number(hours) });
      setLast(s);
      setTab("new");
      setRefresh((n) => n + 1);
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
    } finally {
      setRunning(false);
    }
  };

  const setTriage = async (p: Posting, triage: Triage) => {
    try {
      const updated = await api.patchPosting(p.id, { triage });
      setPostings((cur) =>
        cur.map((x) => (x.id === p.id ? updated : x)).filter((x) => tab === "all" || x.triage === tab),
      );
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
    }
  };

  const track = async (p: Posting) => {
    try {
      await api.trackPosting(p.id);
      setRefresh((n) => n + 1);
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
    }
  };

  const eff = targets?.effective ?? {};

  return (
    <div className="grid gap-4 lg:grid-cols-[20rem_1fr]">
      <aside className="flex flex-col gap-4 text-sm">
        <section className="rounded-md border border-line bg-panel p-3">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted">Targets</h2>
          <p className="mt-1 font-mono text-[11px] text-muted break-all">{targets?.path ?? "…"}</p>
          <div className="mt-3">
            <p className="text-xs text-muted">Boards</p>
            <ul className="mt-1 font-mono text-xs">
              {targets?.boards.length ? (
                targets.boards.map((b) => <li key={b}>{b}</li>)
              ) : (
                <li className="text-muted">none</li>
              )}
            </ul>
          </div>
          <div className="mt-3">
            <p className="text-xs text-muted">LinkedIn queries</p>
            <ul className="mt-1 text-xs">
              {targets?.linkedin.length ? (
                targets.linkedin.map((q, i) => (
                  <li key={i}>
                    “{String(q.keywords)}” · {String(q.location)}
                    {q.remote_only ? " · remote" : ""}
                  </li>
                ))
              ) : (
                <li className="text-muted">none</li>
              )}
            </ul>
          </div>
          <dl className="mt-3 grid grid-cols-[6rem_1fr] gap-y-1 font-mono text-[11px]">
            <dt className="text-muted">hours</dt>
            <dd>{String(eff.hours ?? "")}</dd>
            <dt className="text-muted">include</dt>
            <dd className="break-all">{String(eff.include_regex ?? "—")}</dd>
            <dt className="text-muted">exclude</dt>
            <dd className="break-all">{String(eff.exclude_regex ?? "—")}</dd>
            <dt className="text-muted">location</dt>
            <dd className="break-all">{String(eff.location_regex ?? "—")}</dd>
          </dl>
        </section>

        <section className="rounded-md border border-line bg-panel p-3">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted">Run</h2>
          <label className="mt-2 flex items-center gap-2 text-xs">
            <span className="text-muted">hours override</span>
            <input
              type="number"
              min={1}
              value={hours}
              onChange={(e) => setHours(e.target.value === "" ? "" : Number(e.target.value))}
              placeholder={String(eff.hours ?? 24)}
              className="w-20 rounded border border-line bg-canvas px-2 py-1 font-mono"
            />
          </label>
          <button
            onClick={run}
            disabled={running || !targets || (!targets.boards.length && !targets.linkedin.length)}
            className="mt-3 w-full rounded bg-accent px-3 py-1.5 text-xs font-medium text-white disabled:opacity-40"
          >
            {running ? "Scanning… (LinkedIn is slow)" : "Scan now"}
          </button>
          {last ? (
            <p className="mt-2 text-xs text-muted">
              fetched {last.scanned} · matched {last.matched} · <span className="text-ink">{last.new} new</span>
              {last.errors.length ? <span className="text-danger"> · {last.errors.length} errors</span> : null}
            </p>
          ) : null}
          <p className="mt-2 text-[11px] text-muted">New postings are also appended to career/SCAN-&lt;date&gt;.md.</p>
        </section>

        <section className="rounded-md border border-line bg-panel p-3">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted">Recent scans</h2>
          {scans.length === 0 ? (
            <p className="mt-1 text-xs text-muted">none yet</p>
          ) : (
            <ul className="mt-2 flex flex-col gap-1 font-mono text-[11px]">
              {scans.slice(0, 8).map((s) => (
                <li key={s.id} className="flex justify-between gap-2" title={s.errors.join("\n")}>
                  <span className="text-muted">{fmtDate(s.started_at)}</span>
                  <span>
                    {s.matched} / <b>{s.new} new</b>
                    {s.errors.length ? <span className="text-danger"> !{s.errors.length}</span> : null}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </aside>

      <section className="min-w-0">
        <div className="flex flex-wrap items-center gap-1 border-b border-line text-sm">
          {TRIAGE_TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-3 py-2 text-xs ${tab === t.id ? "border-b-2 border-accent font-medium" : "text-muted hover:text-ink"}`}
            >
              {t.label}
            </button>
          ))}
          <span className="ml-auto pr-1 font-mono text-[11px] text-muted">{postings.length}</span>
        </div>

        {error ? (
          <div className="mt-3 rounded border border-danger/40 bg-danger-soft px-3 py-2 text-xs text-danger">
            {error}{" "}
            <button className="underline" onClick={() => setError(null)}>
              dismiss
            </button>
          </div>
        ) : null}

        {postings.length === 0 ? (
          <p className="mt-6 text-center text-sm text-muted">Nothing here. Run a scan.</p>
        ) : (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-[11px] uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-2 py-1.5 font-medium">Company</th>
                  <th className="px-2 py-1.5 font-medium">Role</th>
                  <th className="px-2 py-1.5 font-medium">Location</th>
                  <th className="px-2 py-1.5 font-medium">Posted</th>
                  <th className="px-2 py-1.5 font-medium">Source</th>
                  <th className="px-2 py-1.5 font-medium">Seen</th>
                  <th className="px-2 py-1.5 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {postings.map((p) => (
                  <tr key={p.id} className="border-t border-line align-top hover:bg-panel">
                    <td className="px-2 py-2 font-medium">{p.company}</td>
                    <td className="px-2 py-2">
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noreferrer"
                        className="underline decoration-line hover:decoration-ink"
                      >
                        {p.title}
                      </a>
                      {p.note ? <p className="mt-0.5 text-muted">{p.note}</p> : null}
                    </td>
                    <td className="px-2 py-2 text-muted">{p.location}</td>
                    <td className="px-2 py-2 font-mono text-muted">{(p.posted_at ?? "").slice(0, 10)}</td>
                    <td className="px-2 py-2 font-mono text-muted">
                      {p.source}
                      {p.board && p.board !== "guest" ? `:${p.board}` : ""}
                    </td>
                    <td className="px-2 py-2 font-mono text-muted">{p.times_seen}×</td>
                    <td className="px-2 py-2">
                      <div className="flex flex-wrap gap-1">
                        {p.triage === "tracked" ? (
                          <span className="rounded bg-ok-soft px-1.5 py-0.5 font-mono text-[10px] text-ok">
                            in tracker
                          </span>
                        ) : (
                          <>
                            {p.triage !== "shortlisted" ? (
                              <button
                                onClick={() => setTriage(p, "shortlisted")}
                                className="rounded border border-line px-1.5 py-0.5 hover:border-accent"
                              >
                                shortlist
                              </button>
                            ) : null}
                            <button onClick={() => track(p)} className="rounded bg-accent px-1.5 py-0.5 text-white">
                              track
                            </button>
                            {p.triage !== "dismissed" ? (
                              <button
                                onClick={() => setTriage(p, "dismissed")}
                                className="rounded border border-line px-1.5 py-0.5 text-muted hover:border-danger"
                              >
                                dismiss
                              </button>
                            ) : (
                              <button
                                onClick={() => setTriage(p, "new")}
                                className="rounded border border-line px-1.5 py-0.5 text-muted"
                              >
                                restore
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

import { api, ApiError, STATUSES, type Event, type Row, type Status } from "@/lib/api";
import { fmtDate, mdInline } from "@/lib/md";

import { StatusBadge } from "./StatusBadge";

export function RowDrawer({
  row,
  onClose,
  onSaved,
}: {
  row: Row | null;
  onClose: () => void;
  onSaved: (row: Row) => void;
}) {
  const [status, setStatus] = useState<Status | "">(row?.status ?? "");
  const [nextStep, setNextStep] = useState(row?.next_step ?? "");
  const [applied, setApplied] = useState(row?.applied ?? "");
  const [note, setNote] = useState("");
  const [events, setEvents] = useState<Event[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const rowId = row?.id;
  useEffect(() => {
    if (!rowId) return;
    let alive = true;
    api
      .rowEvents(rowId)
      .then((ev) => alive && setEvents(ev))
      .catch(() => alive && setEvents([]));
    return () => {
      alive = false;
    };
  }, [rowId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!row) return null;

  const dirty = status !== (row.status ?? "") || nextStep !== row.next_step || applied !== row.applied;

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const body: Parameters<typeof api.patchRow>[1] = { note };
      if (status && status !== row.status) body.status = status;
      if (nextStep !== row.next_step) body.next_step = nextStep;
      if (applied !== row.applied) body.applied = applied;
      const updated = await api.patchRow(row.id, body);
      onSaved(updated);
      setNote("");
      setEvents(await api.rowEvents(row.id));
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-20 flex justify-end bg-black/30" onClick={onClose}>
      <aside
        className="flex h-full w-full max-w-lg flex-col overflow-y-auto border-l border-line bg-panel p-5 text-sm shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">{row.company}</h2>
            <p className="text-muted">{row.role}</p>
          </div>
          <button onClick={onClose} className="rounded px-2 py-1 text-muted hover:bg-line" aria-label="Close">
            ✕
          </button>
        </div>

        <dl className="mt-4 grid grid-cols-[6rem_1fr] gap-x-3 gap-y-1.5 text-xs">
          <dt className="text-muted">Req</dt>
          <dd className="font-mono">{row.req || "—"}</dd>
          <dt className="text-muted">Location</dt>
          <dd>{row.location || "—"}</dd>
          <dt className="text-muted">Folder</dt>
          <dd className="font-mono break-all">{row.folder_href || row.folder_text || "—"}</dd>
          <dt className="text-muted">Status</dt>
          <dd>
            <StatusBadge status={row.status} raw={row.status_raw} />
            {row.follow_up_due ? <span className="ml-2 text-warn">follow-up due</span> : null}
            {row.ghost_candidate ? <span className="ml-2 text-muted">ghost candidate</span> : null}
          </dd>
        </dl>

        <div className="mt-5 flex flex-col gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-xs text-muted">Status</span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as Status)}
              className="rounded border border-line bg-canvas px-2 py-1.5 font-mono text-xs"
            >
              {row.status === null ? <option value="">{row.status_raw || "(unknown)"}</option> : null}
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-muted">Applied (as written in the table)</span>
            <input
              value={applied}
              onChange={(e) => setApplied(e.target.value)}
              className="rounded border border-line bg-canvas px-2 py-1.5 font-mono text-xs"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-muted">Next step (markdown, one line)</span>
            <textarea
              value={nextStep}
              onChange={(e) => setNextStep(e.target.value)}
              rows={5}
              className="rounded border border-line bg-canvas px-2 py-1.5 text-xs leading-relaxed"
            />
            <div
              className="cell-md rounded bg-canvas px-2 py-1.5 text-xs text-muted"
              dangerouslySetInnerHTML={{ __html: mdInline(nextStep) || "&nbsp;" }}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-muted">Note for the event log (optional)</span>
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. recruiter email 9/16"
              className="rounded border border-line bg-canvas px-2 py-1.5 text-xs"
            />
          </label>
          {error ? <p className="text-xs text-danger">{error}</p> : null}
          <div className="flex gap-2">
            <button
              onClick={save}
              disabled={!dirty || busy}
              className="rounded bg-accent px-3 py-1.5 text-xs font-medium text-white disabled:opacity-40"
            >
              {busy ? "Saving…" : "Save to tracker.md"}
            </button>
            <button onClick={onClose} className="rounded border border-line px-3 py-1.5 text-xs">
              Cancel
            </button>
          </div>
        </div>

        <section className="mt-6">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">History</h3>
          {events.length === 0 ? (
            <p className="mt-1 text-xs text-muted">No status changes recorded through the app yet.</p>
          ) : (
            <ul className="mt-2 flex flex-col gap-1.5 text-xs">
              {events.map((e) => (
                <li key={e.id} className="flex items-baseline gap-2">
                  <span className="w-28 shrink-0 font-mono text-muted">{fmtDate(e.at)}</span>
                  <span className="font-mono">
                    {e.from_status ?? "∅"} → {e.to_status}
                  </span>
                  {e.note ? <span className="text-muted">— {e.note}</span> : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      </aside>
    </div>
  );
}

"use client";

import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useCallback, useEffect, useMemo, useState } from "react";

import { api, ApiError, STATUSES, type Row, type Status } from "@/lib/api";
import { mdInline } from "@/lib/md";

import { RowDrawer } from "./RowDrawer";
import { StatusBadge } from "./StatusBadge";

const OTHER = "__other__";
type ColumnId = Status | typeof OTHER;

export function Board() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [path, setPath] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [onlyDue, setOnlyDue] = useState(false);
  const [hideClosed, setHideClosed] = useState(true);
  const [active, setActive] = useState<Row | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const t = await api.tracker();
      setRows(t.rows);
      setPath(t.path);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
    }
  }, []);

  useEffect(() => {
    let alive = true;
    api
      .tracker()
      .then((t) => {
        if (!alive) return;
        setRows(t.rows);
        setPath(t.path);
        setError(null);
      })
      .catch((e) => alive && setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e)));
    return () => {
      alive = false;
    };
  }, []);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  const visible = useMemo(() => {
    if (!rows) return [];
    const q = filter.trim().toLowerCase();
    return rows.filter((r) => {
      if (onlyDue && !r.follow_up_due) return false;
      if (q && !`${r.company} ${r.role} ${r.location} ${r.req}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [rows, filter, onlyDue]);

  const columns = useMemo(() => {
    const closed: Status[] = ["REJECTED", "GHOSTED", "WITHDRAWN"];
    const ids: ColumnId[] = STATUSES.filter((s) => !hideClosed || !closed.includes(s));
    const hasOther = visible.some((r) => r.status === null);
    if (hasOther) ids.push(OTHER);
    return ids.map((id) => ({
      id,
      rows: visible.filter((r) => (id === OTHER ? r.status === null : r.status === id)),
    }));
  }, [visible, hideClosed]);

  const onDragStart = (e: DragStartEvent) => {
    setActive(rows?.find((r) => r.id === e.active.id) ?? null);
  };

  const onDragEnd = async (e: DragEndEvent) => {
    setActive(null);
    const target = e.over?.id as ColumnId | undefined;
    const row = rows?.find((r) => r.id === e.active.id);
    if (!row || !target || target === OTHER || target === row.status) return;
    const prev = rows!;
    setRows(prev.map((r) => (r.id === row.id ? { ...r, status: target } : r)));
    try {
      const updated = await api.patchRow(row.id, { status: target, note: "moved on the board" });
      setRows((cur) => (cur ?? prev).map((r) => (r.id === row.id ? updated : r)));
    } catch (err) {
      setRows(prev);
      setError(err instanceof ApiError ? `${err.status}: ${err.message}` : String(err));
    }
  };

  const dueCount = rows?.filter((r) => r.follow_up_due).length ?? 0;

  if (error && !rows) {
    return (
      <div className="rounded border border-danger/40 bg-danger-soft p-4 text-sm text-danger">
        <p className="font-medium">Cannot reach tracker-api</p>
        <p className="mt-1 font-mono text-xs">{error}</p>
        <p className="mt-2 text-ink">
          Start it with{" "}
          <code className="font-mono">CAREER_DIR=/path/to/career uvicorn --factory tracker_api.main:create_app</code> or{" "}
          <code className="font-mono">docker compose up</code>.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-7.5rem)] flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter company / role / location…"
          className="w-72 rounded border border-line bg-panel px-2.5 py-1.5 text-sm outline-none focus:border-accent"
        />
        <label className="flex items-center gap-1.5 text-muted">
          <input type="checkbox" checked={onlyDue} onChange={(e) => setOnlyDue(e.target.checked)} />
          follow-up due
          {dueCount ? (
            <span className="rounded bg-warn-soft px-1.5 font-mono text-[11px] text-warn">{dueCount}</span>
          ) : null}
        </label>
        <label className="flex items-center gap-1.5 text-muted">
          <input type="checkbox" checked={hideClosed} onChange={(e) => setHideClosed(e.target.checked)} />
          hide closed
        </label>
        <span className="ml-auto font-mono text-xs text-muted" title={path}>
          {rows ? `${rows.length} rows` : "loading…"}
        </span>
        <button onClick={load} className="rounded border border-line bg-panel px-2.5 py-1 text-xs hover:border-accent">
          Reload
        </button>
      </div>

      {error ? (
        <div className="rounded border border-danger/40 bg-danger-soft px-3 py-2 text-xs text-danger">
          {error}{" "}
          <button className="underline" onClick={() => setError(null)}>
            dismiss
          </button>
        </div>
      ) : null}

      <DndContext sensors={sensors} onDragStart={onDragStart} onDragEnd={onDragEnd}>
        <div className="flex min-h-0 flex-1 gap-3 overflow-x-auto pb-2">
          {columns.map((c) => (
            <Column key={c.id} id={c.id} rows={c.rows} onOpen={setOpen} />
          ))}
        </div>
        <DragOverlay>{active ? <CardBody row={active} dragging /> : null}</DragOverlay>
      </DndContext>

      {open ? (
        <RowDrawer
          key={open}
          row={rows?.find((r) => r.id === open) ?? null}
          onClose={() => setOpen(null)}
          onSaved={(updated) => setRows((cur) => (cur ?? []).map((r) => (r.id === updated.id ? updated : r)))}
        />
      ) : null}
    </div>
  );
}

function Column({ id, rows, onOpen }: { id: ColumnId; rows: Row[]; onOpen: (id: string) => void }) {
  const droppable = id !== OTHER;
  const { setNodeRef, isOver } = useDroppable({ id, disabled: !droppable });
  return (
    <section
      ref={setNodeRef}
      className={`flex w-64 shrink-0 flex-col rounded-md border bg-panel/60 ${
        isOver ? "border-accent" : "border-line"
      }`}
    >
      <header className="flex items-center justify-between border-b border-line px-3 py-2">
        <span className="font-mono text-xs font-semibold tracking-wide">{id === OTHER ? "OTHER" : id}</span>
        <span className="font-mono text-[11px] text-muted">{rows.length}</span>
      </header>
      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-2">
        {rows.map((r) => (
          <Card key={r.id} row={r} draggable={droppable} onOpen={onOpen} />
        ))}
        {rows.length === 0 ? <p className="px-1 py-3 text-center text-xs text-muted">—</p> : null}
      </div>
    </section>
  );
}

function Card({ row, draggable, onOpen }: { row: Row; draggable: boolean; onOpen: (id: string) => void }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: row.id, disabled: !draggable });
  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      onClick={() => onOpen(row.id)}
      className={`cursor-grab active:cursor-grabbing ${isDragging ? "opacity-30" : ""}`}
    >
      <CardBody row={row} />
    </div>
  );
}

function CardBody({ row, dragging = false }: { row: Row; dragging?: boolean }) {
  return (
    <article
      className={`rounded border border-line bg-panel p-2.5 text-sm shadow-sm ${dragging ? "rotate-1 shadow-lg" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-medium" title={row.company}>
            {row.company}
          </p>
          <p className="truncate text-xs text-muted" title={row.role}>
            {row.role}
          </p>
        </div>
        {row.follow_up_due ? (
          <span
            className="shrink-0 rounded bg-warn-soft px-1.5 py-0.5 font-mono text-[10px] text-warn"
            title="10+ business days since APPLIED"
          >
            follow up
          </span>
        ) : null}
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-muted">
        {row.location ? <span className="truncate">{row.location}</span> : null}
        {row.applied_on ? (
          <span className="font-mono">
            {row.applied_on}
            {row.days_since_applied != null ? ` · ${row.days_since_applied}d` : ""}
          </span>
        ) : null}
      </div>
      {row.next_step ? (
        <p
          className="cell-md mt-1.5 line-clamp-2 text-xs text-ink/80"
          dangerouslySetInnerHTML={{ __html: mdInline(row.next_step) }}
        />
      ) : null}
      {row.status === null ? (
        <div className="mt-1.5">
          <StatusBadge status={null} raw={row.status_raw} />
        </div>
      ) : null}
    </article>
  );
}

"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

import { api, ApiError, getToken, setToken, UNAUTHORIZED_EVENT } from "@/lib/api";

type State = "checking" | "locked" | "open" | "offline";

/** Blocks the app until /api/auth answers 200; any later 401 re-locks it. */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<State>("checking");
  const [attempt, setAttempt] = useState(0);
  const [draft, setDraft] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .auth()
      .then(() => alive && setState("open"))
      .catch((e) => {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 401) {
          setState("locked");
          setMessage(getToken() ? "That token was rejected." : null);
        } else {
          setState("offline");
          setMessage(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
        }
      });
    return () => {
      alive = false;
    };
  }, [attempt]);

  useEffect(() => {
    const relock = () => setState("locked");
    window.addEventListener(UNAUTHORIZED_EVENT, relock);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, relock);
  }, []);

  if (state === "open") return <>{children}</>;

  if (state === "checking") {
    return <p className="py-16 text-center text-sm text-muted">Connecting…</p>;
  }

  if (state === "offline") {
    return (
      <div className="mx-auto mt-16 max-w-md rounded border border-danger/40 bg-danger-soft p-4 text-sm text-danger">
        <p className="font-medium">Cannot reach tracker-api</p>
        <p className="mt-1 font-mono text-xs">{message}</p>
        <button
          onClick={() => setAttempt((n) => n + 1)}
          className="mt-3 rounded border border-danger/40 px-2.5 py-1 text-xs"
        >
          Retry
        </button>
      </div>
    );
  }

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setToken(draft.trim() || null);
    window.dispatchEvent(new Event(TOKEN_CHANGED));
    setDraft("");
    setState("checking");
    setAttempt((n) => n + 1);
  };

  return (
    <form
      onSubmit={submit}
      className="mx-auto mt-16 flex max-w-sm flex-col gap-3 rounded-md border border-line bg-panel p-5 text-sm"
    >
      <h1 className="font-semibold">Tracker token</h1>
      <p className="text-xs text-muted">
        This instance is protected. Paste the <code className="font-mono">TRACKER_TOKEN</code> the API was started with.
      </p>
      <input
        type="password"
        autoFocus
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="token"
        className="rounded border border-line bg-canvas px-2.5 py-1.5 font-mono text-xs outline-none focus:border-accent"
      />
      {message ? <p className="text-xs text-danger">{message}</p> : null}
      <button
        type="submit"
        disabled={!draft.trim()}
        className="rounded bg-accent px-3 py-1.5 text-xs font-medium text-white disabled:opacity-40"
      >
        Unlock
      </button>
    </form>
  );
}

const TOKEN_CHANGED = "tracker:token";

function subscribeToken(cb: () => void) {
  window.addEventListener(TOKEN_CHANGED, cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener(TOKEN_CHANGED, cb);
    window.removeEventListener("storage", cb);
  };
}

export function SignOutButton() {
  const hasToken = useSyncExternalStore(
    subscribeToken,
    () => Boolean(getToken()),
    () => false, // server render: no token
  );
  if (!hasToken) return null;
  return (
    <button
      onClick={() => {
        setToken(null);
        window.dispatchEvent(new Event(TOKEN_CHANGED));
        window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
      }}
      className="text-xs text-muted hover:text-ink"
    >
      sign out
    </button>
  );
}

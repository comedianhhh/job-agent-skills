"""apply-graph-eval: run the graph over real postings, grade every run with code, keep a regression set.

    apply-graph-eval collect --limit 80        # run over career/*/03-Job-Description.md, save traces
    apply-graph-eval build --size 30           # pick failing runs from the latest collect -> regression.json
    apply-graph-eval score --note "prompt v2"  # rerun the regression set, write a scoreboard, diff vs last

Everything lands in <career>/_graph-evals/ (career/ is private; postings and facts never go into this
repo). Runs stop at the human gate: reaching `approve` counts as done, nothing is recorded, and the
cover letter goes to _graph-evals/letters/, never into the real application folder.

Every check is plain code, no LLM judge:
  ran            the run finished without an exception
  decision       APPLY/SKIP matches what Alan did (tracker.md: applied or further -> APPLY, BLOCKED -> SKIP)
  evidence       every evidence quote in the match matrix is really in facts.md
  first_draft    the first draft passed trace_check (no number missing from facts.md)
  gate           an APPLY run reached the human gate instead of BLOCKED after 3 drafts
  paragraphs     the letter has the 3 paragraphs the draft prompt asks for
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from .graph import build_graph
from .llm import ClaudeCodeLLM, ClaudeLLM
from .state import SERDE
from .telemetry import Recorder, per_node

CHECKS = ["ran", "decision", "evidence", "first_draft", "gate", "paragraphs"]
APPLIED = {"APPLIED", "SCREEN", "OA", "TECH", "ONSITE", "OFFER", "REJECTED", "GHOSTED"}
DEFAULT_CAREER = Path(__file__).resolve().parents[3] / "career"


# ---------- ground truth ----------


def expected_decisions(tracker: str) -> dict[str, str]:
    """folder name -> APPLY / SKIP, from the tracker's Status and Folder columns.

    Folders the tracker gives no verdict for are left out."""
    out: dict[str, str] = {}
    for line in tracker.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 8 or cells[0] in {"Company", "---"}:
            continue
        status, folder = cells[5].split()[0].upper() if cells[5] else "", cells[-1]
        if not re.match(r"\d{4}-\d{2}-\d{2}-", folder):
            continue
        if status in APPLIED:
            out[folder] = "APPLY"
        elif status == "BLOCKED":
            out.setdefault(folder, "SKIP")
    return out


# ---------- grading ----------


def _norm(text: str) -> str:
    text = re.sub(r"[*_`>#\"“”‘’]", "", text.lower())
    text = text.replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", text).strip(" .-:;,'")


def missing_quotes(evidence: list[str], facts: str) -> list[str]:
    """Evidence quotes not found in facts.md.

    The model often joins several real lines with '...', ';', ' / ' or ' | ', and adds a short
    parenthetical like '(8 months)'. A quote passes when every piece is in facts.md, with or without
    its parentheticals. Commentary mixed into the quote ("Partial: the facts record no ...") still fails.
    """
    f = _norm(facts)
    bad = []
    for q in evidence:
        pieces = [_norm(p) for p in re.split(r"\.\.\.|…|;\s| / | \| ", q)]
        for p in pieces:
            if len(p) < 12 or p in f:
                continue
            bare = _norm(re.sub(r"\s*\([^()]*\)", "", p))
            # a short label the model put in front, e.g. "servicing-desk — Python 3.12, ..."
            bare = re.sub(r"^[\w .-]{1,30}(?: - |: )(?=.{12})", "", bare) if bare not in f else bare
            if len(bare) >= 12 and bare not in f:
                bad.append(q)
                break
    return bad


def grade(trace: dict, facts: str, expected: str | None) -> dict[str, dict]:
    """check -> {"ok": True/False/None, "why": str}. None means not applicable to this run."""
    na = {"ok": None, "why": ""}
    if trace.get("error"):
        return {"ran": {"ok": False, "why": trace["error"][:200]}} | {c: na for c in CHECKS[1:]}
    m = trace["match"]
    out = {"ran": {"ok": True, "why": ""}}
    out["decision"] = (
        na
        if expected is None
        else {
            "ok": m["decision"] == expected,
            "why": f"got {m['decision']}, expected {expected}: {m['reason']}",
        }
    )
    quotes = [r["evidence"] for r in m["requirements"] if r.get("evidence")]
    bad = missing_quotes(quotes, facts)
    out["evidence"] = {
        "ok": not bad,
        "why": f"{len(bad)}/{len(quotes)} not in facts: " + " | ".join(bad)[:300],
    }
    if m["decision"] == "SKIP":
        return out | {c: na for c in CHECKS[3:]}
    first = trace["findings_per_draft"][0] if trace["findings_per_draft"] else None
    out["first_draft"] = {
        "ok": first == 0,
        "why": f"{first} untraced number(s); per draft {trace['findings_per_draft']}",
    }
    out["gate"] = {"ok": trace["end"] == "gate", "why": f"ended {trace['end']}"}
    paras = [p for p in re.split(r"\n\s*\n", trace.get("draft") or "") if p.strip()]
    out["paragraphs"] = {"ok": len(paras) == 3, "why": f"{len(paras)} paragraphs"}
    return out


# ---------- running ----------


def make_llm(backend: str, model: str | None, effort: str):
    if backend == "api":
        return ClaudeLLM(**({"model": model} if model else {}), effort=effort)
    return ClaudeCodeLLM(**({"model": model} if model else {}), effort=effort)


def run_case(case: str, job: Path, facts: str, root: Path, llm) -> dict:
    rec = Recorder()
    graph = build_graph(llm, checkpointer=InMemorySaver(serde=SERDE), recorder=rec)
    config = {"configurable": {"thread_id": case}}
    out_dir = root / "letters" / case
    t0 = time.perf_counter()
    trace: dict = {"case": case, "job": str(job), "error": None}
    try:
        result = graph.invoke(
            {"job_text": job.read_text(encoding="utf-8"), "facts_text": facts, "out_dir": str(out_dir)},
            config,
        )
        trace["end"] = "gate" if "__interrupt__" in result else result.get("status")
    except Exception as e:  # one bad run must not stop the batch; it is graded as ran=False
        trace["error"] = f"{type(e).__name__}: {e}"
        trace["end"] = "error"
    values = graph.get_state(config).values
    m = values.get("match")
    trace |= {
        "match": m.model_dump() if m else None,
        "draft": values.get("draft"),
        "attempts": values.get("attempts", 0),
        "log": values.get("log", []),
        "findings_per_draft": [
            int(x) for x in re.findall(r"trace_check: (\d+) finding", "\n".join(values.get("log", [])))
        ],
        "spans": rec.spans,
        "wall_ms": round((time.perf_counter() - t0) * 1000),
    }
    return trace


def run_batch(cases: list[tuple[str, Path]], args, label: str) -> list[dict]:
    root = args.career / "_graph-evals"
    facts = (args.career / "facts.md").read_text(encoding="utf-8")
    tdir = root / "traces" / label
    tdir.mkdir(parents=True, exist_ok=True)
    traces = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(run_case, c, j, facts, root, make_llm(args.backend, args.model, args.effort)): c
            for c, j in cases
        }
        for i, fut in enumerate(as_completed(futs), 1):
            t = fut.result()
            (tdir / f"{t['case']}.json").write_text(
                json.dumps(t, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            traces.append(t)
            print(f"[{i}/{len(cases)}] {t['case']}: {t['end']} ({t['wall_ms'] / 1000:.0f}s)", flush=True)
    return sorted(traces, key=lambda t: t["case"])


def grade_all(traces: list[dict], career: Path) -> dict[str, dict]:
    facts = (career / "facts.md").read_text(encoding="utf-8")
    exp = expected_decisions((career / "tracker.md").read_text(encoding="utf-8"))
    return {t["case"]: grade(t, facts, exp.get(t["case"])) for t in traces}


# ---------- reports ----------


def _git(cwd: Path) -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=cwd, capture_output=True, text=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "."], cwd=cwd, capture_output=True, text=True
        ).stdout.strip()
        return sha + (" + uncommitted changes" if dirty else "")
    except OSError:
        return "?"


def totals(grades: dict[str, dict]) -> dict[str, dict]:
    t = {c: {"pass": 0, "fail": 0, "na": 0} for c in CHECKS}
    for g in grades.values():
        for c in CHECKS:
            ok = g.get(c, {}).get("ok")
            t[c]["na" if ok is None else "pass" if ok else "fail"] += 1
    return t


def scoreboard(
    label: str, kind: str, traces: list[dict], grades: dict, args, prev: dict | None
) -> tuple[str, dict]:
    tot = totals(grades)
    passed = sum(v["pass"] for v in tot.values())
    graded = sum(v["pass"] + v["fail"] for v in tot.values())
    cases_clean = sum(1 for g in grades.values() if all(v["ok"] is not False for v in g.values()))
    data = {
        "label": label,
        "kind": kind,
        "note": getattr(args, "note", None),
        "commit": _git(Path(__file__).parent),
        "model": f"{args.backend}/{args.model or 'default'}/{args.effort}",
        "score": round(passed / graded, 3) if graded else 0,
        "cases_clean": cases_clean,
        "cases": len(grades),
        "totals": tot,
        "grades": {c: {k: v["ok"] for k, v in g.items()} for c, g in grades.items()},
        "per_node": per_node([s for t in traces for s in t["spans"]]),
    }
    mark = {True: "✅", False: "❌", None: "·"}
    L = [f"# Scoreboard {label} ({kind})", ""]
    if data["note"]:
        L += [f"**Change:** {data['note']}", ""]
    L += [
        f"- Code: `{data['commit']}` · model `{data['model']}`",
        f"- **Score {data['score']:.0%}** ({passed}/{graded} checks)",
        f"- Clean cases (no failed check): {cases_clean}/{len(grades)}",
    ]
    if prev:
        L.append(
            f"- Previous `{prev['label']}`: {prev['score']:.0%}, clean {prev['cases_clean']}/{prev['cases']}"
        )
    L += ["", "## By check", "", "| check | pass | fail | n/a | previous fail |", "|---|---|---|---|---|"]
    for c in CHECKS:
        pf = prev["totals"][c]["fail"] if prev else "—"
        L.append(f"| {c} | {tot[c]['pass']} | {tot[c]['fail']} | {tot[c]['na']} | {pf} |")

    if prev:
        fixed, broke = [], []
        for case, g in data["grades"].items():
            before = prev["grades"].get(case, {})
            for c, ok in g.items():
                if before.get(c) is False and ok is True:
                    fixed.append(f"{case} · {c}")
                elif before.get(c) is True and ok is False:
                    broke.append(f"{case} · {c}")
        L += ["", "## Changed since previous", ""]
        L += [f"- ✅ fixed: {x}" for x in fixed] + [f"- ❌ broke: {x}" for x in broke]
        if not fixed and not broke:
            L.append("- no check changed")

    L += ["", "## By case", "", "| case | " + " | ".join(CHECKS) + " |", "|---" * (len(CHECKS) + 1) + "|"]
    for case, g in grades.items():
        L.append(f"| {case} | " + " | ".join(mark[g[c]["ok"]] for c in CHECKS) + " |")

    L += [
        "",
        "## Per node: tokens and time",
        "",
        "| node | runs | model calls | avg in tok | avg out tok | avg s | p95 s | cost $ |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in data["per_node"]:
        L.append(
            f"| {r['node']} | {r['runs']} | {r['calls']} | {r['avg_in']:,} | {r['avg_out']:,} | "
            f"{r['avg_ms'] / 1000:.1f} | {r['p95_ms'] / 1000:.1f} | {r['cost_usd']:.2f} |"
        )

    L += ["", "## Failures", ""]
    for case, g in grades.items():
        for c in CHECKS:
            if g[c]["ok"] is False:
                L.append(f"- **{case}** · {c}: {g[c]['why']}")
    return "\n".join(L) + "\n", data


def write_report(root: Path, label: str, kind: str, md: str, data: dict) -> Path:
    d = root / "scores"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{label}-{kind}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    p = d / f"{label}-{kind}.md"
    p.write_text(md, encoding="utf-8")
    return p


def latest(root: Path, kind: str) -> dict | None:
    files = sorted((root / "scores").glob(f"*-{kind}.json"))
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else None


# ---------- commands ----------


def cmd_collect(args) -> None:
    jobs = sorted(args.career.glob("20*/03-Job-Description.md"), reverse=True)
    jobs = jobs[args.offset : args.offset + args.limit]
    cases = [(j.parent.name, j) for j in jobs]
    label = datetime.now().strftime("%Y-%m-%dT%H%M")
    traces = run_batch(cases, args, label)
    md, data = scoreboard(label, "collect", traces, grade_all(traces, args.career), args, None)
    data["traces"] = f"traces/{label}"
    print(f"\n-> {write_report(args.career / '_graph-evals', label, 'collect', md, data)}")


def cmd_build(args) -> None:
    root = args.career / "_graph-evals"
    # every collect so far; a posting run in a later collect replaces its older trace
    by_case: dict[str, dict] = {}
    for rep in sorted((root / "scores").glob("*-collect.json")):
        label = json.loads(rep.read_text(encoding="utf-8"))["label"]
        for p in sorted((root / "traces" / label).glob("*.json")):
            by_case[p.stem] = json.loads(p.read_text(encoding="utf-8")) | {"from": label}
    if not by_case:
        raise SystemExit("no collect run yet: run `apply-graph-eval collect` first")
    traces = list(by_case.values())
    grades = grade_all(traces, args.career)
    failing = {c: [k for k in CHECKS if g[k]["ok"] is False] for c, g in grades.items()}
    failing = {c: f for c, f in failing.items() if f}
    # round-robin over checks so the set covers every failure kind, not 30 copies of the commonest
    picked: list[str] = []
    while len(picked) < args.size and len(picked) < len(failing):
        for check in CHECKS:
            nxt = next((c for c, f in failing.items() if check in f and c not in picked), None)
            if nxt and len(picked) < args.size:
                picked.append(nxt)
    reg = [
        {
            "case": c,
            "job": by_case[c]["job"],
            "failed": failing[c],
            "why": {k: grades[c][k]["why"] for k in failing[c]},
            "from": by_case[c]["from"],
        }
        for c in picked
    ]
    (root / "regression.json").write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = {k: sum(k in f for f in failing.values()) for k in CHECKS}
    print(f"{len(failing)} of {len(traces)} runs failed something; by check: {counts}")
    print(f"regression set: {len(reg)} cases -> {root / 'regression.json'}")
    if len(reg) < args.size:
        print(f"only {len(reg)} failing runs exist; collect more postings to reach {args.size}")


def cmd_score(args) -> None:
    root = args.career / "_graph-evals"
    reg = json.loads((root / "regression.json").read_text(encoding="utf-8"))
    label = datetime.now().strftime("%Y-%m-%dT%H%M")
    traces = run_batch([(r["case"], Path(r["job"])) for r in reg], args, label)
    md, data = scoreboard(label, "score", traces, grade_all(traces, args.career), args, latest(root, "score"))
    p = write_report(root, label, "score", md, data)
    print(f"\n{data['score']:.0%} ({data['cases_clean']}/{data['cases']} clean) -> {p}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="apply-graph-eval")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("collect", "build", "score"):
        s = sub.add_parser(name)
        s.add_argument("--career", type=Path, default=DEFAULT_CAREER)
        s.add_argument("--backend", choices=["api", "claude-code"], default="claude-code")
        s.add_argument("--model", default=None, help="default: the backend's own (opus)")
        s.add_argument("--effort", default="medium")
        s.add_argument("--workers", type=int, default=4)
    sub.choices["collect"].add_argument("--limit", type=int, default=80, help="newest N postings")
    sub.choices["collect"].add_argument("--offset", type=int, default=0, help="skip the newest N first")
    sub.choices["build"].add_argument("--size", type=int, default=30)
    sub.choices["score"].add_argument(
        "--note", default=None, help="what you changed, shown on the scoreboard"
    )
    a = p.parse_args(argv)
    {"collect": cmd_collect, "build": cmd_build, "score": cmd_score}[a.cmd](a)


if __name__ == "__main__":
    main()

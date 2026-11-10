#!/usr/bin/env python3
"""Offline evals over your own career/ workspace — no model calls, nothing leaves the machine.

    python scripts/career-eval.py blocks   career/     # block selection: labels from sent resumes, BM25 baseline
    python scripts/career-eval.py outcomes career/     # response rates from tracker.md, with confidence intervals

`blocks` treats every sent application folder as a labelled example: the resume bullets you
actually shipped are matched back to `blocks.md`, which gives "the blocks this JD needed". Two
numbers come out of that:

  assembly rate   share of shipped bullets that come from blocks.md. The workflow says resumes are
                  assembled, not rewritten; this measures whether that is true.
  Recall@k        a BM25 retriever (the same one jobs-mcp uses) gets the JD's requirements and must
                  find the labelled blocks in its top k. It is the baseline any smarter selection
                  (the agent, embeddings, a reranker) has to beat on the same labels.

`outcomes` reads tracker.md and reports interview rate by track, by seniority and by whether the
resume was tailored, with Wilson 95% intervals. With a few dozen applications the intervals are
wide; read them as "is there a signal yet", not as conclusions.

Stdlib only; reuses BM25 from mcp/jobs-mcp/jobs_mcp/rank.py.
"""

from __future__ import annotations

import argparse
import html
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp" / "jobs-mcp"))
from jobs_mcp.rank import bm25, tokenize  # noqa: E402

MATCH_THRESHOLD = 0.6  # share of a shipped bullet's tokens found in one block
CLUSTER_JACCARD = 0.5  # two blocks this similar are variants of one bullet


# ------------------------------------------------------------------ blocks.md


def parse_blocks(text: str) -> list[dict]:
    """English list items under '## ' sections. Explicit ids (**NW-1**) win; otherwise <Section>-<n>.

    Each block also gets a `cluster`: blocks.md keeps several variants of the same bullet, so a label
    on one variant must count as a hit when the retriever returns another. Variants are blocks whose
    token sets overlap by CLUSTER_JACCARD or more; the cluster is named after the first one."""
    blocks: list[dict] = []
    section, n, cur = "top", 0, None
    used_sections: set[str] = set()

    def flush():
        nonlocal cur
        if cur:
            body = re.sub(r"\s+", " ", cur["text"]).strip()
            # Variant notes look like "说明（32 词）：`Built the …`" — the bullet is the quoted part.
            quoted = re.search(r"`([^`]{60,})`", body)
            note = re.match(r"\W*(Skills|Summary|Headline)\b", body)  # assembly notes, not bullets
            if quoted:
                body = quoted.group(1).strip()
            words = re.findall(r"[A-Za-z][A-Za-z+#.\-]*", body)
            ascii_share = sum(c.isascii() for c in body) / max(1, len(body))
            if len(words) >= 12 and ascii_share > 0.85 and not note:
                cur["text"] = body
                blocks.append(cur)
        cur = None

    for line in text.splitlines():
        if line.startswith("## ") or line.startswith("### "):
            flush()
            if line.startswith("## "):
                head = line[3:].strip()
                base = re.split(r"[|(（—]", head)[0].strip().split()[0] if head else "section"
                section, i = base, 2
                while section in used_sections:  # two "## 2026-09-16 …" headings must not share ids
                    section, i = f"{base}#{i}", i + 1
                used_sections.add(section)
                n = 0
            continue
        m = re.match(r"^- (.*)", line)
        if m:
            flush()
            n += 1
            body = m.group(1)
            idm = re.match(r"\*\*([A-Z]{1,5}-\d+)\*\*\s*(.*)", body)
            bid = idm.group(1) if idm else f"{section}-{n}"
            cur = {"id": bid, "section": section, "text": idm.group(2) if idm else body}
        elif cur and (line.startswith("  ") or line.startswith("\t")) and line.strip():
            cur["text"] += " " + line.strip()
        elif not line.strip():
            flush()
    flush()
    seen, out = set(), []
    for b in blocks:
        key = " ".join(tokenize(b["text"]))
        if key not in seen:  # exact repeats add nothing
            seen.add(key)
            out.append(b)
    heads: list[dict] = []
    for b in out:
        b["tokens"] = set(tokenize(b["text"]))
        for h in heads:
            if len(b["tokens"] & h["tokens"]) / max(1, len(b["tokens"] | h["tokens"])) >= CLUSTER_JACCARD:
                b["cluster"] = h["id"]
                break
        else:
            b["cluster"] = b["id"]
            heads.append(b)
    return out


# ---------------------------------------------------------- application folders


def resume_bullets(html_text: str) -> list[str]:
    items = re.findall(r"<li\b[^>]*>(.*?)</li>", html_text, flags=re.S | re.I)
    out = []
    for it in items:
        t = html.unescape(re.sub(r"<[^>]+>", " ", it))
        t = re.sub(r"\s+", " ", t).strip()
        if len(t.split()) >= 8:
            out.append(t)
    return out


def jd_query(md: str) -> str:
    """Requirements only — never the evidence column, which would leak the labels.

    Prefers a '## Raw posting' section; else the first column of a requirement table; else the
    first section after the title."""
    title = next((ln[2:] for ln in md.splitlines() if ln.startswith("# ")), "")
    raw = re.search(r"^## Raw posting\s*\n(.*?)(?=^## |\Z)", md, flags=re.M | re.S)
    if raw:
        return f"{title}\n{raw.group(1)}"
    reqs: list[str] = []
    in_table = False
    for ln in md.splitlines():
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if not in_table:
                in_table = bool(re.search(r"requirement|要求|JD", cells[0], re.I))
                continue
            if cells and not set(cells[0]) <= set("-: "):
                reqs.append(cells[0])
        else:
            in_table = False
    if reqs:
        return title + "\n" + "\n".join(reqs)
    first = re.search(r"^## .*?\n(.*?)(?=^## |\Z)", md, flags=re.M | re.S)
    return title + "\n" + (first.group(1) if first else "")


def best_block(bullet: str, blocks: list[dict]) -> tuple[str | None, float]:
    bt = set(tokenize(bullet))
    if not bt:
        return None, 0.0
    best, score = None, 0.0
    for b in blocks:
        s = len(bt & b["tokens"]) / len(bt)
        if s > score:
            best, score = b["cluster"], s
    return best, score


def english_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    return sum(c.isascii() for c in letters) / max(1, len(letters))


def eval_blocks(career: Path, ks: tuple[int, ...] = (10, 20)) -> dict:
    """Labels and retrieval both live in cluster space (one id per bullet, whatever the variant)."""
    blocks = parse_blocks((career / "blocks.md").read_text(encoding="utf-8"))
    texts = [b["text"] for b in blocks]
    rows = []
    for folder in sorted(p for p in career.iterdir() if p.is_dir()):
        res, jd = folder / "01-Resume.html", folder / "03-Job-Description.md"
        if not (res.exists() and jd.exists()) or folder.name == "application":
            continue
        bullets = resume_bullets(res.read_text(encoding="utf-8"))
        if not bullets:
            continue
        matched = [best_block(x, blocks) for x in bullets]
        labels = {bid for bid, s in matched if bid and s >= MATCH_THRESHOLD}
        assembled = sum(1 for _, s in matched if s >= MATCH_THRESHOLD)
        row = {
            "folder": folder.name,
            "bullets": len(bullets),
            "assembled": assembled,
            "labels": sorted(labels),
        }
        query = jd_query(jd.read_text(encoding="utf-8"))
        row["query_english"] = english_share(query)
        if labels:
            scores = bm25(query, texts)
            order: list[str] = []
            for i in sorted(range(len(blocks)), key=lambda i: -scores[i]):
                if blocks[i]["cluster"] not in order:
                    order.append(blocks[i]["cluster"])
            for k in ks:
                row[f"recall@{k}"] = len(labels & set(order[:k])) / len(labels)
            row["r_precision"] = len(labels & set(order[: len(labels)])) / len(labels)
        rows.append(row)
    labelled = [r for r in rows if r["labels"]]
    summary = {
        "blocks": len(blocks),
        "clusters": len({b["cluster"] for b in blocks}),
        "folders": len(rows),
        "assembly_rate": sum(r["assembled"] for r in rows) / max(1, sum(r["bullets"] for r in rows)),
    }
    for key in [f"recall@{k}" for k in ks] + ["r_precision"]:
        summary[key] = sum(r[key] for r in labelled) / len(labelled) if labelled else None
    return {"summary": summary, "rows": rows}


# ------------------------------------------------------------------- tracker.md

POSITIVE = {"SCREEN", "OA", "TECH", "ONSITE", "OFFER"}
NEGATIVE = {"REJECTED", "GHOSTED"}
EXCLUDED = {"DRAFT", "EXPIRED", "SUPERSEDED", "WITHDRAWN", "BLOCKED", "ARCHIVED", "SENT", "PASS"}


def business_days(start: date, end: date) -> int:
    d, n = start, 0
    while d < end:
        d += timedelta(days=1)
        n += d.weekday() < 5
    return n


def parse_tracker(text: str) -> list[dict]:
    apps: list[dict] = []
    header: list[str] | None = None
    for ln in text.splitlines():
        if not ln.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        row = dict(zip(header, cells, strict=False))  # ragged rows happen in hand-edited tables
        applied = row.get("applied") or row.get("batch date") or ""
        if "contact person" in row or "role" not in row or not applied:
            continue  # outreach log, not applications
        status = row.get("archived status") or row.get("status") or ""
        history = {s.split("/")[0].strip().upper() for s in (row.get("original status", ""), status)}
        apps.append(
            {
                "company": row.get("company", ""),
                "role": row.get("role", ""),
                "req": row.get("req", ""),
                "notes": " ".join(row.get(k, "") for k in ("next step", "note", "notes")),
                "applied": applied.lstrip("~"),
                "status": status.split("/")[0].strip().upper(),
                # an archived row that once reached SCREEN still counts as an interview
                "reached_interview": bool(history & POSITIVE),
                # None when the table has no Folder column (archived batches kept their files elsewhere)
                "tailored": None if "folder" not in row else row["folder"] not in {"—", "-", ""},
            }
        )
    return apps


def track(role: str) -> str:
    r = role.lower()
    if re.search(r"\b(game|gameplay|technical design|animation|unity|unreal|slot)", r):
        return "games"
    if re.search(r"\b(ai|ml|llm|agent|agentic|agents|machine learning)\b", r):
        return "ai"
    return "backend/full-stack"


def seniority(role: str) -> str:
    return "senior+" if re.search(r"\b(senior|sr\.?|staff|principal|lead)\b", role, re.I) else "mid/junior"


SOURCES = [  # first match wins; read from the Req and Next step cells
    ("referral", r"\breferr(?:al|ed)\b"),
    # "STRATIS (via Vladimir, Head of Eng)", "startup (CEO Russell)": a person, not a job board
    ("direct contact", r"\bvia (?!indeed|linkedin|greenhouse|ashby|lever|workday|workable)\w+|\b(?:ceo|cto|founder)\b"),
    ("linkedin easy apply", r"easy apply"),
    ("workday", r"\bworkday\b|myworkdayjobs"),
    ("greenhouse", r"\bgreenhouse\b"),
    ("lever", r"\blever\b"),
    ("ashby", r"\bashby\b"),
    ("indeed", r"\bindeed\b"),
    ("workable", r"\bworkable\b"),
    ("company site / other ATS", r"\b(?:icims|smartrecruiters|taleo|successfactors|oracle|ukg|eightfold|"
     r"clearcompany|bamboohr|jobvite|paradox|careers? (?:page|site))\b"),
]
# "Stretch: 5+ yrs asked vs 4", "JD wants 2+ yrs", "posting asks 7+ yrs": the tracker's own words
STRETCH = re.compile(
    r"\bstretch\b|\b(?:asks?|asked|wants|requires?)\s+\d+\+?\s*(?:yrs|years)\b|\d+\+?\s*(?:yrs|years) asked",
    re.I,
)


def source(app: dict) -> str:
    text = f"{app.get('company', '')} {app.get('req', '')} {app.get('notes', '')}".lower()
    return next((name for name, rx in SOURCES if re.search(rx, text)), "unknown")


def stretch(app: dict) -> str:
    return "stretch (years / level)" if STRETCH.search(app.get("notes", "")) else "within range"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def eval_outcomes(career: Path, today: date | None = None, wait_days: int = 10) -> dict:
    today = today or date.today()
    apps = parse_tracker((career / "tracker.md").read_text(encoding="utf-8"))
    decided, pending, excluded = [], 0, 0
    for a in apps:
        s = a["status"]
        if a["reached_interview"]:
            decided.append({**a, "interview": True})
            continue
        if s in EXCLUDED or not s:
            excluded += 1
            continue
        if s in POSITIVE or s in NEGATIVE:
            decided.append({**a, "interview": s in POSITIVE})
            continue
        if s == "APPLIED":
            try:
                applied = date.fromisoformat(a["applied"][:10])
            except ValueError:
                excluded += 1
                continue
            if business_days(applied, today) >= wait_days:
                decided.append({**a, "interview": False})  # past the follow-up window, no reply
            else:
                pending += 1
            continue
        excluded += 1

    def group(key):
        out = {}
        for d in decided:
            g = key(d)
            k, n = out.get(g, (0, 0))
            out[g] = (k + d["interview"], n + 1)
        return {
            g: {"interviews": k, "n": n, "rate": k / n, "ci95": wilson(k, n)} for g, (k, n) in out.items()
        }

    k = sum(d["interview"] for d in decided)
    return {
        "decided": len(decided),
        "pending": pending,
        "excluded": excluded,
        "overall": {
            "interviews": k,
            "n": len(decided),
            "rate": k / max(1, len(decided)),
            "ci95": wilson(k, len(decided)),
        },
        "by_track": group(lambda d: track(d["role"])),
        "by_seniority": group(lambda d: seniority(d["role"])),
        "by_tailored": group(
            lambda d: {True: "folder in career/", False: "no folder", None: "unknown (archived)"}[
                d["tailored"]
            ]
        ),
        "by_source": group(source),
        "by_stretch": group(stretch),
        "interviews": [{"company": d["company"], "role": d["role"]} for d in decided if d["interview"]],
    }


GROUPS = (
    ("Track", "by_track"),
    ("Seniority", "by_seniority"),
    ("Tailoring", "by_tailored"),
    ("Source", "by_source"),
    ("Stretch", "by_stretch"),
)


def signals(r: dict, min_n: int = 5, min_gap: float = 0.10) -> list[dict]:
    """Groups whose interview rate differs from the rest of the decided applications.

    `strong` when the two Wilson intervals do not overlap; `weak` when the gap is at least
    `min_gap` with n >= `min_n` on both sides. Everything else is noise at this sample size."""
    total_k, total_n = r["overall"]["interviews"], r["overall"]["n"]
    out = []
    for title, key in GROUPS:
        for g, v in r[key].items():
            k, n = v["interviews"], v["n"]
            rest_k, rest_n = total_k - k, total_n - n
            if n < min_n or rest_n < min_n:
                continue
            rate, rest = k / n, rest_k / rest_n
            lo, hi = wilson(k, n)
            rlo, rhi = wilson(rest_k, rest_n)
            if hi < rlo or lo > rhi:
                strength = "strong"
            elif abs(rate - rest) >= min_gap:
                strength = "weak"
            else:
                continue
            out.append(
                {
                    "dimension": title,
                    "group": g,
                    "interviews": k,
                    "n": n,
                    "rate": rate,
                    "rest_rate": rest,
                    "strength": strength,
                }
            )
    return sorted(out, key=lambda s: (s["strength"] != "strong", -abs(s["rate"] - s["rest_rate"])))


# ------------------------------------------------------------------- reports


def pct(x: float | None) -> str:
    return "—" if x is None else f"{100 * x:.0f}%"


def report_blocks(r: dict) -> str:
    s = r["summary"]
    lines = [
        "## Block selection",
        "",
        f"{s['blocks']} blocks ({s['clusters']} after merging variants) · {s['folders']} sent folders · "
        f"assembly rate **{pct(s['assembly_rate'])}** · BM25 R-precision **{pct(s['r_precision'])}** · "
        f"Recall@10 **{pct(s['recall@10'])}** · Recall@20 **{pct(s['recall@20'])}**",
        "",
        "| Folder | Bullets | From blocks | Labels | Query in English | R-prec | R@10 | R@20 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in r["rows"]:
        lines.append(
            f"| {row['folder']} | {row['bullets']} | {row['assembled']} | {len(row['labels'])} | "
            f"{pct(row['query_english'])} | {pct(row.get('r_precision'))} | "
            f"{pct(row.get('recall@10'))} | {pct(row.get('recall@20'))} |"
        )
    lines += [
        "",
        "R-precision = hits in the top |labels| (a perfect selector scores 100%). A low score with a "
        "mostly non-English query is a vocabulary mismatch, not a retrieval verdict: archive the raw "
        "posting under `## Raw posting` in 03-Job-Description.md.",
    ]
    return "\n".join(lines)


def report_outcomes(r: dict) -> str:
    o = r["overall"]
    lines = [
        "## Outcomes",
        "",
        f"{r['decided']} decided (interview, rejection, ghosted, or past the follow-up window) · "
        f"{r['pending']} still inside the window · {r['excluded']} excluded (draft, expired, withdrawn …)",
        "",
        f"Overall interview rate **{pct(o['rate'])}** ({o['interviews']}/{o['n']}, 95% CI {pct(o['ci95'][0])}–{pct(o['ci95'][1])})",
    ]
    for title, key in GROUPS:
        lines += ["", f"| {title} | Interviews / n | Rate | 95% CI |", "|---|---|---|---|"]
        for g, v in sorted(r[key].items(), key=lambda kv: -kv[1]["n"]):
            lines.append(
                f"| {g} | {v['interviews']}/{v['n']} | {pct(v['rate'])} | {pct(v['ci95'][0])}–{pct(v['ci95'][1])} |"
            )
    return "\n".join(lines)


def report_calibration(r: dict, today: date) -> str:
    """career/calibration.md: what /job-match may cite from your own history, and how strongly."""
    o = r["overall"]
    sig = signals(r)
    lines = [
        "# Calibration from past applications",
        "",
        f"Generated {today.isoformat()} by `scripts/career-eval.py calibrate` from `tracker.md`. "
        "Regenerate after outcomes change; do not edit by hand.",
        "",
        f"Baseline: **{pct(o['rate'])}** interview rate ({o['interviews']}/{o['n']} decided, "
        f"95% CI {pct(o['ci95'][0])}–{pct(o['ci95'][1])}); {r['pending']} still inside the follow-up window.",
        "",
        "## Signals",
        "",
        "`strong` = the group's 95% interval does not overlap the rest's. `weak` = a gap of 10+ points "
        "with 5+ applications on each side — a hint, not a rule. Only these may be cited.",
        "",
    ]
    if sig:
        lines += ["| Strength | Dimension | Group | Interviews / n | Rate | Rest |", "|---|---|---|---|---|---|"]
        for s in sig:
            lines.append(
                f"| {s['strength']} | {s['dimension']} | {s['group']} | {s['interviews']}/{s['n']} | "
                f"{pct(s['rate'])} | {pct(s['rest_rate'])} |"
            )
    else:
        lines.append("None yet: no group differs from the rest beyond noise at this sample size.")
    lines += ["", "## Reached an interview", ""]
    lines += [f"- {i['company']} — {i['role']}" for i in r["interviews"]] or ["- none yet"]
    lines += ["", "## Detail", "", report_outcomes(r).split("\n", 2)[2]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("what", choices=["blocks", "outcomes", "calibrate", "all"])
    ap.add_argument("career", type=Path, help="path to your career/ workspace")
    ap.add_argument("--out", type=Path, help="calibrate: where to write (default <career>/calibration.md)")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.what == "calibrate":
        today = date.today()
        out = a.out or a.career / "calibration.md"
        out.write_text(report_calibration(eval_outcomes(a.career, today=today), today), encoding="utf-8")
        print(f"career-eval: wrote {out}")
        return 0
    parts = []
    if a.what in ("blocks", "all"):
        parts.append(report_blocks(eval_blocks(a.career)))
    if a.what in ("outcomes", "all"):
        parts.append(report_outcomes(eval_outcomes(a.career)))
    print("\n\n".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())

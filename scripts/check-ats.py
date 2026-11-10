#!/usr/bin/env python3
"""ATS gate: read the exported resume PDF the way a parser does, from its text layer.

    python scripts/check-ats.py career/2026-11-09-Acme-Backend/            # newest resume PDF in the folder
    python scripts/check-ats.py career/<folder>/ --pdf other.pdf --json

An ATS never sees the rendered page, only the PDF's embedded text. A layout that looks right can
extract as garbage: icon glyphs where the email should be, a sidebar spliced into the middle of a
bullet, the name buried below the first job. This compares the text layer with the source
01-Resume.html and the posting:

  text layer    there is extractable text, without replacement or (cid:NN) glyphs   FAIL
  contact       every email and phone number in the HTML is literal text in the PDF  FAIL
  bullets       each resume bullet comes out as one contiguous run of words          FAIL below --min-intact
  name          the name (the HTML's <h1>) is in the first lines of the text         WARN
  links         every href is also printed as text (an ATS drops hyperlinks)          WARN
  icons         private-use glyphs (icon fonts) in the text                          WARN
  keywords      tech terms from the posting: in the PDF / in facts.md but not the     INFO
                resume (supported — consider adding) / in neither (a gap — never add)

Extractor: pypdf when importable (pip install pypdf), else Poppler/Xpdf `pdftotext`. With neither,
the check is skipped (exit 3). Parsers differ; this is one honest reading, not every ATS.

Exit status: 0 pass, 1 fail, 2 usage error, 3 skipped (no extractor). Stdlib only otherwise.
"""

from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PUA = re.compile("[-]")
BAD_GLYPH = re.compile(r"�|\(cid:\d+\)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")

# Terms that look technical (caps, digits, dots) but are not skills.
NOT_KEYWORDS = {
    "US", "USA", "CA", "UK", "EU", "ON", "BC", "QC", "NY", "SF", "NYC", "GTA", "HQ", "CAD", "USD", "EUR",
    "EEO", "EEOC", "LGBTQ", "LGBTQ+", "PTO", "RRSP", "DEI", "FAQ", "OK", "TBD", "NA", "AND", "OR", "THE",
    "AODA", "ADA", "OTE", "VP", "CEO", "CTO", "CFO", "COO", "HR", "IT", "AM", "PM", "EST", "PST", "ET",
    "PT", "I", "II", "III", "IV", "SR", "JR", "FT", "WFH", "YOE", "BS", "MS", "BA", "MBA", "PHD", "PhD",
}
# Lower-case skill words that the shape test below would miss.
LOWER_SKILLS = {
    "python", "java", "golang", "rust", "kotlin", "swift", "scala", "ruby", "php", "typescript",
    "javascript", "kubernetes", "docker", "terraform", "kafka", "redis", "postgres", "postgresql",
    "mysql", "mongodb", "graphql", "react", "vue", "angular", "svelte", "django", "flask", "fastapi",
    "rails", "spring", "linux", "git", "airflow", "spark", "pytorch", "tensorflow", "unity", "unreal",
    "elasticsearch", "snowflake", "dbt", "grpc", "protobuf", "websockets", "webrtc", "nginx", "jenkins",
}


# ----------------------------------------------------------------- extraction


def extract(pdf: Path) -> tuple[str | None, str]:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]

        return "\n".join(p.extract_text() or "" for p in PdfReader(str(pdf)).pages), "pypdf"
    except ImportError:
        pass
    exe = shutil.which("pdftotext")
    if exe:
        r = subprocess.run([exe, "-enc", "UTF-8", str(pdf), "-"], capture_output=True)
        if r.returncode == 0:
            return r.stdout.decode("utf-8", "replace"), "pdftotext"
    return None, "none"


# --------------------------------------------------------------------- source


def visible_html_text(src: str) -> str:
    s = re.sub(r"<(head|script|style)\b.*?</\1>", " ", src, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return htmllib.unescape(s)


def html_name(src: str) -> str | None:
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", src, flags=re.S | re.I)
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip() if m else None


def html_bullets(src: str) -> list[str]:
    out = []
    for it in re.findall(r"<li\b[^>]*>(.*?)</li>", src, flags=re.S | re.I):
        t = re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", it))).strip()
        if len(t.split()) >= 8:
            out.append(t)
    return out


def html_links(src: str) -> list[str]:
    return [
        h
        for h in re.findall(r"""<a\b[^>]*\bhref\s*=\s*["']([^"']+)["']""", src, flags=re.I)
        if h.startswith(("http://", "https://"))
    ]


# ------------------------------------------------------------------- matching


def words(s: str) -> list[str]:
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)  # words hyphenated across a line break
    return re.findall(r"[a-z0-9]+", s.lower())


def contiguous(needle: list[str], hay: str) -> bool:
    return " " + " ".join(needle) + " " in hay


def bare_url(u: str) -> str:
    u = re.sub(r"^https?://(www\.)?", "", u.strip().lower())
    return u.rstrip("/")


# ------------------------------------------------------------------- keywords


def jd_text(md: str) -> str:
    raw = re.search(r"^## Raw posting\s*\n(.*?)(?=^## |\Z)", md, flags=re.M | re.S)
    if raw:
        return raw.group(1)
    # Without the raw posting, read only the requirement column — the rest is the candidate's evidence.
    reqs = []
    for ln in md.splitlines():
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if cells and not set(cells[0]) <= set("-: ") and not re.match(r"requirement", cells[0], re.I):
                reqs.append(cells[0])
    # A short hand-written summary with neither: use it whole (less precise; archive the raw posting).
    return "\n".join(reqs) if reqs else md


TERM = re.compile(r"(?<![\w+#.])([A-Za-z][\w+#./-]*[\w+#]|[A-Za-z])(?![\w+#])")


WHOLE_PAIRS = {"CI/CD", "UI/UX", "A/B"}  # slash terms that are one skill; JS/TS, GCP/AWS are split
# All-caps English that shouts in postings ("DO NOT", "YOU WILL").
CAPS_WORDS = {"DO", "NOT", "YOU", "WE", "OUR", "ALL", "ANY", "NEW", "NO", "YES", "MUST", "IS", "ARE", "BE",
              "TO", "OF", "IN", "FOR", "WITH", "AT", "BY", "AN", "AS", "IF", "WILL", "CAN", "MAY", "OUT", "UP"}
NOT_TERMS = {
    "linkedin", "indeed", "greenhouse", "lever", "ashby", "workday", "workable", "glassdoor", "talentegg",
    "ziprecruiter", "monster", "jd",
}
URLISH = re.compile(
    r"\S*(?:https?://|www\.)\S*|\b[\w-]+\.(?:com|io|ai|dev|org|net|co|ca|us|uk|jobs|careers)\b(?:/\S*)?", re.I
)


def _base(t: str) -> str:
    """Plural-insensitive key: APIs -> api, CRDTs -> crdt, SDKs -> sdk."""
    low = t.lower()
    return low[:-1] if re.fullmatch(r"[A-Z]{2,6}s", t) else low


def _parts(t: str) -> list[str]:
    if t.upper() in WHOLE_PAIRS:
        return [t]
    return [x for x in t.split("/") if x]


def keywords(jd: str, exclude: set[str]) -> list[str]:
    found: dict[str, str] = {}
    for line in jd.splitlines():
        line = URLISH.sub(" ", line)
        for m in TERM.finditer(line):
            for t in _parts(m.group(1)):
                t = t.strip("./-")
                low = t.lower()
                employer = any(len(e) > 3 and e in low for e in exclude)  # FidelityCanadaStaffing
                noise = t in NOT_KEYWORDS or t in CAPS_WORDS or low in NOT_TERMS or low in exclude
                if len(t) < 2 or noise or employer:
                    continue
                techy = (
                    low in LOWER_SKILLS
                    or re.search(r"[a-z][A-Z]", t)  # PostgreSQL, TypeScript, GraphQL
                    or re.fullmatch(r"[A-Z]{2,6}s?", t)  # AWS, SQL, APIs
                    or re.search(r"\d|[+#]|\.\w", t)  # S3, C++, C#, Node.js, .NET
                    or t.upper() in WHOLE_PAIRS
                )
                if techy:
                    found.setdefault(_base(t), t)
    return list(found.values())


def has_term(term: str, text: str) -> bool:
    forms = {term}
    if re.fullmatch(r"[A-Z]{2,6}s", term):
        forms.add(term[:-1])
    elif re.fullmatch(r"[A-Z]{2,6}", term):
        forms.add(term + "s")
    return any(
        re.search(r"(?<![\w+#])" + re.escape(f) + r"(?![\w+#])", text, flags=re.I) is not None for f in forms
    )


# ---------------------------------------------------------------------- check


def check(pdf_text: str, src: str, jd: str | None, facts: str | None, company: str = "") -> dict:
    findings: list[dict] = []

    def add(level: str, kind: str, msg: str) -> None:
        findings.append({"level": level, "kind": kind, "message": msg})

    stripped = re.sub(r"\s+", "", pdf_text)
    if len(stripped) < 200:
        add("FAIL", "text layer", f"only {len(stripped)} characters extract — the PDF is effectively an image")
    bad = BAD_GLYPH.findall(pdf_text)
    if len(bad) > 3:
        add("FAIL", "text layer", f"{len(bad)} unmappable glyphs (\\ufffd / (cid:NN)) — a font lacks a ToUnicode map")
    icons = PUA.findall(pdf_text)
    if icons:
        add("WARN", "icons", f"{len(icons)} icon-font glyph(s) extract as private-use characters next to the text")

    visible = visible_html_text(src)
    flat_pdf = re.sub(r"\s+", "", pdf_text.lower())
    digits_pdf = re.sub(r"\D", "", pdf_text)
    for e in dict.fromkeys(EMAIL.findall(visible)):
        if e.lower() not in flat_pdf:
            add("FAIL", "contact", f"email {e} is not literal text in the PDF")
    for p in dict.fromkeys(PHONE.findall(visible)):
        d = re.sub(r"\D", "", p)
        if len(d) >= 10 and d not in digits_pdf:
            add("FAIL", "contact", f"phone {p.strip()} is not literal text in the PDF")
    for link in dict.fromkeys(html_links(src)):
        if bare_url(link) not in re.sub(r"\s+", "", pdf_text.lower()).replace("https://", "").replace("www.", ""):
            add("WARN", "links", f"{link} exists only as a hyperlink; print it as text")

    name = html_name(src)
    if name:
        head = " ".join(words(pdf_text)[:40])
        if " ".join(words(name)) not in head:
            first = " ".join(pdf_text.split())[:60]
            add("WARN", "name", f'"{name}" is not in the first lines of the text layer; it starts with "{first}"')

    bullets = html_bullets(src)
    hay = " " + " ".join(words(pdf_text)) + " "
    broken = [b for b in bullets if not contiguous(words(b), hay)]
    intact = 1 - len(broken) / len(bullets) if bullets else 1.0
    for b in broken:
        add("BROKEN", "bullets", b[:90] + ("…" if len(b) > 90 else ""))

    kw: dict[str, list[str]] = {"present": [], "supported": [], "gap": []}
    if jd:
        exclude = {w.lower() for w in re.findall(r"[A-Za-z]+", company)}
        joined = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", pdf_text)  # "Postgre-\nSQL" -> PostgreSQL
        for t in keywords(jd, exclude):
            if has_term(t, joined):
                kw["present"].append(t)
            elif facts and has_term(t, facts):
                kw["supported"].append(t)
            else:
                kw["gap"].append(t)
    total = sum(len(v) for v in kw.values())
    return {
        "chars": len(stripped),
        "bullets": len(bullets),
        "bullets_intact": intact,
        "findings": findings,
        "keywords": kw,
        "keyword_coverage": len(kw["present"]) / total if total else None,
    }


def newest_resume_pdf(folder: Path) -> Path | None:
    pdfs = [p for p in folder.glob("*.pdf") if "cover-letter" not in p.name.lower()]
    return max(pdfs, key=lambda p: p.stat().st_mtime) if pdfs else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder", type=Path, help="application folder (has 01-Resume.html and the exported PDF)")
    ap.add_argument("--pdf", type=Path, help="resume PDF (default: newest non-cover-letter PDF in the folder)")
    ap.add_argument("--facts", type=Path, help="facts.md (default: the folder's parent)")
    ap.add_argument("--min-intact", type=float, default=0.9, help="share of bullets that must extract intact")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    src_path = a.folder / "01-Resume.html"
    pdf = a.pdf or newest_resume_pdf(a.folder)
    if not src_path.exists() or not pdf or not pdf.exists():
        print(f"check-ats: need {src_path} and an exported resume PDF", file=sys.stderr)
        return 2
    text, extractor = extract(pdf)
    if text is None:
        print("check-ats: skipped — no PDF text extractor (pip install pypdf, or install poppler-utils)")
        return 3
    jd_path = a.folder / "03-Job-Description.md"
    facts_path = a.facts or a.folder.resolve().parent / "facts.md"
    company = (a.folder.name.split("-")[3:4] or [""])[0]  # YYYY-MM-DD-Company-Role
    r = check(
        text,
        src_path.read_text(encoding="utf-8"),
        jd_text(jd_path.read_text(encoding="utf-8")) if jd_path.exists() else None,
        facts_path.read_text(encoding="utf-8") if facts_path.exists() else None,
        company,
    )
    failed = any(f["level"] == "FAIL" for f in r["findings"]) or r["bullets_intact"] < a.min_intact
    r.update(pdf=str(pdf), extractor=extractor, passed=not failed)

    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 1 if failed else 0
    for f in r["findings"]:
        print(f"{f['level']:<7} {f['kind']:<10} {f['message']}")
    kw = r["keywords"]
    if r["keyword_coverage"] is not None:
        print(f"KEYWORDS  in resume ({len(kw['present'])}): {', '.join(kw['present']) or '—'}")
        print(f"KEYWORDS  in facts.md, not the resume — consider adding ({len(kw['supported'])}): "
              f"{', '.join(kw['supported']) or '—'}")
        print(f"KEYWORDS  in neither — a gap, never add ({len(kw['gap'])}): {', '.join(kw['gap']) or '—'}")
    cov = "—" if r["keyword_coverage"] is None else f"{100 * r['keyword_coverage']:.0f}%"
    print(
        f"check-ats: {'PASS' if not failed else 'FAIL'} · {extractor} · {r['chars']} chars · "
        f"bullets intact {r['bullets'] - sum(f['kind'] == 'bullets' for f in r['findings'])}/{r['bullets']} · "
        f"keyword coverage {cov}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

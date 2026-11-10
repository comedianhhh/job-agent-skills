"""Integrity gate for a job posting: clean it, scan it, say what was found.

A posting is third-party text that the agent reads next to the candidate's private files, so it
is the obvious place to hide instructions for that agent. This module is the deterministic part
of the defence — it does not depend on the model noticing anything:

  * hidden HTML (display:none, visibility:hidden, opacity:0, font-size:0, color:transparent,
    clip / clip-path, far off-screen positioning, a zero-size box with overflow:hidden, the
    `hidden` attribute, aria-hidden) is **removed** from the text; what it said is reported
    under `hidden_blocks`. Comments and script / style / noscript / template / svg blocks are
    removed too; comments are scanned for instructions.
  * invisible characters (zero-width, bidi controls, soft hyphen, BOM) are removed and counted;
    the ones that indicate tampering (a zero-width character inside a word, a bidi override or
    isolate) set `tampering`.
  * Unicode tag characters (U+E0000–U+E007F) and runs of variation selectors can spell text the
    user cannot see but a model can read. Both are removed, decoded, and listed under
    `invisible_text` (flag-emoji tag sequences are kept).
  * instruction-shaped lines aimed at an agent rather than a reader are **quoted, never
    removed** (a posting for an AI-agent role legitimately talks about agents).
  * URLs that appear only in hidden content, and words that mix Latin with Cyrillic or Greek
    look-alike letters, are listed.

    from jobs_mcp.guard import guard
    text, report = guard(raw_html_or_text)
    report["verdict"]   # "clean" or "flagged: 2 hidden block(s), 1 instruction-shaped line(s)"

Stdlib only.
"""

from __future__ import annotations

import html
import re
import unicodedata
from html.parser import HTMLParser
from typing import Any

MAX_EXCERPT = 200
MAX_ITEMS = 10

# ----------------------------------------------------------------- hidden HTML

_SKIP = {"script", "style", "noscript", "template", "svg", "head", "title", "iframe", "object"}
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
_BREAK_END = {"p", "li", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "ul", "ol", "section", "article"}
_HIDDEN_STYLE = [
    re.compile(r"display:none"),
    re.compile(r"visibility:(?:hidden|collapse)"),
    re.compile(r"opacity:0*(?:\.0+)?(?:;|$|!)"),
    re.compile(r"font-size:0*(?:\.0+)?(?:px|pt|em|rem|%|vw|vh)?(?:;|$|!)"),
    re.compile(r"(?<![-\w])color:transparent"),
    re.compile(r"clip:rect\(0(?:px)?,?0(?:px)?,?0(?:px)?,?0(?:px)?\)"),
    re.compile(r"clip-path:inset\((?:50|100)%"),
    re.compile(r"(?:left|top|right|text-indent|margin-left):-\d{3,}(?:px|em|rem)"),
    re.compile(r"transform:scale\(0\)"),
]
_ZERO_BOX = re.compile(r"(?:^|;)(?:height|width|max-height|max-width):0*(?:\.0+)?(?:px|em|rem|%)?(?:;|$|!)")


def _style_hides(style: str) -> bool:
    s = re.sub(r"/\*.*?\*/", "", style, flags=re.S)  # CSS comments break naive matching
    s = re.sub(r"\s+", "", s.lower())
    if any(rx.search(s) for rx in _HIDDEN_STYLE):
        return True
    return bool(_ZERO_BOX.search(s)) and "overflow:hidden" in s


def _attrs_hide(attrs: list[tuple[str, str | None]]) -> bool:
    for k, v in attrs:
        k = k.lower()
        if k == "hidden":
            return True
        if k == "aria-hidden" and (v or "").strip().lower() == "true":
            return True
        if k == "style" and v and _style_hides(v):
            return True
    return False


class _Splitter(HTMLParser):
    """Splits HTML into visible text and hidden blocks, keeping the old _strip_html line breaks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.visible: list[str] = []
        self.hidden: list[str] = []  # one entry per hidden subtree
        self.comments: list[str] = []
        self.hidden_urls: list[str] = []
        self._stack: list[tuple[str, bool, bool]] = []  # (tag, hides, skips)
        self._hidden_depth = 0
        self._skip_depth = 0
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            (self._buf if self._hidden_depth else self.visible).append("\n")
            return
        if self._hidden_depth and tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hidden_urls.append(href)
        if tag in _VOID:
            return
        hides = _attrs_hide(attrs)
        skips = tag in _SKIP
        self._stack.append((tag, hides, skips))
        if hides:
            self._hidden_depth += 1
        if skips:
            self._skip_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if not any(t == tag for t, _, _ in self._stack):
            return  # stray end tag
        while self._stack:
            t, hides, skips = self._stack.pop()
            if skips:
                self._skip_depth -= 1
            if hides:
                self._hidden_depth -= 1
                if not self._hidden_depth:
                    block = re.sub(r"\s+", " ", "".join(self._buf)).strip()
                    if block:
                        self.hidden.append(block)
                    self._buf = []
            if t == tag:
                break
        if tag in _BREAK_END and not self._skip_depth:
            (self._buf if self._hidden_depth else self.visible).append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        (self._buf if self._hidden_depth else self.visible).append(data)

    def handle_comment(self, data: str) -> None:
        if data.strip():
            self.comments.append(data.strip())

    def close(self) -> None:
        super().close()
        if self._buf:  # unclosed hidden element at end of input
            block = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if block:
                self.hidden.append(block)


def _tidy(s: str) -> str:
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


# -------------------------------------------------------- invisible characters

_ZERO_WIDTH = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD, 0x180E}
_BIDI_MARKS = {0x200E, 0x200F, 0x061C}
_BIDI_CONTROLS = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A))  # overrides, embeds, isolates
_TAGS = range(0xE0000, 0xE0080)
_FLAG = re.compile("\U0001f3f4[\U000e0061-\U000e007a]{2,7}\U000e007f")  # 🏴 + tag letters + cancel tag


def _is_vs(c: str) -> bool:
    o = ord(c)
    return 0xFE00 <= o <= 0xFE0F or 0xE0100 <= o <= 0xE01EF


def _vs_byte(c: str) -> int:
    o = ord(c)
    return o - 0xFE00 if o <= 0xFE0F else o - 0xE0100 + 16


def _strip_invisible(text: str, report: dict[str, Any]) -> str:
    counts: dict[str, int] = {}
    flags = _FLAG.findall(text)
    text = _FLAG.sub("\x00FLAG\x00", text)

    # Text spelled in tag characters: each one is an ASCII letter shifted to U+E00xx.
    for run in re.findall("[\U000e0000-\U000e007f]+", text):
        decoded = "".join(chr(ord(c) - 0xE0000) for c in run if 0x20 <= ord(c) - 0xE0000 < 0x7F)
        if decoded.strip():
            report["invisible_text"].append(decoded.strip()[:MAX_EXCERPT])
    # Text smuggled as variation selectors, one byte each (an emoji uses at most one in a row).
    for run in re.findall("[︀-️\U000e0100-\U000e01ef]{4,}", text):
        decoded = bytes(_vs_byte(c) for c in run).decode("utf-8", "replace")
        if decoded.strip():
            report["invisible_text"].append(decoded.strip()[:MAX_EXCERPT])
            text = text.replace(run, "")
            counts["variation_selector"] = counts.get("variation_selector", 0) + len(run)

    out: list[str] = []
    for i, c in enumerate(text):
        o = ord(c)
        kind = None
        if o in _TAGS:
            kind = "tag"
            report["tampering"] = True
        elif o in _BIDI_CONTROLS:
            kind = "bidi_control"
            report["tampering"] = True
        elif o in _BIDI_MARKS:
            kind = "bidi_mark"
        elif o in _ZERO_WIDTH:
            prev = text[i - 1] if i else ""
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if (
                o == 0x200D
                and prev
                and nxt
                and not prev.isalnum()
                and not nxt.isalnum()
                and ord(prev) > 0x2000
            ):
                out.append(c)  # zero-width joiner inside an emoji sequence
                continue
            kind = "zero_width"
            if prev.isalnum() and nxt.isalnum() and o != 0x00AD:  # soft hyphens inside words are normal
                report["tampering"] = True
        if kind:
            counts[kind] = counts.get(kind, 0) + 1
            continue
        out.append(c)
    text = "".join(out)
    for f in flags:
        text = text.replace("\x00FLAG\x00", f, 1)
    report["invisible"] = counts
    return text


# ------------------------------------------------------- instruction-shaped lines

_AGENT = (
    r"(?:AI|A\.I\.|LLMs?|GPT|ChatGPT|Claude|Gemini|Copilot|(?:large )?language models?|"
    r"chat ?bots?|bots?|assistants?|agents?)"
)
# "If you are an AI engineer" is a job ad, not an instruction: skip agent words followed by a role noun.
_NOT_ROLE = (
    r"(?![\s/&-]*(?:[\w.+]+[\s/&-]+){0,2}(?:engineers?|developers?|researchers?|scientists?|enthusiasts?|"
    r"practitioners?|experts?|specialists?|teams?|platforms?|products?|compan(?:y|ies)|startups?|leaders?|"
    r"builders?|native|first|powered|driven|infrastructure|systems?|tools?|features?|"
    # "You are AI-fluent / AI-savvy": a trait the job asks for (DoorDash, live 2026-11)
    r"fluent|savvy|literate|curious|enabled|forward|ready|minded|aware)\b)"
)
_INSTRUCTION = [
    re.compile(
        r"\b(?:ignore|disregard|forget|override|bypass)\b.{0,40}\b(?:instructions?|prompts?|rules|guidelines|"
        r"directions|everything (?:above|before)|previous|prior)\b",
        re.I,
    ),
    re.compile(r"\b(?:if|when) you(?:'re| are) (?:an? |the )?" + _AGENT + r"\b" + _NOT_ROLE, re.I),
    re.compile(r"\byou are (?:an? |the )?" + _AGENT + r"\b" + _NOT_ROLE, re.I),
    re.compile(
        r"\b(?:note|message|instructions?|hey|dear)\s*(?:to|for|,|:)\s*(?:the |all |any )?"
        + _AGENT
        + r"\b"
        + _NOT_ROLE,
        re.I,
    ),
    re.compile(
        _AGENT + r"\s+(?:reading|processing|screening|parsing|reviewing|summari[sz]ing) (?:this|the) "
        r"(?:posting|job|description|application|resume|cv|text|page|listing)\b",
        re.I,
    ),
    # Security roles list "jailbreak testing" and "system prompts" as work (Coinbase, live 2026-11):
    # flag only the request, not the topic.
    re.compile(
        r"\b(?:reveal|print|show|repeat|output|ignore|disregard)\b.{0,25}\bsystem prompt\b|"
        r"\b(?:here are|follow) (?:your |the |these )?new instructions\b|\b(?:enter|enable) developer mode\b",
        re.I,
    ),
    re.compile(
        r"\b(?:include|insert|add|use|mention) the (?:word|phrase|keyword|code ?word|string)s?\b", re.I
    ),
    re.compile(
        r"\b(?:respond|reply|answer|output)\s+(?:only\s+)?"
        r"(?:with\s+(?:only|exactly|the (?:word|phrase|following)|"
        r"[\"'“‘])|in the (?:following )?format)",
        re.I,
    ),
    re.compile(
        r"\b(?:rate|score|rank|mark|recommend) (?:this|the) "
        r"(?:candidate|applicant|application|role|job|posting)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:reveal|share|send|output|print|email|forward|post|upload)\b.{0,40}"
        r"\b(?:passwords?|api keys?|tokens?|"
        r"credentials|facts\.md|answers\.yaml|career/|ssn|social insurance)\b",
        re.I,
    ),
    re.compile(r"<\s*/?\s*(?:system|instructions?|im_start|im_end)\s*>|\[\s*/?\s*(?:system|INST)\s*\]", re.I),
]


def _instruction_lines(text: str) -> list[str]:
    hits = []
    for line in re.split(r"\n|(?<=[.!?])\s+", text):
        s = line.strip()
        if s and any(rx.search(s) for rx in _INSTRUCTION):
            hits.append(s[:MAX_EXCERPT])
    return list(dict.fromkeys(hits))[:MAX_ITEMS]


# ------------------------------------------------------------ look-alike spoofing


def _script(c: str) -> str | None:
    if not c.isalpha():
        return None
    name = unicodedata.name(c, "")
    for s in ("LATIN", "CYRILLIC", "GREEK"):
        if name.startswith(s):
            return s
    return "OTHER"


def _mixed_script_words(text: str) -> list[str]:
    out = []
    for w in re.findall(r"\w{2,}", text):
        scripts = {_script(c) for c in w} - {None, "OTHER"}
        if "LATIN" in scripts and scripts & {"CYRILLIC", "GREEK"}:
            out.append(w)
    return list(dict.fromkeys(out))[:MAX_ITEMS]


# --------------------------------------------------------------------- guard

_URL = re.compile(r"https?://[^\s\"'<>)]+", re.I)
_LOOKS_HTML = re.compile(r"<(?:p|div|span|br|li|ul|ol|h\d|a|strong|em|b|i|section|table)\b[^>]*>", re.I)


def guard(raw: str | None, is_html: bool | None = None) -> tuple[str, dict[str, Any]]:
    """(cleaned text, report). `is_html=None` detects HTML by its tags."""
    report: dict[str, Any] = {
        "verdict": "clean",
        "hidden_blocks": [],
        "hidden_urls": [],
        "invisible": {},
        "invisible_text": [],
        "tampering": False,
        "instruction_lines": [],
        "mixed_script": [],
    }
    if not raw:
        return "", report
    text = raw
    if is_html is None:
        is_html = bool(_LOOKS_HTML.search(text)) or (
            "&lt;" in text and bool(_LOOKS_HTML.search(html.unescape(text)))
        )
    comments: list[str] = []
    if is_html:
        if "<" not in text or "&lt;" in text:  # Greenhouse sends escaped HTML
            text = html.unescape(text)
        p = _Splitter()
        p.feed(text)
        p.close()
        visible = "".join(p.visible)
        report["hidden_blocks"] = [b[:MAX_EXCERPT] for b in p.hidden][:MAX_ITEMS]
        hidden_text = " ".join(p.hidden)
        urls = set(p.hidden_urls) | set(_URL.findall(hidden_text))
        report["hidden_urls"] = sorted(u for u in urls if u not in visible)[:MAX_ITEMS]
        comments = p.comments
        text = visible
    else:
        hidden_text = ""
    text = _strip_invisible(text, report)
    text = _tidy(text)

    scanned = "\n".join([text, hidden_text, *comments, *report["invisible_text"]])
    report["instruction_lines"] = _instruction_lines(scanned)
    report["mixed_script"] = _mixed_script_words(text)
    report["verdict"] = verdict(report)
    return text, report


def verdict(report: dict[str, Any]) -> str:
    parts = []
    if report["hidden_blocks"]:
        parts.append(f"{len(report['hidden_blocks'])} hidden block(s)")
    if report["invisible_text"]:
        parts.append(f"{len(report['invisible_text'])} invisible text run(s)")
    if report["tampering"]:
        parts.append("invisible-character tampering")
    if report["instruction_lines"]:
        parts.append(f"{len(report['instruction_lines'])} instruction-shaped line(s)")
    if report["hidden_urls"]:
        parts.append(f"{len(report['hidden_urls'])} hidden-only URL(s)")
    if report["mixed_script"]:
        parts.append(f"{len(report['mixed_script'])} look-alike word(s)")
    return "flagged: " + ", ".join(parts) if parts else "clean"


def compact(report: dict[str, Any]) -> dict[str, Any]:
    """The report without empty fields — what the MCP tools attach to a posting."""
    return {k: v for k, v in report.items() if v or k == "verdict"}

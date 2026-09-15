"""Static checks for the eval suite — runs in CI without credentials, before `claude plugin eval` costs anything.

    python evals/validate.py

Checks every case under evals/: frontmatter keys, grader types and options, regexes compile,
`tool_used: Skill` graders name a real skill, fixtures are in sync, and nothing under the plugin is a
hard link (the harness refuses those).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGIN = ROOT.parent
SKILLS = {p.parent.name for p in (PLUGIN / "skills").glob("*/SKILL.md")}

PROMPT_KEYS = {
    "schema_version", "name", "description", "tags", "plugins", "runs", "expected_outcome", "model",
    "max_turns", "timeout_seconds", "allowed_tools", "append_system_prompt", "env",
}
GRADER_TYPES = {
    "regex": {"pattern", "flags", "match", "target"},
    "tool_used": {"tool", "input_match", "min", "max"},
    "tool_order": {"before", "after"},
    "file_exists": {"path", "exists"},
    "llm": {"criteria", "focus"},
    "baseline": {"baseline_file", "criteria"},
}
COMMON_GRADER_KEYS = {"type", "weight", "arm"}
READ_ONLY_TOOLS = {"Read", "Glob", "Grep", "NotebookRead", "Skill", "Agent", "TodoWrite"}
GATED_TOOLS = {"Write", "Edit", "Bash", "WebFetch", "WebSearch"}


def frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    end = text.index("\n---", 3)
    fm: dict[str, str] = {}
    for line in text[3:end].strip().splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip("'\"")
    return fm, text[end + 4 :].strip()


def js_regex_ok(pattern: str) -> str | None:
    if "(?i)" in pattern:
        return "inline (?i) is not supported; use flags: i"
    try:
        re.compile(pattern)  # Python's engine is a close-enough proxy for the JS syntax used here
    except re.error as e:
        return f"does not compile: {e}"
    return None


def check_case(case_dir: Path, errors: list[str]) -> None:
    rel = case_dir.relative_to(ROOT)
    prompt = case_dir / "prompt.md"
    case_yaml = case_dir / "case.yaml"
    if not prompt.exists() and not case_yaml.exists():
        return
    if prompt.exists():
        fm, body = frontmatter(prompt)
        for k in fm:
            if k not in PROMPT_KEYS:
                errors.append(f"{rel}/prompt.md: unknown frontmatter key {k!r}")
        if not body:
            errors.append(f"{rel}/prompt.md: empty prompt body")
        tools = re.findall(r"[A-Za-z]+", fm.get("allowed_tools", ""))
        for t in tools:
            if t not in READ_ONLY_TOOLS | GATED_TOOLS | {"TaskCreate", "TaskGet", "TaskList", "TaskUpdate", "TaskStop", "TaskOutput"}:
                errors.append(f"{rel}/prompt.md: unknown tool {t!r} in allowed_tools")
        if "Bash" in tools:
            errors.append(f"{rel}/prompt.md: Bash needs an OS sandbox; native Windows has none — keep cases shell-free")
    if case_yaml.exists():
        text = case_yaml.read_text(encoding="utf-8")
        if 'schema_version: "1.1"' not in text:
            errors.append(f"{rel}/case.yaml: missing schema_version \"1.1\"")
        m = re.search(r"^name:\s*(\S+)", text, re.M)
        if not m or m.group(1) != case_dir.name:
            errors.append(f"{rel}/case.yaml: name must equal the directory name")
        m = re.search(r"scaffold_script:\s*(\S+)", text)
        if m and not (case_dir / m.group(1)).exists():
            errors.append(f"{rel}/case.yaml: scaffold_script {m.group(1)} not found")
        if m and not (case_dir / "resources" / "career" / "facts.md").exists():
            errors.append(f"{rel}: scaffold needs resources/career (run sync_fixtures.py)")
        for d in re.findall(r"add_dirs:\s*\[([^\]]*)\]", text):
            for name in [x.strip() for x in d.split(",") if x.strip()]:
                if not (case_dir / name).is_dir():
                    errors.append(f"{rel}/case.yaml: add_dirs entry {name!r} is not a directory (run sync_fixtures.py)")

    graders = sorted((case_dir / "graders").glob("*.md"))
    if not graders:
        errors.append(f"{rel}: no graders")
    for g in graders:
        fm, body = frontmatter(g)
        t = fm.get("type")
        if t not in GRADER_TYPES:
            errors.append(f"{rel}/graders/{g.name}: unknown type {t!r}")
            continue
        for k in fm:
            if k not in GRADER_TYPES[t] | COMMON_GRADER_KEYS:
                errors.append(f"{rel}/graders/{g.name}: key {k!r} is not valid for type {t}")
        if t == "regex":
            if not fm.get("pattern"):
                errors.append(f"{rel}/graders/{g.name}: regex needs a pattern")
            elif (why := js_regex_ok(fm["pattern"])):
                errors.append(f"{rel}/graders/{g.name}: pattern {why}")
            if fm.get("match") not in (None, "contains", "not_contains") and not str(fm.get("match")).startswith("count:"):
                errors.append(f"{rel}/graders/{g.name}: match must be contains | not_contains | count:N")
        if t == "tool_used":
            if not fm.get("tool"):
                errors.append(f"{rel}/graders/{g.name}: tool_used needs a tool")
            if fm.get("tool") == "Skill":
                im = fm.get("input_match", "")
                named = re.search(r"\)\?([\w-]+)\"?$", im)  # ...(?:[\w-]+:)?<skill>"
                if not named or named.group(1) not in SKILLS:
                    errors.append(f"{rel}/graders/{g.name}: Skill grader must name one of {sorted(SKILLS)}")
            if (im := fm.get("input_match")) and (why := js_regex_ok(im)):
                errors.append(f"{rel}/graders/{g.name}: input_match {why}")
        if t == "llm" and not body and not fm.get("criteria"):
            errors.append(f"{rel}/graders/{g.name}: llm grader needs a rubric body")
        if t == "file_exists" and not fm.get("path"):
            errors.append(f"{rel}/graders/{g.name}: file_exists needs a path")


def check_fixtures_in_sync(errors: list[str]) -> None:
    src = ROOT / "_fixtures" / "career"
    for res in ROOT.rglob("resources/career"):
        if "results" in res.parts:
            continue
        for f in src.rglob("*"):
            if f.is_file():
                mirror = res / f.relative_to(src)
                if not mirror.exists() or mirror.read_bytes() != f.read_bytes():
                    errors.append(f"{res.relative_to(ROOT)}: out of date vs _fixtures (run sync_fixtures.py)")
                    break


def check_hardlinks(errors: list[str]) -> None:
    for root, dirs, files in os.walk(PLUGIN):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".next"}]
        for f in files:
            p = Path(root) / f
            try:
                if os.stat(p).st_nlink > 1:
                    errors.append(
                        f"hard link under the plugin: {p.relative_to(PLUGIN)} — the harness refuses these "
                        f"(for uv venvs: UV_LINK_MODE=copy uv sync --reinstall)"
                    )
                    return
            except OSError:
                continue


def main() -> int:
    errors: list[str] = []
    cases = [p.parent for p in ROOT.rglob("prompt.md") if "results" not in p.parts and "_fixtures" not in p.parts]
    cases += [p.parent for p in ROOT.rglob("case.yaml") if p.parent not in cases and "results" not in p.parts]
    for c in sorted(set(cases)):
        check_case(c, errors)
    check_fixtures_in_sync(errors)
    check_hardlinks(errors)
    skills_covered = {c.parent.name for c in cases}
    missing = SKILLS - skills_covered
    if missing:
        errors.append(f"skills without any eval case: {sorted(missing)}")
    graders = sum(1 for _ in ROOT.rglob("graders/*.md") if "results" not in str(_))
    print(f"{len(set(cases))} cases, {graders} graders, {len(skills_covered)}/{len(SKILLS)} skills covered")
    for e in errors:
        print("ERROR", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

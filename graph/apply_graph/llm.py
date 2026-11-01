"""The one model call the graph needs: system + user text in, a validated Pydantic object out.

Nodes depend on the `LLM` protocol, not on the SDK, so tests run on a scripted fake with no network.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

MODEL = "claude-opus-5-5"


class LLM(Protocol):
    def parse(self, system: str, user: str, schema: type[T]) -> T: ...


class RefusalError(RuntimeError):
    pass


class ClaudeLLM:
    def __init__(self, model: str = MODEL, effort: str = "medium") -> None:
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model
        self.effort = effort

    def parse(self, system: str, user: str, schema: type[T]) -> T:
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": self.effort},
            output_format=schema,
        )
        if response.stop_reason == "refusal":
            raise RefusalError(str(response.stop_details))
        return response.parsed_output


def _native_install() -> str | None:
    # the native installer puts claude in ~/.local/bin, which is not always on PATH
    for name in ("claude.exe", "claude"):
        if (p := Path.home() / ".local" / "bin" / name).is_file():
            return str(p)
    return None


class ClaudeCodeLLM:
    """Same call through the Claude Code CLI (`claude -p`), which uses its own login instead of an API key.

    Runs with no tools, in an empty temp folder, so the posting cannot make it touch files.
    """

    def __init__(self, model: str = "opus", effort: str = "medium", exe: str | None = None) -> None:
        self.exe = exe or shutil.which("claude") or _native_install() or "claude"
        self.model = model
        self.effort = effort

    def parse(self, system: str, user: str, schema: type[T]) -> T:
        cmd = [
            self.exe, "-p",
            "--output-format", "json",
            "--json-schema", json.dumps(schema.model_json_schema()),
            "--system-prompt", system,
            "--tools", "",
            "--model", self.model,
            "--effort", self.effort,
            "--no-session-persistence",
        ]
        with tempfile.TemporaryDirectory() as cwd:
            proc = subprocess.run(
                cmd, input=user, capture_output=True, text=True, encoding="utf-8", cwd=cwd
            )
        if proc.returncode != 0:
            detail = proc.stderr.strip() or proc.stdout[:500]
            raise RuntimeError(f"claude -p failed ({proc.returncode}): {detail}")
        out = json.loads(proc.stdout)
        if out.get("is_error") or out.get("structured_output") is None:
            raise RefusalError(out.get("result") or out.get("subtype") or "no structured output")
        return schema.model_validate(out["structured_output"])

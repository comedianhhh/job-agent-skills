from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tracker_api.config import Settings
from tracker_api.main import create_app

# Mirrors a real tracker: prose above and below, non-English headers, bold + backticks + links in cells,
# one row with a status the parser does not know, and CRLF line endings.
TRACKER_MD = (
    "# Pipeline\r\n"
    "\r\n"
    "Follow-up rule: 10 business days → one message.\r\n"
    "\r\n"
    "Statuses: `DRAFT` → `APPLIED` → `SCREEN`\r\n"
    "\r\n"
    "| 公司 | 岗位 | Req | 地点 | 投递日 | 状态 | 下一步 | 文件夹 |\r\n"
    "|---|---|---|---|---|---|---|---|\r\n"
    "| **Affirm** | **Software Engineer II** — Card | Greenhouse 7981805003 | Remote Canada | **2026-09-12** | `APPLIED` | ✅ 已投。跟进 → 9/26 | [2026-09-12-Affirm-…](2026-09-12-Affirm-Software-Engineer-II-7981805003/) |\r\n"
    "| Cohere | Software Engineer, Adoption | Ashby `732c05f5…` | Toronto / 远程 | 2026-09-14 | `APPLIED` | follow up 2026-09-29 | [2026-09-14-Cohere-…](2026-09-14-Cohere-Software-Engineer-Adoption-Toronto/) |\r\n"
    "| Clio | Software Developer | Workday REQ-4630 | Toronto | — | `DRAFT` | Alan applies himself | [2026-09-14-Clio-…](2026-09-14-Clio-Software-Developer-Toronto/) |\r\n"
    "| Emterra | AI / Full Stack Engineer | — | Oakville | ~2026-08-31 | `SCREEN` | call 9/10 | [2026-08-31-Emterra-…](2026-08-31-Emterra-AI-Full-Stack-Engineer/) |\r\n"
    "| Mystery | Something | — | — | — | `PENDING` | unknown status on purpose | |\r\n"
    "\r\n"
    "---\r\n"
    "\r\n"
    "## 待办\r\n"
    "\r\n"
    "- [ ] keep this list untouched\r\n"
)

TARGETS_YAML = """boards:
  - greenhouse:doordashcanada
  - ashby:cohere
linkedin:
  - { keywords: "backend engineer", location: "Toronto, Ontario, Canada" }
filters:
  hours: 48
  include_regex: "engineer|developer"
  exclude_regex: ""
  location_regex: "Toronto|Canada|Remote"
"""


@pytest.fixture
def career(tmp_path: Path) -> Path:
    (tmp_path / "tracker.md").write_bytes(TRACKER_MD.encode("utf-8"))
    (tmp_path / "targets.yaml").write_text(TARGETS_YAML, encoding="utf-8")
    return tmp_path


@pytest.fixture
def settings(career: Path) -> Settings:
    return Settings(career_dir=career, database_url=f"sqlite:///{(career / 'test.sqlite').as_posix()}")


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))

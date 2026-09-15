"""Two knobs, both environment variables.

CAREER_DIR    the private workspace created by /career-init (tracker.md, targets.yaml, SCAN-*.md)
DATABASE_URL  SQLAlchemy URL; docker-compose points it at Postgres, default is a local SQLite file
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    career_dir: Path
    database_url: str

    @property
    def tracker_path(self) -> Path:
        p = self.career_dir / "tracker.md"
        if not p.exists():  # older private workspaces spell it TRACKER.md; case matters on Linux
            for alt in self.career_dir.glob("*"):
                if alt.name.lower() == "tracker.md":
                    return alt
        return p

    @property
    def targets_path(self) -> Path:
        return self.career_dir / "targets.yaml"


def load_settings() -> Settings:
    career = Path(os.environ.get("CAREER_DIR", "career")).expanduser().resolve()
    db = os.environ.get("DATABASE_URL", f"sqlite:///{(career / '.tracker-api.sqlite').as_posix()}")
    return Settings(career_dir=career, database_url=db)

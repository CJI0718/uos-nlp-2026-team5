"""The verification Skill text, shared by the experiment runners and the schedule assistant."""

from __future__ import annotations

import re
from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parents[2] / "skills/factcheck-mission-agent/SKILL.md"


def skill_body(path: str | Path = SKILL_PATH) -> str:
    """SKILL.md without its YAML frontmatter."""
    text = Path(path).read_text(encoding="utf-8")
    return re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S).strip()

"""Round-specific skills: skills/<name>/SKILL.md is loaded only for the matching round."""

from __future__ import annotations

from pathlib import Path

from .config import PROJECT_ROOT

_ROUND_TO_SKILL = {"behav": "behavioural"}


def load_skill(round_name: str, skills_dir: Path | None = None) -> str:
    skills_dir = skills_dir or PROJECT_ROOT / "skills"
    r = round_name.lower()
    for prefix, skill in _ROUND_TO_SKILL.items():
        if r.startswith(prefix):
            path = skills_dir / skill / "SKILL.md"
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                if text.startswith("---"):  # drop the front matter
                    text = text.split("---", 2)[2]
                return text.strip()
    return ""

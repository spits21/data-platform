"""ui.backend.skills — parse .claude/skills/*/SKILL.md frontmatter.

Skill discovery is purely folder-based (no manifest file — confirmed by
reading the actual SKILL.md files: frontmatter has exactly two keys, `name`
and `description`), so this is a manual scan rather than a YAML dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import settings

# Fixed display order for the known ODR skills; any future skill folder
# not in this list is appended alphabetically after them.
_DISPLAY_ORDER = ["odr-report", "odr-new-chart", "odr-new-domain"]


@dataclass
class SkillInfo:
    name: str
    description: str


def _parse_frontmatter(skill_md: Path) -> SkillInfo | None:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    front = text[3:end]

    name = ""
    description = ""
    for line in front.splitlines():
        line = line.strip()
        if line.startswith("name:"):
            name = line[len("name:") :].strip()
        elif line.startswith("description:"):
            description = line[len("description:") :].strip()

    if not name:
        return None
    return SkillInfo(name=name, description=description)


def list_skills() -> list[SkillInfo]:
    if not settings.SKILLS_DIR.exists():
        return []

    found: dict[str, SkillInfo] = {}
    for folder in settings.SKILLS_DIR.iterdir():
        if not folder.is_dir():
            continue
        skill_md = folder / "SKILL.md"
        if not skill_md.exists():
            continue
        info = _parse_frontmatter(skill_md)
        if info:
            found[info.name] = info

    ordered = [found[n] for n in _DISPLAY_ORDER if n in found]
    remaining = sorted(
        (v for k, v in found.items() if k not in _DISPLAY_ORDER), key=lambda s: s.name
    )
    return ordered + remaining

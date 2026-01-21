from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class Skill:
    """Represents a skill with its metadata and content.

    Attributes:
        name: The skill name
        path: Path to the skill Markdown file
        content: Full Markdown content of the skill
    """
    name: str
    path: Path
    content: str

    @property
    def group(self) -> str | None:
        """Extract the skill group from the path (e.g., 'HR-scopes')."""
        parts = list(self.path.parts)
        try:
            idx = parts.index("skills_v2")
        except ValueError:
            return None
        if idx + 1 >= len(parts):
            return None
        group = parts[idx + 1]
        return group or None

    @property
    def logic_flow_steps(self) -> list[str]:
        """Extract logic flow steps from the '## Logic Flow' section."""
        lines = self.content.splitlines()
        start_idx = None
        for idx, line in enumerate(lines):
            if line.strip().lower() == "## logic flow":
                start_idx = idx + 1
                break
        if start_idx is None:
            return []

        steps: list[str] = []
        for line in lines[start_idx:]:
            stripped = line.strip()
            if stripped.startswith("## "):
                break
            m = re.match(r"^\d+\.\s+(.*)$", stripped)
            if m:
                steps.append(m.group(1).strip())

        return steps


class SkillRegistry:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir

    def list_skill_groups(self) -> list[str]:
        if not self.skills_dir.exists():
            return []
        groups: list[str] = []
        for p in sorted([x for x in self.skills_dir.iterdir() if x.is_dir()]):
            if not p.name.endswith("-scopes"):
                continue
            groups.append(p.name)
        return groups

    def list_skills(self) -> list[Skill]:
        skills: list[Skill] = []
        if not self.skills_dir.exists():
            return skills

        for scope_dir in sorted([p for p in self.skills_dir.iterdir() if p.is_dir()]):
            examples_dir = scope_dir / "examples"
            if not examples_dir.exists():
                continue
            for example_md in sorted(examples_dir.glob("*.md")):
                try:
                    content = example_md.read_text(encoding="utf-8")
                except OSError:
                    continue
                name = _extract_skill_title(content) or example_md.stem.replace("_", " ").title()
                skills.append(Skill(name=name, path=example_md, content=content))

        candidates = list(self.skills_dir.rglob("SKILL.md")) + list(self.skills_dir.rglob("SKILLS.md"))
        for skill_md in sorted(set(candidates)):
            if skill_md.name == "SKILL.md" and skill_md.parent.name.endswith("-scopes") and (skill_md.parent / "examples").exists():
                continue
            try:
                content = skill_md.read_text(encoding="utf-8")
            except OSError:
                continue

            name = skill_md.parent.name
            skills.append(Skill(name=name, path=skill_md, content=content))
        return skills

    def read_skills_readme(self) -> str:
        readme = self.skills_dir / "Readme.md"
        if not readme.exists():
            return ""
        try:
            return readme.read_text(encoding="utf-8")
        except OSError:
            return ""


def _extract_skill_title(content: str) -> str | None:
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        title = stripped.lstrip("#").strip()
        if title.lower().startswith("skill:"):
            title = title.split(":", 1)[1].strip()
        if title:
            return title
        return None
    return None

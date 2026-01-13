from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path
    content: str


class SkillRegistry:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir

    def list_skills(self) -> list[Skill]:
        skills: list[Skill] = []
        if not self.skills_dir.exists():
            return skills

        candidates = list(self.skills_dir.rglob("SKILL.md")) + list(self.skills_dir.rglob("SKILLS.md"))
        for skill_md in sorted(set(candidates)):
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

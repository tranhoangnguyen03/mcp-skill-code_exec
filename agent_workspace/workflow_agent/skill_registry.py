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

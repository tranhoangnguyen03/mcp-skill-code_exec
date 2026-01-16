from __future__ import annotations

from pathlib import Path


class PromptStore:
    def __init__(self, prompts_dir: Path):
        self.prompts_dir = prompts_dir

    def load(self, name: str) -> str:
        path = self.prompts_dir / name
        return path.read_text(encoding="utf-8")

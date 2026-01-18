from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def data_dir() -> Path:
    return repo_root() / "agent_workspace" / "data"


def load_json(relative_path: str):
    path = data_dir() / relative_path
    raw = path.read_text(encoding="utf-8")
    return json.loads(_expand_date_tokens(raw))


def _expand_date_tokens(text: str) -> str:
    import re

    today = date.today()

    def replacer(match):
        token = match.group(0)
        if token == "${TODAY}":
            return today.isoformat()

        m = re.match(r"\$\{TODAY_(PLUS|MINUS)_(\d+)\}", token)
        if m:
            op, days = m.groups()
            delta = timedelta(days=int(days))
            res = today + delta if op == "PLUS" else today - delta
            return res.isoformat()
        return token

    return re.sub(r"\$\{TODAY(?:_(?:PLUS|MINUS)_\d+)?\}", replacer, text)

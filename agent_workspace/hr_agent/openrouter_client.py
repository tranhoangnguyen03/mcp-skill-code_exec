from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


class OpenRouterClient:
    def __init__(self, api_key: str | None, model: str | None):
        if not api_key:
            raise ValueError("Missing open_router_api_key")
        if not model:
            raise ValueError("Missing open_router_model_name")
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[LLMMessage], temperature: float = 0.2) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }

        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


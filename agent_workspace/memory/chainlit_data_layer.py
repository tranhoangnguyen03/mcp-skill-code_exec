"""Custom Chainlit data layer using file-based YAML storage."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from chainlit.data.base import BaseDataLayer
from chainlit.types import (
    Feedback,
    PageInfo,
    PaginatedResponse,
    Pagination,
    ThreadDict,
    ThreadFilter,
)
from chainlit.user import PersistedUser, User
from literalai import Step as LiteralStep


class _TolerantYamlLoader(yaml.SafeLoader):
    pass


def _construct_python_object_apply(loader: _TolerantYamlLoader, _suffix: str, node: yaml.Node):
    if isinstance(node, yaml.SequenceNode):
        seq = loader.construct_sequence(node)
        if len(seq) == 1 and isinstance(seq[0], str):
            return seq[0]
        return seq
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    return None


_TolerantYamlLoader.add_multi_constructor(
    "tag:yaml.org,2002:python/object/apply:", _construct_python_object_apply
)


class FileDataLayer(BaseDataLayer):
    """File-based data layer for Chainlit using YAML storage.

    Each thread is stored as a single YAML file containing:
    - session_id, created_at, updated_at
    - user_id, userIdentifier, name, metadata, tags
    - messages[] (role, content, timestamp) - conversation turns only
    - steps[] (step_type, category, content, metadata, timestamp) - working artifacts
    - facts[] (fact, source_turn, timestamp)

    Design: messages[] stores conversation turns (user/assistant dialogue),
    while steps[] stores working artifacts (plan, codegen, execute outputs).
    This prevents duplication and provides clear separation of concerns.
    """

    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = storage_dir or Path(__file__).parent / "sessions"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._users_path = self.storage_dir / "_users.yaml"

    def _get_thread_path(self, thread_id: str) -> Path:
        """Get the file path for a thread's YAML file."""
        return self.storage_dir / f"{thread_id}.yaml"

    # --- User Methods ---

    def _load_users(self) -> dict[str, dict[str, Any]]:
        """Load users from YAML."""
        if not self._users_path.exists():
            return {}
        content = self._users_path.read_text(encoding="utf-8")
        return yaml.safe_load(content) or {}

    def _lookup_user_identifier(self, user_id: str | None) -> str | None:
        if not user_id:
            return None
        users = self._load_users()
        for identifier, data in users.items():
            if data.get("id") == user_id:
                return identifier
        return None

    def _save_users(self, users: dict[str, dict[str, Any]]) -> None:
        """Save users to YAML."""
        self._save_yaml(self._users_path, users)

    async def get_user(self, identifier: str) -> PersistedUser | None:
        users = self._load_users()
        if identifier in users:
            u = users[identifier]
            return PersistedUser(
                id=u["id"],
                identifier=identifier,
                createdAt=u.get("createdAt", datetime.now(timezone.utc).isoformat()),
                metadata=u.get("metadata", {}),
            )
        return None

    async def create_user(self, user: User) -> PersistedUser | None:
        users = self._load_users()
        now = datetime.now(timezone.utc).isoformat()
        if user.identifier in users:
            existing = users[user.identifier]
            if user.metadata:
                existing_metadata = existing.get("metadata", {})
                existing["metadata"] = {**existing_metadata, **user.metadata}
                self._save_users(users)
            return PersistedUser(
                id=existing["id"],
                identifier=user.identifier,
                createdAt=existing.get("createdAt", now),
                metadata=existing.get("metadata", {}),
            )

        user_id = str(uuid.uuid4())
        users[user.identifier] = {
            "id": user_id,
            "identifier": user.identifier,
            "createdAt": now,
            "metadata": user.metadata or {},
        }
        self._save_users(users)
        return PersistedUser(
            id=user_id,
            identifier=user.identifier,
            createdAt=now,
            metadata=user.metadata or {},
        )

    async def delete_user_session(self, id: str) -> bool:
        return True

    # --- Thread Methods ---

    def _load_thread(self, thread_id: str) -> dict[str, Any] | None:
        """Load thread data from YAML file."""
        path = self._get_thread_path(thread_id)
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8")
        try:
            return yaml.load(content, Loader=_TolerantYamlLoader)
        except Exception:
            return None

    def _save_thread(self, thread_id: str, data: dict[str, Any]) -> None:
        """Save thread data to YAML file."""
        path = self._get_thread_path(thread_id)
        self._save_yaml(path, data)

    def _save_yaml(self, path: Path, data: Any) -> None:
        """Save data to YAML file."""
        path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def _get_thread_data(self, thread_id: str, create_if_missing: bool = False) -> dict[str, Any]:
        """Get thread data, optionally creating a new one."""
        data = self._load_thread(thread_id)
        if data is not None:
            return data
        if not create_if_missing:
            return {}
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        return {
            "session_id": thread_id,
            "created_at": now,
            "updated_at": now,
            "user_id": None,
            "user_identifier": None,
            "name": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": {},
            "tags": [],
            "messages": [],
            "steps": [],  # Working step artifacts (plan, codegen, execute)
            "facts": [],
        }

    def _default_thread_name(self, *, thread_id: str, created_at: str | None) -> str:
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at)
                return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        return f"Conversation {thread_id[:8]}"

    def _thread_data_to_dict(self, thread_id: str, data: dict[str, Any]) -> ThreadDict:
        """Convert thread data to ThreadDict."""
        messages = data.get("messages", [])
        steps = []
        for i, msg in enumerate(messages):
            steps.append({
                "id": f"{thread_id}_step_{i}",
                "name": msg.get("role", "unknown"),
                "type": "user_message" if msg.get("role") == "user" else "assistant_message",
                "threadId": thread_id,
                "output": msg.get("content", ""),
                "createdAt": msg.get("timestamp", ""),
            })

        name = data.get("name")
        if not name:
            name = self._default_thread_name(thread_id=thread_id, created_at=data.get("created_at"))

        user_id = data.get("user_id")
        user_identifier = data.get("user_identifier") or self._lookup_user_identifier(user_id)

        return ThreadDict(
            id=thread_id,
            name=name,
            createdAt=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            userId=user_id,
            userIdentifier=user_identifier,
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            steps=steps,
        )

    def _list_thread_files(self) -> list[Path]:
        """List all thread YAML files in storage directory."""
        return [
            p for p in self.storage_dir.glob("*.yaml")
            if p.name != "_users.yaml"
        ]

    async def list_threads(
        self, pagination: Pagination, filters: ThreadFilter
    ) -> PaginatedResponse[ThreadDict]:
        threads: list[ThreadDict] = []
        thread_files = self._list_thread_files()

        user_id_filter = getattr(filters, "userId", None)
        user_identifier_filter = getattr(filters, "userIdentifier", None)

        for path in thread_files:
            thread_id = path.stem
            data = self._load_thread(thread_id)
            if data is None:
                continue
            if user_id_filter and data.get("user_id") != user_id_filter:
                continue
            if user_identifier_filter:
                effective_identifier = data.get("user_identifier") or self._lookup_user_identifier(
                    data.get("user_id")
                )
                if effective_identifier != user_identifier_filter:
                    continue
            threads.append(self._thread_data_to_dict(thread_id, data))

        # Sort by createdAt descending (newest first)
        threads.sort(key=lambda t: t.get("createdAt", ""), reverse=True)

        # Apply pagination
        start = 0
        if pagination.cursor:
            for i, t in enumerate(threads):
                if t["id"] == pagination.cursor:
                    start = i + 1
                    break

        page_size = pagination.first or 20
        page = threads[start : start + page_size]
        has_next = len(threads) > start + page_size

        return PaginatedResponse(
            data=page,
            pageInfo=PageInfo(
                hasNextPage=has_next,
                startCursor=page[0]["id"] if page else None,
                endCursor=page[-1]["id"] if page else None,
            ),
        )

    async def get_thread(self, thread_id: str) -> ThreadDict | None:
        data = self._load_thread(thread_id)
        if data is None:
            return None
        return self._thread_data_to_dict(thread_id, data)

    async def get_thread_author(self, thread_id: str) -> str:
        data = self._load_thread(thread_id)
        if not data:
            return ""
        user_identifier = data.get("user_identifier") or self._lookup_user_identifier(
            data.get("user_id")
        )
        return user_identifier or ""

    async def update_thread(
        self,
        thread_id: str,
        name: str | None = None,
        user_id: str | None = None,
        metadata: dict | None = None,
        tags: list[str] | None = None,
    ) -> None:
        data = self._get_thread_data(thread_id, create_if_missing=True)
        now = datetime.now(timezone.utc).isoformat()

        if name is not None:
            data["name"] = name
        if user_id is not None:
            data["user_id"] = user_id
            if not data.get("user_identifier"):
                inferred_identifier = self._lookup_user_identifier(user_id)
                if inferred_identifier:
                    data["user_identifier"] = inferred_identifier
        if metadata is not None:
            data["metadata"] = metadata
        if tags is not None:
            data["tags"] = tags
        data["updated_at"] = now

        self._save_thread(thread_id, data)

    async def delete_thread(self, thread_id: str) -> None:
        path = self._get_thread_path(thread_id)
        if path.exists():
            path.unlink()

    # --- Step Methods ---

    async def create_step(self, step_dict: dict) -> None:
        """No-op: Message storage is handled by SessionMemory.add_response().

        This prevents duplicate writes that previously occurred when both
        cl.Message().send() (via create_step) and SessionMemory.add_message()
        wrote to the same storage.

        Working step artifacts (plan, codegen, execute) are stored via
        SessionMemory.add_working_step() which writes to the steps[] array.
        """
        # Messages are now stored via SessionMemory.add_response()
        # This method is a no-op to prevent duplication
        pass

    async def update_step(self, step_dict: dict) -> None:
        # For simplicity, we don't update individual steps
        pass

    async def delete_step(self, step_id: str) -> None:
        # For simplicity, we don't delete individual steps
        pass

    # --- Element Methods ---

    async def create_element(self, element_dict: dict) -> None:
        pass

    async def get_element(self, thread_id: str, element_id: str) -> dict | None:
        return None

    async def delete_element(self, element_id: str) -> None:
        pass

    # --- Feedback Methods ---

    async def upsert_feedback(self, feedback: Feedback) -> str:
        return feedback.id or str(uuid.uuid4())

    async def delete_feedback(self, feedback_id: str) -> bool:
        return True

    # --- Required Abstract Methods ---

    async def close(self) -> None:
        """No-op: YAML storage doesn't require connection cleanup."""
        pass

    async def get_favorite_steps(self, thread_id: str) -> list[dict]:
        """Favorites feature not implemented; return empty list."""
        return []

    async def build_debug_url(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        return ""

    # --- Helper Methods ---

    @classmethod
    def from_literal_step(cls, step: LiteralStep) -> dict:
        """Convert a Literal AI step to a step dict."""
        return {
            "id": step.id,
            "name": step.name,
            "type": step.type,
            "threadId": step.thread_id,
            "output": step.output,
            "createdAt": step.created_at,
        }

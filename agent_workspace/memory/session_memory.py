"""Session memory with YAML persistence via FileDataLayer."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .chainlit_data_layer import FileDataLayer


class StepType(str, Enum):
    """Types of working steps in the workflow."""
    PLAN = "plan"
    CODEGEN = "codegen"
    EXECUTE = "execute"
    RESPONSE = "response"


class StepCategory(str, Enum):
    """Category of a step - working artifacts vs conversation turns."""
    WORKING = "working"   # Plan, codegen, execute - display as Chainlit steps
    RESPONSE = "response" # Chat/final response - display as Chainlit messages


@dataclass(frozen=True)
class Message:
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(frozen=True)
class WorkingStep:
    """Immutable record of a working step artifact.

    Working steps include plan proposals, generated code, execution outputs.
    These are distinct from conversation turns (messages) which are the
    actual user/assistant dialogue.
    """
    step_type: str         # "plan", "codegen", "execute"
    category: StepCategory # WORKING or RESPONSE
    content: str           # JSON, code, output, etc.
    metadata: dict | None = None  # Extra data (exit_code, attempt_num, etc.)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(frozen=True)
class KeyFact:
    """Immutable record of an extracted fact."""

    fact: str
    source_turn: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class SessionMemory:
    """Session memory that delegates to FileDataLayer for persistence.

    Provides a convenient app-level API while using the unified
    storage layer (FileDataLayer) for YAML persistence.
    """

    def __init__(
        self, session_id: str | None = None, memory_dir: Path | None = None
    ) -> None:
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
        self._data_layer = FileDataLayer(storage_dir=memory_dir)

    @property
    def file_path(self) -> Path:
        """Path to the thread YAML file."""
        return self._data_layer._get_thread_path(self.session_id)

    # --- Core APIs ---

    def add_response(self, role: str, content: str) -> None:
        """Add a conversation turn (user input or assistant response).

        This is the SINGLE write path for conversation turns.
        Chainlit's cl.Message().send() handles UI display only.
        This prevents duplicate writes that previously occurred via both
        add_message() and create_step().
        """
        data = self._data_layer._get_thread_data(self.session_id, create_if_missing=True)
        now = datetime.now().isoformat()

        data["messages"].append({
            "role": role,
            "content": content,
            "timestamp": now,
        })
        data["updated_at"] = now

        self._data_layer._save_thread(self.session_id, data)

    def add_message(self, role: str, content: str) -> None:
        """Alias for add_response() - kept for backward compatibility."""
        self.add_response(role, content)

    def add_working_step(
        self,
        step_type: str,
        content: str,
        category: StepCategory,
        metadata: dict | None = None,
    ) -> None:
        """Add a working step artifact (plan, codegen code, execution output).

        Working steps are distinct from conversation turns (messages).
        They store intermediate artifacts that are useful for debugging,
        session resumption, and understanding the agent's decision process.

        Args:
            step_type: Type of step ("plan", "codegen", "execute")
            content: The step content (JSON, code, output, etc.)
            category: WORKING for artifacts, RESPONSE for final outputs
            metadata: Optional extra data (exit_code, attempt_num, etc.)
        """
        data = self._data_layer._get_thread_data(self.session_id, create_if_missing=True)
        now = datetime.now().isoformat()

        if isinstance(step_type, Enum):
            step_type_value = str(step_type.value)
        else:
            step_type_value = str(step_type)

        data["steps"].append({
            "step_type": step_type_value,
            "category": category.value,
            "content": content,
            "metadata": metadata or {},
            "timestamp": now,
        })
        data["updated_at"] = now

        self._data_layer._save_thread(self.session_id, data)

    def add_fact(self, fact: str) -> None:
        """Add a key fact and save."""
        self._add_facts([fact])

    def add_facts(self, facts: list[str]) -> None:
        """Add multiple facts at once."""
        if not facts:
            return

        data = self._data_layer._get_thread_data(self.session_id, create_if_missing=True)
        turn = len(data.get("messages", []))
        now = datetime.now().isoformat()

        for f in facts:
            data["facts"].append({
                "fact": f,
                "source_turn": turn,
                "timestamp": now,
            })
        data["updated_at"] = now

        self._data_layer._save_thread(self.session_id, data)

    def _add_facts(self, facts: list[str]) -> None:
        """Internal method to add facts."""
        self.add_facts(facts)

    def get_messages(self) -> list[Message]:
        """Return all messages in this session."""
        data = self._data_layer._load_thread(self.session_id)
        if data is None:
            return []

        messages = []
        for msg in data.get("messages", []):
            messages.append(Message(
                role=msg.get("role", ""),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp", ""),
            ))
        return messages

    def get_facts(self) -> list[KeyFact]:
        """Return all key facts."""
        data = self._data_layer._load_thread(self.session_id)
        if data is None:
            return []

        facts = []
        for f in data.get("facts", []):
            facts.append(KeyFact(
                fact=f.get("fact", ""),
                source_turn=f.get("source_turn", 0),
                timestamp=f.get("timestamp", ""),
            ))
        return facts

    def get_working_steps(self) -> list[WorkingStep]:
        """Return all working step artifacts for this session.

        Working steps include plan proposals, generated code, execution outputs.
        These are distinct from conversation turns (messages).
        """
        data = self._data_layer._load_thread(self.session_id)
        if data is None:
            return []

        steps = []
        for step in data.get("steps", []):
            steps.append(WorkingStep(
                step_type=step.get("step_type", ""),
                category=StepCategory(step.get("category", "working")),
                content=step.get("content", ""),
                metadata=step.get("metadata"),
                timestamp=step.get("timestamp", ""),
            ))
        return steps

    def get_context_summary(self, max_messages: int = 10) -> str:
        """Return recent messages + all facts as a context string for prompts."""
        parts: list[str] = []
        facts = self.get_facts()

        if facts:
            parts.append("## Key Facts")
            for kf in facts:
                parts.append(f"- {kf.fact}")
            parts.append("")

        messages = self.get_messages()
        recent = messages[-max_messages:] if max_messages else messages
        if recent:
            parts.append("## Recent Conversation")
            for msg in recent:
                prefix = "User" if msg.role == "user" else "Assistant"
                # Truncate long messages
                content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
                parts.append(f"**{prefix}**: {content}")
            parts.append("")

        return "\n".join(parts)

    def get_conversation_history(self, max_messages: int = 10) -> str:
        messages = self.get_messages()
        recent = messages[-max_messages:] if max_messages else messages
        parts: list[str] = []
        for msg in recent:
            prefix = "User" if msg.role == "user" else "Assistant"
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            parts.append(f"{prefix}: {content}")
        return "\n".join(parts)

    def clear(self) -> None:
        """Clear session and delete file."""
        self._data_layer.delete_thread(self.session_id)

    # --- Persistence helpers (for backward compatibility) ---

    def _load_if_exists(self) -> None:
        """Load from YAML if file exists. (No-op: lazy loading via FileDataLayer)."""
        pass

    def _save(self) -> None:
        """Save session to YAML file. (No-op: changes are saved immediately)."""
        pass

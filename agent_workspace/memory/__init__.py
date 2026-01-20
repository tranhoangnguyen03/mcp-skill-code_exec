"""Session memory module for conversation persistence."""

from .fact_extractor import extract_facts_simple
from .session_memory import (
    KeyFact,
    Message,
    SessionMemory,
    StepType,
    StepCategory,
    WorkingStep,
)

__all__ = [
    "SessionMemory",
    "Message",
    "KeyFact",
    "StepType",
    "StepCategory",
    "WorkingStep",
    "extract_facts_simple",
]


def get_chainlit_data_layer():
    """Get the Chainlit data layer (lazy import to avoid circular deps)."""
    from .chainlit_data_layer import FileDataLayer
    return FileDataLayer()

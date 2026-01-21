"""Standalone execution result dataclass.

This module is intentionally independent to avoid circular imports.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionResult:
    """Result of code execution."""
    stdout: str
    stderr: str
    exit_code: int

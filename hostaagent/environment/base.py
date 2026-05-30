"""The Environment seam — the agent's *body*: what it can do and touch.

Subclass `Environment`, override `tools()` to expose callables and `context()` to
add prompt context. Concrete bodies (LocalFS, and future ones) live alongside this
file so they stay detachable.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


class Environment:
    """Subclass. Override `tools()` to expose callables; `context()` for prompt context."""

    def tools(self) -> list[Callable[..., Any]]:
        return []

    def context(self) -> str:
        return ""

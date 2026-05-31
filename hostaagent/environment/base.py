"""The Environment seam — the agent's *body*: what it can do and touch.

Subclass `Environment`, override `tools()` to expose callables and `context()` to
add prompt context. Concrete bodies (LocalFS, HttpEnv, MultiEnv, future ones) live
alongside this file so they stay detachable.

Lifecycle: the *driver* may `await env.setup()` before a run and `await env.close()`
after (DB connections, auth tokens). The core loop never calls them — they're an
optional convenience, not a requirement.
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

    async def setup(self) -> None:
        """Optional: acquire resources (DB, auth). Called by the driver, not the core."""

    async def close(self) -> None:
        """Optional: release resources. Called by the driver after the run."""

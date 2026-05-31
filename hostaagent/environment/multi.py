"""MultiEnv — compose several environments into one body."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import Environment


def _tool_name(fn: Callable[..., Any]) -> str:  # mirrors core._tool_name (avoids a cycle)
    meta = getattr(fn, "__hosta_tool__", None)
    return meta.name if meta is not None else fn.__name__


class MultiEnv(Environment):
    """Merge N environments: `tools()` = union (last env wins on a name clash),
    `context()` = the non-empty contexts joined. `setup()`/`close()` fan out to every
    child. Permissions are applied by the *agent* (via its `principal`), not here.
    """

    def __init__(self, envs: list[Environment]) -> None:
        self.envs = envs

    def context(self) -> str:
        return "\n\n".join(c for c in (e.context() for e in self.envs) if c)

    def tools(self) -> list[Callable[..., Any]]:
        merged: dict[str, Callable[..., Any]] = {}
        for env in self.envs:
            for fn in env.tools():
                merged[_tool_name(fn)] = fn  # later env shadows an earlier same-named tool
        return list(merged.values())

    async def setup(self) -> None:
        for env in self.envs:
            await env.setup()

    async def close(self) -> None:
        for env in self.envs:
            await env.close()

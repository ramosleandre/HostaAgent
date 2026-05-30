"""The Driver seam — the agent's *lifecycle*: how and when it's launched.

`CliDriver` runs one task per invocation (the library-level driver; the rich
`hosta` terminal app lives in `hostaagent.driver.cli`). `DaemonDriver` is
always-on; subclass and provide `events()` yielding tasks.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Any

from ..core import Agent
from ..types import AgentResult


class Driver:
    """Subclass for new lifecycles. The CLI driver covers the common case."""

    def __init__(self, agent_factory: Callable[[], Agent]) -> None:
        self.agent_factory = agent_factory


class CliDriver(Driver):
    """One task per invocation. The `hosta` command wraps this in a violet UI."""

    def run(self, task: str | None = None) -> AgentResult:
        agent = self.agent_factory()
        task = task or input("task> ")
        result = asyncio.run(agent.run(task))
        print(result.answer)
        return result


class DaemonDriver(Driver):
    """Always-on. Subclass and provide `events()` yielding tasks."""

    async def events(self) -> AsyncIterator[str]:
        raise NotImplementedError  # subclass: yield strings (tasks)
        yield ""  # pragma: no cover  (makes this an async generator)

    async def serve(self) -> None:
        # Keep strong refs so concurrent runs aren't garbage-collected mid-flight,
        # and await any in-flight runs when the event stream ends.
        tasks: set[asyncio.Task[Any]] = set()
        async for task in self.events():
            agent = self.agent_factory()
            t = asyncio.create_task(agent.run(task))
            tasks.add(t)
            t.add_done_callback(tasks.discard)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

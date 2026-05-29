"""A custom Driver — change the *lifecycle*, keep the loop.

A `DaemonDriver` that turns each line on stdin into a task (stand-in for a real
webhook / message queue). Subclass `DaemonDriver` and implement `events()` to
yield tasks; the base `serve()` runs an agent per event.

Run:  echo "list the python files" | python examples/daemon_webhook.py
"""
import asyncio
import sys
from collections.abc import AsyncIterator

from hostaagent import Agent, DaemonDriver, LocalFS


class StdinDriver(DaemonDriver):
    """Yield one task per line read from stdin (swap for HTTP/Slack/etc.)."""

    async def events(self) -> AsyncIterator[str]:
        loop = asyncio.get_running_loop()
        while True:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:  # EOF
                return
            task = line.strip()
            if task:
                yield task


def make_agent() -> Agent:
    return Agent(env=LocalFS("."))


if __name__ == "__main__":
    asyncio.run(StdinDriver(make_agent).serve())

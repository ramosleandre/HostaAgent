"""A custom Environment — change the *body*, keep the loop.

`ReadOnlyFS` is a LocalFS that drops the mutating tools (write/bash). Same brain,
safer body. Run:  hosta --agent examples/custom_env.py "what does core.py do?"
"""
from collections.abc import Callable

from hostaagent import Agent, Environment, LocalFS


class ReadOnlyFS(Environment):
    """A filesystem body that can only read and search — never write or run shell."""

    def __init__(self, root: str = "."):
        self._fs = LocalFS(root)

    def context(self) -> str:
        return f"{self._fs.context()} (read-only: no write/bash)"

    def tools(self) -> list[Callable]:
        # Reuse LocalFS's read-only tools, drop the mutating ones.
        return [t for t in self._fs.tools() if getattr(t, "__hosta_tool__", None)
                and t.__hosta_tool__.read_only]


def make_agent() -> Agent:
    agent = Agent(env=ReadOnlyFS("."))
    agent.persona = "You are a read-only code explorer. Explain, never modify."
    return agent


if __name__ == "__main__":
    from hostaagent.driver.cli import launch

    launch(make_agent())

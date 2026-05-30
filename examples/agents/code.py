"""A coding agent — reads, edits, and runs the test suite. The default `hosta` agent.

Register:  hosta add agent examples/agents/code.py
Run:       hosta --agent code "fix the failing test"
Direct:    python examples/agents/code.py
"""
from __future__ import annotations

import subprocess

from hostaagent import Agent, LocalFS, tool


@tool
def run_tests(suite: str = "all") -> str:
    "Run pytest on the project."
    target = [] if suite == "all" else [suite]
    return subprocess.run(
        ["pytest", *target], capture_output=True, text=True
    ).stdout[:3000]


class CodeAgent(Agent):
    persona = "You are a coding agent. Read before editing. Run tests after changes."

    def register_tools(self) -> None:
        self.use(run_tests)


def make_agent() -> Agent:
    return CodeAgent(env=LocalFS("."))


if __name__ == "__main__":
    from hostaagent.driver import cli
    cli.launch(make_agent)

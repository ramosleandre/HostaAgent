"""The canonical CodeAgent — a coding assistant in a dozen lines.

Run it:  hosta --agent examples/code_agent.py "summarize README.md"
or:      python examples/code_agent.py
(needs a model configured — see `hosta config`).
"""
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


# `make_agent` lets `hosta --agent examples/code_agent.py` load this agent.
def make_agent() -> Agent:
    return CodeAgent(env=LocalFS("."))


if __name__ == "__main__":
    from hostaagent.driver.cli import launch
    launch(make_agent())

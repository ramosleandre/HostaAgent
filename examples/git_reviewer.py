"""A code-review agent for your local git changes.

It reads the diff (and recent history), finds real bugs, and suggests concrete
fixes — without modifying anything. A coding agent's read-only sibling.

Run it (inside a git repo with changes):
    hosta --agent examples/git_reviewer.py "review my staged changes"
    python examples/git_reviewer.py
"""
from __future__ import annotations

import subprocess

from hostaagent import Agent, LocalFS, tool


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()[:6000] or "(empty)"


@tool(read_only=True)
def git_diff(staged: bool = False) -> str:
    "Show the git diff — unstaged by default, or staged if staged=True."
    return _git("diff", "--staged") if staged else _git("diff")


@tool(read_only=True)
def git_log(n: int = 10) -> str:
    "Show the last n commits (oneline)."
    return _git("log", f"-{n}", "--oneline")


class GitReviewer(Agent):
    persona = ("You are a senior code reviewer. Read the diff, focus on real bugs and "
               "risky changes, and give concrete, minimal fixes. Be concise; skip nits.")

    def register_tools(self) -> None:
        # Compose: read-only file access (read/grep) + git context.
        self.use(git_diff, git_log)


def make_agent() -> Agent:
    return GitReviewer(env=LocalFS("."))


if __name__ == "__main__":
    from hostaagent.driver import cli
    cli.launch(make_agent)

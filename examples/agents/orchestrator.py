"""A multi-agent orchestrator — routes to specialist sub-agents, no new core code.

The orchestrator is a pure router (empty body): its only tools are specialists
wrapped via `as_tool`, plus `spawn_subagent` for ad-hoc delegation. Each specialist
is a plain `Agent`; only their final answers come back. This is the whole
multi-agent story — composition, not framework.

Register:  hosta add agent examples/agents/orchestrator.py
Run:       hosta --agent orchestrator "summarize README.md, then list the .py files"
"""
from __future__ import annotations

import sys
from pathlib import Path

from hostaagent import Agent, Environment, LocalFS

# Import the subagent helpers from examples/tools/ (sibling example module).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.subagent import as_tool, spawn_subagent  # noqa: E402


class _Summarizer(Agent):
    persona = "You summarize text or a file's content crisply, in at most 3 bullet points."


class _FileScout(Agent):
    persona = "You explore the local files (read/grep) and answer factually. Never modify."


def make_agent() -> Agent:
    summarize = as_tool(_Summarizer(env=LocalFS(".")), "summarize",
                        "Summarize a piece of text, or a file given its path.")
    scout = as_tool(_FileScout(env=LocalFS(".")), "explore_files",
                    "Ask a read-only file question (list/inspect/grep the project).")

    orchestrator = Agent(env=Environment())  # pure router: no body tools of its own
    orchestrator.persona = (
        "You are an orchestrator. Break the task into sub-tasks and DELEGATE each to a "
        "specialist tool — `summarize`, `explore_files`, or `spawn_subagent` for anything "
        "ad-hoc. Then synthesize their answers into one final response."
    )
    orchestrator.use(summarize, scout, spawn_subagent)
    return orchestrator


if __name__ == "__main__":
    from hostaagent.driver import cli
    cli.launch(make_agent)

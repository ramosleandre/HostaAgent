"""Subagents as tools — the multi-agent primitive, with no new framework code.

An `Agent.run()` is async and HostaAgent tools may be async, so *any* agent can be
exposed as a `@tool` that an orchestrator delegates to. Two patterns:

    as_tool(agent, name, description)   wrap an existing agent as one tool
    spawn_subagent(task, persona)       spin up a fresh agent on the fly

Only the subagent's final answer returns to the parent — its own trace stays
internal (mirrors how Claude Code's AgentTool returns just the result).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from hostaagent import Agent, LocalFS, tool


def as_tool(agent: Agent, name: str, description: str) -> Callable[..., Any]:
    """Expose an existing `agent` as a single tool an orchestrator can call."""
    @tool(name=name, description=description)
    async def delegate(task: str) -> str:
        result = await agent.run(task)
        return str(result.answer)
    return delegate


@tool
async def spawn_subagent(task: str, persona: str = "You are a focused specialist.") -> str:
    "Spin up a fresh sub-agent with the given persona to handle a sub-task; returns its answer."
    sub = Agent(env=LocalFS("."))
    sub.persona = persona
    result = await sub.run(task)
    return str(result.answer)

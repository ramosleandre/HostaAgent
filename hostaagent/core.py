"""The Agent — the irreducible async ReAct loop. The whole brain is below.

Subclass to define a specific agent: set `persona`, override `register_tools()`
to add agent-specific tools, optionally override `system()` for the prompt.
Everything else (a new body, a new lifecycle) plugs in around this loop — the
loop itself does not grow.
"""
from __future__ import annotations

from collections.abc import Callable
from inspect import iscoroutinefunction
from typing import Any

from OpenHosta import config, tool_to_schema

from .environment import Environment
from .types import AgentResult, ToolUse, Turn, _ToolResult


def _tool_name(fn: Callable[..., Any]) -> str:
    """The name the model sees — the `@tool(name=...)` override, else `__name__`."""
    meta = getattr(fn, "__hosta_tool__", None)
    return meta.name if meta is not None else fn.__name__


class Agent:
    persona: str = "You are a helpful autonomous agent."
    max_steps: int = 25

    def __init__(self, *, env: Environment, model: Any = None) -> None:
        self.env = env
        self.model = model if model is not None else config.DefaultModel
        self.tools: dict[str, Callable[..., Any]] = {_tool_name(fn): fn for fn in env.tools()}
        self.register_tools()

    # ---- extension points ----
    def register_tools(self) -> None: ...  # subclass: self.use(my_tool)

    def system(self) -> str:
        return f"{self.persona}\n\n{self.env.context()}"

    def use(self, *fns: Callable[..., Any]) -> None:
        for fn in fns:
            self.tools[_tool_name(fn)] = fn

    # ---- the ReAct loop ----
    async def run(self, task: str) -> AgentResult:
        msgs: list[dict[str, Any]] = [{"role": "user", "content": task}]
        turns: list[Turn] = []
        schemas = [tool_to_schema(fn) for fn in self.tools.values()]
        for _ in range(self.max_steps):
            r = await self.model.respond(self.system(), msgs, tools=schemas)
            if not r.tool_calls:
                turns.append(Turn(r.text))
                return AgentResult(r.text or "", turns, "done")
            msgs.append({"role": "assistant", "content": r.text, "tool_calls": r.raw_calls})
            results = [await self._call(c) for c in r.tool_calls]
            turns.append(Turn(r.text, [ToolUse(c.name, c.args, x.content, x.is_error)
                                       for c, x in zip(r.tool_calls, results, strict=True)]))
            for c, x in zip(r.tool_calls, results, strict=True):
                msgs.append({"role": "tool", "tool_call_id": x.id,
                             "name": c.name, "content": x.content})
        return AgentResult("(max steps reached)", turns, "max_steps")

    async def _call(self, c: Any) -> _ToolResult:
        fn = self.tools.get(c.name)
        if fn is None:
            return _ToolResult(c.id, f"unknown tool {c.name}", is_error=True)
        try:
            res = await fn(**c.args) if iscoroutinefunction(fn) else fn(**c.args)
            return _ToolResult(c.id, str(res)[:8000])
        except Exception as e:
            return _ToolResult(c.id, f"error: {e}", is_error=True)

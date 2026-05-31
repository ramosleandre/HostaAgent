"""The Agent — the irreducible async ReAct loop. The whole brain is below.

Subclass to define a specific agent: set `persona`, override `register_tools()`
to add agent-specific tools, optionally override `system()` for the prompt.
Everything else (a new body, a new lifecycle) plugs in around this loop — the
loop itself does not grow.
"""
from __future__ import annotations

import collections.abc
from collections.abc import Callable
from inspect import iscoroutinefunction
from typing import Any, get_origin

from OpenHosta import config, tool_to_schema

from .environment import Environment
from .events import OnEvent, Token, ToolEnd, ToolStart, TurnEnd
from .permissions import Principal, visible
from .types import AgentResult, ToolUse, Turn, _ToolResult

_ITERATOR_ORIGINS = (
    collections.abc.Iterator, collections.abc.Iterable, collections.abc.Generator,
    collections.abc.AsyncIterator, collections.abc.AsyncIterable, collections.abc.AsyncGenerator,
)


def _tool_name(fn: Callable[..., Any]) -> str:
    """The name the model sees — the `@tool(name=...)` override, else `__name__`."""
    meta = getattr(fn, "__hosta_tool__", None)
    return meta.name if meta is not None else fn.__name__


def _is_iterator_type(tp: Any) -> bool:
    """A streaming type (`Iterator[T]`, `Generator[...]`, …) — rejected as `output_type`.

    OpenHosta auto-promotes such return types to generator mode, which `_format`'s
    single-value `await` cannot consume. `list`/`tuple`/`dict` are fine (not here).
    """
    return get_origin(tp) in _ITERATOR_ORIGINS


def _ignore(event: Any) -> None:  # default event sink when nobody is listening
    return None


class Agent:
    """A ReAct agent. Set `output_type` (default `str`) to get a typed answer:

    a final non-streamed pass coerces the answer text into that type, so
    `result.answer` is an instance of `output_type` *iff* `stop_reason == "done"`
    and the model produced a non-empty answer. Otherwise `answer` is the raw
    `str` (the `"(max steps reached)"` sentinel, or `""`). Check `stop_reason`
    before treating `answer` as typed. Streaming/iterator types are rejected.
    """

    persona: str = "You are a helpful autonomous agent."
    max_steps: int = 25

    def __init__(self, *, env: Environment, model: Any = None,
                 output_type: type = str, principal: Principal | None = None) -> None:
        if output_type is not str and _is_iterator_type(output_type):
            raise TypeError(
                f"output_type={output_type!r} is a streaming/iterator type; typed "
                "output formats one value, not a stream (use list[T]/tuple[T] instead)."
            )
        self.env = env
        self.model = model if model is not None else config.DefaultModel
        self.output_type = output_type
        self.principal = principal
        self.tools: dict[str, Callable[..., Any]] = {_tool_name(fn): fn for fn in env.tools()}
        self.register_tools()
        # Identity comes from the caller (driver/auth), not the body: tools the principal
        # can't see are dropped here, so the LLM is never even offered them.
        self.tools = {n: fn for n, fn in self.tools.items() if visible(fn, principal)}

    # ---- extension points ----
    def register_tools(self) -> None: ...  # subclass: self.use(my_tool)

    def system(self) -> str:
        return f"{self.persona}\n\n{self.env.context()}"

    def use(self, *fns: Callable[..., Any]) -> None:
        for fn in fns:
            self.tools[_tool_name(fn)] = fn

    # ---- the ReAct loop ----
    async def run(self, task: str, on_event: OnEvent | None = None,
                  history: list[dict[str, Any]] | None = None) -> AgentResult:
        emit = on_event if on_event is not None else _ignore
        on_token = (lambda t: emit(Token(t))) if on_event is not None else None
        msgs: list[dict[str, Any]] = [*(history or []), {"role": "user", "content": task}]
        turns: list[Turn] = []
        schemas = [tool_to_schema(fn) for fn in self.tools.values()]
        for _ in range(self.max_steps):
            r = await self.model.respond(self.system(), msgs, tools=schemas, on_token=on_token)
            if not r.tool_calls:
                turns.append(Turn(r.text))
                emit(TurnEnd(turns[-1]))
                msgs.append({"role": "assistant", "content": r.text})
                answer: Any = r.text or ""
                if self.output_type is not str and r.text:  # skip empty text (would fabricate)
                    answer = await self._format(r.text)
                return AgentResult(answer, turns, "done", msgs)
            msgs.append({"role": "assistant", "content": r.text, "tool_calls": r.raw_calls})
            results = []
            for c in r.tool_calls:
                emit(ToolStart(c.name, c.args))
                results.append(x := await self._call(c))
                emit(ToolEnd(c.name, x.content, x.is_error))
            turns.append(Turn(r.text, [ToolUse(c.name, c.args, x.content, x.is_error)
                                       for c, x in zip(r.tool_calls, results, strict=True)]))
            emit(TurnEnd(turns[-1]))
            for c, x in zip(r.tool_calls, results, strict=True):
                msgs.append({"role": "tool", "tool_call_id": x.id,
                             "name": c.name, "content": x.content})
        return AgentResult("(max steps reached)", turns, "max_steps", msgs)

    async def _format(self, text: str) -> Any:
        """Coerce the final answer text into `self.output_type` via one OpenHosta pass.

        Runs only when `output_type != str` and the run reached a real answer. It uses
        `self.model` (the same model as the loop — no split brain) and is *not* streamed.
        Overridable: tests subclass and return a fixed typed object, no live model needed.
        May raise — a parse failure raises after OpenHosta's retries, a network error
        immediately; we don't hide it.
        """
        from OpenHosta import emulate_async
        from OpenHosta.pipelines import OneTurnConversationPipeline

        pipeline = OneTurnConversationPipeline(model_list=[self.model])

        async def _formatter(answer: str) -> Any:  # plain nested fn: OpenHosta would send `self`
            "Reformat the answer as the requested return type, preserving its meaning."
            return await emulate_async(pipeline=pipeline)
        _formatter.__annotations__["return"] = self.output_type  # PEP 563-safe (set at runtime)
        assert _formatter.__annotations__["return"] is self.output_type  # guard silent str fallback
        return await _formatter(text)

    async def _call(self, c: Any) -> _ToolResult:
        fn = self.tools.get(c.name)
        if fn is None:
            return _ToolResult(c.id, f"unknown tool {c.name}", is_error=True)
        try:
            res = await fn(**c.args) if iscoroutinefunction(fn) else fn(**c.args)
            return _ToolResult(c.id, str(res)[:8000])
        except Exception as e:
            return _ToolResult(c.id, f"error: {e}", is_error=True)

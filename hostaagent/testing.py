"""hostaagent.testing — offline test utilities. No rich/CLI dependency.

`MockModel` scripts LLM responses (no API key); `fuzz_tools` hammers every tool
an agent exposes with edge-case args and verifies the safety contract — a tool
failure must come back as a result, never an unhandled crash. Both are usable in
a bare pytest environment.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from OpenHosta import ModelResponse

from .core import Agent
from .types import _ToolResult

__all__ = ["MockModel", "FuzzResult", "fuzz_tools", "assert_no_violations"]


class MockModel:
    """Script `ModelResponse`s in advance — no API key needed.

    Mirrors `OpenAICompatibleModel.respond(...)`: the loop calls `respond(...)` and
    gets the next scripted response; `.calls` records every (system, messages, tools)
    it saw. An exhausted script returns a clean stop sentinel instead of erroring.
    """

    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []  # recorded (system, messages, tools) per turn

    async def respond(self, system: str, messages: list[dict[str, Any]], *, tools: Any = None,
                      tool_choice: str = "auto", on_token: Any = None, **_: Any) -> ModelResponse:
        self.calls.append(
            {"system": system, "messages": [dict(m) for m in messages], "tools": tools})
        if not self._responses:
            return ModelResponse(text="(no more scripted responses)", tool_calls=[],
                                 raw_calls=[], finish_reason="stop")
        r = self._responses.pop(0)
        if on_token is not None and r.text:  # simulate streaming the text out
            for ch in r.text:
                on_token(ch)
        return r


@dataclass
class FuzzResult:
    """One fuzz probe: the tool, the args thrown at it, its outcome, any violation."""
    tool: str
    args: dict[str, Any]
    result: _ToolResult
    violation: str | None = None  # non-None ⇒ the "never crash the loop" contract broke


class _FakeCall:
    """A minimal stand-in for OpenHosta's `ToolCall`, the only shape `_call` reads."""

    def __init__(self, name: str, args: dict[str, Any]) -> None:
        self.id = "fuzz"
        self.name = name
        self.args = args


_FUZZ_ARGS: list[dict[str, Any]] = [
    {},                                              # missing every arg
    {"unexpected": "garbage"},                       # an arg the tool never declared
    {"path": None, "content": None, "command": None, "pattern": None},  # wrong type (None)
    {"path": 42, "content": [], "command": {}, "pattern": 3.14},        # wrong types (mixed)
    {"path": "", "content": "", "command": "", "pattern": ""},          # empty strings
    {"path": "../../../../etc/shadow"},              # path traversal probe
    {"path": "x\x00y", "command": "x\x00y"},         # embedded null byte
]


async def fuzz_tools(agent: Agent, extra_args: list[dict[str, Any]] | None = None,
                     ) -> list[FuzzResult]:
    """Throw edge-case args at every tool via `Agent._call`; return all outcomes.

    Drives only `_call` (no LLM, no loop) and asserts the safety contract: `_call`
    must always *return* a `_ToolResult` — a tool that raises is caught and reported
    as `is_error`, never escaping. A `FuzzResult.violation` is set only if that
    boundary is breached (an exception escaped, or a non-`_ToolResult` came back).
    """
    probes = _FUZZ_ARGS + (extra_args or [])
    results: list[FuzzResult] = []
    for name in agent.tools:
        for args in probes:
            try:
                r = await agent._call(_FakeCall(name, args))
                violation = None if isinstance(r, _ToolResult) else \
                    f"_call returned {type(r).__name__}, not _ToolResult"
            except Exception as e:  # the contract says this can't happen — record it if it does
                r = _ToolResult("fuzz", f"escaped: {e}", is_error=True)
                violation = f"_call raised {type(e).__name__}: {e}"
            results.append(FuzzResult(name, args, r, violation))
    return results


def assert_no_violations(results: list[FuzzResult]) -> None:
    """Raise `AssertionError` listing every safety-contract violation in `results`."""
    bad = [r for r in results if r.violation]
    if bad:
        lines = "\n".join(f"  {r.tool}({r.args!r}): {r.violation}" for r in bad)
        raise AssertionError(f"fuzz_tools found {len(bad)} safety violation(s):\n{lines}")

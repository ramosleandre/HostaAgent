"""hostaagent.testing (MockModel + fuzz_tools) and hostaagent.debug (with_trace)."""
from __future__ import annotations

import pytest
from OpenHosta import ModelResponse

from hostaagent import Agent, LocalFS, tool, with_trace
from hostaagent.events import Token, ToolStart, TurnEnd
from hostaagent.testing import FuzzResult, MockModel, assert_no_violations, fuzz_tools
from hostaagent.types import _ToolResult

# ---- MockModel -------------------------------------------------------------

async def test_mock_model_scripts_a_response(tmp_path):
    model = MockModel([ModelResponse(text="hi", tool_calls=[], raw_calls=[], finish_reason="stop")])
    r = await Agent(env=LocalFS(str(tmp_path)), model=model).run("hello")
    assert r.answer == "hi"
    assert model.calls and model.calls[0]["system"]  # the system prompt was recorded


async def test_mock_model_exhausted_returns_sentinel(tmp_path):
    r = await Agent(env=LocalFS(str(tmp_path)), model=MockModel([])).run("hello")
    assert "(no more scripted responses)" in r.answer


async def test_mock_model_simulates_streaming(tmp_path):
    model = MockModel([ModelResponse(text="abc", tool_calls=[], raw_calls=[],
                                     finish_reason="stop")])
    tokens: list[str] = []
    await Agent(env=LocalFS(str(tmp_path)), model=model).run(
        "go", on_event=lambda e: tokens.append(e.text) if isinstance(e, Token) else None)
    assert "".join(tokens) == "abc"


# ---- fuzz_tools ------------------------------------------------------------

async def test_fuzz_tools_localfs_holds_the_contract(tmp_path):
    # Real LocalFS tools, hammered with garbage args: _call must never raise.
    agent = Agent(env=LocalFS(str(tmp_path)), model=MockModel([]))
    results = await fuzz_tools(agent)
    assert results and all(isinstance(r, FuzzResult) for r in results)
    assert_no_violations(results)  # raises if any probe escaped _call


async def test_fuzz_tools_catches_a_crashing_tool(tmp_path):
    # A tool that always raises is still safe — _call turns the crash into an error result.
    @tool
    def explode(x: str = "") -> str:
        "Always raises."
        raise RuntimeError("boom")

    class BoomAgent(Agent):
        def register_tools(self) -> None:
            self.use(explode)

    agent = BoomAgent(env=LocalFS(str(tmp_path)), model=MockModel([]))
    results = await fuzz_tools(agent)
    boom = [r for r in results if r.tool == "explode"]
    assert boom and all(r.result.is_error for r in boom)
    assert all(r.violation is None for r in boom)  # caught, not escaped
    assert_no_violations(results)


def test_assert_no_violations_reports_a_breach():
    breach = FuzzResult("t", {}, _ToolResult("fuzz", "escaped: x", is_error=True),
                        violation="_call raised RuntimeError: x")
    with pytest.raises(AssertionError, match="safety violation"):
        assert_no_violations([breach])


# ---- with_trace ------------------------------------------------------------

async def test_with_trace_is_pure_and_captures_events(tmp_path):
    # No rich involved — emit into a list and assert turn boundaries were traced.
    (tmp_path / "x.txt").write_text("hi")
    from test_core import _tool_call_response  # reuse the helper
    model = MockModel([
        _tool_call_response("c1", "read", {"path": "x.txt"}, text="reading"),
        ModelResponse(text="done", tool_calls=[], raw_calls=[], finish_reason="stop"),
    ])
    lines: list[str] = []
    await Agent(env=LocalFS(str(tmp_path)), model=model).run(
        "read x.txt", on_event=with_trace(emit=lines.append))
    assert any(line.startswith("[trace] → read") for line in lines)   # tool call traced
    assert any("[trace] ←" in line for line in lines)                 # tool result traced
    assert sum("turn end" in line for line in lines) == 2             # two turns


async def test_with_trace_forwards_to_the_chained_handler(tmp_path):
    model = MockModel([ModelResponse(text="x", tool_calls=[], raw_calls=[], finish_reason="stop")])
    seen: list = []
    traced = with_trace(handler=seen.append, emit=lambda _: None)
    await Agent(env=LocalFS(str(tmp_path)), model=model).run("q", on_event=traced)
    assert any(isinstance(e, TurnEnd) for e in seen)  # original handler still ran
    assert any(isinstance(e, (ToolStart, TurnEnd, Token)) for e in seen)

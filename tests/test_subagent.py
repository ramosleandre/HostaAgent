"""Multi-agent via composition: an Agent wrapped as a tool (the examples/tools helper)."""
import sys
from pathlib import Path

from mockmodel import MockModel
from OpenHosta import ModelResponse, ToolCall

from hostaagent import Agent, Environment, LocalFS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))


async def test_subagent_as_tool_delegates_and_returns_answer(tmp_path):
    from tools.subagent import as_tool

    # the specialist answers in one turn
    specialist = Agent(env=LocalFS(str(tmp_path)), model=MockModel([
        ModelResponse(text="specialist says hi", tool_calls=[], raw_calls=[], finish_reason="stop"),
    ]))
    delegate = as_tool(specialist, "ask_specialist", "Delegate to the specialist.")

    # the orchestrator calls that tool, then answers
    raw = [{"id": "c1", "type": "function",
            "function": {"name": "ask_specialist", "arguments": "{}"}}]
    call = ToolCall("c1", "ask_specialist", {"task": "x"})
    orch = Agent(env=Environment(), model=MockModel([
        ModelResponse(text="delegating", tool_calls=[call], raw_calls=raw,
                      finish_reason="tool_calls"),
        ModelResponse(text="final answer", tool_calls=[], raw_calls=[], finish_reason="stop"),
    ]))
    orch.use(delegate)

    assert "ask_specialist" in orch.tools          # keyed by the tool's name
    r = await orch.run("delegate please")
    assert r.tools_used == ["ask_specialist"]
    assert r.turns[0].tools[0].result == "specialist says hi"  # subagent's answer flowed back
    assert r.answer == "final answer"


def test_orchestrator_example_loads():
    from hostaagent.driver.cli.app import _load_agent
    cfg = {"model": {"name": "m", "base_url": "http://localhost:11434/v1", "api_key": "k"}}
    agent = _load_agent(Path("examples/agents/orchestrator.py"), cfg)
    assert {"summarize", "explore_files", "spawn_subagent"}.issubset(agent.tools)

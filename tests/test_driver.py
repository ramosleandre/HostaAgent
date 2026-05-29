"""Drivers: CliDriver (one task per invocation) and DaemonDriver (events loop)."""
import asyncio

import pytest
from mockmodel import MockModel
from OpenHosta import ModelResponse

from hostaagent import Agent, CliDriver, DaemonDriver, LocalFS


def _answer_model(text):
    return MockModel([ModelResponse(text=text, tool_calls=[], raw_calls=[], finish_reason="stop")])


def test_cli_driver_runs_explicit_task(tmp_path, capsys):
    def factory():
        return Agent(env=LocalFS(str(tmp_path)), model=_answer_model("the answer"))

    result = CliDriver(factory).run("do a thing")
    assert result.answer == "the answer"
    assert "the answer" in capsys.readouterr().out


def test_cli_driver_prompts_when_no_task(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "typed task")

    def factory():
        return Agent(env=LocalFS(str(tmp_path)), model=_answer_model("done"))

    result = CliDriver(factory).run()
    assert result.answer == "done"


def test_daemon_driver_runs_agent_per_event(tmp_path):
    seen = []

    class FakeAgent(Agent):
        async def run(self, task):  # type: ignore[override]
            seen.append(task)
            return None

    class TwoEvents(DaemonDriver):
        async def events(self):
            yield "task-1"
            yield "task-2"

    def factory():
        return FakeAgent(env=LocalFS(str(tmp_path)), model=_answer_model("x"))

    driver = TwoEvents(factory)

    async def go():
        await driver.serve()
        await asyncio.sleep(0)  # let the create_task'd agent runs settle

    asyncio.run(go())
    assert seen == ["task-1", "task-2"]


def test_daemon_events_not_implemented_by_default(tmp_path):
    def factory():
        return Agent(env=LocalFS(str(tmp_path)), model=_answer_model("x"))

    async def go():
        async for _ in DaemonDriver(factory).events():
            pass

    with pytest.raises(NotImplementedError):
        asyncio.run(go())

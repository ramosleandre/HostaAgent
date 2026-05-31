"""MultiEnv composition: context join, tool union, collisions, lifecycle, agent wiring."""
from __future__ import annotations

from hostaagent import Agent, MockModel, MultiEnv, tool
from hostaagent.environment import Environment


def _env(name: str, ctx: str, *tools):
    e = Environment()
    e.context = lambda: ctx          # type: ignore[method-assign]
    e.tools = lambda: list(tools)    # type: ignore[method-assign]
    e._name = name                   # type: ignore[attr-defined]
    return e


@tool
def alpha() -> str:
    "A."
    return "a"


@tool
def beta() -> str:
    "B."
    return "b"


def test_context_joins_non_empty():
    env = MultiEnv([_env("1", "first"), _env("2", ""), _env("3", "third")])
    assert env.context() == "first\n\nthird"   # empty context dropped


def test_tools_are_unioned():
    env = MultiEnv([_env("1", "", alpha), _env("2", "", beta)])
    assert {t.__hosta_tool__.name for t in env.tools()} == {"alpha", "beta"}


def test_last_env_wins_on_name_collision():
    @tool(name="dup")
    def first() -> str:
        "first"
        return "first"

    @tool(name="dup")
    def second() -> str:
        "second"
        return "second"

    env = MultiEnv([_env("1", "", first), _env("2", "", second)])
    tools = env.tools()
    assert len(tools) == 1 and tools[0]() == "second"  # rightmost shadows


async def test_setup_and_close_fan_out():
    calls: list[str] = []

    class Tracked(Environment):
        def __init__(self, tag): self.tag = tag
        async def setup(self): calls.append(f"setup:{self.tag}")
        async def close(self): calls.append(f"close:{self.tag}")

    env = MultiEnv([Tracked("a"), Tracked("b")])
    await env.setup()
    await env.close()
    assert calls == ["setup:a", "setup:b", "close:a", "close:b"]


async def test_multienv_drives_an_agent(tmp_path):
    env = MultiEnv([_env("1", "ctx-one", alpha), _env("2", "ctx-two", beta)])
    agent = Agent(env=env, model=MockModel([]))
    assert set(agent.tools) == {"alpha", "beta"}
    assert "ctx-one" in agent.system() and "ctx-two" in agent.system()

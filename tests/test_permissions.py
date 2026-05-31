"""Tag-based permissions: @tool(requires=...), Principal, visible, and agent filtering."""
from __future__ import annotations

from dataclasses import FrozenInstanceError

from hostaagent import Agent, MockModel, Principal, tool
from hostaagent.environment import Environment
from hostaagent.permissions import visible


@tool
def public_tool() -> str:
    "Anyone can see this."
    return "ok"


@tool(requires=["admin"])
def admin_tool() -> str:
    "Only admins can see this."
    return "danger"


def test_public_tool_visible_to_everyone():
    assert visible(public_tool, None) is True
    assert visible(public_tool, Principal({"user"})) is True


def test_tagged_tool_hidden_from_none_and_partial():
    assert visible(admin_tool, None) is False
    assert visible(admin_tool, Principal({"user"})) is False


def test_tagged_tool_visible_to_matching_principal():
    assert visible(admin_tool, Principal({"admin", "user"})) is True


@tool(requires=["admin", "write"])
def two_tag_tool() -> str:
    "Needs both."
    return "x"


def test_all_tags_required():
    assert visible(two_tag_tool, Principal({"admin"})) is False           # missing "write"
    assert visible(two_tag_tool, Principal({"admin", "write"})) is True


def test_requires_is_stored_on_tool_meta():
    assert admin_tool.__hosta_tool__.requires == frozenset({"admin"})     # on the @tool meta
    assert public_tool.__hosta_tool__.requires == frozenset()             # public by default


def test_principal_normalizes_and_is_frozen():
    import pytest
    p = Principal({"a", "b"})           # a plain set
    assert p.tags == frozenset({"a", "b"}) and isinstance(p.tags, frozenset)
    assert Principal.of("x", "y").tags == frozenset({"x", "y"})
    with pytest.raises(FrozenInstanceError):  # frozen dataclass — cannot reassign
        p.tags = frozenset()             # type: ignore[misc]


class _TwoToolEnv(Environment):
    def tools(self):
        return [public_tool, admin_tool]


def test_agent_filters_tools_by_principal(tmp_path):
    # The AGENT holds identity now: a non-admin agent simply never has admin_tool.
    agent = Agent(env=_TwoToolEnv(), model=MockModel([]), principal=Principal({"user"}))
    assert set(agent.tools) == {"public_tool"}


def test_agent_admin_principal_sees_all(tmp_path):
    agent = Agent(env=_TwoToolEnv(), model=MockModel([]), principal=Principal.of("admin"))
    assert set(agent.tools) == {"public_tool", "admin_tool"}


def test_agent_no_principal_sees_only_public(tmp_path):
    agent = Agent(env=_TwoToolEnv(), model=MockModel([]))  # principal=None (default)
    assert set(agent.tools) == {"public_tool"}


def test_principal_also_filters_use_registered_tools(tmp_path):
    # Tools added via register_tools()/use() are filtered too (filter runs after register).
    class AdminAgent(Agent):
        def register_tools(self) -> None:
            self.use(admin_tool)

    blocked = AdminAgent(env=Environment(), model=MockModel([]), principal=Principal({"user"}))
    assert "admin_tool" not in blocked.tools
    allowed = AdminAgent(env=Environment(), model=MockModel([]), principal=Principal.of("admin"))
    assert "admin_tool" in allowed.tools


async def test_denied_tool_never_reaches_the_loop(tmp_path):
    # End-to-end: a non-admin agent's tool table has no admin_tool → the LLM can't call it.
    agent = Agent(env=_TwoToolEnv(), model=MockModel([]), principal=Principal({"user"}))
    assert "admin_tool" not in agent.tools and "public_tool" in agent.tools

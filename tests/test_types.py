"""The output model: AgentResult.tools_used, str(), Turn/ToolUse shape."""
from hostaagent import AgentResult, ToolUse, Turn


def test_str_is_the_answer():
    assert str(AgentResult(answer="hello")) == "hello"
    assert str(AgentResult(answer=42)) == "42"


def test_tools_used_flattens_turns():
    turns = [
        Turn(text="t1", tools=[ToolUse("read", {"path": "a"}, "...")]),
        Turn(text="t2", tools=[ToolUse("grep", {"pattern": "x"}, "..."),
                               ToolUse("write", {"path": "b"}, "ok")]),
        Turn(text="final", tools=[]),
    ]
    result = AgentResult(answer="final", turns=turns)
    assert result.tools_used == ["read", "grep", "write"]


def test_defaults():
    r = AgentResult(answer="x")
    assert r.turns == []
    assert r.stop_reason == "done"
    assert r.tools_used == []


def test_tooluse_fields():
    tu = ToolUse(name="bash", args={"command": "ls"}, result="files", is_error=False)
    assert tu.name == "bash"
    assert tu.args == {"command": "ls"}
    assert tu.is_error is False

"""The ReAct loop, driven entirely by a scripted MockModel."""
from mockmodel import MockModel
from OpenHosta import ModelResponse, ToolCall

from hostaagent import Agent, LocalFS


def _tool_call_response(cid, name, args, text="working"):
    raw = [{"id": cid, "type": "function",
            "function": {"name": name, "arguments": str(args)}}]
    return ModelResponse(text=text, tool_calls=[ToolCall(cid, name, args)],
                         raw_calls=raw, finish_reason="tool_calls")


async def test_simple_tool_loop(tmp_path):
    (tmp_path / "x.txt").write_text("hello")
    model = MockModel([
        _tool_call_response("c1", "read", {"path": "x.txt"}, text="reading"),
        ModelResponse(text="the file says hello", tool_calls=[], raw_calls=[],
                      finish_reason="stop"),
    ])
    agent = Agent(env=LocalFS(str(tmp_path)), model=model)
    r = await agent.run("read x.txt and tell me")
    assert "hello" in r.answer
    assert r.tools_used == ["read"]
    assert r.stop_reason == "done"


async def test_no_tools_immediate_answer(tmp_path):
    model = MockModel([ModelResponse(text="42", tool_calls=[], raw_calls=[], finish_reason="stop")])
    agent = Agent(env=LocalFS(str(tmp_path)), model=model)
    r = await agent.run("what is the answer?")
    assert r.answer == "42"
    assert r.tools_used == []
    assert len(r.turns) == 1


async def test_tool_result_fed_back(tmp_path):
    (tmp_path / "x.txt").write_text("secret-value")
    model = MockModel([
        _tool_call_response("c1", "read", {"path": "x.txt"}),
        ModelResponse(text="done", tool_calls=[], raw_calls=[], finish_reason="stop"),
    ])
    agent = Agent(env=LocalFS(str(tmp_path)), model=model)
    await agent.run("read it")
    # The second turn must have seen the tool result fed back as a `tool` message.
    second_call_msgs = model.calls[1]["messages"]
    tool_msgs = [m for m in second_call_msgs if m.get("role") == "tool"]
    assert tool_msgs and "secret-value" in tool_msgs[0]["content"]


async def test_unknown_tool_is_reported(tmp_path):
    model = MockModel([
        _tool_call_response("c1", "does_not_exist", {}),
        ModelResponse(text="ok", tool_calls=[], raw_calls=[], finish_reason="stop"),
    ])
    agent = Agent(env=LocalFS(str(tmp_path)), model=model)
    r = await agent.run("call a bogus tool")
    assert r.turns[0].tools[0].is_error
    assert "unknown tool" in r.turns[0].tools[0].result


async def test_tool_exception_becomes_error_result(tmp_path):
    model = MockModel([
        _tool_call_response("c1", "read", {"path": "missing.txt"}),
        ModelResponse(text="handled", tool_calls=[], raw_calls=[], finish_reason="stop"),
    ])
    agent = Agent(env=LocalFS(str(tmp_path)), model=model)
    r = await agent.run("read a missing file")
    tu = r.turns[0].tools[0]
    assert tu.is_error and tu.result.startswith("error:")


async def test_max_steps(tmp_path):
    # Always returns a tool call -> never terminates on its own.
    looping = [_tool_call_response(f"c{i}", "read", {"path": "x.txt"}) for i in range(50)]
    (tmp_path / "x.txt").write_text("hi")
    agent = Agent(env=LocalFS(str(tmp_path)), model=MockModel(looping))
    agent.max_steps = 3
    r = await agent.run("loop forever")
    assert r.stop_reason == "max_steps"
    assert len(r.turns) == 3


async def test_register_tools_and_use(tmp_path):
    from hostaagent import tool

    @tool
    def ping() -> str:
        "Return pong."
        return "pong"

    class PingAgent(Agent):
        def register_tools(self) -> None:
            self.use(ping)

    model = MockModel([
        _tool_call_response("c1", "ping", {}),
        ModelResponse(text="got pong", tool_calls=[], raw_calls=[], finish_reason="stop"),
    ])
    agent = PingAgent(env=LocalFS(str(tmp_path)), model=model)
    assert "ping" in agent.tools
    r = await agent.run("ping it")
    assert r.tools_used == ["ping"]
    assert r.turns[0].tools[0].result == "pong"


async def test_custom_tool_name_is_resolvable(tmp_path):
    # A @tool(name="...") override must be the key the model calls by, otherwise
    # the loop would report "unknown tool".
    from hostaagent import tool

    @tool(name="do_ping")
    def ping_impl() -> str:
        "Return pong."
        return "pong"

    class PingAgent(Agent):
        def register_tools(self) -> None:
            self.use(ping_impl)

    agent = PingAgent(env=LocalFS(str(tmp_path)), model=MockModel([]))
    assert "do_ping" in agent.tools          # keyed by the custom name, not __name__
    assert "ping_impl" not in agent.tools
    model = MockModel([
        _tool_call_response("c1", "do_ping", {}),
        ModelResponse(text="ok", tool_calls=[], raw_calls=[], finish_reason="stop"),
    ])
    agent.model = model
    r = await agent.run("call it by its tool name")
    assert r.tools_used == ["do_ping"]
    assert not r.turns[0].tools[0].is_error
    assert r.turns[0].tools[0].result == "pong"


async def test_tool_message_includes_name(tmp_path):
    # OpenAI-compatible tool-role messages should carry the tool name.
    (tmp_path / "x.txt").write_text("hi")
    model = MockModel([
        _tool_call_response("c1", "read", {"path": "x.txt"}),
        ModelResponse(text="done", tool_calls=[], raw_calls=[], finish_reason="stop"),
    ])
    agent = Agent(env=LocalFS(str(tmp_path)), model=model)
    await agent.run("read it")
    tool_msgs = [m for m in model.calls[1]["messages"] if m.get("role") == "tool"]
    assert tool_msgs and tool_msgs[0]["name"] == "read"
    assert tool_msgs[0]["tool_call_id"] == "c1"

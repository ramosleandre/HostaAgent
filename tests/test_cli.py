"""CLI rendering: it must not crash on tool output that contains rich markup."""
from mockmodel import MockModel
from OpenHosta import ModelResponse, ToolCall

import hostaagent.cli as cli
from hostaagent import Agent, LocalFS


def _loop_with_tool(args, result_text):
    """A 2-turn script: call `read` with `args`, then answer `result_text`."""
    raw = [{"id": "c1", "type": "function",
            "function": {"name": "read", "arguments": "{}"}}]
    return MockModel([
        ModelResponse(text="thinking [bold]hard[/bold]", tool_calls=[ToolCall("c1", "read", args)],
                      raw_calls=raw, finish_reason="tool_calls"),
        ModelResponse(text=result_text, tool_calls=[], raw_calls=[], finish_reason="stop"),
    ])


def test_render_survives_markup_in_args_and_text(tmp_path, capsys):
    # Tool arg value (and the final answer) contain rich-markup-looking strings.
    # The read fails (missing file) -> the error result also carries the markup-y
    # path, exercising the escaped error-rendering path too.
    bad_arg = "weird[/tool.arg]name"
    answer = "answer with [unclosed and [/result] tags"
    agent = Agent(env=LocalFS(str(tmp_path)), model=_loop_with_tool({"path": bad_arg}, answer))
    cli._run_one(agent, "render [bold]this[/bold]")  # must not raise MarkupError
    out = capsys.readouterr().out
    assert "render" in out
    assert "answer with" in out


def test_violet_theme_styles_are_valid():
    # Every style in the theme must be parseable, else console.print crashes at runtime.
    from rich.console import Console
    from rich.style import Style

    from hostaagent.theme import VIOLET

    console = Console(theme=VIOLET)
    for name in ("primary", "accent", "muted", "tool", "tool.arg", "result", "ok", "warn", "err"):
        resolved = console.get_style(name)
        assert isinstance(resolved, Style)


def test_render_tool_result_with_markup(tmp_path, capsys):
    # The tool's *result* contains markup-like content (e.g. a file with brackets).
    (tmp_path / "f.txt").write_text("array[0] and [/x] markup")
    model = _loop_with_tool({"path": "f.txt"}, "done")
    agent = Agent(env=LocalFS(str(tmp_path)), model=model)
    cli._run_one(agent, "read f.txt")  # must not raise
    assert "done" in capsys.readouterr().out

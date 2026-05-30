"""CLI rendering: condensed, escape-safe, message-before-status, no duplication."""
from mockmodel import MockModel
from OpenHosta import ModelResponse, ToolCall
from rich.console import Console

from hostaagent import Agent, LocalFS
from hostaagent.driver.cli import render
from hostaagent.driver.cli.repl import run_one
from hostaagent.driver.cli.theme import VIOLET


def _console():
    # record output to a buffer instead of the terminal
    return Console(theme=VIOLET, force_terminal=False, width=100, record=True)


def _loop_with_tool(args, result_text):
    raw = [{"id": "c1", "type": "function", "function": {"name": "read", "arguments": "{}"}}]
    return MockModel([
        ModelResponse(text="thinking [bold]hard[/bold]", tool_calls=[ToolCall("c1", "read", args)],
                      raw_calls=raw, finish_reason="tool_calls"),
        ModelResponse(text=result_text, tool_calls=[], raw_calls=[], finish_reason="stop"),
    ])


def test_condense_shortens_paths_and_long_values():
    assert render._condense("/Users/me/Desktop/work/proj/README.md").endswith("README.md")
    assert "Users" not in render._condense("/Users/me/Desktop/work/proj/README.md")
    assert render._condense("x" * 100).endswith("…")
    assert render._condense("short.txt") == "short.txt"


def test_render_message_then_status_no_duplicate(tmp_path):
    # A plain "bonjour" answer: rendered once, with status AFTER it, 0 tools.
    model = MockModel([ModelResponse(text="Bonjour ! 👋", tool_calls=[], raw_calls=[],
                                     finish_reason="stop")])
    agent = Agent(env=LocalFS(str(tmp_path)), model=model)
    console = _console()
    run_one(console, agent, "bonjour")
    out = console.export_text()
    assert out.count("Bonjour ! 👋") == 1            # not duplicated
    assert "0 tools" in out
    # the answer comes before the status line
    assert out.index("Bonjour") < out.index("done")


def test_render_condenses_tool_and_survives_markup(tmp_path, capsys):
    # read fails (missing file) -> error result carries the markup-y path; arg + answer
    # both contain rich-markup-looking strings. Must not crash; paths condensed.
    bad = "deep/nested/dir/weird[/x]name.txt"
    model = _loop_with_tool({"path": bad}, "ans [/result] z")
    agent = Agent(env=LocalFS(str(tmp_path)), model=model)
    console = _console()
    run_one(console, agent, "read [bold]it[/bold]")
    out = console.export_text()
    assert "ans" in out and "read" in out
    assert "/Users" not in out  # no absolute paths leaked into the trace


def test_violet_theme_styles_are_valid():
    from rich.style import Style
    console = Console(theme=VIOLET)
    for name in ("primary", "accent", "muted", "tool", "tool.arg", "result", "ok", "warn", "err"):
        assert isinstance(console.get_style(name), Style)


def test_run_one_handles_model_errors_gracefully(tmp_path):
    # A model that raises must not crash the CLI: run_one returns None + styled error.
    class BoomModel:
        async def respond(self, *a, **k):
            raise RuntimeError("boom: bad api key")

    agent = Agent(env=LocalFS(str(tmp_path)), model=BoomModel())
    console = _console()
    result = run_one(console, agent, "do a thing")
    assert result is None
    out = console.export_text()
    assert "RuntimeError" in out and "boom" in out


def test_condense_never_returns_empty():
    assert render._condense("/" * 30) != ""
    assert render._condense("") == ""  # empty in -> empty out is fine; only paths must not vanish


def test_import_hostaagent_does_not_load_cli_deps():
    import os
    import subprocess
    import sys
    # In a fresh interpreter, importing the library must not import prompt_toolkit.
    code = "import hostaagent, sys; assert 'prompt_toolkit' not in sys.modules; print('ok')"
    env = {**os.environ, "OPENHOSTA_SILENCE_ENV_WARNING": "1"}
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert "ok" in r.stdout, r.stderr


def test_default_agent_honors_configured_path(tmp_path):
    from hostaagent.driver.cli import app

    agent_file = tmp_path / "my_agent.py"
    agent_file.write_text(
        "from hostaagent import Agent, LocalFS\n"
        "def make_agent():\n"
        "    a = Agent(env=LocalFS('.'))\n"
        "    a.persona = 'custom default'\n"
        "    return a\n"
    )
    cfg = {"model": {"name": "m", "base_url": "http://localhost:11434/v1", "api_key": "k"},
           "agent": {"path": str(agent_file)}}
    agent = app._default_agent(cfg)
    assert agent.persona == "custom default"

    # no agent.path -> the built-in code agent
    cfg2 = {"model": cfg["model"], "agent": {"path": ""}}
    assert app._default_agent(cfg2).persona == "You are a helpful autonomous agent."


def test_set_default_model_applies_to_new_agents():
    # The configured model becomes OpenHosta's default, so any Agent built without an
    # explicit model uses it (the bug where examples fell back to OpenAI).
    from OpenHosta import config as ohc

    from hostaagent.config import set_default_model
    m = ohc.DefaultModel
    orig_name, orig_url = m.model_name, m.base_url
    try:
        set_default_model({"model": {"name": "qwen3.5:9b",
                                     "base_url": "http://localhost:11434/v1", "api_key": ""}})
        agent = Agent(env=LocalFS("."))
        assert agent.model.model_name == "qwen3.5:9b"
        assert "11434" in agent.model.base_url
    finally:
        m.model_name, m.base_url = orig_name, orig_url


def test_default_agent_resolves_registered_name(tmp_path, monkeypatch):
    from hostaagent.driver.cli import app
    af = tmp_path / "ag.py"
    af.write_text("from hostaagent import Agent, LocalFS\n"
                  "def make_agent():\n    a = Agent(env=LocalFS('.'))\n"
                  "    a.persona = 'registered'\n    return a\n")
    # default points at a registered NAME; stub the registry lookup
    monkeypatch.setattr(app, "resolve_agent", lambda ref: str(af) if ref == "mine" else None)
    cfg = {"model": {"name": "m", "base_url": "http://localhost:11434/v1", "api_key": "k"},
           "agent": {"default": "mine", "path": ""}}
    assert app._default_agent(cfg).persona == "registered"


def test_main_unknown_agent_errors_cleanly(monkeypatch):
    import pytest
    from rich.console import Console

    from hostaagent.driver.cli import app
    from hostaagent.driver.cli.theme import VIOLET
    rec = Console(theme=VIOLET, record=True, force_terminal=False)
    monkeypatch.setattr(app, "console", rec)
    monkeypatch.setattr(app, "load_config",
                        lambda: {"model": {"name": "m", "base_url": "x", "api_key": ""}})
    monkeypatch.setattr(app, "set_default_model", lambda cfg: None)
    with pytest.raises(SystemExit) as exc:
        app.main(["--agent", "nope", "do a thing"])
    assert exc.value.code == 1
    lines = [ln.strip() for ln in rec.export_text().splitlines()]
    assert any("unknown agent" in ln for ln in lines)
    assert "1" not in lines  # regression: the SystemExit code must not be printed as output


def test_validate_agent_file(tmp_path):
    from hostaagent.driver.cli import app
    cfg = {"model": {"name": "m", "base_url": "http://localhost:11434/v1", "api_key": "k"}}

    good = tmp_path / "ag.py"
    good.write_text("from hostaagent import Agent, LocalFS\n"
                    "def make_agent():\n    return Agent(env=LocalFS('.'))\n")
    assert app._validate_agent_file(str(good), cfg) is None

    bad = tmp_path / "notagent.py"   # valid python, but no agent in it
    bad.write_text("x = 1\n")
    assert app._validate_agent_file(str(bad), cfg) is not None

    assert app._validate_agent_file(str(tmp_path / "missing.py"), cfg) is not None


def test_slash_completer_suggests_commands():
    from prompt_toolkit.document import Document

    from hostaagent.driver.cli.repl import _SlashCompleter
    comps = list(_SlashCompleter().get_completions(Document("/mo"), None))
    assert any(c.text == "/model" for c in comps)
    # non-slash input yields nothing
    assert list(_SlashCompleter().get_completions(Document("hello"), None)) == []

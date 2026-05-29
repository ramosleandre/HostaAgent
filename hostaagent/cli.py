"""The ``hosta`` command — the CliDriver in violet.

No business logic lives here, only display + IO: build an agent, run a task (or a
REPL), and render the trace with the violet theme. Streaming is deferred (see
blueprint 08_FUTURE), so the trace is rendered from ``AgentResult.turns`` once a
run completes.
"""
from __future__ import annotations

import argparse
import asyncio
import runpy
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from .config import build_model, load_config, run_config_wizard
from .core import Agent
from .environment import LocalFS
from .theme import VIOLET

console = Console(theme=VIOLET)


def _default_agent(cfg: dict[str, Any]) -> Agent:
    return Agent(env=LocalFS("."), model=build_model(cfg))


def _load_agent(path: Path, cfg: dict[str, Any]) -> Agent:
    """Load a custom agent from a Python file.

    The file may expose: a module-level ``agent`` (an Agent instance), a
    ``make_agent()`` / ``build()`` factory, or an ``Agent`` subclass (which we
    instantiate with ``LocalFS('.')`` and the configured model).
    """
    ns = runpy.run_path(str(path))
    candidate = ns.get("agent")
    if isinstance(candidate, Agent):
        return candidate
    for factory in ("make_agent", "build"):
        fn = ns.get(factory)
        if callable(fn):
            built = fn()
            if isinstance(built, Agent):
                return built
    for value in ns.values():
        if isinstance(value, type) and issubclass(value, Agent) and value is not Agent:
            return value(env=LocalFS("."), model=build_model(cfg))
    raise SystemExit(f"[err] No Agent, make_agent(), or build() found in {path}")


def _render_result(result: Any) -> None:
    # Tool args/results and model text are untrusted — escape before embedding in
    # rich markup so a value like "[bold]" or "[/x]" can't break or hijack rendering.
    for turn in result.turns:
        if turn.text and turn.text.strip():
            console.print("\n→ thinking…", style="accent")
            console.print(f"  {escape(turn.text.strip())}", style="muted")
        for tu in turn.tools:
            args = "  ".join(f"[tool.arg]{escape(str(k))}={escape(repr(v))}[/tool.arg]"
                             for k, v in tu.args.items())
            console.print(f"  [tool]⚙ {escape(tu.name)}[/tool]  {args}")
            line = (tu.result or "").strip().splitlines()
            preview = escape(line[0][:120]) if line else ""
            style = "err" if tu.is_error else "result"
            console.print(f"    [{style}]← {preview}[/{style}]")
    mark, style = ("✓", "ok") if result.stop_reason == "done" else ("⚠", "warn")
    n_tools, n_turns = len(result.tools_used), len(result.turns)
    console.print(f"\n[{style}]{mark} {result.stop_reason}[/{style}] · "
                  f"{n_tools} tools used · {n_turns} turns\n")


def _run_one(agent: Agent, task: str) -> None:
    console.print(Panel(f"task: {escape(task)}", title="HostaAgent · code-agent",
                        border_style="primary", expand=False))
    with console.status("[accent]thinking…[/accent]", spinner="dots"):
        result = asyncio.run(agent.run(task))
    _render_result(result)
    console.print(escape(str(result.answer)), style="result")


_HELP = """[primary]slash commands[/primary]
  /model <name>   switch model for the session
  /tools          list available tools
  /clear          reset the session
  /help           this help
  /exit           quit (or Ctrl-D)"""


def _repl(agent: Agent, cfg: dict[str, Any]) -> None:
    console.print(Panel("Interactive session — type a task, or /help",
                        title="HostaAgent", border_style="primary", expand=False))
    while True:
        try:
            line = console.input("[primary]hosta>[/primary] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[muted]bye[/muted]")
            return
        if not line:
            continue
        if line.startswith("/"):
            cmd, _, arg = line[1:].partition(" ")
            if cmd in ("exit", "quit"):
                return
            if cmd == "help":
                console.print(_HELP)
            elif cmd == "tools":
                console.print("  ".join(f"[tool]{escape(n)}[/tool]" for n in agent.tools))
            elif cmd == "model":
                if arg.strip():
                    cfg["model"]["name"] = arg.strip()
                    agent.model = build_model(cfg)
                    console.print(f"[ok]model → {escape(arg.strip())}[/ok]")
                else:
                    console.print(f"[muted]current model: {escape(cfg['model']['name'])}[/muted]")
            elif cmd == "clear":
                console.print("[muted]session cleared[/muted]")
            else:
                console.print(f"[warn]unknown command: /{escape(cmd)}[/warn]")
            continue
        _run_one(agent, line)


def main(argv: list[str] | None = None) -> None:
    raw = list(sys.argv[1:] if argv is None else argv)

    # `hosta config` / `hosta config show` — handled before argparse.
    if raw and raw[0] == "config":
        if len(raw) > 1 and raw[1] == "show":
            cfg = load_config()
            console.print(cfg or "[warn]no config yet — run `hosta config`[/warn]")
        else:
            run_config_wizard()
        return

    parser = argparse.ArgumentParser(
        prog="hosta", description="Claude Code in 50 lines you can fork.")
    parser.add_argument("task", nargs="?", help="task to run (omit for an interactive session)")
    parser.add_argument("-a", "--agent", type=Path, help="load a custom agent from a Python file")
    parser.add_argument("-m", "--model", help="override the model name")
    args = parser.parse_args(raw)

    cfg = load_config() or run_config_wizard()
    if args.model:
        cfg["model"]["name"] = args.model

    try:
        agent = _load_agent(args.agent, cfg) if args.agent else _default_agent(cfg)
    except SystemExit as e:
        console.print(str(e), style="err")
        sys.exit(1)

    if args.task:
        _run_one(agent, args.task)
    else:
        _repl(agent, cfg)


if __name__ == "__main__":
    main()

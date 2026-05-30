"""The ``hosta`` command — argument parsing + dispatch.

No business logic lives here, only wiring: resolve config (launching the wizard on
first run), wire the configured model in, then run a task or open the REPL.
`launch()` is the same machinery exposed for an example's ``__main__`` block.
"""
from __future__ import annotations

import argparse
import runpy
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markup import escape

from ...config import (
    add_agent,
    list_agents,
    load_config,
    remove_agent,
    resolve_agent,
    set_default_model,
    set_value,
)
from ...core import Agent
from ...environment import LocalFS
from .repl import run_one, run_repl
from .theme import VIOLET
from .wizard import run_config_wizard

console = Console(theme=VIOLET)


# ---- loading agents ----

def _default_agent(cfg: dict[str, Any]) -> Agent:
    # Honor a configured default agent (a registered name or a path); otherwise the
    # built-in code agent rooted at the current directory.
    agent_cfg = cfg.get("agent") or {}
    ref = agent_cfg.get("default") or agent_cfg.get("path") or ""
    resolved = resolve_agent(ref) if ref else None
    if resolved and Path(resolved).exists():
        return _load_agent(Path(resolved), cfg)
    return Agent(env=LocalFS("."))


def _load_agent(path: Path, cfg: dict[str, Any]) -> Agent:
    """Load a custom agent from a Python file: an ``agent`` instance, a
    ``make_agent()`` / ``build()`` factory, or an ``Agent`` subclass."""
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
            return value(env=LocalFS("."))
    raise SystemExit(f"No Agent, make_agent(), or build() found in {path}")


def _validate_agent_file(path_str: str, cfg: dict[str, Any]) -> str | None:
    """Return a human-readable problem if `path_str` isn't a loadable agent, else None."""
    p = Path(path_str).expanduser()
    if not p.exists():
        return f"no such file: {path_str}"
    try:
        _load_agent(p, cfg)
    except SystemExit as e:
        return str(e)
    except Exception as e:
        return f"could not load agent from {path_str}: {type(e).__name__}: {e}"
    return None


def launch(agent: Agent | Callable[[], Agent], task: str | None = None) -> None:
    """Run an agent in the violet `hosta` UI — for an example's ``__main__`` block.

    Accepts an `Agent` or a `make_agent` factory. Resolves config (wizard on first
    run), wires it into the default model, then runs a one-shot task (from `task` or
    argv) or the interactive REPL.
    """
    cfg = load_config() or run_config_wizard()
    set_default_model(cfg)  # any Agent built without an explicit model now uses this
    resolved: Agent = agent() if callable(agent) and not isinstance(agent, Agent) else agent
    if task is None and len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    if task:
        if run_one(console, resolved, task) is None:
            sys.exit(1)
    else:
        run_repl(console, resolved, cfg)


# ---- verbs ----

def _handle_config(raw: list[str]) -> None:
    sub = raw[1] if len(raw) > 1 else ""
    if sub == "show":
        cfg = load_config()
        console.print(cfg or "[warn]no config yet — run [tool]hosta config[/tool][/warn]")
    elif sub == "set":
        if len(raw) < 4:
            console.print("[err]usage: hosta config set <section.key> <value>[/err] "
                          "[muted](e.g. model.name gpt-4o)[/muted]")
            sys.exit(1)
        key, value = raw[2], raw[3]
        if key == "agent.path" and value:
            problem = _validate_agent_file(value, load_config() or {})
            if problem:
                console.print(f"[err]not a usable agent file:[/err] {escape(problem)}")
                sys.exit(1)
        try:
            set_value(key, value)
        except ValueError as e:
            console.print(f"[err]{escape(str(e))}[/err]")
            sys.exit(1)
        console.print(f"[ok]✓ set {escape(key)} = {escape(value)}[/ok]")
    else:
        run_config_wizard()


def _handle_agents() -> None:
    agents = list_agents()
    default = (load_config() or {}).get("agent", {}).get("default", "")
    if not agents:
        console.print("[muted]no agents registered yet — add one:[/muted] "
                      "[tool]hosta add agent <path>[/tool]")
        return
    console.print("[primary]registered agents[/primary]")
    for name, path in sorted(agents.items()):
        mark = "  [ok]✓ default[/ok]" if name == default else ""
        console.print(f"  [tool]{escape(name)}[/tool]{mark}\n    [muted]{escape(path)}[/muted]")


def _handle_add(raw: list[str]) -> None:
    if len(raw) < 3 or raw[1] != "agent":
        console.print("[err]usage: hosta add agent <path> [--name <name>][/err]")
        sys.exit(1)
    path = raw[2]
    name = None
    if "--name" in raw:
        i = raw.index("--name")
        name = raw[i + 1] if i + 1 < len(raw) else None
    name = name or Path(path).stem
    problem = _validate_agent_file(path, load_config() or {})
    if problem:
        console.print(f"[err]not a usable agent file:[/err] {escape(problem)}")
        sys.exit(1)
    try:
        add_agent(name, path)
    except ValueError as e:
        console.print(f"[err]{escape(str(e))}[/err]")
        sys.exit(1)
    console.print(f"[ok]✓ added agent[/ok] [tool]{escape(name)}[/tool]")
    console.print(f"[muted]run:[/muted] [tool]hosta --agent {escape(name)}[/tool]  "
                  f"[muted]· make default:[/muted] [tool]hosta use {escape(name)}[/tool]")


def _handle_remove(raw: list[str]) -> None:
    if len(raw) < 3 or raw[1] != "agent":
        console.print("[err]usage: hosta remove agent <name>[/err]")
        sys.exit(1)
    name = raw[2]
    if name not in list_agents():
        console.print(f"[warn]no agent named[/warn] [tool]{escape(name)}[/tool]")
        return
    remove_agent(name)
    console.print(f"[ok]✓ removed agent[/ok] [tool]{escape(name)}[/tool]")


def _handle_use(raw: list[str]) -> None:
    if len(raw) < 2:
        console.print("[err]usage: hosta use <name>[/err]")
        sys.exit(1)
    name = raw[1]
    if resolve_agent(name) is None:
        console.print(f"[err]unknown agent:[/err] {escape(name)} "
                      "[muted](register it with `hosta add agent <path>`)[/muted]")
        sys.exit(1)
    set_value("agent.default", name)
    console.print(f"[ok]✓ default agent →[/ok] [tool]{escape(name)}[/tool] "
                  "[muted](plain `hosta` runs it)[/muted]")


_VERBS: dict[str, Callable[[list[str]], None]] = {
    "config": _handle_config,
    "agents": lambda raw: _handle_agents(),
    "add": _handle_add,
    "remove": _handle_remove,
    "use": _handle_use,
}


def main(argv: list[str] | None = None) -> None:
    raw = list(sys.argv[1:] if argv is None else argv)

    if raw and raw[0] in _VERBS:  # config / agents / add / remove / use
        _VERBS[raw[0]](raw)
        return

    parser = argparse.ArgumentParser(
        prog="hosta", description="A framework to build agents the simplest way possible.")
    parser.add_argument("task", nargs="?", help="task to run (omit for an interactive session)")
    parser.add_argument("-a", "--agent", help="agent to run: a registered name or a Python file")
    parser.add_argument("-m", "--model", help="override the model name")
    args = parser.parse_args(raw)

    cfg = load_config() or run_config_wizard()  # first run launches the wizard
    if args.model:
        cfg["model"]["name"] = args.model
    set_default_model(cfg)  # wire config into the default model before building agents

    agent_path: Path | None = None
    if args.agent:
        resolved = resolve_agent(args.agent)
        if resolved is None:
            console.print(f"[err]unknown agent:[/err] {escape(args.agent)} "
                          "[muted](try `hosta agents`, or pass a file path)[/muted]")
            sys.exit(1)
        agent_path = Path(resolved)

    try:  # _load_agent may raise SystemExit with a "no agent found" message
        agent = _load_agent(agent_path, cfg) if agent_path else _default_agent(cfg)
    except SystemExit as e:
        console.print(f"[err]{escape(str(e))}[/err]")
        sys.exit(1)

    if args.task:
        if run_one(console, agent, args.task) is None:
            sys.exit(1)  # the run raised (already shown as a styled error)
    else:
        run_repl(console, agent, cfg)


if __name__ == "__main__":
    main()

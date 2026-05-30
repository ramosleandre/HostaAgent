"""The ``hosta`` command — argument parsing + dispatch.

No business logic lives here, only wiring: resolve config (launching the wizard on
first run), build the agent, then either run one task or open the REPL.
"""
from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path
from typing import Any

from rich.console import Console

from ...config import build_model, load_config
from ...core import Agent
from ...environment import LocalFS
from .repl import run_one, run_repl
from .theme import VIOLET
from .wizard import run_config_wizard

console = Console(theme=VIOLET)


def _default_agent(cfg: dict[str, Any]) -> Agent:
    return Agent(env=LocalFS("."), model=build_model(cfg))


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
            return value(env=LocalFS("."), model=build_model(cfg))
    raise SystemExit(f"No Agent, make_agent(), or build() found in {path}")


def main(argv: list[str] | None = None) -> None:
    raw = list(sys.argv[1:] if argv is None else argv)

    # `hosta config` / `hosta config show` — handled before argparse.
    if raw and raw[0] == "config":
        if len(raw) > 1 and raw[1] == "show":
            cfg = load_config()
            console.print(cfg or "[warn]no config yet — run [tool]hosta config[/tool][/warn]")
        else:
            run_config_wizard()
        return

    parser = argparse.ArgumentParser(
        prog="hosta", description="Claude Code in 50 lines you can fork.")
    parser.add_argument("task", nargs="?", help="task to run (omit for an interactive session)")
    parser.add_argument("-a", "--agent", type=Path, help="load a custom agent from a Python file")
    parser.add_argument("-m", "--model", help="override the model name")
    args = parser.parse_args(raw)

    cfg = load_config() or run_config_wizard()  # first run launches the wizard
    if args.model:
        cfg["model"]["name"] = args.model

    try:
        agent = _load_agent(args.agent, cfg) if args.agent else _default_agent(cfg)
    except SystemExit as e:
        console.print(f"[err]{e}[/err]")
        sys.exit(1)

    if args.task:
        if run_one(console, agent, args.task) is None:
            sys.exit(1)  # the run raised (already shown as a styled error)
    else:
        run_repl(console, agent, cfg)


if __name__ == "__main__":
    main()

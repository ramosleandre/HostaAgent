"""The interactive `hosta` REPL.

prompt_toolkit drives input: arrow-navigable autocomplete for ``/`` commands and
``erase_when_done`` so the typed line is replaced by a task card (no duplicate).
Tracks per-session stats and prints a summary on exit.
"""
from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from rich.console import Console
from rich.live import Live
from rich.markup import escape
from rich.panel import Panel

from ...config import build_model
from ...core import Agent
from ...events import OnEvent
from ...session import new_session_id, save_session
from .render import task_panel
from .stream import StreamRenderer
from .theme import PROMPT_STYLE

SLASH_COMMANDS: dict[str, str] = {
    "/model": "switch model for the session (/model <name>)",
    "/tools": "list available tools",
    "/think": "toggle showing the agent's reasoning",
    "/save": "save this session to disk now (also auto-saved each turn)",
    "/clear": "clear the screen and start a fresh session",
    "/help": "show this help",
    "/exit": "quit (or Ctrl-D)",
}


@dataclass
class _Stats:
    tasks: int = 0
    tools: int = 0
    turns: int = 0


class _SlashCompleter(Completer):
    """Autocomplete ``/`` commands with their descriptions in the menu."""

    def get_completions(self, document: Any, complete_event: Any) -> Iterable[Completion]:
        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        for cmd, desc in SLASH_COMMANDS.items():
            if cmd.startswith(text):
                yield Completion(cmd, start_position=-len(text), display=cmd, display_meta=desc)


def _help(console: Console) -> None:
    console.print("[primary]commands[/primary]")
    for cmd, desc in SLASH_COMMANDS.items():
        console.print(f"  [tool]{cmd:<8}[/tool] [muted]{desc}[/muted]")


def run_one(console: Console, agent: Agent, task: str, show_thinking: bool = True,
            history: list[dict[str, Any]] | None = None, debug: bool = False) -> Any:
    """Render the task card, run the agent streaming events live, then the status.

    `history` carries the prior conversation so the agent remembers earlier turns.
    `debug` dumps the system prompt + raw messages and traces full tool I/O.
    Returns the ``AgentResult`` (whose ``.messages`` is the conversation to carry
    forward), or ``None`` if the run raised — shown as a styled line, no crash.
    """
    console.print(task_panel(task))
    renderer = StreamRenderer(show_thinking=show_thinking)
    on_event: OnEvent = renderer.handle
    if debug:
        from .debug import print_raw_messages, print_system_prompt, trace_handler
        print_system_prompt(console, agent)
        on_event = trace_handler(console, renderer.handle)
    try:
        if console.is_terminal and not debug:
            with Live(console=console, refresh_per_second=12,
                      vertical_overflow="visible") as live:
                renderer.bind(live)
                result = asyncio.run(agent.run(task, on_event=on_event, history=history))
        else:  # piped/captured OR --debug: no live region (it would fight the trace lines)
            result = asyncio.run(agent.run(task, on_event=on_event, history=history))
            console.print(renderer.render())
    except KeyboardInterrupt:
        console.print("[warn]interrupted[/warn]")
        return None
    except Exception as e:  # bad key, network, rate limit, bad endpoint, …
        console.print(f"[err]✗ {type(e).__name__}:[/err] {escape(str(e))}")
        return None
    console.print(renderer.final_status(result))
    if debug:
        print_raw_messages(console, result.messages)
    return result


def run_repl(console: Console, agent: Agent, cfg: dict[str, Any], debug: bool = False,
             resume_history: list[dict[str, Any]] | None = None) -> None:
    console.print(Panel("[accent]Interactive session[/accent] — type a task, or [tool]/help[/tool]",
                        title="[primary]HostaAgent[/primary]", border_style="primary",
                        expand=False))
    # A real terminal gets the rich prompt_toolkit prompt (autocomplete, erase-on-
    # submit); piped/redirected stdin falls back to plain input() so it never hangs.
    session: PromptSession[str] | None = None
    if sys.stdin.isatty():
        session = PromptSession(
            completer=_SlashCompleter(), complete_while_typing=True,
            erase_when_done=True, style=PROMPT_STYLE,
        )
    stats = _Stats()
    show_thinking = True
    # The running conversation (multi-turn memory). A resumed session continues an
    # older one; either way this REPL writes under a fresh id (sessions are append-only).
    history: list[dict[str, Any]] = list(resume_history) if resume_history else []
    session_id = new_session_id()

    while True:
        try:
            line = (session.prompt([("class:prompt", "hosta ❯ ")]) if session
                    else input("hosta > ")).strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue

        if line.startswith("/"):
            cmd, _, arg = line[1:].partition(" ")
            if cmd in ("exit", "quit"):
                break
            elif cmd == "help":
                _help(console)
            elif cmd == "tools":
                chips = "  ".join(f"[tool]{n}[/tool]" for n in agent.tools)
                console.print(chips or "[muted](none)[/muted]")
            elif cmd == "think":
                show_thinking = not show_thinking
                console.print(f"[muted]reasoning {'shown' if show_thinking else 'hidden'}[/muted]")
            elif cmd == "model":
                if arg.strip():
                    cfg["model"]["name"] = arg.strip()
                    agent.model = build_model(cfg)
                    console.print(f"[ok]model → {arg.strip()}[/ok]")
                else:
                    console.print(f"[muted]current model: {cfg['model']['name']}[/muted]")
            elif cmd == "save":
                if history:
                    save_session(session_id, history)
                    console.print(f"[ok]✓ saved[/ok] [muted]{session_id}[/muted]")
                else:
                    console.print("[muted]nothing to save yet[/muted]")
            elif cmd == "clear":
                history = []  # forget the conversation; a new session from here on
                session_id = new_session_id()
                console.clear()
            else:
                console.print(f"[warn]unknown command: /{cmd}[/warn] [muted](try /help)[/muted]")
            continue

        result = run_one(console, agent, line, show_thinking, history=history, debug=debug)
        if result is not None:
            history = result.messages  # carry the conversation into the next turn
            save_session(session_id, history)  # persist after every turn
            stats.tasks += 1
            stats.tools += len(result.tools_used)
            stats.turns += len(result.turns)

    turn_word = "turn" if stats.turns == 1 else "turns"
    console.print(Panel(
        f"[accent]{stats.tasks}[/accent] tasks [muted]·[/muted] "
        f"[accent]{stats.tools}[/accent] tool calls [muted]·[/muted] "
        f"[accent]{stats.turns}[/accent] {turn_word}",
        title="[primary]session ended[/primary]", border_style="primary", expand=False))

"""`hosta --debug` rendering: violet event trace + system-prompt / raw-messages dumps.

Kept in the CLI layer (it needs rich) so `hostaagent.debug` stays dependency-free.
`trace_handler` chains after the normal `StreamRenderer` so live rendering is intact.
"""
from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from ...events import Event, OnEvent, ToolEnd, ToolStart, TurnEnd


def trace_handler(console: Console, handler: OnEvent | None = None) -> OnEvent:
    """A rich event tracer that prints full tool I/O, then forwards to `handler`."""
    def _on_event(ev: Event) -> None:
        if isinstance(ev, ToolStart):
            console.print(f"[muted]→[/muted] [tool]{escape(ev.name)}[/tool] "
                          f"[muted]{escape(json.dumps(ev.args, default=str))}[/muted]")
        elif isinstance(ev, ToolEnd):
            tag = "[err]error[/err]" if ev.is_error else "[ok]ok[/ok]"
            console.print(f"[muted]←[/muted] [tool]{escape(ev.name)}[/tool] {tag} "
                          f"{escape(ev.result)}")
        elif isinstance(ev, TurnEnd):
            console.print(f"[muted]· turn end · tools={len(ev.turn.tools)}[/muted]")
        if handler is not None:
            handler(ev)
    return _on_event


def print_system_prompt(console: Console, agent: Any) -> None:
    """Dump the system prompt sent on every turn (the `--debug` preamble)."""
    console.print(Panel(escape(agent.system()), title="[primary]system prompt[/primary]",
                        border_style="muted", expand=False))


def print_raw_messages(console: Console, messages: list[dict[str, Any]]) -> None:
    """Dump the full raw conversation (the `--debug` postamble)."""
    console.print(Panel(escape(json.dumps(messages, indent=2, default=str)),
                        title="[primary]raw messages[/primary]",
                        border_style="muted", expand=False))

"""hostaagent.debug — a pure trace listener for the run event stream.

`with_trace` wraps (or starts) an `on_event` callback to print every tool call,
its full result, and turn boundaries — plain text, no rich dependency, so it works
anywhere. The CLI has a richer violet variant; this is the library primitive.
"""
from __future__ import annotations

import json
from collections.abc import Callable

from .events import Event, OnEvent, Token, ToolEnd, ToolStart, TurnEnd

__all__ = ["with_trace"]


def _line(ev: Event) -> str | None:
    """One trace line for an event, or None to skip it (tokens are too noisy here)."""
    if isinstance(ev, ToolStart):
        return f"[trace] → {ev.name}({json.dumps(ev.args, default=str)})"
    if isinstance(ev, ToolEnd):
        return f"[trace] ← {ev.name} [{'error' if ev.is_error else 'ok'}] {ev.result}"
    if isinstance(ev, TurnEnd):
        text = (ev.turn.text or "").strip()
        return f"[trace] · turn end (tools={len(ev.turn.tools)}) {text!r}"
    if isinstance(ev, Token):
        return None
    return None


def with_trace(handler: OnEvent | None = None,
               emit: Callable[[str], None] = print) -> OnEvent:
    """Return an `on_event` that traces each event via `emit`, then forwards to `handler`.

    `handler`: an existing `on_event` to chain after tracing (e.g. a renderer); `None`
    for trace-only. `emit`: where the formatted line goes (default: `print`). Pass a
    list's `.append` to capture lines in tests.
    """
    def _on_event(ev: Event) -> None:
        line = _line(ev)
        if line is not None:
            emit(line)
        if handler is not None:
            handler(ev)
    return _on_event

"""Live rendering of a run's event stream.

Consumes `Agent.run(on_event=...)` events and builds a growing transcript: completed
steps become cards, the in-progress step shows streaming reasoning + running tools,
and the final answer streams in token by token. Bound to a `rich.Live` it updates in
place; unbound (non-terminal) it just accumulates and is printed once at the end.
"""
from __future__ import annotations

from typing import Any

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text

from ...events import Event, Token, ToolEnd, ToolStart, TurnEnd
from .render import status_line, tool_chip


class StreamRenderer:
    def __init__(self, show_thinking: bool = True) -> None:
        self.show_thinking = show_thinking
        self._cards: list[Any] = []          # finalized step cards
        self._reasoning = ""                 # current step's streaming text
        self._tools: list[dict[str, Any]] = []  # current step's tools
        self._answer: str | None = None      # the final answer (last turn)
        self._live: Live | None = None

    def bind(self, live: Live) -> None:
        self._live = live
        live.update(self.render())

    def handle(self, ev: Event) -> None:
        if isinstance(ev, Token):
            self._reasoning += ev.text
        elif isinstance(ev, ToolStart):
            self._tools.append({"name": ev.name, "args": ev.args, "result": None, "error": False})
        elif isinstance(ev, ToolEnd):
            if self._tools:
                self._tools[-1].update(result=ev.result, error=ev.is_error)
        elif isinstance(ev, TurnEnd):
            self._finalize(ev.turn)
        if self._live is not None:
            self._live.update(self.render())

    def _finalize(self, turn: Any) -> None:
        if turn.tools:
            self._cards.append(self._step_card())
        else:
            self._answer = (turn.text or self._reasoning or "").strip() or None
        self._reasoning = ""
        self._tools = []

    def _step_card(self) -> Panel:
        body: list[Any] = []
        if self.show_thinking and self._reasoning.strip():
            body.append(Text(f"▸ {self._reasoning.strip()}", style="muted"))
        for t in self._tools:
            body.append(tool_chip(t["name"], t["args"], t["result"], t["error"],
                                  running=t["result"] is None))
        names = " · ".join(dict.fromkeys(t["name"] for t in self._tools)) or "…"
        return Panel(Group(*body), title=f"[muted]{names}[/muted]",
                     border_style="muted", expand=False, padding=(0, 1))

    def render(self) -> Group:
        items = list(self._cards)
        if self._answer is not None:
            items.append(Text(self._answer, style="result"))
        elif self._reasoning.strip() or self._tools:
            items.append(self._step_card())  # in-progress
        elif not items:
            # nothing has streamed yet — show a live "thinking…" so the wait is visible
            # (matters for non-streaming models, which emit nothing until the answer)
            items.append(Spinner("dots", text=Text(" thinking…", style="accent")))
        return Group(*items)

    def final_status(self, result: Any) -> str:
        return status_line(result)

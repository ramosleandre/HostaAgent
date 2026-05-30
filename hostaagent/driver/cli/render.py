"""Rendering the agent trace in violet.

Layout per run:  [step cards: reasoning + condensed tool chips] → the answer →
the status line. Tool args/results are condensed (basenames, truncation) and
markup-escaped — never the raw absolute paths or indigestible blobs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console, Group
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text

_ARG_MAX = 44
_RESULT_MAX = 88


def _condense(value: Any) -> str:
    """Shorten a tool-arg value: basenames for paths, truncation for long blobs."""
    if isinstance(value, str):
        s = value
        if "/" in s and len(s) > 28:
            p = Path(s)
            s = f"…/{p.parent.name}/{p.name}" if p.parent.name else (p.name or s)
    else:
        s = repr(value)
    s = s.replace("\n", " ")
    if len(s) > _ARG_MAX:
        s = s[: _ARG_MAX - 1] + "…"
    return s


def _preview(result: str) -> str:
    for line in (result or "").splitlines():
        line = line.strip()
        if line:
            return line[: _RESULT_MAX - 1] + "…" if len(line) > _RESULT_MAX else line
    return ""


def _tool_chip(tu: Any) -> Text:
    args = "  ".join(_condense(v) for v in tu.args.values())
    chip = Text()
    chip.append("⚙ ", style="tool")
    chip.append(tu.name, style="tool")
    if args:
        chip.append("  ")
        chip.append(escape(args), style="tool.arg")
    preview = _preview(tu.result)
    if preview:
        chip.append("\n  ↳ ", style="muted")
        chip.append(escape(preview), style="err" if tu.is_error else "result")
    return chip


def task_panel(task: str) -> Panel:
    return Panel(Text(task, style="accent"), title="[primary]task[/primary]",
                 border_style="primary", expand=False, padding=(0, 1))


def render_result(console: Console, result: Any, show_thinking: bool = True) -> None:
    """Render the trace, then the answer, then the status line (in that order)."""
    for turn in result.turns:
        if not turn.tools:
            continue  # the final answer turn is rendered below, not as a step
        body: list[Any] = []
        if show_thinking and turn.text and turn.text.strip():
            body.append(Text(f"▸ {turn.text.strip()}", style="muted"))
        body.extend(_tool_chip(tu) for tu in turn.tools)
        names = " · ".join(dict.fromkeys(t.name for t in turn.tools))
        console.print(Panel(Group(*body), title=f"[muted]{escape(names)}[/muted]",
                            border_style="muted", expand=False, padding=(0, 1)))

    answer = "" if result.answer is None else str(result.answer)
    if answer.strip():
        console.print(Text(answer, style="result"))

    mark, style = ("✓", "ok") if result.stop_reason == "done" else ("⚠", "warn")
    n_tools, n_turns = len(result.tools_used), len(result.turns)
    turn_word = "turn" if n_turns == 1 else "turns"
    console.print(
        f"[{style}]{mark} {result.stop_reason}[/{style}] [muted]·[/muted] "
        f"{n_tools} tools [muted]·[/muted] {n_turns} {turn_word}"
    )

"""Violet rendering building blocks, shared by the live `StreamRenderer`.

Tool args/results are condensed (basenames, truncation) and markup-escaped —
never the raw absolute paths or indigestible blobs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

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


def tool_chip(name: str, args: dict[str, Any], result: str | None,
              is_error: bool = False, running: bool = False) -> Text:
    """One condensed tool line: `⚙ name  arg  arg` + a `↳ result` (or `· running…`)."""
    arg_str = "  ".join(_condense(v) for v in args.values())
    chip = Text()
    chip.append("⚙ ", style="tool")
    chip.append(name, style="tool")
    if arg_str:
        chip.append("  ")
        chip.append(escape(arg_str), style="tool.arg")
    if running and result is None:
        chip.append("  · running…", style="muted")
    else:
        preview = _preview(result or "")
        if preview:
            chip.append("\n  ↳ ", style="muted")
            chip.append(escape(preview), style="err" if is_error else "result")
    return chip


def status_line(result: Any) -> str:
    """The `✓ done · N tools · M turns` footer as a themed markup string."""
    mark, style = ("✓", "ok") if result.stop_reason == "done" else ("⚠", "warn")
    n_tools, n_turns = len(result.tools_used), len(result.turns)
    turn_word = "turn" if n_turns == 1 else "turns"
    return (f"[{style}]{mark} {result.stop_reason}[/{style}] [muted]·[/muted] "
            f"{n_tools} tools [muted]·[/muted] {n_turns} {turn_word}")


def task_panel(task: str) -> Panel:
    return Panel(Text(task, style="accent"), title="[primary]task[/primary]",
                 border_style="primary", expand=False, padding=(0, 1))

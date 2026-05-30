"""The violet palette, shared across rich (output), prompt_toolkit (REPL input),
and questionary (the wizard) so the whole `hosta` experience is one brand color."""
from __future__ import annotations

from prompt_toolkit.styles import Style as PTStyle
from questionary import Style as QStyle
from rich.theme import Theme

VIOLET = Theme({
    "primary": "bold #a78bfa",   # the brand violet
    "accent": "#c4b5fd",
    "muted": "#6b7280",
    "tool": "#a78bfa",
    "tool.arg": "italic #c4b5fd",
    "result": "#d1d5db",
    "ok": "#22c55e",
    "warn": "#f59e0b",
    "err": "bold #ef4444",
})

# prompt_toolkit: the REPL prompt + the slash-command completion menu.
PROMPT_STYLE = PTStyle.from_dict({
    "prompt": "bold #a78bfa",
    "completion-menu": "bg:#1f2937",
    "completion-menu.completion": "bg:#1f2937 #d1d5db",
    "completion-menu.completion.current": "bg:#a78bfa #111827 bold",
    "completion-menu.meta.completion": "bg:#1f2937 #6b7280",
    "completion-menu.meta.completion.current": "bg:#7c3aed #e5e7eb",
    "scrollbar.background": "bg:#374151",
    "scrollbar.button": "bg:#a78bfa",
})

# questionary: the arrow-key wizard selects/inputs.
WIZARD_STYLE = QStyle([
    ("qmark", "#a78bfa bold"),
    ("question", "bold"),
    ("answer", "#c4b5fd bold"),
    ("pointer", "#a78bfa bold"),
    ("highlighted", "#a78bfa bold"),
    ("selected", "#c4b5fd"),
    ("separator", "#6b7280"),
    ("instruction", "#6b7280"),
    ("text", "#d1d5db"),
])

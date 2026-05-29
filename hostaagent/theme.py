"""The violet CLI theme (Claude-style). A single, tight palette via `rich`."""
from __future__ import annotations

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

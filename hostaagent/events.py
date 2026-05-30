"""Run events — the driver-agnostic streaming seam.

`Agent.run(task, on_event=...)` emits these as the loop progresses. Any driver
(the violet CLI, a daemon, a web SSE endpoint) renders them however it likes; the
agent never knows who's listening. Token events only fire when the model streams.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .types import Turn


@dataclass
class Token:
    """A streamed text delta from the model (only when streaming is on)."""
    text: str


@dataclass
class ToolStart:
    """A tool is about to run."""
    name: str
    args: dict[str, Any]


@dataclass
class ToolEnd:
    """A tool finished, with its (truncated) result."""
    name: str
    result: str
    is_error: bool


@dataclass
class TurnEnd:
    """One assistant turn completed (its text + any tools)."""
    turn: Turn


Event = Token | ToolStart | ToolEnd | TurnEnd
OnEvent = Callable[[Event], None]

"""The output model of an agent run: AgentResult -> Turn -> ToolUse."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolUse:
    """One tool invocation within a turn, with its result."""
    name: str
    args: dict[str, Any]
    result: str
    is_error: bool = False


@dataclass
class Turn:
    """One assistant turn: its text plus any tools it called."""
    text: str | None
    tools: list[ToolUse] = field(default_factory=list)


@dataclass
class AgentResult:
    """The full result of `Agent.run`: final answer + the whole trace."""
    answer: Any
    turns: list[Turn] = field(default_factory=list)
    stop_reason: str = "done"  # "done" | "max_steps"
    messages: list[dict[str, Any]] = field(default_factory=list)  # full convo, to continue it

    def __str__(self) -> str:
        return str(self.answer)

    @property
    def tools_used(self) -> list[str]:
        return [t.name for tn in self.turns for t in tn.tools]


@dataclass
class _ToolResult:
    """Internal: a tool's outcome, fed back to the model as a `tool` message."""
    id: str
    content: str
    is_error: bool = False

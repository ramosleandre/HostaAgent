"""HostaAgent — Claude Code in ~50 lines you can fork.

One import surface. Users never import OpenHosta directly; `tool` is re-exported.
"""
from OpenHosta import tool  # re-export — users never import OpenHosta directly

from .core import Agent
from .driver import CliDriver, DaemonDriver, Driver
from .environment import Environment, LocalFS
from .types import AgentResult, ToolUse, Turn

__version__ = "0.1.0"

__all__ = [
    "Agent",
    "AgentResult",
    "Turn",
    "ToolUse",
    "Environment",
    "LocalFS",
    "Driver",
    "CliDriver",
    "DaemonDriver",
    "tool",
    "__version__",
]

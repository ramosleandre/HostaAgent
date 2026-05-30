"""HostaAgent — a minimalist skeleton for building agents.

One import surface. Users never import OpenHosta directly; `tool` is re-exported.
"""
import os as _os

# Quiet OpenHosta's .env warnings by default (the user can override). Must run
# before OpenHosta is imported below.
_os.environ.setdefault("OPENHOSTA_SILENCE_ENV_WARNING", "1")

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

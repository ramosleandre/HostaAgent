"""HostaAgent — a minimalist skeleton for building agents.

One import surface. Users never import OpenHosta directly; `tool` is re-exported.
"""
import contextlib as _ctx
import io as _io
import os as _os
import sys as _sys

# Quiet OpenHosta's import-time .env chatter (some lines aren't gated by the flag).
# We capture stderr only for the OpenHosta import and re-emit anything that isn't
# its dotenv noise — so real errors/tracebacks are never hidden.
_os.environ.setdefault("OPENHOSTA_SILENCE_ENV_WARNING", "1")
_buf = _io.StringIO()
with _ctx.redirect_stderr(_buf):
    from OpenHosta import tool  # re-export — users never import OpenHosta directly
for _line in _buf.getvalue().splitlines():
    if "OpenHosta/CONFIG" not in _line and "dotenv" not in _line:
        print(_line, file=_sys.stderr)

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

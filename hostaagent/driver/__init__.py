"""Drivers — the lifecycle seam.

`base` holds the framework lifecycle classes. The rich `hosta` terminal app lives
in the `cli` subpackage and is imported only by the `hosta` entry point, so
`import hostaagent` never *imports* the CLI deps (rich / prompt_toolkit /
questionary) at runtime — only the `hosta` command loads them.
"""
from .base import CliDriver, DaemonDriver, Driver

__all__ = ["Driver", "CliDriver", "DaemonDriver"]

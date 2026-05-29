"""The Environment seam — the agent's *body*: what it can do and touch.

Subclass `Environment`, override `tools()` to expose callables and `context()`
to add prompt context. `LocalFS` is the default body for a code agent.
"""
from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from OpenHosta import tool


class Environment:
    """Subclass. Override `tools()` to expose callables; `context()` for prompt context."""

    def tools(self) -> list[Callable[..., Any]]:
        return []

    def context(self) -> str:
        return ""


class LocalFS(Environment):
    """The default body for a code agent: read / grep / write / bash, rooted at a dir."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def context(self) -> str:
        return f"You work in: {self.root}"

    def tools(self) -> list[Callable[..., Any]]:
        root = self.root

        @tool(read_only=True)
        def read(path: str) -> str:
            "Read a file (capped at 8000 chars)."
            return (root / path).read_text()[:8000]

        @tool(read_only=True)
        def grep(pattern: str, path: str = ".") -> str:
            "Search files for a regex."
            r = subprocess.run(
                ["rg", "-n", pattern, str(root / path)],
                capture_output=True, text=True,
            )
            return (r.stdout or "no matches")[:5000]

        @tool
        def write(path: str, content: str) -> str:
            "Write/overwrite a file."
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            return "ok"

        @tool
        def bash(command: str) -> str:
            "Run a shell command (cwd=root, 60s timeout)."
            r = subprocess.run(
                command, shell=True, cwd=root,
                capture_output=True, text=True, timeout=60,
            )
            return (r.stdout + r.stderr)[:5000]

        return [read, grep, write, bash]

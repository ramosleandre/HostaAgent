"""The violet `hosta` terminal app (the entry point for the `hosta` command).

Imported only by the `hosta` script — keeps the interactive deps (prompt_toolkit,
questionary) out of `import hostaagent`.
"""
from .app import main

__all__ = ["main"]

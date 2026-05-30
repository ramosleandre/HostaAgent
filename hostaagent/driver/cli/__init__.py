"""The violet `hosta` terminal app (the entry point for the `hosta` command).

`main` powers the `hosta` binary; `launch` runs the same UI for any agent (used by
the examples' `__main__` blocks). Imported only by the `hosta` script and examples —
keeps the interactive deps (prompt_toolkit, questionary) out of `import hostaagent`.
"""
from .app import launch, main

__all__ = ["main", "launch"]

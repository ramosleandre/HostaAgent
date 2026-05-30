"""Environments — the body seam. A new body = a new agent type, the loop unchanged."""
from .base import Environment
from .local import LocalFS

__all__ = ["Environment", "LocalFS"]

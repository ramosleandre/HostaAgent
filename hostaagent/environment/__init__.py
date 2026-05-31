"""Environments — the body seam. A new body = a new agent type, the loop unchanged."""
from .base import Environment
from .http import HttpEnv
from .local import LocalFS
from .multi import MultiEnv

__all__ = ["Environment", "LocalFS", "MultiEnv", "HttpEnv"]

"""Tag-based access control: a `Principal` (the caller) and the `visible` check.

A tool declares the tags it needs with `@tool(requires=[...])` (OpenHosta's decorator).
A `Principal` carries the caller's tags. The agent filters its tools by visibility, so
a denied tool is simply never shown to the LLM — the loop is untouched. Identity comes
from the user/driver; the library stores no users.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Principal:
    """The caller's identity: an immutable set of capability tags.

    Accepts any iterable of tags (``Principal({"admin"})``); stored as a frozenset.
    """
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(self, "tags", frozenset(self.tags))  # normalize set/list → frozenset

    @classmethod
    def of(cls, *tags: str) -> Principal:
        """Build a principal from loose tag args: ``Principal.of("admin", "read")``."""
        return cls(frozenset(tags))


def _required_tags(fn: Callable[..., Any]) -> frozenset[str]:
    """The tags a tool requires, from its `@tool(requires=[...])` metadata (else none)."""
    meta = getattr(fn, "__hosta_tool__", None)
    return getattr(meta, "requires", frozenset())


def visible(fn: Callable[..., Any], principal: Principal | None) -> bool:
    """True iff `principal` may see `fn`: no required tags ⇒ public; else all must be held."""
    required = _required_tags(fn)
    if not required:
        return True
    return principal is not None and required <= principal.tags

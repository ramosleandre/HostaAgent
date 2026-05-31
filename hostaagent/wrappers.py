"""Tool wrappers — add cross-cutting behavior to a tool by composition, no core change.

Each wrapper uses `functools.wraps` (which sets `__wrapped__`, so OpenHosta's
`tool_to_schema` still reads the *original* signature) then copies `__hosta_tool__`
across, so the name, description, and `requires` tags survive. A wrapper that denies a
call just *returns an error string* — the loop already turns that into a tool result.
"""
from __future__ import annotations

import functools
import time
from collections.abc import Callable
from inspect import iscoroutinefunction
from typing import Any

Tool = Callable[..., Any]
AuditLog = Callable[[str, dict[str, Any], str], None]


def _carry_meta(src: Tool, dst: Tool) -> Tool:
    """Copy the OpenHosta tool metadata (name, description, read_only, requires) onto `dst`."""
    if (meta := getattr(src, "__hosta_tool__", None)) is not None:
        dst.__hosta_tool__ = meta  # type: ignore[attr-defined]
    return dst


def with_audit(fn: Tool, log: AuditLog | None = None) -> Tool:
    """Wrap `fn` to log every call as `(name, args, result)`. `log` defaults to print."""
    emit = log or (lambda name, args, res: print(f"[audit] {name}({args}) → {res}"))

    if iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def aw(**kwargs: Any) -> Any:
            res = await fn(**kwargs)
            emit(fn.__name__, kwargs, str(res))
            return res
        return _carry_meta(fn, aw)

    @functools.wraps(fn)
    def w(**kwargs: Any) -> Any:
        res = fn(**kwargs)
        emit(fn.__name__, kwargs, str(res))
        return res
    return _carry_meta(fn, w)


def rate_limited(fn: Tool, min_interval: float = 1.0) -> Tool:
    """Wrap `fn` to refuse calls less than `min_interval` seconds apart (returns an error)."""
    last = {"t": float("-inf")}  # monotonic time of the last allowed call

    def _too_soon() -> str | None:
        gap = time.monotonic() - last["t"]
        if gap < min_interval:
            return f"error: rate limit — wait {min_interval - gap:.1f}s"
        last["t"] = time.monotonic()
        return None

    if iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def aw(**kwargs: Any) -> Any:
            return msg if (msg := _too_soon()) else await fn(**kwargs)
        return _carry_meta(fn, aw)

    @functools.wraps(fn)
    def w(**kwargs: Any) -> Any:
        return msg if (msg := _too_soon()) else fn(**kwargs)
    return _carry_meta(fn, w)

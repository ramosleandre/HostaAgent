"""Tool wrappers: behavior + metadata/signature preservation (the schema-safety guard)."""
from __future__ import annotations

import inspect

from OpenHosta import tool, tool_to_schema

from hostaagent.wrappers import rate_limited, with_audit


@tool(read_only=True, requires=["admin"])
def read(path: str, limit: int = 100) -> str:
    "Read a file."
    return f"read {path} ({limit})"


def test_with_audit_logs_each_call():
    log: list = []
    audited = with_audit(read, log=lambda n, a, r: log.append((n, a, r)))
    out = audited(path="x.txt")
    assert out == "read x.txt (100)"
    assert log == [("read", {"path": "x.txt"}, "read x.txt (100)")]


def test_with_audit_preserves_meta_and_tags():
    audited = with_audit(read)
    assert audited.__hosta_tool__ is read.__hosta_tool__              # name/description/requires
    assert audited.__hosta_tool__.requires == frozenset({"admin"})   # permission survives


def test_with_audit_preserves_signature_and_schema():
    # THE load-bearing guarantee: OpenHosta's schema must be identical through the wrapper
    # (it follows __wrapped__), or the LLM would get a broken tool signature.
    audited = with_audit(read)
    assert inspect.signature(audited) == inspect.signature(read)
    assert tool_to_schema(audited) == tool_to_schema(read)


async def test_with_audit_async():
    @tool
    async def afetch(url: str) -> str:
        "Fetch."
        return f"got {url}"

    log: list = []
    audited = with_audit(afetch, log=lambda n, a, r: log.append(n))
    out = await audited(url="http://x")
    assert out == "got http://x" and log == ["afetch"]


def test_rate_limited_blocks_then_allows():
    calls = {"n": 0}

    @tool
    def ping() -> str:
        "Ping."
        calls["n"] += 1
        return "pong"

    limited = rate_limited(ping, min_interval=10.0)
    assert limited() == "pong"                       # first call allowed
    second = limited()                               # immediate second call refused
    assert second.startswith("error: rate limit") and calls["n"] == 1


def test_rate_limited_allows_after_interval():
    @tool
    def ping() -> str:
        "Ping."
        return "pong"

    limited = rate_limited(ping, min_interval=0.0)   # no gap required
    assert limited() == "pong" and limited() == "pong"


def test_rate_limited_preserves_meta_and_schema():
    limited = rate_limited(read, min_interval=5.0)
    assert limited.__hosta_tool__ is read.__hosta_tool__
    assert limited.__hosta_tool__.requires == frozenset({"admin"})
    assert tool_to_schema(limited) == tool_to_schema(read)


def test_wrappers_chain():
    # rate_limited(with_audit(fn)) — both layers keep the tool usable + tagged.
    chained = rate_limited(with_audit(read), min_interval=0.0)
    assert chained.__hosta_tool__ is read.__hosta_tool__
    assert chained.__hosta_tool__.requires == frozenset({"admin"})
    assert tool_to_schema(chained) == tool_to_schema(read)
    assert chained(path="a") == "read a (100)"

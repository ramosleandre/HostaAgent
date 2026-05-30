"""Session persistence — save/load/list conversations under ~/.hostaagent/sessions/.

A session is just a conversation: the `list[dict]` that `Agent.run` already returns
as `AgentResult.messages`. The core never touches this; a driver saves after a turn
and feeds a saved conversation back in as `history`. Pure stdlib, offline-testable
(tests monkeypatch `SESSIONS_DIR`).
"""
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

SESSIONS_DIR: Path = Path.home() / ".hostaagent" / "sessions"
_TITLE_MAX = 60


@dataclass
class SessionInfo:
    """Metadata for one past session (the messages are loaded separately)."""
    id: str
    created: str   # ISO-8601
    updated: str   # ISO-8601
    title: str     # first user message, truncated
    turns: int     # assistant turns (a rough size)


def new_session_id() -> str:
    """A time-ordered, practically-unique id: ``YYYYMMDDTHHMMSS-<4 hex>``."""
    return f"{datetime.now().strftime('%Y%m%dT%H%M%S')}-{secrets.token_hex(2)}"


def _title_of(messages: list[dict[str, Any]]) -> str:
    for m in messages:
        if m.get("role") == "user" and m.get("content"):
            text = str(m["content"])
            return text[:_TITLE_MAX] + ("…" if len(text) > _TITLE_MAX else "")
    return "(empty)"


def save_session(session_id: str, messages: list[dict[str, Any]]) -> Path:
    """Write `messages` to ``<SESSIONS_DIR>/<id>.json``; keep the original `created`."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSIONS_DIR / f"{session_id}.json"
    now = datetime.now().isoformat(timespec="seconds")
    created = now
    if path.exists():  # preserve the original creation time across re-saves
        try:
            created = json.loads(path.read_text()).get("created", now)
        except (json.JSONDecodeError, OSError):
            pass
    path.write_text(json.dumps({
        "id": session_id, "created": created, "updated": now,
        "title": _title_of(messages), "messages": messages,
    }, ensure_ascii=False, indent=2))
    return path


def load_session(session_id: str) -> list[dict[str, Any]]:
    """Return a session's messages; raise `FileNotFoundError` if it doesn't exist."""
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"no session: {session_id}")
    messages: list[dict[str, Any]] = json.loads(path.read_text())["messages"]
    return messages


def list_sessions() -> list[SessionInfo]:
    """All sessions, newest-updated first; corrupt files are skipped."""
    if not SESSIONS_DIR.exists():
        return []
    infos: list[SessionInfo] = []
    for p in SESSIONS_DIR.glob("*.json"):
        try:
            rec = json.loads(p.read_text())
            turns = sum(1 for m in rec.get("messages", []) if m.get("role") == "assistant")
            infos.append(SessionInfo(rec["id"], rec.get("created", ""), rec.get("updated", ""),
                                     rec.get("title", "(unknown)"), turns))
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    infos.sort(key=lambda s: s.updated, reverse=True)
    return infos

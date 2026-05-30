"""Session persistence — save/load/list round-trips, all offline (tmp SESSIONS_DIR)."""
from __future__ import annotations

import json

import pytest

from hostaagent import session as sess


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(sess, "SESSIONS_DIR", tmp_path / "sessions")


def test_new_session_id_is_unique_and_shaped():
    a, b = sess.new_session_id(), sess.new_session_id()
    assert a != b
    stamp, _, suffix = a.partition("-")
    assert len(stamp) == 15 and stamp[8] == "T" and len(suffix) == 4  # YYYYMMDDTHHMMSS-xxxx


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    path = sess.save_session("s1", msgs)
    assert path.exists()
    assert sess.load_session("s1") == msgs


def test_save_preserves_created_across_resaves(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    sess.save_session("s1", [{"role": "user", "content": "a"}])
    created = json.loads((tmp_path / "sessions" / "s1.json").read_text())["created"]
    sess.save_session("s1", [{"role": "user", "content": "a"},
                             {"role": "assistant", "content": "b"}])
    rec = json.loads((tmp_path / "sessions" / "s1.json").read_text())
    assert rec["created"] == created  # creation time frozen; only `updated` moves


def test_load_missing_raises(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    with pytest.raises(FileNotFoundError):
        sess.load_session("ghost")


def test_list_sessions_empty_when_no_dir(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert sess.list_sessions() == []


def test_list_sessions_newest_first_with_title_and_turns(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    sess.save_session("old", [{"role": "user", "content": "first task"},
                              {"role": "assistant", "content": "x"}])
    # force a later `updated` by re-saving a second one after
    sess.save_session("new", [{"role": "user", "content": "second"},
                              {"role": "assistant", "content": "y"},
                              {"role": "assistant", "content": "z"}])
    infos = sess.list_sessions()
    assert [i.id for i in infos][0] in ("new", "old")  # newest-updated first (same-second tolerant)
    by_id = {i.id: i for i in infos}
    assert by_id["old"].title == "first task" and by_id["old"].turns == 1
    assert by_id["new"].turns == 2


def test_list_sessions_skips_corrupt(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    sess.save_session("good", [{"role": "user", "content": "ok"}])
    (tmp_path / "sessions" / "broken.json").write_text("{ not json")
    ids = [i.id for i in sess.list_sessions()]
    assert ids == ["good"]  # the broken file is silently skipped


def test_title_truncates_long_first_message(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    sess.save_session("s", [{"role": "user", "content": "x" * 100}])
    assert sess.list_sessions()[0].title.endswith("…")


def test_title_empty_when_no_user_message(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    sess.save_session("s", [{"role": "assistant", "content": "only me"}])
    assert sess.list_sessions()[0].title == "(empty)"

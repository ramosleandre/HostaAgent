"""HttpEnv: tool shape + GET/POST behavior (urllib mocked — no real network)."""
from __future__ import annotations

import io
from unittest.mock import patch

from hostaagent import HttpEnv


def _tools(env):
    return {t.__hosta_tool__.name: t for t in env.tools()}


def test_context_names_the_base_url():
    assert "api.example.com" in HttpEnv("https://api.example.com/").context()


def test_get_is_read_only_post_is_not():
    t = _tools(HttpEnv("https://x"))
    assert t["http_get"].__hosta_tool__.read_only is True
    assert t["http_post"].__hosta_tool__.read_only is False


class _FakeResp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


def test_get_builds_url_and_returns_body():
    captured = {}

    def fake_urlopen(req, timeout=15):
        captured["url"] = req.full_url
        captured["method"] = req.method
        return _FakeResp(b'{"ok": true}')

    with patch("urllib.request.urlopen", fake_urlopen):
        out = _tools(HttpEnv("https://api.x"))["http_get"]("users/1")
    assert captured["url"] == "https://api.x/users/1" and captured["method"] == "GET"
    assert out == '{"ok": true}'


def test_post_sends_normalized_json_and_headers():
    captured = {}

    def fake_urlopen(req, timeout=15):
        captured["body"] = req.data
        captured["auth"] = req.headers.get("Authorization")
        return _FakeResp(b"created")

    env = HttpEnv("https://api.x", headers={"Authorization": "Bearer t"})
    with patch("urllib.request.urlopen", fake_urlopen):
        out = _tools(env)["http_post"]("items", '{"k":"v"}')
    assert out == "created"
    assert captured["body"] == b'{"k": "v"}'        # re-serialized (normalized) JSON
    assert captured["auth"] == "Bearer t"           # fixed header forwarded


def test_post_rejects_invalid_json():
    out = _tools(HttpEnv("https://x"))["http_post"]("p", "not-json")
    assert out.startswith("error: invalid JSON")


def test_network_error_becomes_a_tool_result():
    def boom(req, timeout=15):
        raise OSError("connection refused")

    with patch("urllib.request.urlopen", boom):
        out = _tools(HttpEnv("https://x"))["http_get"]("p")
    assert out.startswith("error:")                  # never raises — comes back as a result

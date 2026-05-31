"""HttpEnv — a minimal REST body (stdlib urllib, no new dependency)."""
from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from typing import Any

from OpenHosta import tool

from .base import Environment


class HttpEnv(Environment):
    """A body for REST agents: GET / POST against a base URL, with optional headers."""

    def __init__(self, base_url: str, headers: dict[str, str] | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}

    def context(self) -> str:
        return f"You call the REST API at {self.base_url}."

    def tools(self) -> list[Callable[..., Any]]:
        base, headers = self.base_url, self.headers

        def request(method: str, path: str, body: bytes | None = None) -> str:
            url = f"{base}/{path.lstrip('/')}"
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    text: str = resp.read(16_000).decode(errors="replace")
                    return text
            except Exception as e:  # network / HTTP errors come back as a tool result
                return f"error: {e}"

        @tool(read_only=True)
        def http_get(path: str) -> str:
            "GET <base_url>/<path>; returns the response body."
            return request("GET", path)

        @tool
        def http_post(path: str, body: str) -> str:
            "POST a JSON <body> to <base_url>/<path>; returns the response body."
            try:
                payload = json.dumps(json.loads(body)).encode()  # validate + normalize JSON
            except json.JSONDecodeError as e:
                return f"error: invalid JSON body: {e}"
            return request("POST", path, payload)

        return [http_get, http_post]

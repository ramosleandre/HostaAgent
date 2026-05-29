"""A MockModel that scripts `ModelResponse`s in advance — no API key needed.

It mirrors `OpenAICompatibleModel.respond(...)`: the loop calls `respond(system,
msgs, tools=...)` and gets the next scripted response. `AgentResult.turns` is the
assertion target.
"""
from __future__ import annotations

from typing import Any

from OpenHosta import ModelResponse


class MockModel:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []  # recorded (system, messages) per turn

    async def respond(self, system: str, messages: list[dict], *,
                      tools: Any = None, tool_choice: str = "auto", **_: Any) -> ModelResponse:
        self.calls.append(
            {"system": system, "messages": [dict(m) for m in messages], "tools": tools})
        if not self._responses:
            # Safety net: if a test under-scripts, end the loop cleanly.
            return ModelResponse(text="(no more scripted responses)", tool_calls=[],
                                 raw_calls=[], finish_reason="stop")
        return self._responses.pop(0)

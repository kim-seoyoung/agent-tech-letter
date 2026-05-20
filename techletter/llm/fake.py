"""FakeLLMClient — test fixture mimicking the Anthropic SDK surface.

Per TSD: no live Anthropic API in any automated test. All tests inject
this fake via `LlmClient(client_factory=lambda: FakeLLMClient(...))`.

The fake exposes the same `.messages.create(model, max_tokens, messages)`
call surface as the real `anthropic.Anthropic` client and returns objects
with `.content[0].text` and `.usage.{input_tokens, output_tokens}`.

Tokenizer: deterministic character-count proxy (1 token per 4 chars
rounded up). Good enough for budget-math tests; never used in production.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


def _char_count_tokens(text: str) -> int:
    """Deterministic token count: 1 token per 4 chars (ceil)."""
    return max(1, math.ceil(len(text) / 4))


@dataclass(frozen=True)
class FakeContentBlock:
    text: str


@dataclass(frozen=True)
class FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class FakeResponse:
    content: list[FakeContentBlock]
    usage: FakeUsage


class _FakeMessages:
    def __init__(self, responses: Iterable[str | Exception]) -> None:
        self._responses: list[str | Exception] = list(responses)
        self._idx = 0
        self.calls: list[dict[str, Any]] = []

    @property
    def call_count(self) -> int:
        return self._idx

    def create(
        self, *, model: str, max_tokens: int, messages: list[dict[str, Any]]
    ) -> FakeResponse:
        self.calls.append({"model": model, "max_tokens": max_tokens, "messages": messages})
        if self._idx >= len(self._responses):
            raise RuntimeError("FakeLLMClient ran out of queued responses")
        r = self._responses[self._idx]
        self._idx += 1
        if isinstance(r, Exception):
            raise r
        text = r
        prompt_text = "".join(str(m.get("content", "")) for m in messages)
        return FakeResponse(
            content=[FakeContentBlock(text=text)],
            usage=FakeUsage(
                input_tokens=_char_count_tokens(prompt_text),
                output_tokens=_char_count_tokens(text),
            ),
        )


class FakeLLMClient:
    """A fake Anthropic-shaped client. Pop responses from a FIFO queue.

    Usage:
        fake = FakeLLMClient(responses=["hello", "world", anthropic.RateLimitError(...)])
        client = LlmClient(client_factory=lambda: fake)
    """

    def __init__(self, responses: Iterable[str | Exception] | None = None) -> None:
        self.messages = _FakeMessages(responses or [])

    @property
    def call_count(self) -> int:
        return self.messages.call_count

    @property
    def calls(self) -> list[dict[str, Any]]:
        return self.messages.calls

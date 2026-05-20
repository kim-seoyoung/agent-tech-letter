"""LLM client wrapper with token counting and budget enforcement.

Provides a provider-neutral surface over the Anthropic Messages API.
Every LLM call in EP0002 goes through `LlmClient.generate()`.

Key responsibilities:
- Per-call token usage tracking (input + output)
- Pre-compose budget guard via `check_budget(projected_additional_tokens)`
  raising `BudgetExceededError` before any wasteful compose call
- Tenacity-wrapped network call with retry on transient failures
- Thread-safe usage ledger updates
- End-of-run usage report suitable for `RenderedIssue.meta`
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

__all__ = [
    "BudgetExceededError",
    "CallSummary",
    "LlmClient",
    "LlmResponse",
    "LlmUnavailableError",
    "LlmUsage",
]

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_BUDGET_TOKENS = 200_000


class BudgetExceededError(Exception):
    """Raised by `check_budget` when projected usage would exceed the budget."""


class LlmUnavailableError(Exception):
    """Raised after tenacity retries are exhausted on a network/API failure."""


@dataclass(frozen=True)
class LlmResponse:
    """Provider-neutral response from `generate()`."""

    text: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class CallSummary:
    """Per-call accounting row included in `usage_report()`."""

    input_tokens: int
    output_tokens: int


@dataclass
class LlmUsage:
    """Mutable ledger of token usage across `generate()` calls.

    Thread-safe: updates are guarded by `_lock`.
    """

    input_tokens_used: int = 0
    output_tokens_used: int = 0
    calls: list[CallSummary] = field(default_factory=lambda: [])
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    @property
    def total_tokens_used(self) -> int:
        return self.input_tokens_used + self.output_tokens_used

    def record(self, input_tokens: int, output_tokens: int) -> None:
        with self._lock:
            self.input_tokens_used += input_tokens
            self.output_tokens_used += output_tokens
            self.calls.append(CallSummary(input_tokens=input_tokens, output_tokens=output_tokens))


def _default_client_factory() -> Any:
    """Lazy-import the real Anthropic client so tests don't require API key at import time."""
    import anthropic  # type: ignore[import-untyped]

    return anthropic.Anthropic()


class LlmClient:
    """Provider-neutral LLM client wrapper around the Anthropic SDK.

    Construct once per run. `generate()` is the single entry point;
    `check_budget()` is the pre-compose guard; `usage_report()` is the
    end-of-run ledger consumed by `RenderedIssue.meta`.
    """

    def __init__(
        self,
        budget_tokens: int = DEFAULT_BUDGET_TOKENS,
        model: str = DEFAULT_MODEL,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        if budget_tokens <= 0:
            raise ValueError(f"budget_tokens must be > 0, got {budget_tokens}")
        self.budget_tokens = budget_tokens
        self.model = model
        self.usage = LlmUsage()
        self._client_factory = (
            client_factory if client_factory is not None else _default_client_factory
        )
        self._client: Any | None = None

    @property
    def _api_client(self) -> Any:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    def generate(
        self,
        prompt: str,
        *,
        max_output_tokens: int,
        response_format: Literal["text", "json"] = "text",
    ) -> LlmResponse:
        """Make a single LLM call, record usage, return text + token counts.

        Raises:
            ValueError: if max_output_tokens <= 0
            LlmUnavailableError: if retries are exhausted (or the SDK raises an
                                  unrecoverable error like 400 bad request)
        """
        if max_output_tokens <= 0:
            raise ValueError(f"max_output_tokens must be > 0, got {max_output_tokens}")
        # response_format is reserved for future use; v1 returns raw text and
        # the caller parses JSON. Suppress unused warnings.
        _ = response_format

        try:
            response = self._call_with_retry(prompt=prompt, max_tokens=max_output_tokens)
        except RetryError as e:
            inner = e.last_attempt.exception()
            raise LlmUnavailableError(f"LLM exhausted retries: {inner}") from e

        text, in_tokens, out_tokens = self._coerce_response(response)
        self.usage.record(input_tokens=in_tokens, output_tokens=out_tokens)
        return LlmResponse(text=text, input_tokens=in_tokens, output_tokens=out_tokens)

    def check_budget(self, projected_additional_tokens: int) -> None:
        """Pre-compose guard: raise BudgetExceededError if projection overflows."""
        projected_total = self.usage.total_tokens_used + projected_additional_tokens
        if projected_total > self.budget_tokens:
            raise BudgetExceededError(
                f"projected {projected_total} > budget {self.budget_tokens} "
                f"(used: {self.usage.total_tokens_used}, "
                f"projected additional: {projected_additional_tokens})"
            )

    def usage_report(self) -> dict[str, Any]:
        """End-of-run usage ledger for `RenderedIssue.meta` + workflow logs."""
        return {
            "model": self.model,
            "budget_tokens": self.budget_tokens,
            "input_tokens_used": self.usage.input_tokens_used,
            "output_tokens_used": self.usage.output_tokens_used,
            "total_tokens_used": self.usage.total_tokens_used,
            "budget_remaining": self.budget_tokens - self.usage.total_tokens_used,
            "calls": [
                {"input_tokens": c.input_tokens, "output_tokens": c.output_tokens}
                for c in self.usage.calls
            ],
        }

    # --- internals -----------------------------------------------------------

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(
            multiplier=0, min=0, max=0
        ),  # no wait in tests; real prod overrides via env
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=False,
    )
    def _call_with_retry(self, *, prompt: str, max_tokens: int) -> Any:
        try:
            import anthropic  # type: ignore[import-untyped]

            transient_anthropic_types: tuple[type[BaseException], ...] = (
                anthropic.RateLimitError,  # type: ignore[attr-defined]
                anthropic.APIConnectionError,  # type: ignore[attr-defined]
            )
        except ImportError:
            transient_anthropic_types = ()

        client = self._api_client
        try:
            return client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except (ConnectionError, TimeoutError):
            # Known transient — let tenacity retry by re-raising as-is
            raise
        except Exception as e:
            if transient_anthropic_types and isinstance(e, transient_anthropic_types):
                # Anthropic SDK transient — map to ConnectionError so tenacity retries
                raise ConnectionError(f"transient LLM error: {e}") from e
            # Non-transient: 400 bad request, auth, malformed model id, etc.
            raise LlmUnavailableError(f"LLM call failed: {e}") from e

    @staticmethod
    def _coerce_response(response: Any) -> tuple[str, int, int]:
        """Extract text + token counts from the SDK response object.

        FakeLLMClient and real SDK objects both expose .content[0].text and
        .usage.{input_tokens, output_tokens}.
        """
        try:
            content = response.content
            first_block: Any = content[0]
            text = str(first_block.text)
        except (AttributeError, IndexError, TypeError) as e:
            raise LlmUnavailableError(f"malformed LLM response: {e}") from e

        usage = getattr(response, "usage", None)
        in_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        out_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        return text, in_tokens, out_tokens

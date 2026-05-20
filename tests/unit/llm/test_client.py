"""Tests for techletter.llm.client - mirrors TS0002 TC0056-TC0064."""

from __future__ import annotations

import pytest

from techletter.llm import (
    BudgetExceededError,
    LlmClient,
    LlmResponse,
    LlmUnavailableError,
)
from techletter.llm.fake import FakeLLMClient

# --- TC0056: usage accumulates across calls ------------------------------------


def test_tc0056_usage_accumulates() -> None:
    fake = FakeLLMClient(responses=["first answer", "second answer"])
    client = LlmClient(budget_tokens=100_000, client_factory=lambda: fake)

    client.generate(prompt="prompt 1 with some content", max_output_tokens=100)
    client.generate(prompt="prompt 2", max_output_tokens=50)

    assert client.usage.total_tokens_used > 0
    assert client.usage.input_tokens_used > 0
    assert client.usage.output_tokens_used > 0
    assert len(client.usage.calls) == 2


# --- TC0057: check_budget overage raises ---------------------------------------


def test_tc0057_check_budget_overage_raises() -> None:
    fake = FakeLLMClient(responses=["x" * 100])  # ~25 output tokens
    client = LlmClient(budget_tokens=100, client_factory=lambda: fake)
    # Force usage to a known level
    client.usage.record(input_tokens=80, output_tokens=0)
    with pytest.raises(BudgetExceededError) as exc:
        client.check_budget(projected_additional_tokens=50)
    assert "130" in str(exc.value) and "100" in str(exc.value)


# --- TC0058: BudgetExceededError boundary at exact budget ----------------------


def test_tc0058_check_budget_at_exact_budget_passes() -> None:
    """Boundary: projected_total == budget is OK; > budget raises."""
    client = LlmClient(budget_tokens=100, client_factory=lambda: FakeLLMClient())
    client.usage.record(input_tokens=60, output_tokens=0)
    # 60 + 40 = 100 exactly — should pass
    client.check_budget(projected_additional_tokens=40)
    # 60 + 41 = 101 — should raise
    with pytest.raises(BudgetExceededError):
        client.check_budget(projected_additional_tokens=41)


# --- TC0059: check_budget under budget returns silently ------------------------


def test_tc0059_check_budget_under_budget_silent() -> None:
    client = LlmClient(budget_tokens=200_000, client_factory=lambda: FakeLLMClient())
    client.usage.record(input_tokens=160_000, output_tokens=0)
    # 160k + 30k = 190k < 200k
    assert client.check_budget(projected_additional_tokens=30_000) is None


# --- TC0060: tenacity retries on transient failures ----------------------------


def test_tc0060_retries_on_transient_then_succeeds() -> None:
    fake = FakeLLMClient(
        responses=[
            ConnectionError("transient 1"),
            ConnectionError("transient 2"),
            "third attempt succeeds",
        ]
    )
    client = LlmClient(budget_tokens=10_000, client_factory=lambda: fake)
    response = client.generate(prompt="hello", max_output_tokens=100)
    assert "third attempt succeeds" in response.text


# --- TC0061: tenacity exhaustion raises LlmUnavailableError --------------------


def test_tc0061_exhausted_retries_raise_unavailable() -> None:
    fake = FakeLLMClient(responses=[ConnectionError(f"transient {i}") for i in range(10)])
    client = LlmClient(budget_tokens=10_000, client_factory=lambda: fake)
    with pytest.raises(LlmUnavailableError):
        client.generate(prompt="hello", max_output_tokens=100)


# --- TC0062: non-transient error (e.g. bad model) raises immediately ----------


def test_tc0062_non_transient_immediate_raise() -> None:
    fake = FakeLLMClient(responses=[ValueError("bad model id (simulated 400)")])
    client = LlmClient(budget_tokens=10_000, client_factory=lambda: fake)
    with pytest.raises(LlmUnavailableError):
        client.generate(prompt="hello", max_output_tokens=100)


# --- TC0063: usage_report dict shape ------------------------------------------


def test_tc0063_usage_report_shape() -> None:
    fake = FakeLLMClient(responses=["answer one"])
    client = LlmClient(
        budget_tokens=100_000, model="claude-sonnet-4-6", client_factory=lambda: fake
    )
    client.generate(prompt="some prompt", max_output_tokens=50)
    report = client.usage_report()
    expected_keys = {
        "model",
        "budget_tokens",
        "input_tokens_used",
        "output_tokens_used",
        "total_tokens_used",
        "budget_remaining",
        "calls",
    }
    assert set(report.keys()) >= expected_keys
    assert report["model"] == "claude-sonnet-4-6"
    assert report["budget_tokens"] == 100_000
    assert report["total_tokens_used"] > 0
    assert report["budget_remaining"] == report["budget_tokens"] - report["total_tokens_used"]
    assert len(report["calls"]) == 1


# --- TC0064: invalid constructor args raise -----------------------------------


@pytest.mark.parametrize("bad_budget", [0, -1, -1000])
def test_tc0064_budget_tokens_invalid_raises(bad_budget: int) -> None:
    with pytest.raises(ValueError):
        LlmClient(budget_tokens=bad_budget, client_factory=lambda: FakeLLMClient())


@pytest.mark.parametrize("bad_max", [0, -1])
def test_tc0064_max_output_tokens_invalid_raises(bad_max: int) -> None:
    client = LlmClient(budget_tokens=10_000, client_factory=lambda: FakeLLMClient(responses=[]))
    with pytest.raises(ValueError):
        client.generate(prompt="x", max_output_tokens=bad_max)


# --- TC0064b: usage_report before any generate() returns zero-shape -----------


def test_tc0064b_empty_report_is_valid() -> None:
    client = LlmClient(budget_tokens=100_000, client_factory=lambda: FakeLLMClient())
    report = client.usage_report()
    assert report["total_tokens_used"] == 0
    assert report["budget_remaining"] == 100_000
    assert report["calls"] == []


# --- TC0064c: LlmResponse has the right shape ---------------------------------


def test_tc0064c_response_shape() -> None:
    fake = FakeLLMClient(responses=["hello world"])
    client = LlmClient(budget_tokens=10_000, client_factory=lambda: fake)
    response = client.generate(prompt="say hi", max_output_tokens=10)
    assert isinstance(response, LlmResponse)
    assert response.text == "hello world"
    assert response.input_tokens > 0
    assert response.output_tokens > 0

"""Tests for techletter.compose.deep_dive - mirrors TS0002 TC0092-TC0110."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from techletter.compose.deep_dive import (
    ComposeError,
    HypeWordDetected,
    compose_deep_dive,
    format_shipping_signals,
    scrub_hype_words,
)
from techletter.compose.types import DeepDive
from techletter.llm.client import LlmClient
from techletter.llm.fake import FakeLLMClient
from techletter.models import Item
from techletter.pipeline.cluster import Cluster


def _item(
    url: str,
    *,
    source: str = "arxiv",
    kind: str = "paper",
    title: str = "T",
    raw: dict[str, Any] | None = None,
    maturity: str | None = None,
) -> Item:
    return Item.model_validate(
        {
            "source": source,
            "title": title,
            "url": url,
            "summary_excerpt": "summary text",
            "published_at": datetime(2026, 5, 20, tzinfo=UTC),
            "item_kind": kind,
            "maturity": maturity,
            "raw": raw or {},
        }
    )


def _cluster(items: list[Item], topic: str = "Topic") -> Cluster:
    return Cluster(topic=topic, items=items, rationale="rationale")


def _llm_with(payload: dict[str, str]) -> LlmClient:
    return LlmClient(
        budget_tokens=100_000,
        client_factory=lambda: FakeLLMClient(responses=[json.dumps(payload)]),
    )


# --- TC0092: Paper-dominant cluster routes to paper prompt + returns DeepDive --


def test_tc0092_paper_cluster_produces_deepdive() -> None:
    cluster = _cluster(
        [
            _item("https://arxiv.org/abs/2026.0001", kind="paper", title="Paper A"),
            _item("https://arxiv.org/abs/2026.0002", kind="paper", title="Paper B"),
        ]
    )
    llm = _llm_with({"title": "A clear title", "body_md": "Some honest analysis here."})
    dd = compose_deep_dive(cluster, llm, rationale="strong work")
    assert isinstance(dd, DeepDive)
    assert dd.item_kind == "paper"
    assert dd.title == "A clear title"
    assert "honest analysis" in dd.body_md


# --- TC0093: Repo-dominant cluster routes to repo prompt + carries maturity ---


def test_tc0093_repo_cluster_carries_maturity() -> None:
    cluster = _cluster(
        [
            _item(
                "https://github.com/o/r",
                source="github",
                kind="repo",
                maturity="beta",
                raw={"stars": 500, "last_commit_at": "2026-05-20T00:00:00Z"},
            )
        ]
    )
    llm = _llm_with({"title": "Repo title", "body_md": "Active and well-maintained."})
    dd = compose_deep_dive(cluster, llm)
    assert dd.item_kind == "repo"
    assert dd.maturity == "beta"


# --- TC0094: source_count counts distinct sources -----------------------------


def test_tc0094_source_count_distinct() -> None:
    cluster = _cluster(
        [
            _item("https://x/1", source="arxiv", kind="paper"),
            _item("https://x/2", source="arxiv", kind="paper"),
            _item("https://x/3", source="rss", kind="blog_post"),
        ]
    )
    llm = _llm_with({"title": "T", "body_md": "Body."})
    dd = compose_deep_dive(cluster, llm)
    assert dd.source_count == 2  # arxiv + rss


# --- TC0095-0106: BANNED_HYPE_WORDS detection ---------------------------------


@pytest.mark.parametrize(
    "banned",
    ["revolutionary", "groundbreaking", "10x", "game-changing", "AI-powered"],
)
def test_tc0095_hype_word_detection(banned: str) -> None:
    body = f"This is a {banned} new approach to agents."
    with pytest.raises(HypeWordDetected) as exc:
        scrub_hype_words(body)
    assert banned.lower() in str(exc.value).lower()


def test_tc0096_clean_body_passes() -> None:
    # No raise
    scrub_hype_words("This is a careful, well-cited analysis of the methodology.")


def test_tc0097_hype_in_compose_output_raises() -> None:
    cluster = _cluster([_item("https://x/1", kind="paper")])
    llm = _llm_with({"title": "T", "body_md": "This is a revolutionary paper."})
    with pytest.raises(HypeWordDetected):
        compose_deep_dive(cluster, llm)


def test_tc0098_word_boundary_not_substring() -> None:
    """Word-boundary aware: 'leverage' is banned but 'leveraging' is too — only
    if it matches. 'preverage' (containing 'verage') should NOT match 'leverage'."""
    scrub_hype_words("The preverage signal is unusual.")  # no raise


# TC0106: BANNED_HYPE_WORDS is a single shared constant across compose modules
def test_tc0106_banned_hype_words_is_shared_constant() -> None:
    # The frozenset has identity (it's a module-level constant)
    from techletter.compose.deep_dive import BANNED_HYPE_WORDS as bw_dd
    from techletter.compose.types import BANNED_HYPE_WORDS as bw_types

    assert bw_dd is bw_types  # SAME object


# --- TC0107: format_shipping_signals deterministic output ---------------------


def test_tc0107_format_shipping_signals_complete() -> None:
    out = format_shipping_signals(
        {
            "stars": 1250,
            "last_commit_at": "2026-05-15T12:00:00Z",
            "has_recent_release": True,
            "hosted_demo_url": "https://demo.example.com",
        }
    )
    assert "Stars: 1,250" in out
    assert "Last commit: 2026-05-15" in out
    assert "Recent release: yes" in out
    assert "Demo: https://demo.example.com" in out


def test_tc0108_format_shipping_signals_partial() -> None:
    out = format_shipping_signals({"stars": 50})
    assert "Stars: 50" in out


def test_tc0109_format_shipping_signals_empty() -> None:
    out = format_shipping_signals({})
    assert "no signals" in out


# --- TC0110: LLM output missing required fields → ComposeError ----------------


def test_tc0110_missing_field_raises() -> None:
    cluster = _cluster([_item("https://x/1", kind="paper")])
    llm = _llm_with({"title": "T"})  # missing body_md
    with pytest.raises(ComposeError):
        compose_deep_dive(cluster, llm)


def test_tc0110b_invalid_json_raises() -> None:
    cluster = _cluster([_item("https://x/1", kind="paper")])
    fake = FakeLLMClient(responses=["not JSON"])
    llm = LlmClient(budget_tokens=100_000, client_factory=lambda: fake)
    with pytest.raises(ComposeError):
        compose_deep_dive(cluster, llm)

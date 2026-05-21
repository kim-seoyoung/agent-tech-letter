"""Tests for techletter.compose.issue — TC0111-TC0125 (incl. byte-identical determinism)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

import pytest

from techletter.compose.issue import (
    RenderedIssue,
    assemble_issue,
    content_hash,
)
from techletter.compose.types import DeepDive, QuickMention


def _dd(
    cluster_id: str = "c1",
    title: str = "A title",
    body: str = "Body content here.",
    kind: str = "paper",
    maturity: str | None = None,
    url: str = "https://arxiv.org/abs/2026.0001",
    source_count: int = 2,
) -> DeepDive:
    return DeepDive.model_validate(
        {
            "cluster_id": cluster_id,
            "title": title,
            "body_md": body,
            "item_kind": kind,
            "maturity": maturity,
            "primary_url": url,
            "source_count": source_count,
        }
    )


def _qm(title: str = "A repo", one_liner: str = "A line.") -> QuickMention:
    return QuickMention.model_validate(
        {
            "title": title,
            "url": "https://github.com/o/r",
            "source": "github",
            "item_kind": "repo",
            "one_liner": one_liner,
        }
    )


_BASE_ARGS: dict[str, Any] = {
    "issue_id": "issue-2026-05-20",
    "issue_date": datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC),
}


# --- TC0111: assemble_issue returns RenderedIssue --------------------------------


def test_tc0111_returns_rendered_issue() -> None:
    issue = assemble_issue(
        **_BASE_ARGS,
        deep_dives=[
            _dd(title="D1"),
            _dd(title="D2", cluster_id="c2"),
            _dd(title="D3", cluster_id="c3"),
        ],
        quick_mentions=[_qm(title=f"Q{i}", one_liner=f"line {i}") for i in range(3)],
    )
    assert isinstance(issue, RenderedIssue)
    assert issue.issue_id == "issue-2026-05-20"
    assert "AI Agent Weekly" in issue.body_md
    assert "D1" in issue.body_md
    assert "Q0" in issue.body_md


# --- TC0112: deep_dive count outside [2, 5] raises -----------------------------


def test_tc0112_too_few_deep_dives_raises() -> None:
    with pytest.raises(ValueError):
        assemble_issue(**_BASE_ARGS, deep_dives=[_dd()], quick_mentions=[])


def test_tc0112_too_many_deep_dives_raises() -> None:
    with pytest.raises(ValueError):
        assemble_issue(
            **_BASE_ARGS,
            deep_dives=[_dd(cluster_id=f"c{i}") for i in range(6)],
            quick_mentions=[],
        )


def test_tc0112_too_many_quick_mentions_raises() -> None:
    with pytest.raises(ValueError):
        assemble_issue(
            **_BASE_ARGS,
            deep_dives=[_dd(cluster_id=f"c{i}") for i in range(3)],
            quick_mentions=[_qm() for _ in range(11)],
        )


# --- TC0113: Front matter contains required keys -------------------------------


def test_tc0113_front_matter_contains_keys() -> None:
    issue = assemble_issue(
        **_BASE_ARGS,
        deep_dives=[_dd(cluster_id=f"c{i}") for i in range(3)],
        quick_mentions=[_qm() for _ in range(5)],
        usage_report={"total_tokens_used": 12_500, "budget_tokens": 200_000},
        source_counts={"arxiv": 3, "github": 2, "rss": 4},
    )
    assert "issue_id: issue-2026-05-20" in issue.body_md
    assert "tokens_used: 12500" in issue.body_md
    assert "source_count_arxiv: 3" in issue.body_md
    assert "source_count_github: 2" in issue.body_md
    assert "source_count_rss: 4" in issue.body_md


# --- TC0114: item_kind label rendered ------------------------------------------


def test_tc0114_item_kind_labels() -> None:
    issue = assemble_issue(
        **_BASE_ARGS,
        deep_dives=[
            _dd(cluster_id="c1", kind="paper", title="P"),
            _dd(cluster_id="c2", kind="repo", title="R", maturity="beta"),
            _dd(cluster_id="c3", kind="blog_post", title="B"),
        ],
        quick_mentions=[],
    )
    assert "**Paper**" in issue.body_md
    assert "**Repo (beta)**" in issue.body_md
    assert "**Blog**" in issue.body_md


# --- TC0115-0124: Smaller checks ----------------------------------------------


def test_tc0115_content_hash_is_sha256() -> None:
    h = content_hash("hello world")
    assert h == hashlib.sha256(b"hello world").hexdigest()
    assert len(h) == 64


def test_tc0116_quick_mention_count_in_meta() -> None:
    issue = assemble_issue(
        **_BASE_ARGS,
        deep_dives=[_dd(cluster_id=f"c{i}") for i in range(3)],
        quick_mentions=[_qm() for _ in range(7)],
    )
    assert issue.meta["quick_mention_count"] == 7


# --- TC0125: BYTE-IDENTICAL DETERMINISM (the load-bearing test) ---------------


def test_tc0125_byte_identical_determinism() -> None:
    """Two calls with identical inputs produce identical body_md AND sha."""
    args: dict[str, Any] = {
        **_BASE_ARGS,
        "deep_dives": [
            _dd(cluster_id="c1", title="One", body="b1"),
            _dd(cluster_id="c2", title="Two", body="b2"),
            _dd(cluster_id="c3", title="Three", body="b3"),
        ],
        "quick_mentions": [_qm(title=f"Q{i}", one_liner=f"line {i}") for i in range(5)],
        "usage_report": {"total_tokens_used": 50_000, "budget_tokens": 200_000},
        "source_counts": {"arxiv": 2, "github": 1, "rss": 3},
    }
    issue1 = assemble_issue(**args)
    issue2 = assemble_issue(**args)
    assert issue1.body_md == issue2.body_md
    assert issue1.content_sha256 == issue2.content_sha256
    # And the hash matches the actual sha256
    expected = hashlib.sha256(issue1.body_md.encode("utf-8")).hexdigest()
    assert issue1.content_sha256 == expected


def test_tc0125b_source_counts_lexicographic() -> None:
    """source_counts must render in sorted key order for determinism."""
    args1: dict[str, Any] = {
        **_BASE_ARGS,
        "deep_dives": [_dd(cluster_id=f"c{i}") for i in range(3)],
        "quick_mentions": [],
        "source_counts": {"github": 2, "arxiv": 3, "rss": 1},  # insertion order
    }
    args2: dict[str, Any] = {
        **_BASE_ARGS,
        "deep_dives": [_dd(cluster_id=f"c{i}") for i in range(3)],
        "quick_mentions": [],
        "source_counts": {"rss": 1, "arxiv": 3, "github": 2},  # different insertion order
    }
    assert assemble_issue(**args1).body_md == assemble_issue(**args2).body_md


# --- compose_quick_mentions smoke test ----------------------------------------


def test_compose_quick_mentions_returns_list() -> None:
    import json

    from techletter.compose.quick_mentions import compose_quick_mentions
    from techletter.llm.client import LlmClient
    from techletter.llm.fake import FakeLLMClient
    from techletter.models import Item
    from techletter.pipeline.cluster import Cluster

    items = [
        Item.model_validate(
            {
                "source": "github",
                "title": f"Repo {i}",
                "url": f"https://github.com/o/r{i}",
                "summary_excerpt": "s",
                "published_at": datetime(2026, 5, 20, tzinfo=UTC),
                "item_kind": "repo",
                "raw": {},
            }
        )
        for i in range(3)
    ]
    clusters = [Cluster(topic=f"T{i}", items=[items[i]], rationale="") for i in range(3)]
    payload = json.dumps(
        {
            "mentions": [
                {"item_index": 0, "one_liner": "First repo."},
                {"item_index": 1, "one_liner": "Second repo."},
                {"item_index": 2, "one_liner": "Third repo."},
            ]
        }
    )
    fake = FakeLLMClient(responses=[payload])
    llm = LlmClient(budget_tokens=100_000, client_factory=lambda: fake)
    mentions = compose_quick_mentions(clusters, llm)
    assert len(mentions) == 3
    assert mentions[0].title == "Repo 0"
    assert mentions[0].one_liner == "First repo."

"""Tests for techletter.pipeline.rank - mirrors TS0002 TC0080-TC0091."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from techletter.llm.client import BudgetExceededError, LlmClient
from techletter.llm.fake import FakeLLMClient
from techletter.models import Item
from techletter.pipeline.cluster import Cluster
from techletter.pipeline.rank import (
    RankedClusters,
    RankParseError,
    rank_clusters,
)


def _item(url: str, kind: str = "paper", title: str = "T") -> Item:
    return Item.model_validate(
        {
            "source": "arxiv" if kind == "paper" else ("github" if kind == "repo" else "rss"),
            "title": title,
            "url": url,
            "summary_excerpt": "s",
            "published_at": datetime(2026, 5, 20, tzinfo=UTC),
            "item_kind": kind,
            "raw": {},
        }
    )


def _cluster(id_: str, topic: str, items: list[Item]) -> Cluster:
    return Cluster(id=id_, topic=topic, items=items, rationale=f"r-{topic}")


def _scores_response(scored: dict[str, tuple[float, float]]) -> str:
    """Build a fake rank JSON response."""
    return json.dumps(
        {
            "scores": {
                cid: {"significance": sig, "novelty": nov} for cid, (sig, nov) in scored.items()
            },
            "rationale_by_cluster_id": {cid: f"r-for-{cid}" for cid in scored},
        }
    )


# --- TC0080: Empty clusters returns empty RankedClusters with no LLM call -----


def test_tc0080_empty_clusters_no_llm_call() -> None:
    fake = FakeLLMClient(responses=[])
    llm = LlmClient(budget_tokens=100_000, client_factory=lambda: fake)
    result = rank_clusters([], llm)
    assert result == RankedClusters()
    assert fake.call_count == 0


# --- TC0081: Significance + novelty populated on each cluster ------------------


def test_tc0081_scores_populated() -> None:
    clusters = [
        _cluster("c1", "T1", [_item("https://x/1")]),
        _cluster("c2", "T2", [_item("https://x/2")]),
    ]
    fake = FakeLLMClient(responses=[_scores_response({"c1": (0.8, 0.3), "c2": (0.5, 0.6)})])
    llm = LlmClient(budget_tokens=100_000, client_factory=lambda: fake)
    result = rank_clusters(clusters, llm)
    sigs = {c.id: c.significance for c in result.deep + result.quick + result.unselected}
    assert sigs["c1"] == pytest.approx(0.8)
    assert sigs["c2"] == pytest.approx(0.5)


# --- TC0082: Sort order is significance DESC → novelty DESC → input order ----


def test_tc0082_sort_order() -> None:
    clusters = [
        _cluster("a", "TA", [_item("https://x/a")]),  # 0.5/0.5
        _cluster("b", "TB", [_item("https://x/b")]),  # 0.9/0.1
        _cluster("c", "TC", [_item("https://x/c")]),  # 0.5/0.9
    ]
    fake = FakeLLMClient(
        responses=[_scores_response({"a": (0.5, 0.5), "b": (0.9, 0.1), "c": (0.5, 0.9)})]
    )
    llm = LlmClient(budget_tokens=100_000, client_factory=lambda: fake)
    result = rank_clusters(clusters, llm, top_deep=3, top_quick=10)
    ordered_ids = [c.id for c in result.deep + result.quick + result.unselected]
    # b (sig=0.9) → c (sig=0.5, nov=0.9) → a (sig=0.5, nov=0.5)
    assert ordered_ids[:3] == ["b", "c", "a"]


# --- TC0083: top_deep + top_quick selection ----------------------------------


def test_tc0083_top_selection_counts() -> None:
    clusters = [_cluster(f"c{i}", f"T{i}", [_item(f"https://x/{i}")]) for i in range(20)]
    scores = {f"c{i}": (1.0 - i / 20.0, 0.5) for i in range(20)}
    fake = FakeLLMClient(responses=[_scores_response(scores)])
    llm = LlmClient(budget_tokens=400_000, client_factory=lambda: fake)
    result = rank_clusters(clusters, llm, top_deep=3, top_quick=10)
    assert len(result.deep) == 3
    assert len(result.quick) == 10
    assert len(result.unselected) == 7
    assert [c.id for c in result.deep] == ["c0", "c1", "c2"]


# --- TC0084: Fewer clusters than top_deep + top_quick handled silently --------


def test_tc0084_fewer_clusters_than_target() -> None:
    clusters = [_cluster(f"c{i}", f"T{i}", [_item(f"https://x/{i}")]) for i in range(4)]
    scores = {f"c{i}": (1.0 - i / 4.0, 0.5) for i in range(4)}
    fake = FakeLLMClient(responses=[_scores_response(scores)])
    llm = LlmClient(budget_tokens=100_000, client_factory=lambda: fake)
    result = rank_clusters(clusters, llm, top_deep=3, top_quick=10)
    assert len(result.deep) == 3
    assert len(result.quick) == 1
    assert len(result.unselected) == 0


# --- TC0085: rationale_by_cluster_id is populated -----------------------------


def test_tc0085_rationale_populated() -> None:
    clusters = [_cluster("c1", "T1", [_item("https://x/1")])]
    fake = FakeLLMClient(responses=[_scores_response({"c1": (0.8, 0.3)})])
    llm = LlmClient(budget_tokens=100_000, client_factory=lambda: fake)
    result = rank_clusters(clusters, llm)
    assert result.rationale_by_cluster_id["c1"] == "r-for-c1"


# --- TC0086: Score clamping for out-of-range LLM output -----------------------


def test_tc0086_scores_clamped_to_unit(caplog: pytest.LogCaptureFixture) -> None:
    clusters = [_cluster("c1", "T1", [_item("https://x/1")])]
    fake = FakeLLMClient(responses=[_scores_response({"c1": (1.5, -0.2)})])
    llm = LlmClient(budget_tokens=100_000, client_factory=lambda: fake)
    with caplog.at_level("WARNING"):
        result = rank_clusters(clusters, llm)
    c = (result.deep + result.quick + result.unselected)[0]
    assert c.significance == pytest.approx(1.0)
    assert c.novelty == pytest.approx(0.0)
    assert any("clamping" in r.message for r in caplog.records)


# --- TC0087: LLM omits cluster id → RankParseError ----------------------------


def test_tc0087_missing_cluster_id_raises() -> None:
    clusters = [
        _cluster("c1", "T1", [_item("https://x/1")]),
        _cluster("c2", "T2", [_item("https://x/2")]),
    ]
    fake = FakeLLMClient(responses=[_scores_response({"c1": (0.8, 0.3)})])  # missing c2
    llm = LlmClient(budget_tokens=100_000, client_factory=lambda: fake)
    with pytest.raises(RankParseError):
        rank_clusters(clusters, llm)


# --- TC0088: LLM invents an unknown cluster id → RankParseError ---------------


def test_tc0088_extra_cluster_id_raises() -> None:
    clusters = [_cluster("c1", "T1", [_item("https://x/1")])]
    fake = FakeLLMClient(responses=[_scores_response({"c1": (0.8, 0.3), "ghost": (0.5, 0.5)})])
    llm = LlmClient(budget_tokens=100_000, client_factory=lambda: fake)
    with pytest.raises(RankParseError):
        rank_clusters(clusters, llm)


# --- TC0089: Pre-compose budget gate fires (THE critical guard) ---------------


def test_tc0089_pre_compose_budget_gate_raises() -> None:
    """If projected compose tokens push past budget, BudgetExceededError
    is raised BEFORE any compose call is made."""
    clusters = [_cluster("c1", "T1", [_item("https://x/1")])]
    fake = FakeLLMClient(responses=[_scores_response({"c1": (0.8, 0.3)})])
    # Budget is tight enough that projected compose (3 * 8k + 600 = 24,600) overflows
    llm = LlmClient(budget_tokens=10_000, client_factory=lambda: fake)
    with pytest.raises(BudgetExceededError):
        rank_clusters(clusters, llm, top_deep=3, top_quick=10)


# --- TC0090: Stable sort preserves input order on tied scores -----------------


def test_tc0090_stable_sort_on_ties() -> None:
    clusters = [
        _cluster("a", "T1", [_item("https://x/1")]),
        _cluster("b", "T2", [_item("https://x/2")]),
        _cluster("c", "T3", [_item("https://x/3")]),
    ]
    # All identical scores → stable sort preserves a, b, c order
    fake = FakeLLMClient(
        responses=[_scores_response({"a": (0.5, 0.5), "b": (0.5, 0.5), "c": (0.5, 0.5)})]
    )
    llm = LlmClient(budget_tokens=400_000, client_factory=lambda: fake)
    result = rank_clusters(clusters, llm)
    assert [c.id for c in result.deep] == ["a", "b", "c"]


# --- TC0091: Invalid JSON → RankParseError ------------------------------------


def test_tc0091_invalid_json_raises() -> None:
    clusters = [_cluster("c1", "T1", [_item("https://x/1")])]
    fake = FakeLLMClient(responses=["this is not JSON"])
    llm = LlmClient(budget_tokens=100_000, client_factory=lambda: fake)
    with pytest.raises(RankParseError):
        rank_clusters(clusters, llm)


# --- Compose types smoke tests (BANNED_HYPE_WORDS etc.) -----------------------


def test_banned_hype_words_is_frozenset() -> None:
    """TC0106: BANNED_HYPE_WORDS is a single frozenset (identity check downstream)."""
    from techletter.compose.types import BANNED_HYPE_WORDS

    assert isinstance(BANNED_HYPE_WORDS, frozenset)
    assert "revolutionary" in BANNED_HYPE_WORDS
    assert "groundbreaking" in BANNED_HYPE_WORDS
    # The set is non-trivial
    assert len(BANNED_HYPE_WORDS) >= 10


def test_deep_dive_model_basic() -> None:
    from techletter.compose.types import DeepDive

    dd = DeepDive(
        cluster_id="c1",
        title="A title",
        body_md="# Body\n\nWith content.",
        item_kind="paper",
        primary_url="https://arxiv.org/abs/2026.0001",  # type: ignore[arg-type]
        source_count=2,
    )
    assert dd.cluster_id == "c1"
    assert dd.source_count == 2


def test_quick_mention_model_basic() -> None:
    from techletter.compose.types import QuickMention

    qm = QuickMention(
        title="Some repo",
        url="https://github.com/o/r",  # type: ignore[arg-type]
        source="github",
        item_kind="repo",
        one_liner="A trending repo worth a look.",
    )
    assert qm.source == "github"

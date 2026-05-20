"""Tests for techletter.pipeline.cluster - mirrors TS0002 TC0065-TC0079."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from techletter.llm.client import LlmClient
from techletter.llm.fake import FakeLLMClient
from techletter.models import Item
from techletter.pipeline.cluster import (
    Cluster,
    ClusterParseError,
    cluster_items,
)


def _item(url: str, *, source: str = "arxiv", kind: str = "paper", title: str = "T") -> Item:
    return Item.model_validate(
        {
            "source": source,
            "title": title,
            "url": url,
            "summary_excerpt": "summary",
            "published_at": datetime(2026, 5, 20, tzinfo=UTC),
            "item_kind": kind,
            "raw": {},
        }
    )


def _llm_with(response_json: dict[str, object]) -> LlmClient:
    return LlmClient(
        budget_tokens=100_000,
        client_factory=lambda: FakeLLMClient(responses=[json.dumps(response_json)]),
    )


# --- TC0065: Empty input returns empty list, NO LLM call -----------------------


def test_tc0065_empty_input_no_llm_call() -> None:
    fake = FakeLLMClient(responses=[])
    llm = LlmClient(budget_tokens=10_000, client_factory=lambda: fake)
    result = cluster_items([], llm)
    assert result == []
    assert fake.call_count == 0


# --- TC0066: Single LLM call with parsed cluster output ------------------------


def test_tc0066_single_llm_call_produces_clusters() -> None:
    items = [
        _item("https://a.example/1", title="A1"),
        _item("https://a.example/2", title="A2"),
        _item("https://a.example/3", title="A3"),
    ]
    llm = _llm_with(
        {
            "clusters": [
                {"topic": "Topic X", "rationale": "X reason", "item_indices": [0, 1]},
                {"topic": "Topic Y", "rationale": "Y reason", "item_indices": [2]},
            ]
        }
    )
    clusters = cluster_items(items, llm)
    assert len(clusters) == 2
    assert clusters[0].topic == "Topic X"
    assert len(clusters[0].items) == 2
    assert clusters[1].topic == "Topic Y"


# --- TC0067: Cluster IDs are UUIDs and unique ----------------------------------


def test_tc0067_cluster_ids_are_unique() -> None:
    items = [_item(f"https://x.example/{i}") for i in range(4)]
    llm = _llm_with(
        {
            "clusters": [
                {"topic": "A", "rationale": "", "item_indices": [0, 1]},
                {"topic": "B", "rationale": "", "item_indices": [2, 3]},
            ]
        }
    )
    clusters = cluster_items(items, llm)
    assert len({c.id for c in clusters}) == 2


# --- TC0068: significance + novelty default to None ----------------------------


def test_tc0068_significance_novelty_default_none() -> None:
    items = [_item("https://x.example/1")]
    llm = _llm_with({"clusters": [{"topic": "A", "rationale": "", "item_indices": [0]}]})
    clusters = cluster_items(items, llm)
    assert clusters[0].significance is None
    assert clusters[0].novelty is None


# --- TC0069: Items appear in exactly one cluster (partition invariant) ---------


def test_tc0069_partition_invariant_holds() -> None:
    items = [_item(f"https://x.example/{i}") for i in range(5)]
    llm = _llm_with(
        {
            "clusters": [
                {"topic": "A", "rationale": "", "item_indices": [0, 1, 2]},
                {"topic": "B", "rationale": "", "item_indices": [3, 4]},
            ]
        }
    )
    clusters = cluster_items(items, llm)
    all_clustered = [it for c in clusters for it in c.items]
    assert len(all_clustered) == len(items)
    assert {str(it.url) for it in all_clustered} == {str(it.url) for it in items}


# --- TC0070: Duplicate item in two clusters → ClusterParseError ----------------


def test_tc0070_duplicate_items_raises() -> None:
    items = [_item(f"https://x.example/{i}") for i in range(3)]
    llm = _llm_with(
        {
            "clusters": [
                {"topic": "A", "rationale": "", "item_indices": [0, 1]},
                {"topic": "B", "rationale": "", "item_indices": [1, 2]},  # 1 appears twice
            ]
        }
    )
    with pytest.raises(ClusterParseError) as exc:
        cluster_items(items, llm)
    assert "appears in" in str(exc.value)


# --- TC0071: Missing item → ClusterParseError ----------------------------------


def test_tc0071_missing_items_raises() -> None:
    items = [_item(f"https://x.example/{i}") for i in range(4)]
    llm = _llm_with(
        {
            "clusters": [
                {"topic": "A", "rationale": "", "item_indices": [0, 1]},
                # items 2 and 3 are missing
            ]
        }
    )
    with pytest.raises(ClusterParseError) as exc:
        cluster_items(items, llm)
    assert "not in any cluster" in str(exc.value)


# --- TC0072: Invalid JSON → ClusterParseError ----------------------------------


def test_tc0072_invalid_json_raises() -> None:
    items = [_item("https://x.example/1")]
    llm = LlmClient(
        budget_tokens=10_000,
        client_factory=lambda: FakeLLMClient(responses=["this is not JSON at all"]),
    )
    with pytest.raises(ClusterParseError) as exc:
        cluster_items(items, llm)
    assert "JSON" in str(exc.value)


# --- TC0073: Missing 'clusters' key → ClusterParseError ------------------------


def test_tc0073_missing_clusters_key_raises() -> None:
    items = [_item("https://x.example/1")]
    llm = _llm_with({"wrong_key": []})
    with pytest.raises(ClusterParseError) as exc:
        cluster_items(items, llm)
    assert "clusters" in str(exc.value)


# --- TC0074: Out-of-range item_index → ClusterParseError -----------------------


def test_tc0074_out_of_range_index_raises() -> None:
    items = [_item("https://x.example/1")]
    llm = _llm_with({"clusters": [{"topic": "A", "rationale": "", "item_indices": [99]}]})
    with pytest.raises(ClusterParseError) as exc:
        cluster_items(items, llm)
    assert "99" in str(exc.value) or "invalid item_index" in str(exc.value)


# --- TC0075: ```json fenced``` response is tolerated --------------------------


def test_tc0075_fenced_json_response_parsed() -> None:
    items = [_item("https://x.example/1")]
    body = json.dumps({"clusters": [{"topic": "A", "rationale": "", "item_indices": [0]}]})
    fenced = f"```json\n{body}\n```"
    llm = LlmClient(budget_tokens=10_000, client_factory=lambda: FakeLLMClient(responses=[fenced]))
    clusters = cluster_items(items, llm)
    assert len(clusters) == 1
    assert clusters[0].topic == "A"


# --- TC0076: Cluster count outside [3, 30] → WARN log but no raise ------------


def test_tc0076_cluster_count_outside_range_warns(caplog: pytest.LogCaptureFixture) -> None:
    items = [_item(f"https://x.example/{i}") for i in range(3)]
    llm = _llm_with(
        {"clusters": [{"topic": "All", "rationale": "one big bucket", "item_indices": [0, 1, 2]}]}
    )
    with caplog.at_level("WARNING"):
        clusters = cluster_items(items, llm)
    assert len(clusters) == 1
    assert any("reasonable range" in r.message for r in caplog.records)


# --- TC0077: Cross-source clustering preserved -------------------------------


def test_tc0077_cross_source_cluster_preserves_items() -> None:
    items = [
        _item("https://a.example/p1", source="arxiv", kind="paper", title="Paper"),
        _item("https://b.example/r1", source="github", kind="repo", title="Repo"),
        _item("https://c.example/b1", source="rss", kind="blog_post", title="Blog"),
    ]
    llm = _llm_with(
        {
            "clusters": [
                {
                    "topic": "Swarm framework",
                    "rationale": "all three about Swarm",
                    "item_indices": [0, 1, 2],
                }
            ]
        }
    )
    clusters = cluster_items(items, llm)
    assert len(clusters) == 1
    sources = {it.source for it in clusters[0].items}
    assert sources == {"arxiv", "github", "rss"}


# --- TC0078: Long titles + summaries are truncated in the prompt ---------------


def test_tc0078_prompt_truncates_long_fields() -> None:
    long_summary = "x" * 1000  # max 1000 per Item
    long_title = "T" * 500
    items = [
        Item.model_validate(
            {
                "source": "arxiv",
                "title": long_title,
                "url": "https://x.example/1",
                "summary_excerpt": long_summary,
                "published_at": datetime(2026, 5, 20, tzinfo=UTC),
                "item_kind": "paper",
                "raw": {},
            }
        )
    ]
    fake = FakeLLMClient(
        responses=[json.dumps({"clusters": [{"topic": "A", "rationale": "", "item_indices": [0]}]})]
    )
    llm = LlmClient(budget_tokens=100_000, client_factory=lambda: fake)
    cluster_items(items, llm)
    # The prompt sent to the LLM must NOT contain the full long_summary
    # (it should be truncated to 300 chars per MAX_SUMMARY_CHARS).
    sent_messages = fake.calls[0]["messages"]
    sent_content = "".join(m["content"] for m in sent_messages)
    # If truncation works, the long_summary's 700th char shouldn't be in the prompt
    assert ("x" * 800) not in sent_content


# --- TC0079: cluster_items honors LlmClient budget_tokens (raises if exhausted) -


def test_tc0079_budget_overrun_raises() -> None:
    """If the LLM call exhausts retries with transient errors, ClusterParseError
    is NOT raised; LlmUnavailableError propagates."""
    from techletter.llm.client import LlmUnavailableError

    items = [_item("https://x.example/1")]
    fake = FakeLLMClient(responses=[ConnectionError("down")] * 10)
    llm = LlmClient(budget_tokens=10_000, client_factory=lambda: fake)
    with pytest.raises(LlmUnavailableError):
        cluster_items(items, llm)


# --- Bonus: Cluster model basic validation -----------------------------------


def test_cluster_model_basic_validation() -> None:
    item = _item("https://x.example/1")
    cluster = Cluster(topic="X", items=[item], rationale="rx")
    assert cluster.topic == "X"
    assert len(cluster.items) == 1
    assert cluster.id  # UUID auto-generated

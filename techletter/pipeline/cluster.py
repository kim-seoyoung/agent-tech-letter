"""Cluster step: group items into topical clusters via a single LLM call.

Per US0007: one LLM call per run, JSON output with item indices (not full
item bodies, to keep the response compact). After parse, indices are
mapped back to Item objects and invariants are validated:

- No item appears in more than one cluster.
- The union of clustered items equals the input set (no losses).

Significance + novelty scoring lives in US0008's rank step.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field

from techletter.llm.client import LlmClient
from techletter.llm.prompts import load_prompt
from techletter.models import Item

__all__ = ["Cluster", "ClusterParseError", "cluster_items"]

logger = logging.getLogger(__name__)

# Bounded cluster count — a single bucket or 50 singletons are equally useless.
MIN_REASONABLE_CLUSTERS = 3
MAX_REASONABLE_CLUSTERS = 30

# Per AC3: item-in-prompt body bounds
MAX_TITLE_CHARS = 200
MAX_SUMMARY_CHARS = 300

# LLM output budget for the cluster JSON
CLUSTER_OUTPUT_TOKENS = 4096


class ClusterParseError(Exception):
    """Raised when the LLM cluster output cannot be reconciled with input."""


class Cluster(BaseModel):
    """A topical cluster of items.

    `significance` + `novelty` are filled in by the rank step (US0008);
    they default to None here.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    items: list[Item]
    rationale: str = ""
    significance: float | None = None
    novelty: float | None = None


def cluster_items(items: list[Item], llm: LlmClient) -> list[Cluster]:
    """Cluster items into topics via one LLM call.

    Args:
        items: normalised Items from the source layer (EP0001 output)
        llm: configured LlmClient

    Returns:
        list of Cluster objects (significance + novelty are None;
        US0008's rank step fills them in)

    Raises:
        ClusterParseError: if the LLM output cannot be reconciled with input
    """
    if not items:
        logger.info("cluster: no items to cluster; skipping LLM call")
        return []

    prompt = _build_prompt(items)
    logger.info("cluster: prompt size = %d chars across %d items", len(prompt), len(items))

    response = llm.generate(
        prompt=prompt, max_output_tokens=CLUSTER_OUTPUT_TOKENS, response_format="json"
    )

    parsed = _parse_response(response.text)
    clusters = _materialize_clusters(parsed, items)
    _validate_partition(clusters, items)

    n = len(clusters)
    if n < MIN_REASONABLE_CLUSTERS or n > MAX_REASONABLE_CLUSTERS:
        logger.warning(
            "cluster: produced %d clusters, outside reasonable range [%d, %d] — HYL should inspect",
            n,
            MIN_REASONABLE_CLUSTERS,
            MAX_REASONABLE_CLUSTERS,
        )

    return clusters


def _build_prompt(items: list[Item]) -> str:
    template = load_prompt("cluster")
    item_lines: list[str] = []
    for i, item in enumerate(items):
        title = item.title[:MAX_TITLE_CHARS]
        summary = item.summary_excerpt[:MAX_SUMMARY_CHARS]
        item_lines.append(
            f"{i}. [{item.source}/{item.item_kind}] {title}\n"
            f"   url: {item.url}\n"
            f"   summary: {summary}"
        )
    item_block = "\n\n".join(item_lines)
    return template.replace("{{ITEMS}}", item_block)


def _parse_response(text: str) -> dict[str, Any]:
    """Extract the JSON object from the LLM response.

    Robust to ```json``` code fences or leading prose.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        # strip ``` fences (with or without language tag)
        lines = stripped.splitlines()
        start = 1
        end = len(lines)
        if lines[-1].strip().startswith("```"):
            end -= 1
        stripped = "\n".join(lines[start:end])
    try:
        parsed: Any = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ClusterParseError(f"LLM output is not valid JSON: {e}") from e
    if not isinstance(parsed, dict):
        raise ClusterParseError(f"LLM output is not a JSON object, got {type(parsed).__name__}")
    parsed_dict = cast(dict[str, Any], parsed)
    if "clusters" not in parsed_dict:
        raise ClusterParseError("LLM output missing required 'clusters' key")
    return parsed_dict


def _materialize_clusters(parsed: dict[str, Any], items: list[Item]) -> list[Cluster]:
    raw_clusters: Any = parsed["clusters"]
    if not isinstance(raw_clusters, list):
        raise ClusterParseError(f"'clusters' must be a list, got {type(raw_clusters).__name__}")

    out: list[Cluster] = []
    for i, raw_any in enumerate(cast(list[Any], raw_clusters)):
        if not isinstance(raw_any, dict):
            raise ClusterParseError(f"cluster {i} is not an object")
        raw = cast(dict[str, Any], raw_any)
        try:
            topic = str(raw["topic"]).strip()
            rationale = str(raw.get("rationale", "")).strip()
            idx_field: Any = raw["item_indices"]
        except KeyError as e:
            raise ClusterParseError(f"cluster {i} missing required key: {e}") from e
        if not isinstance(idx_field, list):
            raise ClusterParseError(
                f"cluster {i} item_indices must be a list, got {type(idx_field).__name__}"
            )
        cluster_items_list: list[Item] = []
        for idx_any in cast(list[Any], idx_field):
            if not isinstance(idx_any, int) or idx_any < 0 or idx_any >= len(items):
                raise ClusterParseError(
                    f"cluster {i} has invalid item_index {idx_any!r} (range [0, {len(items)}))"
                )
            cluster_items_list.append(items[idx_any])
        out.append(Cluster(topic=topic, items=cluster_items_list, rationale=rationale))
    return out


def _validate_partition(clusters: list[Cluster], items: list[Item]) -> None:
    """AC5: items form a partition — no duplicates, no losses."""
    seen_urls: dict[str, int] = {}  # url -> cluster index
    for ci, cluster in enumerate(clusters):
        for item in cluster.items:
            url = str(item.url)
            if url in seen_urls:
                raise ClusterParseError(
                    f"item {url!r} appears in cluster {seen_urls[url]} and cluster {ci}"
                )
            seen_urls[url] = ci

    input_urls = {str(item.url) for item in items}
    missing = input_urls - set(seen_urls)
    if missing:
        raise ClusterParseError(
            f"{len(missing)} input items not in any cluster: {sorted(missing)[:5]}"
        )

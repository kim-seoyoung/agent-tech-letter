"""Rank step: score clusters by significance + novelty, select top-N for deep
dives and next-M for quick mentions.

Per US0008: one LLM call per run; item_kind-aware rubric in `prompts/rank.md`.
After scoring, the step calls `llm.check_budget(COMPOSE_BUDGET_ESTIMATE)` —
this is where the pre-compose budget gate (TC0089) actually fires.
"""

from __future__ import annotations

import json
import logging
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field

from techletter.llm.client import LlmClient
from techletter.llm.prompts import load_prompt
from techletter.pipeline.cluster import Cluster

__all__ = ["RankParseError", "RankedClusters", "rank_clusters"]

logger = logging.getLogger(__name__)

RANK_OUTPUT_TOKENS = 4096

# Conservative per-section compose-cost estimates (input + output combined).
# Used to pre-flight the compose budget after ranking.
DEEP_DIVE_COST_TOKENS = 8_000
QUICK_MENTION_COST_TOKENS = 600  # batched for all 10


class RankParseError(Exception):
    """Raised when the LLM rank output cannot be reconciled with input clusters."""


class RankedClusters(BaseModel):
    """Output of the rank step.

    `deep` and `quick` are ordered by combined significance/novelty score
    (descending; stable sort preserves input order on ties).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    deep: list[Cluster] = Field(default_factory=lambda: [])
    quick: list[Cluster] = Field(default_factory=lambda: [])
    unselected: list[Cluster] = Field(default_factory=lambda: [])
    rationale_by_cluster_id: dict[str, str] = Field(default_factory=lambda: {})


def rank_clusters(
    clusters: list[Cluster],
    llm: LlmClient,
    *,
    top_deep: int = 3,
    top_quick: int = 10,
) -> RankedClusters:
    """Score and rank clusters; return top-N as deep, next-M as quick.

    Stable sort: significance DESC → novelty DESC → original insertion order.

    Calls `llm.check_budget(COMPOSE_BUDGET_ESTIMATE)` before returning —
    raises `BudgetExceededError` if projected compose tokens would exceed
    the run budget.

    Raises:
        RankParseError: if the LLM omits or invents a cluster id
        BudgetExceededError: if projected compose would exceed budget
    """
    if not clusters:
        logger.info("rank: no clusters to rank; skipping LLM call")
        return RankedClusters()

    prompt = _build_prompt(clusters)
    response = llm.generate(
        prompt=prompt, max_output_tokens=RANK_OUTPUT_TOKENS, response_format="json"
    )

    parsed = _parse_response(response.text)
    scored = _apply_scores(clusters, parsed)
    deep, quick, unselected = _select(scored, top_deep=top_deep, top_quick=top_quick)
    raw_rationales: Any = parsed.get("rationale_by_cluster_id", {})
    rationale_map: dict[str, str] = (
        {k: str(v) for k, v in cast(dict[str, Any], raw_rationales).items()}
        if isinstance(raw_rationales, dict)
        else {}
    )
    rationales: dict[str, str] = {c.id: rationale_map.get(c.id, "") for c in scored}

    # Pre-compose budget gate (per US0008 AC + TC0089)
    projected = top_deep * DEEP_DIVE_COST_TOKENS + QUICK_MENTION_COST_TOKENS
    llm.check_budget(projected_additional_tokens=projected)

    return RankedClusters(
        deep=deep,
        quick=quick,
        unselected=unselected,
        rationale_by_cluster_id=rationales,
    )


def _build_prompt(clusters: list[Cluster]) -> str:
    template = load_prompt("rank")
    blocks: list[str] = []
    for c in clusters:
        kinds: dict[str, int] = {}
        for it in c.items:
            kinds[it.item_kind] = kinds.get(it.item_kind, 0) + 1
        kinds_str = ", ".join(f"{k}:{v}" for k, v in sorted(kinds.items()))
        sample_titles = [it.title[:120] for it in c.items[:2]]
        blocks.append(
            f"cluster_id: {c.id}\n"
            f"topic: {c.topic}\n"
            f"rationale: {c.rationale}\n"
            f"item_kinds: {kinds_str}\n"
            f"sample_titles: {' | '.join(sample_titles)}"
        )
    return template.replace("{{CLUSTERS}}", "\n\n---\n\n".join(blocks))


def _parse_response(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        end = len(lines)
        if lines[-1].strip().startswith("```"):
            end -= 1
        stripped = "\n".join(lines[1:end])
    try:
        parsed: Any = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise RankParseError(f"LLM output is not valid JSON: {e}") from e
    if not isinstance(parsed, dict):
        raise RankParseError(f"LLM output is not a JSON object, got {type(parsed).__name__}")
    return cast(dict[str, Any], parsed)


def _apply_scores(clusters: list[Cluster], parsed: dict[str, Any]) -> list[Cluster]:
    """Apply scores in place (preserving Cluster instance identity) and validate.

    LLM response shape:
        {
          "scores": {
            "<cluster_id>": {"significance": 0.8, "novelty": 0.4},
            ...
          },
          "rationale_by_cluster_id": { "<cluster_id>": "...", ... }
        }
    """
    raw_scores: Any = parsed.get("scores")
    if not isinstance(raw_scores, dict):
        raise RankParseError("LLM output missing 'scores' object")
    scores = cast(dict[str, Any], raw_scores)

    expected_ids = {c.id for c in clusters}
    actual_ids = set(scores.keys())
    missing = expected_ids - actual_ids
    if missing:
        raise RankParseError(f"LLM scores missing {len(missing)} cluster id(s)")
    extra = actual_ids - expected_ids
    if extra:
        raise RankParseError(f"LLM scored unknown cluster id(s): {sorted(extra)[:3]}")

    for c in clusters:
        entry_any: Any = scores[c.id]
        if not isinstance(entry_any, dict):
            raise RankParseError(f"score for {c.id} is not an object")
        entry = cast(dict[str, Any], entry_any)
        sig = _clamp_to_unit(entry.get("significance", 0.0))
        nov = _clamp_to_unit(entry.get("novelty", 0.5))
        c.significance = sig
        c.novelty = nov

    return clusters


def _clamp_to_unit(v: Any) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        logger.warning("rank: non-numeric score %r; defaulting to 0.0", v)
        return 0.0
    if f < 0.0:
        logger.warning("rank: score %.3f < 0; clamping to 0.0", f)
        return 0.0
    if f > 1.0:
        logger.warning("rank: score %.3f > 1; clamping to 1.0", f)
        return 1.0
    return f


def _select(
    scored: list[Cluster], *, top_deep: int, top_quick: int
) -> tuple[list[Cluster], list[Cluster], list[Cluster]]:
    """Stable selection: significance DESC → novelty DESC → input order."""
    indexed: list[tuple[int, Cluster]] = list(enumerate(scored))

    def _sort_key(pair: tuple[int, Cluster]) -> tuple[float, float, int]:
        idx, c = pair
        return (-(c.significance or 0.0), -(c.novelty or 0.0), idx)

    indexed.sort(key=_sort_key)
    sorted_clusters = [c for _, c in indexed]
    deep = sorted_clusters[:top_deep]
    quick = sorted_clusters[top_deep : top_deep + top_quick]
    unselected = sorted_clusters[top_deep + top_quick :]
    return deep, quick, unselected

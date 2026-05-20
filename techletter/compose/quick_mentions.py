"""Batch quick-mention composition.

One LLM call produces all 10 quick-mention one-liners from the selected
clusters. Per US0011 — supports US0011 only.
"""

from __future__ import annotations

import json
import logging
from typing import Any, cast

from techletter.compose.deep_dive import scrub_hype_words
from techletter.compose.types import QuickMention
from techletter.llm.client import LlmClient
from techletter.llm.prompts import load_prompt
from techletter.pipeline.cluster import Cluster

__all__ = ["QuickMentionsParseError", "compose_quick_mentions"]

logger = logging.getLogger(__name__)

QUICK_MENTIONS_OUTPUT_TOKENS = 1500


class QuickMentionsParseError(Exception):
    """Raised when the LLM quick-mentions output cannot be parsed."""


def compose_quick_mentions(clusters: list[Cluster], llm: LlmClient) -> list[QuickMention]:
    """Compose quick mentions for the given clusters in a single LLM call.

    Returns one QuickMention per cluster (picking the highest-significance
    item from each cluster as the surface item).
    """
    if not clusters:
        return []

    template = load_prompt("quick_mentions")
    surface_items = [c.items[0] for c in clusters]
    items_block = "\n".join(
        f"{i}. [{it.source}/{it.item_kind}] {it.title}\n   url: {it.url}\n"
        f"   summary: {it.summary_excerpt[:200]}"
        for i, it in enumerate(surface_items)
    )
    prompt = template.replace("{{ITEMS}}", items_block)

    response = llm.generate(
        prompt=prompt,
        max_output_tokens=QUICK_MENTIONS_OUTPUT_TOKENS,
        response_format="json",
    )
    parsed = _parse(response.text)

    raw_mentions: Any = parsed.get("mentions")
    if not isinstance(raw_mentions, list):
        raise QuickMentionsParseError("missing or non-list 'mentions'")

    out: list[QuickMention] = []
    for i, raw_any in enumerate(cast(list[Any], raw_mentions)):
        if not isinstance(raw_any, dict):
            raise QuickMentionsParseError(f"mention {i} not an object")
        raw = cast(dict[str, Any], raw_any)
        idx_raw: Any = raw.get("item_index", i)
        if not isinstance(idx_raw, int) or idx_raw < 0 or idx_raw >= len(surface_items):
            raise QuickMentionsParseError(f"mention {i} bad item_index {idx_raw!r}")
        one_liner = str(raw.get("one_liner", "")).strip()
        if not one_liner:
            raise QuickMentionsParseError(f"mention {i} missing one_liner")
        scrub_hype_words(one_liner)
        source_item = surface_items[idx_raw]
        out.append(
            QuickMention(
                title=source_item.title[:200],
                url=source_item.url,
                source=source_item.source,
                item_kind=source_item.item_kind,
                one_liner=one_liner[:300],
            )
        )
    return out


def _parse(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        end = len(lines) - (1 if lines[-1].strip().startswith("```") else 0)
        stripped = "\n".join(lines[1:end])
    try:
        parsed: Any = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise QuickMentionsParseError(f"invalid JSON: {e}") from e
    if not isinstance(parsed, dict):
        raise QuickMentionsParseError("not a JSON object")
    return cast(dict[str, Any], parsed)

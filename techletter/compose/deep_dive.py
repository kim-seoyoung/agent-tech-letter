"""Deep-dive composition (paper / repo / blog_post variants).

Each cluster selected for deep-dive is rendered via a single LLM call,
using an `item_kind`-conditioned prompt (`prompts/compose_{paper,repo,blog}.md`).
The output is validated against `BANNED_HYPE_WORDS` and parsed into a
`DeepDive` model.

Per US0009 (paper), US0010 (repo), US0011 (blog) — shared compose surface.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from typing import Any, Literal, cast

from techletter.compose.types import BANNED_HYPE_WORDS, DeepDive
from techletter.llm.client import LlmClient
from techletter.llm.prompts import load_prompt
from techletter.models import Item, Maturity
from techletter.pipeline.cluster import Cluster

__all__ = [
    "ComposeError",
    "HypeWordDetected",
    "compose_deep_dive",
    "format_shipping_signals",
    "scrub_hype_words",
]

logger = logging.getLogger(__name__)

DEEP_DIVE_OUTPUT_TOKENS = 2_000


class ComposeError(Exception):
    """Raised when the LLM compose output cannot be parsed."""


class HypeWordDetected(Exception):
    """Raised when the LLM produced a banned hype word in the deep-dive body."""


def compose_deep_dive(
    cluster: Cluster,
    llm: LlmClient,
    *,
    rationale: str = "",
) -> DeepDive:
    """Compose one deep-dive section for the cluster.

    Dispatches by the dominant `item_kind` in the cluster:
    - paper-dominant   → prompts/compose_paper.md
    - repo-dominant    → prompts/compose_repo.md
    - blog_post-dominant → prompts/compose_blog.md  (US0011)

    Raises:
        ComposeError: if the LLM output is unparseable or missing fields
        HypeWordDetected: if a BANNED_HYPE_WORDS token appears in the body
    """
    item_kind = _dominant_kind(cluster)
    prompt_name = _prompt_for_kind(item_kind)
    template = load_prompt(prompt_name)
    prompt = _render_prompt(template, cluster, rationale)

    response = llm.generate(
        prompt=prompt, max_output_tokens=DEEP_DIVE_OUTPUT_TOKENS, response_format="json"
    )

    parsed = _parse_response(response.text)
    title = str(parsed.get("title", "")).strip()
    body_md = str(parsed.get("body_md", "")).strip()
    if not title or not body_md:
        raise ComposeError("LLM output missing 'title' or 'body_md'")

    scrub_hype_words(body_md)

    primary_item = _primary_item(cluster, item_kind)
    maturity = _maturity_from_cluster(cluster, item_kind)
    return DeepDive(
        cluster_id=cluster.id,
        title=title,
        body_md=body_md,
        item_kind=item_kind,
        maturity=maturity,
        primary_url=primary_item.url,  # type: ignore[arg-type]
        source_count=len({it.source for it in cluster.items}),
    )


def scrub_hype_words(text: str) -> None:
    """Raise HypeWordDetected if any BANNED_HYPE_WORDS token appears.

    Word-boundary aware (case-insensitive). Single source of truth identity:
    callers must `from techletter.compose.types import BANNED_HYPE_WORDS` —
    TC0106 asserts the constant is shared across paper/repo/blog modules.
    """
    text_lower = text.lower()
    for banned in BANNED_HYPE_WORDS:
        if re.search(rf"\b{re.escape(banned)}\b", text_lower):
            raise HypeWordDetected(f"banned hype word in body: {banned!r}")


def format_shipping_signals(meta: dict[str, Any]) -> str:
    """Format a repo's shipping signals into a one-line markdown string.

    Pure deterministic helper — TDD-friendly. Used by the repo compose
    prompt as a pre-rendered context block.

    Example output: "Stars: 1,250 · Last commit: 2026-05-15 · Recent
    release: yes · Demo: https://example.com"
    """
    parts: list[str] = []
    stars = meta.get("stars")
    if isinstance(stars, int):
        parts.append(f"Stars: {stars:,}")
    last_commit = meta.get("last_commit_at")
    if isinstance(last_commit, str) and last_commit:
        parts.append(f"Last commit: {last_commit[:10]}")
    has_release = meta.get("has_recent_release")
    if isinstance(has_release, bool):
        parts.append(f"Recent release: {'yes' if has_release else 'no'}")
    demo = meta.get("hosted_demo_url")
    if isinstance(demo, str) and demo:
        parts.append(f"Demo: {demo}")
    return " · ".join(parts) if parts else "(no signals available)"


# --- internals -----------------------------------------------------------


def _dominant_kind(cluster: Cluster) -> Literal["paper", "blog_post", "repo"]:
    if not cluster.items:
        raise ComposeError(f"cluster {cluster.id} has no items")
    counts = Counter(it.item_kind for it in cluster.items)
    most_common, _ = counts.most_common(1)[0]
    if most_common == "paper":
        return "paper"
    if most_common == "repo":
        return "repo"
    if most_common == "blog_post":
        return "blog_post"
    raise ComposeError(f"unrecognised item_kind: {most_common}")


def _prompt_for_kind(kind: Literal["paper", "blog_post", "repo"]) -> str:
    return {
        "paper": "compose_paper",
        "repo": "compose_repo",
        "blog_post": "compose_blog",
    }[kind]


def _render_prompt(template: str, cluster: Cluster, rationale: str) -> str:
    items_block_lines: list[str] = []
    for it in cluster.items:
        items_block_lines.append(
            f"- [{it.source}/{it.item_kind}] {it.title}\n  url: {it.url}\n"
            f"  summary: {it.summary_excerpt[:400]}"
        )
    items_block = "\n".join(items_block_lines)

    primary = _primary_item(cluster, _dominant_kind(cluster))
    shipping = ""
    if primary.item_kind == "repo":
        shipping = format_shipping_signals(dict(primary.raw))

    rendered = template
    rendered = rendered.replace("{{TOPIC}}", cluster.topic)
    rendered = rendered.replace("{{RATIONALE}}", rationale or cluster.rationale)
    rendered = rendered.replace("{{ITEMS}}", items_block)
    rendered = rendered.replace("{{SHIPPING_SIGNALS}}", shipping)
    return rendered


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
        raise ComposeError(f"LLM output is not valid JSON: {e}") from e
    if not isinstance(parsed, dict):
        raise ComposeError("LLM output is not a JSON object")
    return cast(dict[str, Any], parsed)


def _primary_item(cluster: Cluster, kind: Literal["paper", "blog_post", "repo"]) -> Item:
    """Pick the first item matching the dominant kind."""
    for it in cluster.items:
        if it.item_kind == kind:
            return it
    return cluster.items[0]


def _maturity_from_cluster(
    cluster: Cluster, kind: Literal["paper", "blog_post", "repo"]
) -> Maturity | None:
    if kind != "repo":
        return None
    primary = _primary_item(cluster, kind)
    return primary.maturity

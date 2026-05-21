"""RenderedIssue model + `assemble_issue` — the deterministic Markdown renderer.

Per US0011 + TC0125: `assemble_issue` must produce byte-identical output for
identical inputs (verified via sha256). This is load-bearing for EP0003's
idempotency story — the workflow uses content hashes to decide whether a
"send" is a retry of an existing issue or a new one.

Determinism rules:
- DeepDive sections rendered in the order given
- QuickMention sections rendered in the order given
- Front matter keys in fixed lexicographic order
- Datetimes formatted as ISO-8601 with Z suffix
- No use of dict.items() order from untrusted sources
- No random IDs or timestamps inside the render (the caller passes them)
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from techletter.compose.types import DeepDive, QuickMention

__all__ = [
    "IssueStructure",
    "RenderedIssue",
    "assemble_issue",
    "content_hash",
]


class IssueStructure(BaseModel):
    """Sidecar JSON schema: full `RenderedIssue` minus `body_md` (cross-checked).

    Per US0023: written alongside `drafts/<issue_id>.md` so `send` can
    reconstruct structured `DeepDive` / `QuickMention` data — channel
    renderers can then operate on structure instead of regex-parsing the
    Markdown body. `content_sha256` MUST remain derived from `body_md`
    alone; this sidecar does not participate in the idempotency hash.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int = 1
    issue_id: str
    issue_date: datetime
    body_md: str  # mirror of the .md content for the cross-check (AC6)
    deep_dives: list[DeepDive]
    quick_mentions: list[QuickMention]
    meta: dict[str, Any] = Field(default_factory=lambda: {})
    content_sha256: str


class RenderedIssue(BaseModel):
    """A fully-rendered weekly issue, ready for delivery.

    `body_md` is the canonical Markdown body the channel adapters consume.
    `deep_dives` / `quick_mentions` carry the structured data (post-US0023);
    empty lists are the legacy fallback path when no sidecar JSON exists.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    issue_id: str
    issue_date: datetime
    body_md: str
    deep_dives: list[DeepDive] = Field(default_factory=lambda: [])
    quick_mentions: list[QuickMention] = Field(default_factory=lambda: [])
    meta: dict[str, Any] = Field(default_factory=lambda: {})
    content_sha256: str

    def to_sidecar_json(self) -> str:
        """Serialise to the sidecar JSON format (US0023 AC2)."""
        s = IssueStructure(
            issue_id=self.issue_id,
            issue_date=self.issue_date,
            body_md=self.body_md,
            deep_dives=list(self.deep_dives),
            quick_mentions=list(self.quick_mentions),
            meta=dict(self.meta),
            content_sha256=self.content_sha256,
        )
        return s.model_dump_json(indent=2)

    @classmethod
    def from_sidecar_json(
        cls, json_str: str, *, body_md: str
    ) -> tuple[RenderedIssue, list[str]]:
        """Reconstruct from sidecar JSON; `body_md` is authoritative (.md wins).

        Returns `(issue, warnings)`. Warnings are non-fatal — caller logs them.
        """
        warnings: list[str] = []
        s = IssueStructure.model_validate_json(json_str)
        if s.body_md != body_md:
            warnings.append(
                "sidecar body_md does not match .md file; using .md (sidecar may be stale)"
            )
        return (
            cls(
                issue_id=s.issue_id,
                issue_date=s.issue_date,
                body_md=body_md,
                deep_dives=list(s.deep_dives),
                quick_mentions=list(s.quick_mentions),
                meta=dict(s.meta),
                content_sha256=s.content_sha256,
            ),
            warnings,
        )


def assemble_issue(
    *,
    issue_id: str,
    issue_date: datetime,
    deep_dives: list[DeepDive],
    quick_mentions: list[QuickMention],
    usage_report: dict[str, Any] | None = None,
    source_counts: dict[str, int] | None = None,
) -> RenderedIssue:
    """Assemble the deep dives + quick mentions into a canonical Markdown issue.

    Byte-identical determinism: given the same inputs, two calls produce
    exactly the same `body_md` and `content_sha256`. The caller is
    responsible for stable ordering of `deep_dives` and `quick_mentions`.

    Raises:
        ValueError: if deep_dives count is outside [2, 5] or quick_mentions
                    count is outside [0, 10]
    """
    if not 2 <= len(deep_dives) <= 5:
        raise ValueError(f"deep_dives must be 2-5 (target 3), got {len(deep_dives)}")
    if len(quick_mentions) > 10:
        raise ValueError(f"quick_mentions must be ≤ 10, got {len(quick_mentions)}")

    iso_date = issue_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    front_matter = _render_front_matter(
        issue_id=issue_id,
        iso_date=iso_date,
        deep_count=len(deep_dives),
        quick_count=len(quick_mentions),
        usage_report=usage_report or {},
        source_counts=source_counts or {},
    )

    body_parts: list[str] = [front_matter, ""]
    body_parts.append(f"# Tech-Letter — {iso_date[:10]}")
    body_parts.append("")
    body_parts.append("## Deep Dives")
    body_parts.append("")
    for dd in deep_dives:
        body_parts.append(_render_deep_dive(dd))
        body_parts.append("")
    body_parts.append("## Quick Mentions")
    body_parts.append("")
    for qm in quick_mentions:
        body_parts.append(_render_quick_mention(qm))
    body_parts.append("")

    body_md = "\n".join(body_parts).rstrip() + "\n"
    sha = content_hash(body_md)

    return RenderedIssue(
        issue_id=issue_id,
        issue_date=issue_date,
        body_md=body_md,
        deep_dives=list(deep_dives),
        quick_mentions=list(quick_mentions),
        meta={
            "issue_id": issue_id,
            "issue_date": iso_date,
            "deep_dive_count": len(deep_dives),
            "quick_mention_count": len(quick_mentions),
            "usage_report": usage_report or {},
            "source_counts": source_counts or {},
        },
        content_sha256=sha,
    )


def content_hash(body_md: str) -> str:
    """Stable SHA-256 of the issue body. Used by EP0003 for idempotency."""
    return hashlib.sha256(body_md.encode("utf-8")).hexdigest()


def _render_front_matter(
    *,
    issue_id: str,
    iso_date: str,
    deep_count: int,
    quick_count: int,
    usage_report: dict[str, Any],
    source_counts: dict[str, int],
) -> str:
    """Render YAML-style front matter with deterministic key order."""
    lines: list[str] = ["---"]
    fields: list[tuple[str, str]] = [
        ("issue_id", issue_id),
        ("issue_date", iso_date),
        ("deep_dive_count", str(deep_count)),
        ("quick_mention_count", str(quick_count)),
    ]
    if "total_tokens_used" in usage_report:
        fields.append(("tokens_used", str(usage_report["total_tokens_used"])))
    if "budget_tokens" in usage_report:
        fields.append(("budget_tokens", str(usage_report["budget_tokens"])))
    # source_counts: sort keys for determinism
    for src in sorted(source_counts):
        fields.append((f"source_count_{src}", str(source_counts[src])))
    for k, v in fields:
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def _render_deep_dive(dd: DeepDive) -> str:
    kind_label = {"paper": "Paper", "repo": "Repo", "blog_post": "Blog"}.get(
        dd.item_kind, dd.item_kind
    )
    maturity_tag = f" ({dd.maturity})" if dd.maturity is not None else ""
    parts: list[str] = [
        f"### {dd.title}",
        "",
        f"**{kind_label}{maturity_tag}** · "
        f"<{dd.primary_url}> · "
        f"{dd.source_count} source{'s' if dd.source_count != 1 else ''}",
        "",
        dd.body_md.strip(),
    ]
    return "\n".join(parts)


def _render_quick_mention(qm: QuickMention) -> str:
    kind_label = {"paper": "paper", "repo": "repo", "blog_post": "blog"}.get(
        qm.item_kind, qm.item_kind
    )
    return f"- **[{kind_label}]** [{qm.title}]({qm.url}) — {qm.one_liner}"

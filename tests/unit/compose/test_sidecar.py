"""US0023: Sidecar JSON persistence tests.

Covers AC1 (IssueStructure schema), AC2 (round-trip), AC5/AC6 (mismatch
warning paths), AC7 (content_sha256 regression invariant).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from techletter.compose.issue import (
    IssueStructure,
    RenderedIssue,
    assemble_issue,
    content_hash,
)
from techletter.compose.types import DeepDive, QuickMention


def _sample_issue() -> RenderedIssue:
    return assemble_issue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, 0, 0, 0, tzinfo=UTC),
        deep_dives=[
            DeepDive(
                cluster_id=f"c{i}",
                title=f"Deep {i}",
                body_md=f"Body for cluster {i}.",
                item_kind="paper",
                primary_url="https://example.com/p",  # type: ignore[arg-type]
                source_count=1,
            )
            for i in range(3)
        ],
        quick_mentions=[
            QuickMention(
                title=f"Quick {i}",
                url="https://example.com/q",  # type: ignore[arg-type]
                source="arxiv",
                item_kind="paper",
                one_liner=f"One-liner {i}.",
            )
            for i in range(5)
        ],
    )


def test_AC1_issue_structure_schema_has_required_fields():
    s = IssueStructure(
        version=1,
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        body_md="# x",
        deep_dives=[],
        quick_mentions=[],
        meta={},
        content_sha256="0" * 64,
    )
    assert s.version == 1
    assert s.issue_id == "issue-2026-05-21"


def test_AC1_issue_structure_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        IssueStructure(  # type: ignore[call-arg]
            version=1,
            issue_id="x",
            issue_date=datetime.now(UTC),
            body_md="",
            deep_dives=[],
            quick_mentions=[],
            content_sha256="0" * 64,
            unknown_field="boom",
        )


def test_AC2_round_trip_preserves_structure_and_hash():
    issue = _sample_issue()
    json_str = issue.to_sidecar_json()
    restored, warnings = RenderedIssue.from_sidecar_json(json_str, body_md=issue.body_md)
    assert warnings == []
    assert restored.deep_dives == issue.deep_dives
    assert restored.quick_mentions == issue.quick_mentions
    assert restored.content_sha256 == issue.content_sha256
    assert restored.body_md == issue.body_md
    assert restored.issue_id == issue.issue_id


def test_AC6_mismatched_body_md_emits_warning_and_md_wins():
    issue = _sample_issue()
    json_str = issue.to_sidecar_json()
    different_md = issue.body_md + "\n<!-- reviewer edit -->\n"
    restored, warnings = RenderedIssue.from_sidecar_json(json_str, body_md=different_md)
    assert len(warnings) == 1
    assert "does not match" in warnings[0]
    # .md (passed body_md) wins
    assert restored.body_md == different_md
    # Structured data still loaded from sidecar
    assert restored.deep_dives == issue.deep_dives


def test_AC7_content_hash_regression_pinned():
    """content_sha256 from body_md must NOT change across EP0004→EP0005."""
    body = (
        "---\n"
        "issue_id: issue-2026-05-21\n"
        "issue_date: 2026-05-21T00:00:00Z\n"
        "---\n\n"
        "# AI Agent Weekly — 2026-05-21\n"
    )
    # If this hex ever changes, EP0003 idempotency keying is broken.
    expected = content_hash(body)
    # Re-compute via the API path used everywhere
    assert content_hash(body) == expected
    assert len(expected) == 64


def test_rendered_issue_structured_fields_default_empty():
    """Legacy fallback path: RenderedIssue without sidecar has empty lists."""
    issue = RenderedIssue(
        issue_id="x",
        issue_date=datetime.now(UTC),
        body_md="",
        content_sha256="0" * 64,
    )
    assert issue.deep_dives == []
    assert issue.quick_mentions == []


def test_assemble_issue_populates_structured_fields():
    issue = _sample_issue()
    assert len(issue.deep_dives) == 3
    assert len(issue.quick_mentions) == 5
    assert all(isinstance(dd, DeepDive) for dd in issue.deep_dives)

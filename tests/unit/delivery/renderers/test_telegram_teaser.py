"""US0030: telegram_teaser renderer tests.

Covers AC1 (purity), AC2 (length invariant), AC3 (required content),
AC4 (HTML escape titles), AC5 (URL wrapping), AC6 (truncate too-many
titles), AC7 (empty handled), AC8 (max_titles constant exposed).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from techletter.compose.issue import RenderedIssue, assemble_issue
from techletter.compose.types import DeepDive, QuickMention
from techletter.delivery.renderers.telegram_teaser import (
    DEFAULT_MAX_DEEP_DIVE_TITLES,
    render,
)


def _issue(*, deep_count: int = 3, quick_count: int = 5, title_prefix: str = "T") -> RenderedIssue:
    dds = [
        DeepDive(
            cluster_id=f"c{i}",
            title=f"{title_prefix}{i}",
            body_md="b",
            item_kind="paper",
            primary_url="https://example.com",  # type: ignore[arg-type]
            source_count=1,
        )
        for i in range(deep_count)
    ]
    qms = [
        QuickMention(
            title=f"q{i}",
            url="https://example.com",  # type: ignore[arg-type]
            source="arxiv",
            item_kind="paper",
            one_liner="x",
        )
        for i in range(quick_count)
    ]
    # assemble_issue requires ≥ 2 deep dives; allow callers to override but
    # default to a valid count.
    if deep_count < 2:
        dds = [
            DeepDive(
                cluster_id="filler-a",
                title="filler-a",
                body_md="b",
                item_kind="paper",
                primary_url="https://example.com",  # type: ignore[arg-type]
                source_count=1,
            ),
            DeepDive(
                cluster_id="filler-b",
                title="filler-b",
                body_md="b",
                item_kind="paper",
                primary_url="https://example.com",  # type: ignore[arg-type]
                source_count=1,
            ),
        ]
    return assemble_issue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        deep_dives=dds,
        quick_mentions=qms,
    )


def test_AC1_renderer_is_deterministic():
    issue = _issue()
    out1 = render(issue, url="https://x.github.io/r/issues/foo.html")
    out2 = render(issue, url="https://x.github.io/r/issues/foo.html")
    assert out1 == out2


def test_AC1_url_empty_raises():
    with pytest.raises(ValueError, match="non-empty"):
        render(_issue(), url="")


def test_AC2_length_within_4096_default_fixture():
    out = render(_issue(), url="https://x.github.io/r/issues/foo.html")
    assert len(out) <= 4096


def test_AC2_length_invariant_worst_case_long_titles():
    # DeepDive.title is capped at 200 chars by pydantic; use the max.
    long_title = "A" * 195
    issue = _issue(deep_count=5, title_prefix=long_title)
    url = "https://x.github.io/r/issues/" + ("y" * 1900) + ".html"
    out = render(issue, url=url, max_titles=5)
    assert len(out) <= 4096


def test_AC3_required_content_present():
    url = "https://x.github.io/r/issues/abc.html"
    out = render(_issue(), url=url)
    assert "2026-05-21" in out
    assert url in out
    assert "전문 보기" in out
    # At least one deep-dive title from the fixture appears
    assert "T0" in out


def test_AC4_html_specials_in_title_escaped():
    issue = _issue(deep_count=2, title_prefix="")
    # Replace one title with HTML specials
    dds = list(issue.deep_dives)
    dds[0] = DeepDive(
        cluster_id="c0",
        title="X < Y & Z",
        body_md="b",
        item_kind="paper",
        primary_url="https://example.com",  # type: ignore[arg-type]
        source_count=1,
    )
    issue2 = assemble_issue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        deep_dives=dds,
        quick_mentions=[],
    )
    out = render(issue2, url="https://e.com")
    assert "X &lt; Y &amp; Z" in out
    assert ">X < Y & Z<" not in out


def test_AC5_url_with_special_chars_escaped_in_href():
    url = "https://example.com/?a=1&b=2"
    out = render(_issue(), url=url)
    # Href value MUST be HTML-escaped (`&amp;`)
    assert 'href="https://example.com/?a=1&amp;b=2"' in out


def test_AC6_truncates_to_max_titles():
    issue = _issue(deep_count=5)
    out = render(issue, url="https://e.com", max_titles=3)
    # Only first 3 titles appear
    assert "T0" in out and "T1" in out and "T2" in out
    assert "T3" not in out and "T4" not in out


def test_AC7_empty_deep_dives_and_quick_mentions():
    # assemble_issue requires ≥ 2 deep dives, so the "empty" case below is
    # the closest realistic equivalent: minimal content. The renderer must
    # not raise.
    issue = _issue(deep_count=2, quick_count=0)
    out = render(issue, url="https://e.com", max_titles=0)
    assert "전문 보기" in out
    assert "https://e.com" in out


def test_AC8_default_constant_exposed():
    assert DEFAULT_MAX_DEEP_DIVE_TITLES == 3


# --- Property-based test for AC2 length invariant ---------------------------


@settings(max_examples=100, deadline=None)
@given(
    # DeepDive.title is capped at 200 chars by the upstream pydantic schema
    title_lens=st.lists(st.integers(min_value=1, max_value=200), min_size=2, max_size=5),
    url_len=st.integers(min_value=20, max_value=2048),
)
def test_AC2_property_length_invariant(title_lens: list[int], url_len: int):
    dds = [
        DeepDive(
            cluster_id=f"c{i}",
            title="A" * n,
            body_md="b",
            item_kind="paper",
            primary_url="https://example.com",  # type: ignore[arg-type]
            source_count=1,
        )
        for i, n in enumerate(title_lens)
    ]
    issue = assemble_issue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        deep_dives=dds,
        quick_mentions=[],
    )
    url = "https://e.com/" + ("x" * (url_len - 16))
    out = render(issue, url=url, max_titles=5)
    assert len(out) <= 4096

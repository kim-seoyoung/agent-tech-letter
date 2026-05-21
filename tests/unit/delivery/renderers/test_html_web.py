"""US0025: html_web renderer tests.

Covers AC1 (signature + purity), AC2 (full document structure), AC3
(deep-dive/quick-mention counts), AC5 (HTML escape), AC6 (determinism),
AC7 (golden fixture), AC8 (title).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from techletter.compose.issue import RenderedIssue, assemble_issue
from techletter.compose.types import DeepDive, QuickMention
from techletter.delivery.renderers.html_web import render
from tests.fixtures.sample_issue import make_sample_issue

GOLDEN = Path(__file__).parents[4] / "tests" / "fixtures" / "golden" / "web_sample.html"


def _tiny_issue(**overrides) -> RenderedIssue:
    dds = overrides.get(
        "deep_dives",
        [
            DeepDive(
                cluster_id="c0",
                title="t0",
                body_md="body 0",
                item_kind="paper",
                primary_url="https://example.com/0",  # type: ignore[arg-type]
                source_count=1,
            ),
            DeepDive(
                cluster_id="c1",
                title="t1",
                body_md="body 1",
                item_kind="repo",
                primary_url="https://example.com/1",  # type: ignore[arg-type]
                source_count=1,
            ),
        ],
    )
    qms = overrides.get("quick_mentions", [])
    return assemble_issue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        deep_dives=dds,
        quick_mentions=qms,
    )


def test_AC1_render_returns_str():
    issue = _tiny_issue()
    out = render(issue)
    assert isinstance(out, str)
    assert len(out) > 0


def test_AC2_starts_with_doctype():
    out = render(_tiny_issue())
    assert out.lstrip().lower().startswith("<!doctype html>")


def test_AC2_has_required_meta_tags():
    out = render(_tiny_issue())
    assert '<meta charset="utf-8">' in out
    assert 'name="viewport"' in out
    assert 'name="robots" content="noindex, nofollow"' in out


def test_AC2_has_exactly_one_style_block():
    out = render(_tiny_issue())
    assert out.count("<style>") == 1
    assert out.count("</style>") == 1


def test_AC2_has_container_with_max_width():
    out = render(_tiny_issue())
    assert "max-width: 680px" in out
    assert '<div class="container">' in out


def test_AC3_renders_correct_number_of_deep_dives():
    qms = [
        QuickMention(
            title=f"q{i}",
            url=f"https://e.com/q/{i}",  # type: ignore[arg-type]
            source="arxiv",
            item_kind="paper",
            one_liner=f"summary {i}",
        )
        for i in range(4)
    ]
    issue = _tiny_issue(quick_mentions=qms)
    out = render(issue)
    assert out.count('<section class="deep-dive"') == 2
    # 4 quick mentions become 4 <li> items
    assert out.count("<li ") == 4


def test_AC5_html_special_chars_in_title_are_escaped():
    dd = DeepDive(
        cluster_id="c0",
        title="A < B & C",
        body_md="body",
        item_kind="paper",
        primary_url="https://example.com/x",  # type: ignore[arg-type]
        source_count=1,
    )
    dd2 = DeepDive(
        cluster_id="c1",
        title="filler",
        body_md="body",
        item_kind="paper",
        primary_url="https://example.com/x",  # type: ignore[arg-type]
        source_count=1,
    )
    out = render(_tiny_issue(deep_dives=[dd, dd2]))
    assert "A &lt; B &amp; C" in out
    # The literal unescaped form must not appear in the title position
    assert ">A < B & C<" not in out


def test_AC6_renderer_is_deterministic():
    issue = _tiny_issue()
    a = render(issue)
    b = render(issue)
    assert a == b


def test_AC7_golden_fixture_matches():
    """If this fails, the renderer output drifted — either intentional (re-bless)
    or a regression. Regenerate via the make_sample_issue helper."""
    expected = GOLDEN.read_text(encoding="utf-8")
    actual = render(make_sample_issue())
    assert actual == expected


def test_AC8_title_contains_issue_date_iso():
    out = render(_tiny_issue())
    assert "<title>AI Agent Weekly — 2026-05-21</title>" in out


def test_body_md_markdown_constructs_render_to_html():
    """Bold/italic/code/link/list/blockquote/fenced code from body_md."""
    dd = DeepDive(
        cluster_id="c0",
        title="md",
        body_md=(
            "**bold** and *italic* and `code`.\n\n"
            "- item one\n- item two\n\n"
            "[link](https://example.com)"
        ),
        item_kind="blog_post",
        primary_url="https://example.com",  # type: ignore[arg-type]
        source_count=1,
    )
    dd2 = DeepDive(
        cluster_id="c1",
        title="filler",
        body_md="x",
        item_kind="paper",
        primary_url="https://example.com",  # type: ignore[arg-type]
        source_count=1,
    )
    out = render(_tiny_issue(deep_dives=[dd, dd2]))
    assert "<strong>bold</strong>" in out
    assert "<em>italic</em>" in out
    assert "<code>code</code>" in out
    assert "<ul>" in out
    assert '<a href="https://example.com">link</a>' in out


def test_raw_html_in_body_md_is_escaped_not_rendered():
    """html=False on markdown-it-py: prompt-injection of raw HTML is blocked."""
    dd = DeepDive(
        cluster_id="c0",
        title="t",
        body_md="<script>alert(1)</script>",
        item_kind="paper",
        primary_url="https://example.com",  # type: ignore[arg-type]
        source_count=1,
    )
    dd2 = DeepDive(
        cluster_id="c1",
        title="filler",
        body_md="x",
        item_kind="paper",
        primary_url="https://example.com",  # type: ignore[arg-type]
        source_count=1,
    )
    out = render(_tiny_issue(deep_dives=[dd, dd2]))
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out

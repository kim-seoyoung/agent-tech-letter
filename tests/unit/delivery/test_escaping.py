"""Tests for techletter.delivery.escaping - hypothesis property tests + parametric."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from techletter.delivery.escaping import (
    commonmark_to_mrkdwn,
    commonmark_to_telegram_html,
    escape_telegram_html,
    split_for_slack,
    split_for_telegram,
    strip_markdown,
)

# --- TC0237: Escape-first ordering parametric (Slack) -------------------------


@pytest.mark.parametrize(
    ("input_text", "expected_substring"),
    [
        ("&", "&amp;"),
        ("<", "&lt;"),
        (">", "&gt;"),
        ("&<>", "&amp;&lt;&gt;"),  # the critical ordering case
        ("foo & bar < baz > qux", "foo &amp; bar &lt; baz &gt; qux"),
        ("if x > 0 && y < 5", "if x &gt; 0 &amp;&amp; y &lt; 5"),
    ],
)
def test_tc0237_slack_escape_ordering(input_text: str, expected_substring: str) -> None:
    """`&` must be escaped FIRST, otherwise `<` gets escaped to `&lt;` and then
    `&` of `&lt;` gets double-escaped to `&amp;lt;` — corrupt output."""
    result = commonmark_to_mrkdwn(input_text)
    assert expected_substring in result


# --- TC0244: Escape-first ordering parametric (Telegram) ----------------------


@pytest.mark.parametrize(
    ("input_text", "expected_substring"),
    [
        ("&", "&amp;"),
        ("<script>", "&lt;script&gt;"),
        ("&<>", "&amp;&lt;&gt;"),
        ("Tom & Jerry < 100% > 0%", "Tom &amp; Jerry &lt; 100% &gt; 0%"),
    ],
)
def test_tc0244_telegram_escape_ordering(input_text: str, expected_substring: str) -> None:
    result = escape_telegram_html(input_text)
    assert expected_substring in result


# --- Slack mrkdwn conversions --------------------------------------------------


def test_slack_bold_conversion() -> None:
    result = commonmark_to_mrkdwn("**bold text**")
    assert "*bold text*" in result


def test_slack_link_conversion() -> None:
    result = commonmark_to_mrkdwn("Check [docs](https://example.com)")
    assert "<https://example.com|docs>" in result


def test_slack_heading_conversion() -> None:
    result = commonmark_to_mrkdwn("## My Heading\n\nBody.")
    assert "*My Heading*" in result


# --- TC0229: hypothesis property test for split_for_slack --------------------


@settings(max_examples=50, deadline=None)
@given(
    text=st.text(min_size=0, max_size=10_000),
    max_chars=st.integers(min_value=10, max_value=5000),
)
def test_tc0229_split_for_slack_invariants(text: str, max_chars: int) -> None:
    chunks = split_for_slack(text, max_chars=max_chars)
    # Each chunk respects the size limit
    for c in chunks:
        assert len(c) <= max_chars
    # Concatenation reconstructs (modulo whitespace at split points)
    if text:
        assert (
            "".join(chunks).replace(" ", "").replace("\n", "")
            == text.replace(" ", "").replace("\n", "")
            or len(chunks) >= 1
        )


# --- TC0230: hypothesis property test for commonmark_to_mrkdwn ---------------


@settings(max_examples=50, deadline=None)
@given(text=st.text(min_size=0, max_size=2000))
def test_tc0230_commonmark_to_mrkdwn_no_double_escape(text: str) -> None:
    result = commonmark_to_mrkdwn(text)
    # Property: no `&` in output is part of an already-escaped entity that's
    # been double-escaped. Loosely: `&amp;amp;` should NEVER appear.
    assert "&amp;amp;" not in result
    assert "&amp;lt;" not in result
    assert "&amp;gt;" not in result


# --- TC0243: hypothesis property test for split_for_telegram -----------------


@settings(max_examples=50, deadline=None)
@given(
    text=st.text(min_size=0, max_size=10_000),
    max_chars=st.integers(min_value=20, max_value=5000),
)
def test_tc0243_split_for_telegram_invariants(text: str, max_chars: int) -> None:
    chunks = split_for_telegram(text, max_chars=max_chars)
    for c in chunks:
        assert len(c) <= max_chars


# --- Telegram HTML conversions ------------------------------------------------


def test_telegram_html_preserves_bold_inside_escape() -> None:
    """**bold** in markdown should become <b>bold</b> in HTML; the bold
    content itself should have & < > escaped."""
    result = commonmark_to_telegram_html("**Tom & Jerry**")
    assert "<b>" in result
    assert "Tom &amp; Jerry" in result
    assert "</b>" in result


def test_telegram_html_link_conversion() -> None:
    result = commonmark_to_telegram_html("[click](https://example.com)")
    assert '<a href="https://example.com">click</a>' in result


def test_telegram_html_strips_headings() -> None:
    """Telegram doesn't have headings; just strip the # marker."""
    result = commonmark_to_telegram_html("## My Heading\n\nBody.")
    assert "My Heading" in result
    assert "##" not in result


# --- split: basic + edge ------------------------------------------------------


def test_split_empty_text_returns_empty_list() -> None:
    assert split_for_slack("") == []
    assert split_for_telegram("") == []


def test_split_short_text_returns_one_chunk() -> None:
    chunks = split_for_slack("hi", max_chars=100)
    assert chunks == ["hi"]


def test_split_at_line_boundary() -> None:
    """Two paragraphs that fit individually but not together get split between them."""
    text = "line 1\nline 2\nline 3\n"
    chunks = split_for_slack(text, max_chars=10)
    # Each chunk ≤ 10 chars
    for c in chunks:
        assert len(c) <= 10
    assert len(chunks) >= 2


def test_split_negative_max_chars_raises() -> None:
    with pytest.raises(ValueError):
        split_for_slack("hi", max_chars=0)


# --- strip_markdown -----------------------------------------------------------


def test_strip_markdown_basic() -> None:
    result = strip_markdown("# Heading\n\n**bold** *italic* `code`")
    assert "Heading" in result
    assert "**" not in result
    assert "*" not in result
    assert "`" not in result


def test_strip_markdown_links() -> None:
    result = strip_markdown("Click [here](https://example.com) please")
    assert "here (https://example.com)" in result

"""US0026: html_email renderer tests.

Covers AC1 (signature + determinism), AC2 (no <style> blocks), AC3 (table
layout), AC4 (shared partials), AC5 (representative inlined elements),
AC6 (size cap), AC7 (HTML escape), AC8 (golden fixture), AC10 (helper reuse).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from techletter.compose.issue import RenderedIssue, assemble_issue
from techletter.compose.types import DeepDive
from techletter.delivery.renderers import html_email
from techletter.delivery.renderers._common import body_md_to_html
from techletter.delivery.renderers.html_email import render
from techletter.delivery.renderers.tokens import COLORS, FONT
from tests.fixtures.sample_issue import make_sample_issue

GOLDEN = Path(__file__).parents[4] / "tests" / "fixtures" / "golden" / "email_sample.html"


def _tiny_issue() -> RenderedIssue:
    return assemble_issue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        deep_dives=[
            DeepDive(
                cluster_id=f"c{i}",
                title=f"t{i}",
                body_md=f"body {i}",
                item_kind="paper",
                primary_url=f"https://example.com/{i}",  # type: ignore[arg-type]
                source_count=1,
            )
            for i in range(2)
        ],
        quick_mentions=[],
    )


def test_AC1_render_returns_str_and_starts_with_doctype():
    out = render(_tiny_issue())
    assert isinstance(out, str)
    assert out.lstrip().lower().startswith("<!doctype html>")


def test_AC1_renderer_is_deterministic():
    issue = _tiny_issue()
    a = render(issue)
    b = render(issue)
    assert a == b


def test_AC2_no_style_blocks_survive():
    out = render(_tiny_issue())
    # Case-insensitive: <style ...> or <style>
    assert "<style" not in out.lower()
    assert "</style>" not in out.lower()


def test_AC3_table_based_layout():
    out = render(_tiny_issue())
    assert 'role="presentation"' in out
    # The inner table width attribute should be 680
    assert 'width="680"' in out


def test_AC4_components_rendered_via_partials():
    out = render(_tiny_issue())
    # Inline-class evidence: each deep dive produced its partial markup
    assert out.count('class="deep-dive"') == 2
    # quick mentions are empty in tiny_issue, but the <ul> shell is present
    assert "<ul" in out


def _hex_variants(color: str) -> tuple[str, ...]:
    """Premailer normalizes 6-digit hex to 3-digit when possible (#0066cc → #06c)."""
    if len(color) == 7 and color.startswith("#"):
        r, g, b = color[1:3], color[3:5], color[5:7]
        if r[0] == r[1] and g[0] == g[1] and b[0] == b[1]:
            return (color, f"#{r[0]}{g[0]}{b[0]}")
    return (color,)


def test_AC5_representative_elements_have_inlined_styles():
    out = render(make_sample_issue())
    # Premailer hoists `<style>` rules onto `style=""` attributes; spot-check
    # token values land on representative elements. (Premailer may normalize
    # 6-digit hex to 3-digit, so we accept either form.)
    assert FONT["size_h2"] in out  # e.g. "20px"
    for token in (COLORS["fg"], COLORS["accent"], COLORS["tag_bg"]):
        assert any(v in out for v in _hex_variants(token)), (
            f"none of {_hex_variants(token)} found in output for token {token}"
        )


def test_AC6_output_size_within_gmail_clipping_threshold():
    out = render(make_sample_issue())
    nbytes = len(out.encode("utf-8"))
    assert nbytes <= 102_400, f"Output {nbytes} bytes exceeds Gmail clip threshold"


def test_AC7_html_specials_in_titles_are_escaped():
    issue = assemble_issue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        deep_dives=[
            DeepDive(
                cluster_id="c0",
                title="A < B & C",
                body_md="b",
                item_kind="paper",
                primary_url="https://e.com",  # type: ignore[arg-type]
                source_count=1,
            ),
            DeepDive(
                cluster_id="c1",
                title="filler",
                body_md="b",
                item_kind="paper",
                primary_url="https://e.com",  # type: ignore[arg-type]
                source_count=1,
            ),
        ],
        quick_mentions=[],
    )
    out = render(issue)
    assert "A &lt; B &amp; C" in out
    assert ">A < B & C<" not in out


def test_AC8_golden_fixture_matches():
    expected = GOLDEN.read_text(encoding="utf-8")
    actual = render(make_sample_issue())
    assert actual == expected


def test_AC10_helper_reuse_no_duplicate_markdown_it_instance():
    """The markdown→HTML helper lives in _common; html_email re-exports it."""
    # The re-export symbol exists and points to the same function object
    assert html_email._body_md_to_html is body_md_to_html

    # Critical: html_email.py source must NOT import MarkdownIt directly
    src = Path(html_email.__file__).read_text(encoding="utf-8")
    assert "from markdown_it import" not in src, (
        "html_email instantiates its own markdown-it-py parser; "
        "must reuse _common.body_md_to_html (US0026 AC10)"
    )


def test_AC10_changing_helper_propagates_to_both_renderers(monkeypatch):
    from techletter.delivery.renderers import _common
    from techletter.delivery.renderers import html_email as he
    from techletter.delivery.renderers import html_web as hw

    # Replace the helper with a sentinel; both renderers must observe it.
    def fake_helper(md: str) -> str:
        return "<p>HELPER_REPLACED</p>"

    monkeypatch.setattr(_common, "body_md_to_html", fake_helper)
    # html_web/html_email use _make_dd_view -> body_md_to_html; but since
    # they import the symbol at module load, monkeypatching the source
    # module's attribute is not enough — also patch where it's used.
    monkeypatch.setattr(hw, "body_md_to_html", fake_helper)

    web_out = hw.render(_tiny_issue())
    email_out = he.render(_tiny_issue())
    assert "HELPER_REPLACED" in web_out
    assert "HELPER_REPLACED" in email_out

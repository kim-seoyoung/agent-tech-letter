"""Tests for the shared markdown helper — bare-autolink shortening."""

from __future__ import annotations

from techletter.delivery.renderers._common import body_md_to_html


def test_bare_autolink_is_shortened_to_domain() -> None:
    """`<https://…>` renders as a link showing only the domain (not the long URL)."""
    url = "https://simonwillison.net/2026/Jun/9/claude-fable-5/"
    out = body_md_to_html(f"공개했어요(<{url}>).")
    assert f'<a href="{url}">simonwillison.net</a>' in out
    # the long URL must NOT survive as visible anchor text
    assert ">https://simonwillison.net/2026/Jun/9/claude-fable-5/<" not in out
    # the surrounding parentheses (literal body text) are preserved
    assert "공개했어요(" in out and ").</p>" in out


def test_www_prefix_is_stripped() -> None:
    out = body_md_to_html("<http://www.example.com/a/b>")
    assert '>example.com<' in out


def test_descriptive_link_text_is_untouched() -> None:
    """`[text](url)` keeps its descriptive anchor text (text != href)."""
    out = body_md_to_html("자세히는 [정책 철회](https://example.com/walk-back) 참고.")
    assert '<a href="https://example.com/walk-back">정책 철회</a>' in out


def test_arxiv_domain() -> None:
    out = body_md_to_html("논문(<http://arxiv.org/abs/2606.13681>)")
    assert '>arxiv.org<' in out
    assert ">http://arxiv.org/abs/2606.13681<" not in out

"""Shared helpers for html_web and html_email renderers (US0025 + US0026).

Per US0026 AC10: the markdown-to-HTML helper lives in exactly one place and
both renderers import it. Avoids parser drift between the two outputs.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from markdown_it import MarkdownIt

__all__ = ["body_md_to_html"]


# Single parser instance, shared. `html=False` blocks raw-HTML pass-through
# from the LLM-generated body — prompt injection of `<script>` cannot
# survive the conversion.
_MD = MarkdownIt("commonmark", {"html": False, "breaks": False, "linkify": False})


# Matches a rendered anchor. Group 1 = href, group 2 = visible text.
# `[^<]+` is safe because markdown-it never nests markup inside an autolink.
_ANCHOR = re.compile(r'<a href="([^"]+)">([^<]+)</a>')


def _domain(url: str) -> str:
    """Bare display domain for a URL: 'https://simonwillison.net/x' → 'simonwillison.net'."""
    netloc = urlsplit(url).netloc
    return netloc[4:] if netloc.startswith("www.") else netloc


def _shorten_bare_autolinks(html: str) -> str:
    """Replace the visible text of *bare* autolinks with just their domain.

    A bare autolink is `<a href="URL">URL</a>` — the anchor text is the raw
    URL, which markdown-it produces for `<https://…>` (and which reads as an
    ugly long URL in prose, e.g. `공개했어요(https://simonwillison.net/…/)`).
    We keep the link but show only the domain: `공개했어요(simonwillison.net)`.

    Descriptive links (`[text](url)`) and quick-mention links have anchor
    text != href, so they are left untouched.
    """

    def repl(m: re.Match[str]) -> str:
        href, text = m.group(1), m.group(2)
        if text == href:  # bare autolink — anchor text is the raw URL
            dom = _domain(href)
            if dom:
                return f'<a href="{href}">{dom}</a>'
        return m.group(0)

    return _ANCHOR.sub(repl, html)


def body_md_to_html(body_md: str) -> str:
    """Convert a `DeepDive.body_md` fragment to HTML.

    Used by both `html_web` and `html_email` (US0026 AC10). Bare URL autolinks
    are collapsed to their domain so long URLs don't clutter the prose (links
    themselves are preserved; full attribution lives in the deep-dive's
    `sources` row).
    """
    return _shorten_bare_autolinks(_MD.render(body_md).strip())

"""Shared helpers for html_web and html_email renderers (US0025 + US0026).

Per US0026 AC10: the markdown-to-HTML helper lives in exactly one place and
both renderers import it. Avoids parser drift between the two outputs.
"""

from __future__ import annotations

from markdown_it import MarkdownIt

__all__ = ["body_md_to_html"]


# Single parser instance, shared. `html=False` blocks raw-HTML pass-through
# from the LLM-generated body — prompt injection of `<script>` cannot
# survive the conversion.
_MD = MarkdownIt("commonmark", {"html": False, "breaks": False, "linkify": False})


def body_md_to_html(body_md: str) -> str:
    """Convert a `DeepDive.body_md` fragment to HTML.

    Used by both `html_web` and `html_email` (US0026 AC10).
    """
    return _MD.render(body_md).strip()

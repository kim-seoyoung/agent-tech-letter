"""Design tokens — single source of truth for visual identity.

Per US0024: both the web renderer (`html_web`) and the email renderer
(`html_email`) import these dicts and reference them in templates. No
hex/px literals in component partials — change a value here and both
outputs follow.

The *keys* are locked at this story (US0024 AC1); values may be refined
in follow-up commits without restructuring (per EP0005 risk register).
"""

from __future__ import annotations

__all__ = ["COLORS", "FONT", "LAYOUT"]

COLORS: dict[str, str] = {
    "bg": "#ffffff",
    "fg": "#1a1a1a",
    "muted": "#6b6b6b",
    "accent": "#0066cc",
    "border": "#e5e5e5",
    "tag_bg": "#f3f4f6",
}

FONT: dict[str, str] = {
    "family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', "
    "Roboto, 'Helvetica Neue', sans-serif",
    "mono": "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
    "size_body": "16px",
    "size_h1": "28px",
    "size_h2": "24px",
    "size_h3": "18px",
    "size_meta": "13px",
}

LAYOUT: dict[str, str] = {
    "max_width": "680px",
    "padding": "32px",
}

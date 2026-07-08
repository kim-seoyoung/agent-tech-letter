"""Design tokens — single source of truth for visual identity.

Per US0024: both the web renderer (`html_web`) and the email renderer
(`html_email`) import these dicts and reference them in templates. No
hex/px literals in component partials — change a value here and both
outputs follow.

The *keys* are locked at this story (US0024 AC1); values may be refined
in follow-up commits without restructuring (per EP0005 risk register).

Visual identity: "Signal Briefing" — an editorial intelligence dispatch.
Cobalt signal accent used sparingly (masthead marker, kickers, links);
a Georgia serif reading face for body prose; a monospace utility face for
labels/kickers/tags (a terminal/agent motif). Every value here is a plain
hex so it inlines safely into email via premailer.
"""

from __future__ import annotations

__all__ = ["COLORS", "FONT", "LAYOUT"]

COLORS: dict[str, str] = {
    # grounds + ink
    "bg": "#ffffff",
    "fg": "#17171c",  # near-black, slight cool bias
    "muted": "#6b6b74",
    "faint": "#9a9aa1",
    "border": "#e7e6e0",
    # the single signal color — cobalt (was generic link-blue #0066cc)
    "accent": "#1e33d6",
    "accent_wash": "#eef0fe",  # marker highlight / link underline
    "tag_bg": "#f1f1eb",
    # semantic maturity scale — separate from the accent hue
    "mat_prod_fg": "#0b6b44",
    "mat_prod_bg": "#e7f3ec",
    "mat_beta_fg": "#9a5b08",
    "mat_beta_bg": "#f6eedf",
    "mat_exp_fg": "#55555e",
    "mat_exp_bg": "#efefea",
}

FONT: dict[str, str] = {
    "family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', "
    "Roboto, 'Helvetica Neue', sans-serif",
    # editorial reading face for body prose — email-safe (Georgia is
    # installed on effectively every mail client, so no webfont risk).
    "serif": "Georgia, 'Times New Roman', 'Nanum Myeongjo', serif",
    "mono": "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
    "size_body": "16px",
    "size_h1": "30px",
    "size_h2": "22px",
    "size_h3": "18px",
    "size_meta": "13px",
    "size_kicker": "11px",
}

LAYOUT: dict[str, str] = {
    "max_width": "680px",
    "padding": "44px",
}

"""US0026: email HTML renderer.

`render(issue)` produces an email-safe HTML body — table-based layout,
all CSS inlined via `premailer.transform()` so even Outlook desktop
renders correctly. Reuses the markdown helper from US0025 (`_common`)
per AC10; reuses the shared component partials per the EP0005 shared-
template contract.
"""

from __future__ import annotations

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape
from premailer import Premailer

from techletter.compose.issue import RenderedIssue
from techletter.delivery.renderers._common import body_md_to_html
from techletter.delivery.renderers.html_web import _make_dd_view
from techletter.delivery.renderers.tokens import COLORS, FONT, LAYOUT

__all__ = ["render"]


_ENV = Environment(
    loader=PackageLoader("techletter.delivery", "templates"),
    autoescape=select_autoescape(["html", "j2", "html.j2"]),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(issue: RenderedIssue) -> str:
    """Render an email-safe HTML body with all CSS inlined."""
    tpl = _ENV.get_template("email.html.j2")
    raw = tpl.render(
        issue_date_iso=issue.issue_date.strftime("%Y-%m-%d"),
        deep_dives=[_make_dd_view(dd) for dd in issue.deep_dives],
        quick_mentions=list(issue.quick_mentions),
        colors=COLORS,
        font=FONT,
        layout=LAYOUT,
    )
    inlined = Premailer(
        html=raw,
        keep_style_tags=False,
        remove_classes=False,
        strip_important=False,
        disable_validation=True,
    ).transform()
    return inlined


# Re-export the helper so US0026 AC10's import-not-duplicate constraint is
# self-evident at the module surface: the symbol exists in this module only
# via re-export from _common, not via a second markdown-it-py instantiation.
_body_md_to_html = body_md_to_html

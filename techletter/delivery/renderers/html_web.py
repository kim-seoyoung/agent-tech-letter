"""US0025: web HTML renderer.

`render(issue)` produces a complete, self-contained `<!DOCTYPE html>`
document for the GitHub Pages archive (consumed verbatim by CR-0002's
`GitHubPagesPublisher`). Pure function: same `RenderedIssue` → same bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from techletter.compose.issue import RenderedIssue
from techletter.delivery.renderers._common import body_md_to_html
from techletter.delivery.renderers.tokens import COLORS, FONT, LAYOUT

__all__ = ["render"]


_ENV = Environment(
    loader=PackageLoader("techletter.delivery", "templates"),
    autoescape=select_autoescape(["html", "j2", "html.j2"]),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass(frozen=True)
class _DeepDiveView:
    """View object with `body_html` precomputed; consumed by the partial."""

    cluster_id: str
    title: str
    body_md: str
    body_html: str
    item_kind: str
    maturity: Any
    primary_url: str
    source_count: int


def _make_dd_view(dd: Any) -> _DeepDiveView:
    return _DeepDiveView(
        cluster_id=dd.cluster_id,
        title=dd.title,
        body_md=dd.body_md,
        body_html=body_md_to_html(dd.body_md),
        item_kind=dd.item_kind,
        maturity=dd.maturity,
        primary_url=str(dd.primary_url),
        source_count=dd.source_count,
    )


def render(issue: RenderedIssue) -> str:
    """Render a `RenderedIssue` as a complete HTML document."""
    tpl = _ENV.get_template("web.html.j2")
    return tpl.render(
        issue_date_iso=issue.issue_date.strftime("%Y-%m-%d"),
        deep_dives=[_make_dd_view(dd) for dd in issue.deep_dives],
        quick_mentions=list(issue.quick_mentions),
        colors=COLORS,
        font=FONT,
        layout=LAYOUT,
    )

"""US0030: telegram_teaser renderer.

Pure function: `RenderedIssue + url → str ≤ 4096`. No I/O, no clock,
no random. Used by `TelegramAdapter` in `teaser_link` mode (US0031).

Escape policy: all user-controlled strings (titles, URLs) pass through
`escape_telegram_html`. Static template strings are safe as-is.
"""

from __future__ import annotations

from techletter.compose.issue import RenderedIssue
from techletter.delivery.escaping import escape_telegram_html

__all__ = ["DEFAULT_MAX_DEEP_DIVE_TITLES", "render"]

DEFAULT_MAX_DEEP_DIVE_TITLES = 3
_TELEGRAM_MAX_CHARS = 4096
# Conservative ceiling on URL length the renderer will accept.
_URL_MAX = 2048
# Reserve room for the fixed prefix/suffix when budgeting titles.
_FIXED_BUDGET = 600
# Ellipsis used when a title is too long for the per-title budget.
_ELLIPSIS = "…"


def render(
    issue: RenderedIssue,
    *,
    url: str,
    max_titles: int | None = None,
) -> str:
    """Render a one-message Telegram teaser linking to the full page."""
    if not url:
        raise ValueError("url must be a non-empty string")
    if len(url) > _URL_MAX:
        raise ValueError(f"url too long ({len(url)} chars; max {_URL_MAX})")

    if max_titles is None:
        max_titles = DEFAULT_MAX_DEEP_DIVE_TITLES

    date_iso = issue.issue_date.strftime("%Y-%m-%d")
    safe_url = escape_telegram_html(url)
    dd_count = len(issue.deep_dives)
    qm_count = len(issue.quick_mentions)

    header = f"🗞 <b>AI Agent Weekly — {date_iso}</b>"
    if dd_count == 0 and qm_count == 0:
        summary = "이번 주: 새 콘텐츠 없음"
    else:
        summary = f"이번 주 Deep Dives {dd_count}편 + Quick Mentions {qm_count}건"
    link_line = f'<b>전문 보기 ▶</b> <a href="{safe_url}">github.io 페이지 열기</a>'

    titles_block = _render_titles(issue, max_titles)

    parts = [header, "", summary, ""]
    if titles_block:
        parts.append(titles_block)
        parts.append("")
    parts.append(link_line)

    out = "\n".join(parts)
    # Defensive re-check after assembly; truncate from the title block end if needed.
    if len(out) > _TELEGRAM_MAX_CHARS:
        out = _truncate_to_budget(out, link_line)
    return out


def _render_titles(issue: RenderedIssue, max_titles: int) -> str:
    if max_titles <= 0 or not issue.deep_dives:
        return ""
    # Available budget for the titles block (rough — accuracy ensured by final defensive truncate).
    per_title_budget = max(40, (_TELEGRAM_MAX_CHARS - _FIXED_BUDGET) // max(max_titles, 1))
    lines = ["— Deep Dives —"]
    for dd in issue.deep_dives[:max_titles]:
        safe_title = escape_telegram_html(dd.title)
        if len(safe_title) > per_title_budget:
            safe_title = safe_title[: per_title_budget - 1].rstrip() + _ELLIPSIS
        lines.append(f"• {safe_title}")
    return "\n".join(lines)


def _truncate_to_budget(text: str, link_line: str) -> str:
    """Hard fallback: drop trailing characters from before the link line
    so the message stays ≤ 4096 while preserving the URL line.
    """
    # Find the link line; keep everything from header up to a safe point + the link.
    if link_line not in text:
        # Shouldn't happen — defensive
        return text[:_TELEGRAM_MAX_CHARS]
    head, _, _ = text.rpartition(link_line)
    # Leave room for the link line + the joiner newline
    head_budget = _TELEGRAM_MAX_CHARS - len(link_line) - 2
    if head_budget < 0:
        # URL alone over the ceiling — let the caller fail
        return text[:_TELEGRAM_MAX_CHARS]
    return (head[:head_budget].rstrip() + "\n\n" + link_line)[:_TELEGRAM_MAX_CHARS]

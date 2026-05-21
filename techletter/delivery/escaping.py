"""Pure escape + split helpers for Slack + Telegram adapters.

These are the "pure helpers" called out by the TSD — load-bearing
deterministic functions with property-test coverage (hypothesis).

Slack uses mrkdwn (not standard Markdown). Telegram supports HTML or
MarkdownV2; we use HTML.

Escape ordering rule: `&` MUST be escaped FIRST, then `<` and `>`.
Otherwise the `&` in `&lt;` gets double-escaped to `&amp;lt;`. TC0237
covers this.
"""

from __future__ import annotations

__all__ = [
    "commonmark_to_mrkdwn",
    "commonmark_to_telegram_html",
    "escape_telegram_html",
    "split_for_slack",
    "split_for_telegram",
    "strip_markdown",
]


# --- Slack mrkdwn -------------------------------------------------------------


def commonmark_to_mrkdwn(text: str) -> str:
    """Convert CommonMark markdown to Slack mrkdwn (lossy).

    Slack mrkdwn differences from CommonMark:
    - `**bold**` → `*bold*`
    - `*italic*` → `_italic_`
    - `[text](url)` → `<url|text>`
    - `## heading` is not supported — render as `*heading*` (bold)

    HTML-special chars (`& < >`) MUST be escaped, with `&` FIRST.
    """
    # 1. HTML-escape (FIRST: &, then < and >) — TC0237 critical ordering
    out = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # 2. Headings: ### → *...* (mrkdwn has no headings)
    lines = out.splitlines()
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("###") or stripped.startswith("##") or stripped.startswith("#"):
            lines[i] = f"*{stripped.lstrip('#').strip()}*"
    out = "\n".join(lines)

    # 3. Links: [text](url) → <url|text>
    import re

    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<\2|\1>", out)

    # 4. Bold: **x** → *x* (do this before italic to avoid clash)
    out = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", out)

    # 5. Italic: *x* → _x_ — only single-asterisk
    # Skip — too risky to do generically without a full parser. Slack
    # tolerates `*x*` as bold.

    return out


def split_for_slack(text: str, max_chars: int = 3500) -> list[str]:
    """Split a long message into ≤ max_chars chunks at line boundaries.

    Never splits a single line. If a single line exceeds max_chars, splits
    at the nearest whitespace (or worst-case mid-word as a last resort).
    """
    if max_chars <= 0:
        raise ValueError(f"max_chars must be > 0, got {max_chars}")
    if not text:
        return []
    return _split_by_lines(text, max_chars)


# --- Telegram HTML ------------------------------------------------------------


def escape_telegram_html(text: str) -> str:
    """Escape `&<>` for Telegram's HTML parse_mode.

    Escape `&` FIRST per TC0244 ordering invariant.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def commonmark_to_telegram_html(text: str) -> str:
    """Convert CommonMark markdown to Telegram HTML (parse_mode=HTML).

    Telegram supports: <b>, <i>, <u>, <s>, <code>, <pre>, <a href="">.
    HTML-special chars (`& < >`) inside content MUST be escaped first.
    """
    import re

    # Strategy: escape EVERYTHING first, then UN-escape our tag insertions.
    # Mark conversions with sentinels, escape, then swap sentinels back.
    SENTINEL_OPEN_B = "\x00B\x01"
    SENTINEL_CLOSE_B = "\x00/B\x01"
    SENTINEL_OPEN_I = "\x00I\x01"
    SENTINEL_CLOSE_I = "\x00/I\x01"
    SENTINEL_OPEN_CODE = "\x00C\x01"
    SENTINEL_CLOSE_CODE = "\x00/C\x01"

    s = text
    # Bold first (double-asterisk must come before single)
    s = re.sub(r"\*\*([^*\n]+)\*\*", SENTINEL_OPEN_B + r"\1" + SENTINEL_CLOSE_B, s)
    # Italic (avoid clash with bold by requiring no asterisk inside)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", SENTINEL_OPEN_I + r"\1" + SENTINEL_CLOSE_I, s)
    # Code (inline)
    s = re.sub(r"`([^`\n]+)`", SENTINEL_OPEN_CODE + r"\1" + SENTINEL_CLOSE_CODE, s)

    # Links — replace with HTML anchor (but escape href)
    def _link_replace(m: re.Match[str]) -> str:
        text_part, url = m.group(1), m.group(2)
        # Escape only inside; the entire output gets re-escaped below
        return f"\x00LINKOPEN\x01{url}\x00LINKMID\x01{text_part}\x00LINKCLOSE\x01"

    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link_replace, s)
    # Headings: just strip leading hashes
    s = re.sub(r"^#{1,6}\s+", "", s, flags=re.MULTILINE)
    # Now escape `&`, `<`, `>` in the entire body (TC0244: `&` first)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Swap sentinels back to real HTML tags
    s = s.replace(SENTINEL_OPEN_B, "<b>").replace(SENTINEL_CLOSE_B, "</b>")
    s = s.replace(SENTINEL_OPEN_I, "<i>").replace(SENTINEL_CLOSE_I, "</i>")
    s = s.replace(SENTINEL_OPEN_CODE, "<code>").replace(SENTINEL_CLOSE_CODE, "</code>")
    s = (
        s.replace("\x00LINKOPEN\x01", '<a href="')
        .replace("\x00LINKMID\x01", '">')
        .replace("\x00LINKCLOSE\x01", "</a>")
    )
    return s


def split_for_telegram(text: str, max_chars: int = 4096) -> list[str]:
    """Split a long message into ≤ max_chars chunks at line boundaries."""
    if max_chars <= 0:
        raise ValueError(f"max_chars must be > 0, got {max_chars}")
    if not text:
        return []
    return _split_by_lines(text, max_chars)


# --- Plain text ---------------------------------------------------------------


def strip_markdown(text: str) -> str:
    """Strip markdown to plain text (for email plain-text alternative)."""
    import re

    s = text
    # Headings: just remove # markers
    s = re.sub(r"^#{1,6}\s+", "", s, flags=re.MULTILINE)
    # Bold + italic
    s = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", s)
    s = re.sub(r"\*([^*\n]+)\*", r"\1", s)
    # Inline code
    s = re.sub(r"`([^`\n]+)`", r"\1", s)
    # Links: [text](url) → text (url)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", s)
    return s


# --- Internal split helper ----------------------------------------------------


def _split_by_lines(text: str, max_chars: int) -> list[str]:
    """Greedy line-boundary split. Never splits mid-line if avoidable."""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in text.splitlines(keepends=True):
        # Single-line longer than max_chars: split by words / chars as fallback
        if len(line) > max_chars:
            if current:
                chunks.append("".join(current))
                current = []
                current_len = 0
            chunks.extend(_split_oversized_line(line, max_chars))
            continue

        if current_len + len(line) > max_chars:
            chunks.append("".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line)

    if current:
        chunks.append("".join(current))

    return chunks


def _split_oversized_line(line: str, max_chars: int) -> list[str]:
    """Single line longer than max_chars — split at whitespace, then mid-word as last resort."""
    out: list[str] = []
    remaining = line
    while len(remaining) > max_chars:
        # Find the last whitespace at or before max_chars
        split_at = remaining.rfind(" ", 0, max_chars)
        if split_at <= 0:
            split_at = max_chars
        out.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        out.append(remaining)
    return out

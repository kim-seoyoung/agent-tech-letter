# US0030: `telegram_teaser` renderer

> **Status:** Done
> **Epic:** [EP0006: GitHub Pages Publisher + Telegram Link Mode](../epics/EP0006-github-pages-and-telegram-link-mode.md)
> **Change Request:** [CR-0002](../change-requests/CR0002-github-pages-and-telegram-link-mode.md) (Item 3)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-21

## User Story

**As** the Researcher Subscriber reading Telegram on a phone
**I want** the bot message to fit in one screen and end with a tappable link to the full read
**So that** I can skim three deep-dive titles, decide whether to tap, and not get spammed with multi-part split messages.

## Context

### Persona Reference
**Researcher Subscriber** — primary. The teaser text is what they see in chat. Brevity + tappable link preview is the entire UX.
**HYL** — secondary. Wants the teaser body to stay under Telegram's 4096-char ceiling without any future "ugh it split into parts" surprise.

### Background
Per EP0006, in `teaser_link` mode the Telegram adapter sends one message: a short summary that links to the GitHub Pages URL produced by US0029. This story is the pure renderer — no I/O, no Telegram API, no Publisher. Takes `RenderedIssue + url`, returns an HTML string that's safe for `parse_mode=HTML` and guaranteed ≤ 4096 chars.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| EP0006 | Length | Output ≤ 4096 chars (Telegram single-message ceiling) | Length invariant enforced by the renderer, not by the caller |
| EP0006 | Format | Telegram HTML parse_mode (`<b>`, `<i>`, `<a href=...>`, `<code>`, etc.) | Output uses Telegram's HTML subset only |
| EP0004 TC0244 | Escape ordering | `&` → `&amp;` MUST happen first; then `<`/`>` | Reuse `escape_telegram_html` from existing `delivery/escaping.py` |
| EP0005 | Source data | Reads `issue.deep_dives` titles + `len(quick_mentions)` count + `issue.issue_date` | Operates on structured data, not regex-parsed body_md |

---

## Acceptance Criteria

### AC1: Signature and purity
- **Given** `from techletter.delivery.renderers.telegram_teaser import render`
- **When** called as `render(issue: RenderedIssue, *, url: str) -> str`
- **Then** the function is deterministic: two calls with the same inputs return byte-identical strings
- **And** no I/O, no time-of-day calls, no random source

### AC2: Length invariant — always ≤ 4096 chars
- **Given** any `RenderedIssue` and any `url` (≤ 2048 chars, a sane upper bound)
- **When** `render(issue, url=url)` is called
- **Then** `len(output) <= 4096`
- **And** the test asserts this on a worst-case fixture: 5 deep dives with long titles + a long URL

### AC3: Required content present
- **Given** the teaser output
- **When** inspected
- **Then** it contains:
  - The issue date (ISO format `YYYY-MM-DD`)
  - The URL **verbatim** (no shortening, no rewriting)
  - At least one deep-dive title (up to N where N defaults to 3, configurable via a module constant)
  - A "전문 보기" (or equivalent) phrase preceding the URL
- **And** the URL appears inside an `<a href="...">...</a>` tag (HTML parse mode) OR as a bare URL (link preview works for both; the renderer picks one and is consistent)

### AC4: HTML escape of titles
- **Given** a `DeepDive(title="X < Y & Z")`
- **When** rendered into the teaser
- **Then** the output contains `X &lt; Y &amp; Z` (escaped)
- **And** the document parses cleanly as Telegram HTML (no broken tags)

### AC5: URL appears verbatim, but is also wrapped safely
- **Given** a URL with HTML-special chars (e.g., `https://example.com/?a=1&b=2`)
- **When** rendered
- **Then** the URL appears inside an `<a>` tag with the value HTML-escaped (`&amp;` not `&`)
- **And** the visible href text shows a human-readable form (e.g., the domain + path, or the title with the URL as href)

### AC6: Truncates deep-dive title count if too many
- **Given** an issue with 5 deep dives
- **When** rendered with default `max_titles=3`
- **Then** only the first 3 deep-dive titles appear
- **And** the teaser still fits within length budget

### AC7: Empty deep_dives / quick_mentions handled
- **Given** an issue with `deep_dives=[]` and `quick_mentions=[]` (unusual but possible)
- **When** rendered
- **Then** the output still contains the header, date, URL, and a graceful "no items this week" or equivalent placeholder
- **And** does not raise

### AC8: Module exposes the max_titles constant
- **Given** the module
- **When** imported
- **Then** `DEFAULT_MAX_DEEP_DIVE_TITLES = 3` (or similar named constant) is at module level
- **And** the public `render` signature accepts `max_titles: int | None = None` (None → use the default)

---

## Scope

### In Scope
- `techletter/delivery/renderers/telegram_teaser.py` — `render(issue, *, url, max_titles=None)`.
- Reuses `escape_telegram_html` from `techletter/delivery/escaping.py` (existing helper from EP0004).
- Unit tests in `tests/unit/delivery/renderers/test_telegram_teaser.py`.
- Property-based test (hypothesis): for any reasonable input, `len(output) <= 4096`.

### Out of Scope
- Telegram API call / Bot transport (US0031).
- Link-preview meta tags on the HTML page (already part of EP0005's `html_web` via `<title>`).
- Subject line customization, emoji selection from external dict, i18n of the "전문 보기" label.

---

## Technical Notes

- Output format (illustrative, not normative):

  ```
  🗞 <b>Tech-Letter — 2026-05-21</b>

  이번 주 Deep Dives 3편 + Quick Mentions 5건

  — Deep Dives —
  • Diffusion-as-Optimizer 논문
  • vLLM v0.7 릴리스
  • MoE routing 블로그

  <b>전문 보기 ▶</b> <a href="https://user.github.io/repo/issues/...">github.io 페이지 열기</a>
  ```

- Length budgeting strategy:
  1. Reserve a fixed prefix length (header + counts + URL + footer) — ~300 chars
  2. Compute remaining budget for deep-dive titles
  3. Take up to `max_titles` titles
  4. If any single title is too long for the remaining budget, truncate with `…`
  5. Always re-verify `len(output) <= 4096` at the end (defensive)

- Escape policy: All user-controlled strings (titles, URLs in href) pass through `escape_telegram_html` before rendering. Static template strings are safe as-is.

### API Contracts

```python
DEFAULT_MAX_DEEP_DIVE_TITLES = 3

def render(
    issue: RenderedIssue,
    *,
    url: str,
    max_titles: int | None = None,
) -> str: ...
```

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `url` is empty | Raise `ValueError("url must be a non-empty string")` — caller bug |
| `url` exceeds 4096 chars by itself | Raise `ValueError("url too long")` — defensive; should not happen with GitHub Pages URLs |
| Title contains zero-width chars / weird unicode | Render as-is (Telegram handles unicode); length count is on Python `len()` which counts code points |
| All deep_dive titles together would exceed 4096 even with truncation | Truncate to N titles AND apply per-title truncation; final fallback is the first title only |
| `max_titles=0` | Render the teaser without any deep-dive listings (just the URL + header) |

---

## Test Scenarios

- [ ] Default fixture → output is a non-empty string, contains date, URL, and 3 titles.
- [ ] URL appears in an `<a href="...">` tag with HTML-escaped href.
- [ ] Title with `<`, `>`, `&` is escaped in the output.
- [ ] 5-deep-dive input + `max_titles=3` → only 3 titles rendered, in order.
- [ ] Empty deep_dives + empty quick_mentions → placeholder rendered, still includes URL.
- [ ] Deterministic: two calls with same input produce identical bytes.
- [ ] **Property test (hypothesis):** for any `RenderedIssue` generated with reasonable title lengths and URL up to 2048 chars, `len(render(issue, url=url)) <= 4096`. 200 examples per PR, nightly 2000.
- [ ] `url=""` raises `ValueError`.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0023](US0023-sidecar-json-persistence.md) | Data | Populated `RenderedIssue.deep_dives` | Done |

### External Dependencies

None new. `hypothesis` already in dev deps.

---

## Estimation

**Story Points:** 2
**Complexity:** Low. The length-budget math is the trickiest part; one property-based test handles the worst cases.

---

## Open Questions

- [ ] Use bare URL vs `<a>` tag for the link? Both work for Telegram preview. Lean **`<a>` tag with a friendly text** ("전문 보기 ▶") so the URL doesn't visually dominate.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | HYL | Story created from CR-0002 (Item 3) via `/sdlc-studio cr action`. |

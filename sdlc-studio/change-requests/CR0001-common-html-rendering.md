# CR-0001: Common HTML Rendering (Web + Email)

> **Status:** In Progress
> **Priority:** P2
> **Type:** feature-request
> **Requester:** HYL
> **Date:** 2026-05-21
> **Affects:** F-05 Email delivery, F-07 Telegram delivery (indirect — enables CR-0002)
> **Depends on:** —

## Summary

Replace the current Markdown-string-everywhere rendering with a shared HTML renderer that produces visually consistent web and email output from a single template/component layer. The current `EmailAdapter` wraps the raw Markdown body in `<pre>`, so subscribers see literal `**bold**`, `##`, and `[text](url)` syntax in their inbox. This CR also introduces sidecar JSON persistence so the structured `DeepDive`/`QuickMention` data survives the `draft → send` file boundary — without that, the renderer has nothing structured to consume and falls back to re-parsing Markdown with regex.

## Problem

The newsletter today reaches subscribers' inboxes as a wall of monospaced Markdown source. `EmailAdapter._wrap_html` (`techletter/delivery/email.py:185-191`) HTML-escapes the entire Markdown body and wraps it in `<pre>` — so `**Title**` renders as four literal characters, headings show their hashes, and links are unclickable. Beyond immediate readability, there's a structural problem: `assemble_issue` produces structured `DeepDive` / `QuickMention` lists, but only `body_md` survives to disk (`drafts/<issue_id>.md`). `send` reads the `.md`, builds a `RenderedIssue` with empty `deep_dives` / `quick_mentions`, and every adapter is forced to re-parse Markdown with regex. CR-0002 (Telegram link mode) needs the structured data and an HTML page to link to, so this CR is the structural prerequisite for that work.

---

## Proposed Changes

### Item 1: Sidecar JSON persistence for `RenderedIssue` structure

**Priority:** P2
**Effort:** S (4 pts)

Define an `IssueStructure` pydantic model carrying `deep_dives`, `quick_mentions`, and `meta`. `assemble_issue` returns it alongside `RenderedIssue`. `draft` writes `drafts/<issue_id>.json` alongside `drafts/<issue_id>.md`. `send` loads both and reconstructs the full `RenderedIssue` — missing `.json` is a warning (legacy fallback), not an error. Cross-check `body_md` between `.md` and sidecar; warn on mismatch (catches reviewers editing the `.md` after draft generation). `content_sha256` is still computed from `body_md` alone; sidecar is auxiliary and does **not** participate in the idempotency hash.

### Item 2: Shared design tokens + Jinja2 component partials

**Priority:** P2
**Effort:** S (2 pts)

Add `techletter/delivery/renderers/tokens.py` exporting `COLORS`, `FONT`, `LAYOUT` dicts. Add `techletter/delivery/templates/components/{deep_dive,quick_mention}.html.j2` partials. Both web and email templates `{% include %}` these — a change to a component is reflected in both outputs.

### Item 3: `html_web` renderer + golden fixture

**Priority:** P2
**Effort:** M (3 pts)

`techletter/delivery/renderers/html_web.py` returns a complete `<!DOCTYPE html>` document via `web.html.j2`. Modern CSS allowed (flexbox OK). `<meta name="robots" content="noindex, nofollow">` present. One golden fixture committed under `tests/fixtures/golden/web_<sample>.html`; CI fails on byte diff. The output is the source page CR-0002 will publish to GitHub Pages.

### Item 4: `html_email` renderer + premailer CSS inlining

**Priority:** P2
**Effort:** M (4 pts)

`techletter/delivery/renderers/html_email.py` reuses the same component partials but wraps them in a table-based layout (`email.html.j2`). CSS lives in `<head>`, then `premailer.transform()` inlines every rule onto `style=""` attributes. Width capped at 680px. Output ≤ 102 KB on the canonical sample (Gmail clipping threshold). One golden fixture committed.

### Item 5: `EmailAdapter` swap

**Priority:** P2
**Effort:** S (3 pts)

Drop `_wrap_html` from `EmailAdapter`. Call `html_email.render(issue)` once per `send()` and reuse across recipients (cache, since SMTP loop runs after rendering). Plain-text alternative path (`strip_markdown(body_md)`) unchanged. Manual smoke against Gmail + Apple Mail by HYL.

---

## Impact Assessment

### Existing Functionality

- **Email delivery (F-05):** behavior changes from "wrapped raw markdown" to "properly rendered HTML email". Plain-text fallback unchanged. SMTP connection pattern (one connection per send, per-recipient MIME) unchanged.
- **Idempotency (EP0003):** `content_sha256` remains computed from `body_md` — this CR explicitly does NOT change the hash. Existing `SendRecord` entries remain valid.
- **Draft → send file flow (EP0003):** new `.json` sibling file. PR review experience: reviewer reads `.md` (unchanged), `.json` is auto-generated metadata (recommend `.gitattributes linguist-generated` to collapse diff).
- **Slack and Telegram adapters:** untouched in this CR. They continue on their existing string-conversion paths.

### Affected Modules

| Module | Impact | Change Type |
| --- | --- | --- |
| `techletter/compose/issue.py` | Add `to_sidecar_json()` / `from_sidecar_json()` helpers | Modified |
| `techletter/orchestration/cli.py` | `draft` writes sidecar; `send` reads sidecar | Modified |
| `techletter/delivery/renderers/` | New module: `tokens.py`, `html_web.py`, `html_email.py` | New |
| `techletter/delivery/templates/` | New: `web.html.j2`, `email.html.j2`, components | New |
| `techletter/delivery/email.py` | Drop `_wrap_html`; call `html_email.render` | Modified |
| `pyproject.toml` | Add `jinja2`, `markdown-it-py`, `premailer` | Modified |
| `tests/fixtures/golden/` | New: `web_<sample>.html`, `email_<sample>.html` | New |

### Breaking Changes

- None for downstream consumers — `ChannelAdapter` Protocol unchanged.
- Operationally: subscribers' next email is dramatically different in appearance (this is the *goal*). Worth a heads-up note in the first newsletter that uses the new renderer.

---

## Acceptance Criteria

- [ ] `drafts/<issue_id>.json` is written by `uv run techletter draft` with a stable, documented schema; round-trips via pydantic.
- [ ] `uv run techletter send --draft-path drafts/<issue_id>.md` auto-loads the matching `.json` and constructs `RenderedIssue` with non-empty `deep_dives` / `quick_mentions`. Missing `.json` is a warning, not an error.
- [ ] `content_sha256` for a given `body_md` is **unchanged** from EP0004 (regression-pinned in test).
- [ ] `tokens.py` is the single source for colors/fonts/spacing; no inline color literals in templates.
- [ ] A change to a component partial reflects in both `web.html` and `email.html` outputs (verified by golden diff).
- [ ] `html_web.render` output contains `<meta name="robots" content="noindex, nofollow">`.
- [ ] `html_email.render` output contains **no `<style>` blocks** (all rules inlined). Output ≤ 102 KB on the canonical sample.
- [ ] `EmailAdapter` no longer references `_wrap_html`. HTML body computed once per send, reused across recipients.
- [ ] `uv.lock` updated; `uv run pytest` green; golden fixtures committed.
- [ ] README updated with one screenshot pair (web + email side-by-side on the same sample).

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Sidecar `.json` and `.md` drift after manual edit during PR review | M | M | Cross-check `body_md` on `send`; warn on mismatch and prefer the `.md` |
| Gmail 102 KB clipping triggers on long issues | L | M | Compress whitespace; cap inline CSS surface; future graceful fallback to CR-0002 web link once available |
| Outlook desktop ignores flexbox in shared components | M | L | Email components designed table-friendly; web template wraps with flex, email never does |
| `markdown-it-py` output subtly differs from expectation → confusing diffs | L | L | Renderer changes never affect `content_sha256` (hash is on `body_md`); golden fixtures catch surprises |
| `premailer` slow on large CSS | L | L | Cache `html_email.render(issue)` per-issue (AC requires it) |

---

## Dependencies

### CR Dependencies

None.

### External Dependencies

| Dependency | Type | Status |
| --- | --- | --- |
| `jinja2` | new pip dep | available |
| `markdown-it-py` | new pip dep | available |
| `premailer` | new pip dep | available |

---

## Linked Epics

| Epic | Title | Status |
| --- | --- | --- |
| [EP0005](../epics/EP0005-common-html-rendering.md) | Common HTML Rendering (Web + Email) | Draft |

**Linked Stories:** US0023 (sidecar JSON), US0024 (tokens + components), US0025 (`html_web` + golden), US0026 (`html_email` + premailer), US0027 (`EmailAdapter` swap).

---

## Out of Scope

- GitHub Pages publishing (covered by CR-0002).
- Telegram teaser/link mode (covered by CR-0002).
- Slack Block Kit upgrade (separate future CR).
- MJML or non-Python email build pipelines.
- Dark-mode-specific styling (use `prefers-color-scheme` if cheap; ship light theme otherwise).
- Image-heavy layouts (text + link cards only).

---

## Open Questions

- [ ] Mark sidecar `.json` as `linguist-generated` in `.gitattributes` to collapse PR diffs? — Owner: HYL
- [ ] `markdown-it-py` vs `markdown` (Python-Markdown)? Default `markdown-it-py` for CommonMark compliance, confirm during implementation. — Owner: HYL
- [ ] Populate `RenderedIssue.deep_dives` / `quick_mentions` directly, or keep them on a separate `IssueStructure`? Leaning toward populating on `RenderedIssue` for simpler downstream. — Owner: HYL

---

## Close Reason

> *Filled when CR is closed*

---

## Revision History

| Date | Author | Change |
| --- | --- | --- |
| 2026-05-21 | HYL | CR proposed. Draft epic content preserved at `sdlc-studio/.local/draft-epic-content/EP0005-common-html-rendering.md` for reference when `cr action` generates the formal epic. |
| 2026-05-21 | HYL | CR actioned via `/sdlc-studio cr action --cr CR-0001` — 1 epic (EP0005), 5 stories (US0023–US0027) created. Status: Proposed → In Progress. PRD F-05 description updated with CR reference. |

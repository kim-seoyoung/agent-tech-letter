# EP0005: Common HTML Rendering (Web + Email)

> **Status:** Done
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-21
> **Target Release:** v1.1 (post-launch readability + multi-output rendering)
> **Change Request:** [CR-0001: Common HTML Rendering (Web + Email)](../change-requests/CR0001-common-html-rendering.md)

## Summary

Replace the current Markdown-string-everywhere rendering with a shared HTML renderer that produces visually consistent web and email output from a single template/component layer. The current `EmailAdapter` wraps the raw Markdown body in `<pre>`, so subscribers see literal `**bold**`, `##`, and `[text](url)` syntax in their inbox — unacceptable for v1.1. This epic introduces (1) sidecar-JSON persistence so `RenderedIssue` structure survives the draft → send file boundary, (2) shared Jinja2 components + design tokens, and (3) two output renderers (`html_web`, `html_email`) sharing those components. Email rendering is upgraded in place; the web-page output is a prerequisite for the GitHub Pages + Telegram link-mode work (tracked separately via CR-0002).

## Inherited Constraints

| Source | Type | Constraint | Impact |
|--------|------|------------|--------|
| CR-0001 | Origin | All 5 CR items in scope of this epic | Story breakdown maps 1:1 to CR items |
| EP0002 | Composition | `assemble_issue` produces `DeepDive` + `QuickMention` lists; only `body_md` survives to disk today | Must add a sidecar `.json` written alongside `.md` so `send` can reconstruct structured data |
| EP0003 | Idempotency | `content_sha256` derived from `body_md` is the idempotency key (`SendRecord`) | Sidecar JSON must NOT participate in the hash; same `.md` → same hash |
| EP0004 | Email | Plain-text alternative derived from `strip_markdown(body_md)`; per-recipient send, no BCC | Keep plain-text fallback; only the HTML alternative changes |
| EP0004 | Email | One SMTP connection per send pass | Renderer must complete before SMTP open — no I/O inside the loop |
| EP0004 | ChannelAdapter | Protocol unchanged: `send(issue, recipients) -> SendReport` | Adapter swap is internal; orchestration untouched |
| TRD | Determinism | Renderers must be deterministic: same input → byte-identical output | Required so future-CI can diff golden fixtures |
| TRD | Dependencies | New libraries enter via `pyproject.toml` + `uv lock` | Adds `jinja2`, `markdown-it-py`, `premailer` |

---

## Business Context

### Problem Statement
The newsletter today reaches subscribers' inboxes as a wall of monospaced Markdown source. The `EmailAdapter._wrap_html` helper (`techletter/delivery/email.py:185-191`) wraps the entire Markdown body in `<pre>` after HTML-escaping it — so `**Title**` renders as the literal four characters, headings show their hashes, and links are unclickable. The Researcher Subscriber persona is the only audience (PRD v0.4.0); they are technically tolerant but the current output undermines the perceived quality of the curation work EP0002 produces. Beyond the immediate readability issue, the GitHub Pages + Telegram link-mode work (CR-0002) needs a hosted web page to link to — and we want the web page and the email to look the same, not diverge into two unrelated templates.

**PRD Reference:** [§3 F-05 Email delivery (SMTP)](../prd.md#3-feature-inventory) — implicit quality bar (HTML email, not raw markdown).

### Value Proposition
Two outputs for the price of one renderer. Subscribers get a properly typeset email immediately (v1.1 ship), and the follow-on CR-0002 work inherits a finished web-page renderer to publish to GitHub Pages — no duplicated styling work, no design drift between channels.

### Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Email body shows rendered Markdown (no `**`, `##`, `[]()` in inbox) | 0% | 100% | Manual inspection across Gmail, Apple Mail, Outlook.com |
| Web ↔ email visual parity (deep-dive block) | n/a | "looks the same" side-by-side | Manual reviewer signoff; same component partial drives both |
| Golden HTML fixture diff stability on rebuild | n/a | byte-identical | `pytest` golden compare |
| Sidecar JSON written alongside every `drafts/*.md` | 0% | 100% | `draft` command writes both; integration test |

---

## Scope

### In Scope
- **Sidecar JSON persistence**: `draft` writes `drafts/<issue_id>.json` alongside `drafts/<issue_id>.md`, containing `deep_dives`, `quick_mentions`, and `meta`. `send` loads both and reconstructs the full `RenderedIssue`. Fallback: if `.json` is missing (legacy drafts), continue with `body_md`-only behavior.
- **`content_sha256` invariant preserved**: hash is still computed from `body_md` alone. Sidecar JSON is auxiliary.
- **Design token module** (`techletter/delivery/renderers/tokens.py`) — colors, fonts, spacing as Python constants imported by templates.
- **Shared Jinja2 components** under `techletter/delivery/templates/components/`: `deep_dive.html.j2`, `quick_mention.html.j2`. Both web and email templates `{% include %}` them.
- **`html_web.py` renderer**: produces a complete `<!DOCTYPE html>` page with a `<style>` block; modern CSS allowed (flexbox OK). `noindex,nofollow` meta. The web-page output is what CR-0002 publishes to GitHub Pages.
- **`html_email.py` renderer**: same content + same component partials, but wrapped in table-based layout for client compatibility; CSS in `<head>` then run through `premailer.transform()` to inline every rule onto `style=""` attributes. Width capped at 680px.
- **`markdown-it-py`** used to render the per-`DeepDive` `body_md` body into HTML for both renderers (not used to re-parse the assembled issue).
- **`EmailAdapter` swap**: `_wrap_html` deleted; `html_email.render(issue)` replaces it. Plain-text alternative path unchanged.
- **Golden fixtures**: one `RenderedIssue` fixture → two golden HTML files (`web.html`, `email.html`); CI diff guards regressions.

### Out of Scope
- GitHub Pages publishing — covered by CR-0002.
- Telegram link-mode / teaser rendering — covered by CR-0002.
- Slack Block Kit upgrade — separate future CR, not blocked by this work.
- A general "send a 4th channel" capability — adapter pattern already supports it.
- MJML, Maizzle, or any non-Python email build pipeline. We do CSS inlining in Python (`premailer`) to keep the build self-contained.
- Dark-mode-specific styling. Use `prefers-color-scheme` if cheap; otherwise ship the light theme.
- Image-heavy layouts (hero images, cover art). Text + link cards only in v1.1.

### Affected Personas
- **Researcher Subscriber:** primary — they finally see a properly typeset newsletter in their inbox. Cross-client rendering (Gmail web, Gmail iOS, Apple Mail, Outlook desktop) is what they notice.
- **HYL:** secondary — needs the renderer to be a clean dependency for CR-0002 and to not require touching email-client quirks every release.

---

## Acceptance Criteria (Epic Level)

- [ ] `drafts/<issue_id>.json` is written by `uv run techletter draft` and contains `deep_dives`, `quick_mentions`, `meta` in a stable, documented schema (pydantic-validated round-trip).
- [ ] `uv run techletter send --draft-path drafts/<issue_id>.md` loads the matching `.json` (same stem) automatically and constructs `RenderedIssue` with non-empty `deep_dives` / `quick_mentions`. Missing `.json` is a warning, not an error (legacy fallback).
- [ ] `content_sha256` value for a given `body_md` is unchanged from EP0004 (regression-pinned in test).
- [ ] `techletter/delivery/renderers/tokens.py` exports `COLORS`, `FONT`, `LAYOUT` dicts; templates import only these (no inline colors).
- [ ] `templates/components/deep_dive.html.j2` and `quick_mention.html.j2` are included by both `web.html.j2` and `email.html.j2`. A change to a component partial is reflected in both outputs (verified by golden diff).
- [ ] `html_web.render(issue)` returns a complete `<!DOCTYPE html>` document. `<meta name="robots" content="noindex, nofollow">` is present.
- [ ] `html_email.render(issue)` returns HTML with **no `<style>` blocks remaining** (all rules inlined via premailer). Output ≤ 102 KB (Gmail clipping threshold) for a typical 3-deep-dive + 10-mention issue.
- [ ] `EmailAdapter` no longer references `_wrap_html`; it calls `html_email.render(issue)` exactly once per `send()` (cached for all recipients). Plain-text alternative still derived from `strip_markdown(body_md)`.
- [ ] Two golden HTML fixtures committed under `tests/fixtures/golden/` (`web_<sample-id>.html`, `email_<sample-id>.html`). CI fails on byte diff.
- [ ] `pyproject.toml` adds `jinja2`, `markdown-it-py`, `premailer`; `uv.lock` updated; `uv run pytest` green.
- [ ] README updated with one screenshot pair (web + email side-by-side rendering of the same sample issue).

---

## Dependencies

### Blocked By

| Dependency | Type | Status | Owner |
|------------|------|--------|-------|
| EP0002 Composition Pipeline | Epic | Done | HYL |
| EP0003 Orchestration | Epic | Done | HYL |
| EP0004 Multi-channel Delivery | Epic | Done | HYL |

(All three are shipped; this epic is purely an upgrade-in-place.)

### Blocking

| Item | Type | Impact |
|------|------|--------|
| CR-0002 (GitHub Pages + Telegram link mode) | CR | Needs `html_web` renderer to produce the page; needs sidecar JSON so `send` has structure to render |

---

## Risks & Assumptions

### Assumptions
- `markdown-it-py` handles every Markdown construct EP0002's compose prompts produce (bold, italic, links, code spans, lists, blockquotes, fenced code blocks). No custom tokens needed.
- `premailer` covers our CSS surface (no `:has()`, no container queries; flexbox in web only, table layout in email).
- Sidecar JSON survives the draft-as-PR-merge flow because the merge keeps both files together; the human reviewer reviews `.md` and ignores `.json` (gitattributes can mark it linguist-generated to collapse the diff).
- 680px content width is acceptable for both modern email clients and modern browsers.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Sidecar `.json` and `.md` drift after manual edit during PR review | M | M | Sidecar stores body_md too; `send` cross-checks and prefers `.md` on mismatch with a warning |
| Gmail clipping at 102 KB triggers on long issues with all 10 quick mentions inlined | L | M | Compress whitespace in `html_email.render`; cap inline CSS surface; if hit, link to web page (CR-0002) as graceful degradation |
| Outlook desktop fails to honor flexbox in shared components | M | L | Components designed table-friendly; web template *can* use flex around them, email *must* not |
| `markdown-it-py` HTML output differs subtly from current `body_md` → `content_sha256` regressions | L | M | Hash is on `body_md`, not on rendered HTML; renderer change does not move the hash. Pin a regression test. |
| `premailer` slow on large CSS (parses with `lxml`) | L | L | Cache `html_email.render(issue)` per-issue (compute once, reuse for all recipients) — already an AC |
| Sidecar JSON leaks secrets/PII via `meta` | L | M | Schema explicit allowlist (`deep_dive_count`, token usage, source counts only) |
| Design-token iteration during US0024 stretches scope (HYL refines palette/spacing visually) | M | L | Lock the *keys* of `COLORS`/`FONT`/`LAYOUT` in US0024 AC1 so US0025/26 can proceed against placeholder values; hex/px refinements land in follow-up commits without restructuring |

---

## Technical Considerations

### Architecture Impact
Introduces a **renderer layer** between the orchestration boundary (`RenderedIssue`) and the channel adapters. Today each adapter parses `body_md` directly; after this epic, every HTML-bearing adapter calls into `html_email` or `html_web`. The `ChannelAdapter` Protocol is unchanged. Slack and Telegram are **not** touched in this epic (kept on their existing string-conversion path until CR-0002).

The sidecar JSON pattern follows a known convention (similar to Jekyll's `_data/`, MDX frontmatter), keeping the human-readable `.md` clean for PR review while preserving machine-readable structure for the renderer.

### Integration Points
- **Jinja2** for template rendering.
- **markdown-it-py** for `DeepDive.body_md` → HTML conversion (one direction, never used to re-parse a full issue).
- **premailer** for CSS inlining at email render time.
- **`pydantic`** schema for the sidecar JSON model (`IssueStructure`); reuses `DeepDive` / `QuickMention` directly via `.model_dump_json()` / `.model_validate_json()`.
- **`techletter/orchestration/cli.py`**: `draft` writes sidecar; `send` loads sidecar.

### Directory Layout (post-epic)

```
techletter/
├─ delivery/
│   ├─ renderers/
│   │   ├─ __init__.py
│   │   ├─ tokens.py                  # design tokens
│   │   ├─ html_web.py                # full HTML page renderer
│   │   └─ html_email.py              # email-safe HTML renderer (premailer)
│   ├─ templates/
│   │   ├─ web.html.j2
│   │   ├─ email.html.j2
│   │   └─ components/
│   │       ├─ deep_dive.html.j2
│   │       └─ quick_mention.html.j2
│   ├─ email.py                       # _wrap_html removed
│   ├─ telegram.py                    # untouched (CR-0002)
│   └─ slack.py                       # untouched
├─ orchestration/
│   └─ cli.py                         # draft writes sidecar; send reads sidecar
└─ compose/
    └─ issue.py                       # add to_sidecar_json() / from_sidecar_json() helpers
```

---

## Sizing

**Story Points:** 16
**Estimated Story Count:** 5

**Complexity Factors:**
- Cross-client email rendering iteration (Gmail/Apple Mail/Outlook). Plan for 1–2 manual smoke rounds.
- Premailer integration usually shakes out CSS-spec mismatches the first time it's wired.
- Sidecar JSON schema design must be forward-compatible (we'll evolve it over CR-0002+).
- Two golden fixtures (web + email) need an initial blessed version + a stable regeneration recipe.

---

## Story Breakdown

Stories generated 2026-05-21 from CR-0001 via `/sdlc-studio cr action`. See [Story Index](../stories/_index.md) for full details.

- [x] [US0023](../stories/US0023-sidecar-json-persistence.md) — Sidecar JSON persistence for `RenderedIssue` structure (4 pts)
- [x] [US0024](../stories/US0024-design-tokens-and-jinja2-components.md) — Design tokens + Jinja2 component partials (2 pts)
- [x] [US0025](../stories/US0025-html-web-renderer-and-golden-fixture.md) — `html_web` renderer + golden fixture (3 pts)
- [x] [US0026](../stories/US0026-html-email-renderer-and-premailer-inlining.md) — `html_email` renderer + premailer CSS inlining (4 pts)
- [x] [US0027](../stories/US0027-email-adapter-swap.md) — `EmailAdapter` swap (drop `_wrap_html`) (3 pts)

**Total:** 16 story points across 5 stories.

---

## Test Plan

**Test Spec:** TS0005 — Common HTML Rendering (to be authored).

- **Unit (renderers, pure functions):** `html_web.render` and `html_email.render` against a small set of `RenderedIssue` fixtures — empty quick mentions, max quick mentions, body_md with all Markdown constructs (bold/italic/code/link/list/blockquote/fenced code), title with HTML-special chars (`& < >` must be escaped, not rendered as tags).
- **Unit (premailer integration):** assert no `<style>` block survives in `html_email` output; assert `style="..."` attributes present on representative elements.
- **Unit (sidecar):** `IssueStructure` round-trip via `model_dump_json` / `model_validate_json`; missing-sidecar fallback path; mismatched-`body_md` warning path.
- **Golden:** one canonical sample → `web.html` + `email.html` blessed fixtures; CI fails on byte diff. Regeneration recipe documented (`pytest --regenerate-golden`).
- **Integration:** `draft` → `send` round-trip on a temp dir; assert `.json` written; assert email adapter receives non-empty `deep_dives`.
- **Manual smoke (HYL-owned):** send the sample to a personal Gmail + Apple Mail; visually verify; capture screenshot for README.

---

## Open Questions

- [ ] **Sidecar JSON in `.gitattributes` as `linguist-generated`?** Collapses the diff in PR view; lean yes but want to confirm reviewers can still expand it on demand. — Owner: HYL (inherited from CR-0001)
- [ ] **markdown-it-py vs `markdown` (Python-Markdown)?** Default to `markdown-it-py` for CommonMark compliance and plugin ecosystem, unless we encounter a packaging issue under `uv`. — Owner: HYL (inherited from CR-0001)
- [ ] **Should `assemble_issue` populate `RenderedIssue.deep_dives` / `quick_mentions` directly,** or keep them on a separate `IssueStructure` returned alongside? Leaning toward populating on `RenderedIssue` (simpler downstream) — confirm during US0023. — Owner: HYL (inherited from CR-0001)

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | HYL | Epic created from CR-0001 via `/sdlc-studio cr action`. 5 stories generated (US0023–US0027), 16 pts total. |
| 2026-05-21 | Claude (via /sdlc-studio epic implement --epic EP0005) | All 5 stories implemented and cascaded to Done. 50 new tests added (0 failing), 340 pass total (1 unrelated pre-existing failure). Ruff clean. Deps added: jinja2, markdown-it-py, premailer. AC9 manual smoke check (US0027) remains HYL-owned. |

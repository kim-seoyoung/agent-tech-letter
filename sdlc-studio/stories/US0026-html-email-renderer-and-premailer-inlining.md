# US0026: `html_email` renderer + premailer CSS inlining

> **Status:** Done
> **Epic:** [EP0005: Common HTML Rendering (Web + Email)](../epics/EP0005-common-html-rendering.md)
> **Change Request:** [CR-0001](../change-requests/CR0001-common-html-rendering.md) (Item 4)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-21
> **Promoted to Ready:** 2026-05-21 (RV0001 — F-2 AC5 tightened, F-3 helper coupling made explicit via AC10)

## User Story

**As** the Researcher Subscriber reading the email in Gmail / Apple Mail / Outlook
**I want** the weekly newsletter to render as a clean, properly typeset HTML email
**So that** I see real headlines, real links, and visual hierarchy — not raw `**Markdown**` syntax.

## Context

### Persona Reference
**Researcher Subscriber** — primary. They open the email in their normal mail client. This is the headline outcome of CR-0001.
**HYL** — secondary. Wants the email to match the web archive (CR-0002) visually.

### Background
This is the **email-side** twin of US0025. Same shared component partials from US0024, same design tokens, but wrapped in a table-based layout for client compatibility, with all CSS rules inlined via `premailer.transform()`. The output has no surviving `<style>` blocks — every rule has been pushed onto `style=""` attributes so even the most hostile client (Outlook desktop) renders correctly. Width is capped at 680px. Total size ≤ 102 KB on the canonical sample (Gmail's clipping threshold).

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| EP0005 AC | No `<style>` blocks | All CSS inlined via premailer | Post-condition asserted in tests |
| EP0005 AC | Size cap | ≤ 102 KB on canonical sample | Whitespace compressed; cap inline CSS surface |
| EP0005 AC | Width | ≤ 680px content width | `LAYOUT.max_width` from tokens |
| EP0004 Email | Plain-text alternative | Derived from `strip_markdown(body_md)` | Out of scope here; US0027 handles |
| US0024 | Components | Share partials with `html_web` | Renderer uses same `{% include %}` |
| CR-0001 | Out of scope | No dark-mode specific CSS | Use `prefers-color-scheme` only if cheap |

---

## Acceptance Criteria

### AC1: `html_email.render` signature
- **Given** the module `techletter.delivery.renderers.html_email`
- **When** imported
- **Then** `render(issue: RenderedIssue) -> str` is the public entry point
- **And** the function is deterministic: two calls on the same issue return byte-identical strings
- **And** no I/O occurs inside `render` (premailer is in-process, no network)

### AC2: No `<style>` blocks survive
- **Given** `render(issue)` output
- **When** parsed as HTML
- **Then** **zero** `<style>` elements exist anywhere
- **And** the test asserts `'<style' not in output` (case-insensitive)
- **And** any premailer-unsafe rules (e.g., `@media`, `:hover`) are removed rather than retained in a leftover `<style>` block (premailer's `keep_style_tags=False` is set)

### AC3: Table-based layout, max 680px
- **Given** the output
- **When** parsed
- **Then** the outermost layout is a `<table role="presentation">` with `cellpadding="0" cellspacing="0" border="0"`
- **And** a nested table has `width="680"` (or matches `LAYOUT.max_width` as a number)
- **And** no `<div>` is used as a layout primitive at the top level (acceptable inside content where it doesn't affect column structure)

### AC4: Shared partials drive content
- **Given** an `issue` with 3 deep dives and 10 quick mentions
- **When** rendered
- **Then** the output contains the same component structure produced by US0024's partials (each `<section class="deep-dive">` with its title, tag, link, body)
- **And** the inner content of each component (modulo inlined styles) matches what `html_web` produces for the same issue

### AC5: Premailer inlines tokens onto representative elements
- **Given** the email template's `<head>` contains CSS rules referencing token values
- **When** premailer runs
- **Then** **representative styled elements** carry a `style="..."` attribute whose computed values match the corresponding token values from `tokens.py`:
  - the deep-dive `<h2>` has `font-size` matching `FONT["size_h2"]` and `color` matching `COLORS["fg"]`
  - the `.tag` span has `background` matching `COLORS["tag_bg"]`
  - the body `<a>` has `color` matching `COLORS["accent"]`
- **And** the rule sources are removed from `<head>`
- **Note:** AC2 covers the "no leftover `<style>` block" claim. AC5 does **not** assert that *every* styled element is inlined — premailer may legitimately drop rules with no matching selector or hoist some into `<head>` reset attributes; only the named representative elements are checked.

### AC6: Output size ≤ 102 KB on canonical sample
- **Given** the canonical sample `RenderedIssue` (3 deep dives, 10 quick mentions, realistic body lengths)
- **When** `render(sample)` runs
- **Then** `len(output.encode('utf-8'))` is `≤ 102_400` bytes
- **And** the test pins this cap so future bloat is caught in CI

### AC7: HTML-special characters in titles are escaped
- **Given** `DeepDive(title="X < Y & Z")`
- **When** rendered
- **Then** the output contains `X &lt; Y &amp; Z`
- **And** the document remains well-formed HTML

### AC8: Golden fixture committed
- **Given** the same canonical sample used in US0025
- **When** `pytest tests/delivery/renderers/test_html_email.py::test_golden` runs
- **Then** `render(sample)` matches `tests/fixtures/golden/email_sample.html` byte-for-byte
- **And** `--regenerate-golden` rewrites it

### AC9: Side-by-side comparison with web is documented
- **Given** the test suite has both `web_sample.html` and `email_sample.html` golden fixtures
- **When** a developer wants to verify visual parity
- **Then** a documented recipe (in `tests/fixtures/golden/README.md` or test docstring) describes how to open both in a browser and compare
- **And** an optional `pytest -m visual_diff` marker exists for manual verification (no automated diff)

### AC10: Markdown-to-HTML helper reuse (no duplicate `markdown-it-py` instance)
- **Given** US0025 introduces a module-private `_body_md_to_html(body_md: str) -> str` helper (or a shared `renderers/_common.py`)
- **When** `html_email.py` converts `DeepDive.body_md` to HTML for the partials
- **Then** it **imports** that helper rather than instantiating its own `markdown-it-py` parser
- **And** a grep over `techletter/delivery/renderers/html_email.py` finds no `from markdown_it import` (only an indirect re-export through the shared module)
- **And** changing the helper's behavior in one place is reflected in both renderers (verified by a small unit test that monkey-patches the helper and observes both outputs change)

---

## Scope

### In Scope
- `techletter/delivery/renderers/html_email.py` with `render(issue)`.
- `techletter/delivery/templates/email.html.j2` (table-based wrapper, includes shared partials).
- Premailer integration with sane defaults: `keep_style_tags=False`, `remove_classes=False` (keep classes for accessibility/debugging), `disable_validation=True` (avoid noisy warnings on table-attributes).
- `tests/fixtures/golden/email_sample.html` (committed).
- `tests/delivery/renderers/test_html_email.py` (unit + golden + size cap).

### Out of Scope
- Swapping the actual `EmailAdapter` to use this renderer — US0027.
- Plain-text alternative regeneration — kept on `strip_markdown(body_md)` path (US0027 leaves this untouched).
- Dark-mode-specific CSS rules (`prefers-color-scheme`) — defer; ship light theme.
- Open tracking pixels, link tracking, bounce handling.
- Images / cover art / social cards.

---

## Technical Notes

- Premailer usage:

  ```python
  from premailer import Premailer
  inlined = Premailer(
      html=raw,
      keep_style_tags=False,
      remove_classes=False,
      strip_important=False,
      disable_validation=True,
  ).transform()
  ```

  Wrap with caching at the `render()` level — premailer is the slowest step.

- Table layout pattern (Litmus / Cerberus-inspired):

  ```html
  <body style="margin:0; padding:0; background:#f5f5f5;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td align="center" style="padding: 24px 0;">
          <table role="presentation" width="680" cellpadding="0" cellspacing="0" border="0"
                 style="background:#fff; max-width:680px;">
            <tr>
              <td style="padding: 32px;">
                <!-- content from shared partials -->
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
  ```

- Email head:

  ```html
  <!DOCTYPE html>
  <html><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light only">
    <title>Tech-Letter — {{ issue.issue_date.strftime('%Y-%m-%d') }}</title>
    <style>
      /* Token-driven rules; premailer inlines these */
      body { font-family: {{ font.family }}; color: {{ colors.fg }}; }
      h2 { font-size: {{ font.size_h2 }}; color: {{ colors.fg }}; }
      .deep-dive { margin-bottom: 32px; }
      a { color: {{ colors.accent }}; }
      .tag { background: {{ colors.tag_bg }}; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
      .meta { color: {{ colors.muted }}; font-size: 14px; }
    </style>
  </head>
  ```

- Whitespace: strip surrounding whitespace per Jinja2 (`trim_blocks=True`, `lstrip_blocks=True`); pre-premailer minimization helps the 102 KB budget.

### API Contracts
- `render(issue: RenderedIssue) -> str` — public.
- Internally uses the same `_body_md_to_html` helper as US0025 (extract into `_common.py` if convenient).

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `premailer` raises on invalid HTML | Surface the exception; failing CI is preferable to a silently broken email |
| Empty `body_md` | Empty `body` div; partial still renders title + meta |
| Output approaches 102 KB | Test catches it; if we hit it for real, the message in CR-0001 is to graceful-degrade by linking to the CR-0002 web page |
| Unicode in titles (e.g., emoji) | Renders as-is; UTF-8 declared in `<head>` |
| `prefers-color-scheme` clients (dark mode) | Light theme rendered; acceptable per CR-0001 out-of-scope |

---

## Test Scenarios

- [ ] `render(sample_issue)` returns a string starting with `<!DOCTYPE html>`.
- [ ] **No `<style>` blocks** in the output (case-insensitive check).
- [ ] At least one `<table role="presentation">` exists at the top level.
- [ ] Nested table has `width="680"` (or matches `LAYOUT.max_width`).
- [ ] All deep dives and quick mentions present, same count and order as input.
- [ ] CommonMark body conversion correct (mirrors US0025).
- [ ] HTML-special chars in titles escaped.
- [ ] Output byte-length ≤ 102 KB on canonical sample.
- [ ] Golden fixture matches byte-for-byte.
- [ ] `--regenerate-golden` overwrites the fixture.
- [ ] A representative element has inlined `style="..."` containing token values.
- [ ] Two consecutive `render` calls → byte-identical.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0024](US0024-design-tokens-and-jinja2-components.md) | Schema | Tokens + component partials | Draft |
| [US0025](US0025-html-web-renderer-and-golden-fixture.md) | **Hard helper dependency** | `_body_md_to_html` — must be imported, **not reimplemented**. See AC10. | Draft |
| [US0023](US0023-sidecar-json-persistence.md) | Schema | Structured data at render time | Draft |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `premailer` | new pip dep | to add in this story |
| `jinja2`, `markdown-it-py` | already added (US0024 / US0025) | available |

---

## Estimation

**Story Points:** 4
**Complexity:** Medium. Premailer integration is straightforward once the template is correct; the iteration cost is in cross-client visual verification (Gmail web/iOS, Apple Mail, Outlook desktop). Plan for one or two pass-and-tweak rounds against real clients before declaring AC9 satisfied.

---

## Open Questions

- [ ] Should we include `mso-` style hacks for Outlook-specific layouts? Defer; only add if smoke testing reveals concrete breakage.
- [ ] Cache premailer output per-issue (in-memory) — needed for adapter perf in US0027, or premature here? Lean **defer to US0027** since the adapter is the one calling render N times conceptually.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | HYL | Story created from CR-0001 (Item 4) via `/sdlc-studio cr action`. |

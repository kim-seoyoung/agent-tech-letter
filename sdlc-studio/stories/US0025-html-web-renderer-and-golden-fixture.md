# US0025: `html_web` renderer + golden fixture

> **Status:** Done
> **Epic:** [EP0005: Common HTML Rendering (Web + Email)](../epics/EP0005-common-html-rendering.md)
> **Change Request:** [CR-0001](../change-requests/CR0001-common-html-rendering.md) (Item 3)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-21
> **Promoted to Ready:** 2026-05-21 (RV0001 — `_body_md_to_html` API contract clarified)

## User Story

**As** the GitHub Pages publisher (in CR-0002) and the Researcher Subscriber (when they tap the link)
**I want** a `RenderedIssue` to produce a complete, self-contained, properly typeset HTML page
**So that** the link the bot sends opens to a clean weekly newsletter that doesn't require any external CSS/JS to look right.

## Context

### Persona Reference
**Researcher Subscriber** — primary. They will read this output in a browser after tapping the Telegram link (after CR-0002 lands).
**HYL** — secondary. Wants the published page to look like the email so design changes don't have to be applied twice.

### Background
This story produces the **web-side** of the shared rendering work. The output is a complete `<!DOCTYPE html>` document with `<style>` in `<head>` (modern CSS allowed — flexbox OK), `<meta name="robots" content="noindex, nofollow">`, and the issue body composed from the shared component partials from US0024. The output is consumed verbatim by `GitHubPagesPublisher` in CR-0002's epic. The golden fixture this story commits is what CI uses to catch regressions.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| EP0005 AC | Page completeness | Returns full `<!DOCTYPE html>` document | Standalone HTML, no external CSS link |
| EP0005 AC | noindex/nofollow | `<meta name="robots" content="noindex, nofollow">` | Hard requirement; appears in `<head>` |
| US0024 | Components | Uses shared `deep_dive.html.j2` and `quick_mention.html.j2` | Renderer wires context + includes |
| US0023 | Structure | `RenderedIssue.deep_dives` / `.quick_mentions` are non-empty (post-sidecar) | Renderer can rely on structured data |
| CR-0001 | Determinism | Same input → byte-identical output | No `datetime.now()` inside render; no random ordering |

---

## Acceptance Criteria

### AC1: `html_web.render` signature and pure-function behavior
- **Given** the module `techletter.delivery.renderers.html_web`
- **When** an engineer imports `from techletter.delivery.renderers.html_web import render`
- **Then** `render(issue: RenderedIssue) -> str` is the public entry point
- **And** the function is pure: calling it twice with the same `RenderedIssue` returns the same string byte-for-byte
- **And** no `datetime.now()` or random source is invoked inside `render`

### AC2: Full HTML document structure
- **Given** `render(issue)` output
- **When** parsed as HTML
- **Then** it begins with `<!DOCTYPE html>` (case-insensitive)
- **And** has exactly one `<html>` root with `lang="ko"` (or configurable; defaults to `ko`)
- **And** `<head>` contains: `<meta charset="utf-8">`, `<meta name="viewport" content="width=device-width, initial-scale=1">`, `<meta name="robots" content="noindex, nofollow">`, `<title>` non-empty
- **And** `<head>` contains exactly one `<style>` block (sourcing all CSS rules)
- **And** `<body>` contains a `.container` element with `max-width` matching `LAYOUT.max_width`

### AC3: Page renders deep dives and quick mentions via shared partials
- **Given** an `issue` with `deep_dives` of length 3 and `quick_mentions` of length 10
- **When** rendered
- **Then** the output contains exactly 3 `<section class="deep-dive">` elements (one per `DeepDive`)
- **And** they appear in the same order as `issue.deep_dives`
- **And** the output contains a `<ul>` (or equivalent list) with exactly 10 `<li>` items
- **And** they appear in the same order as `issue.quick_mentions`

### AC4: Markdown body conversion
- **Given** a `DeepDive.body_md` containing all CommonMark constructs (heading, bold, italic, link, inline code, fenced code, blockquote, ordered/unordered list)
- **When** rendered
- **Then** the page contains the equivalent HTML rendering (via `markdown-it-py`)
- **And** the converter is invoked once per `DeepDive`, never on the assembled-issue body
- **And** the resulting `body_html` is what's passed to the `deep_dive.html.j2` partial as `dd.body_html`

### AC5: HTML-special characters in titles are escaped
- **Given** `DeepDive(title="X < Y & Z")` and `QuickMention(title="A > B")`
- **When** rendered
- **Then** the output contains `X &lt; Y &amp; Z` and `A &gt; B` (escaped)
- **And** no closing `</section>` tag is malformed

### AC6: Deterministic / no env leak
- **Given** the same `issue` rendered twice in succession
- **When** byte-diffed
- **Then** the outputs are identical
- **And** no environment-derived value (cwd, hostname, current time) appears anywhere in the output

### AC7: Golden fixture committed
- **Given** a canonical sample `RenderedIssue` fixture (`tests/fixtures/sample_issue.py` factory)
- **When** `pytest tests/delivery/renderers/test_html_web.py::test_golden` runs
- **Then** `render(sample)` matches `tests/fixtures/golden/web_sample.html` byte-for-byte
- **And** a `--regenerate-golden` pytest flag rewrites the file (for intentional design changes)
- **And** the README or test docstring documents the regeneration recipe

### AC8: `<title>` reflects the issue
- **Given** `issue.issue_id = "issue-2026-05-21"` and `issue.issue_date = datetime(2026, 5, 21, ...)`
- **When** rendered
- **Then** `<title>Tech-Letter — 2026-05-21</title>` is present
- **And** no other `<title>` tags exist

---

## Scope

### In Scope
- `techletter/delivery/renderers/html_web.py` with `render(issue)` and module-level `__all__`.
- `techletter/delivery/templates/web.html.j2`.
- Markdown-to-HTML conversion via `markdown-it-py` (one helper, e.g., `_body_md_to_html`).
- `tests/fixtures/sample_issue.py` factory (or reuse existing).
- `tests/fixtures/golden/web_sample.html` (committed).
- `tests/delivery/renderers/test_html_web.py` (unit + golden).
- `--regenerate-golden` pytest plugin hook (if not already present).

### Out of Scope
- Email rendering — US0026.
- Adapter wiring (`EmailAdapter` still uses old path) — US0027.
- Publishing to GitHub Pages — CR-0002.
- Multi-language `<html lang>` configurability beyond the default of `ko`.
- Image embedding, social-share tags (`og:` meta), favicon.
- A site index page.

---

## Technical Notes

- Use `markdown-it-py` with defaults; explicitly disable HTML pass-through (`html=False`) so users can't inject raw HTML through their issue MD.
- Jinja2 env construction shared between `html_web` and `html_email` — extract into a small helper if convenient (e.g., `renderers/_env.py`), or duplicate two lines per file; lean **duplicate** to avoid premature abstraction.
- `<style>` block content should be a single `<style>` tag, not multiple — premailer in US0026 expects a single block to inline cleanly; keeping the web template structurally similar to the email template makes diffing easier.
- Determinism: never call `datetime.now()` inside `render`; use only fields of `issue`. `issue_date` is passed from `RenderedIssue`, which was set by `assemble_issue`.

### API Contracts
- `render(issue: RenderedIssue) -> str` — public.
- `_body_md_to_html(body_md: str) -> str` — module-private to this story's commit, but **must be importable** by US0026 (single-source markdown→HTML helper). Concretely: place it in either `renderers/html_web.py` and accept the cross-module import in US0026, or factor into `renderers/_common.py` at this story's discretion. The constraint is "one implementation, one parser instance, both renderers route through it." See US0026 AC10.

### Sample web template skeleton (illustrative)

```jinja
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>Tech-Letter — {{ issue.issue_date.strftime('%Y-%m-%d') }}</title>
  <style>
    body { font-family: {{ font.family }}; color: {{ colors.fg }}; background: {{ colors.bg }}; margin: 0; }
    .container { max-width: {{ layout.max_width }}; margin: 0 auto; padding: {{ layout.padding }}; }
    h1 { font-size: {{ font.size_h1 }}; }
    .deep-dive { margin-bottom: 32px; }
    .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
    /* … */
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Tech-Letter</h1>
      <p class="date">{{ issue.issue_date.strftime('%Y년 %m월 %d일') }}</p>
    </header>
    <main>
      {% for dd in issue.deep_dives %}
        {% include "components/deep_dive.html.j2" %}
      {% endfor %}
      <h2>Quick Mentions</h2>
      <ul>
        {% for qm in issue.quick_mentions %}
          {% include "components/quick_mention.html.j2" %}
        {% endfor %}
      </ul>
    </main>
  </div>
</body>
</html>
```

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `issue.deep_dives` is empty (e.g., AC violation from upstream) | Render with the deep-dive loop producing nothing; no crash. Test confirms structure. |
| `body_md` contains `<script>` or other raw HTML | `markdown-it-py` with `html=False` escapes them; output is text |
| `body_md` is empty | `body_html` is empty; partial renders title and meta but empty `.body` div |
| `body_md` has unbalanced backticks (mid-code-block in MD) | `markdown-it-py` recovers; resulting HTML is well-formed |
| Locale-affected datetime formatting | Use explicit format strings; don't rely on `locale` for `%B` etc. |

---

## Test Scenarios

- [ ] `render(sample_issue)` returns a string starting with `<!DOCTYPE html>`.
- [ ] Required `<meta>` tags present.
- [ ] Single `<style>` block; non-empty.
- [ ] `len(<section class="deep-dive">)` matches `len(issue.deep_dives)`.
- [ ] `len(<li>)` within `<ul>` matches `len(issue.quick_mentions)`.
- [ ] All CommonMark constructs in a body fixture render correctly.
- [ ] HTML-special chars in titles → escaped.
- [ ] Two consecutive `render` calls → byte-identical.
- [ ] `render(sample_issue)` matches `golden/web_sample.html` byte-for-byte.
- [ ] `--regenerate-golden` overwrites the golden file when invoked.
- [ ] `<title>` contains the ISO date of `issue.issue_date`.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0024](US0024-design-tokens-and-jinja2-components.md) | Schema | `tokens.py`, component partials | Draft |
| [US0023](US0023-sidecar-json-persistence.md) | Schema | `RenderedIssue.deep_dives` / `.quick_mentions` non-empty at render time | Draft |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `markdown-it-py` | new pip dep | to add in this story |
| `jinja2` | already added (US0024) | available |

---

## Estimation

**Story Points:** 3
**Complexity:** Low–Medium. The renderer is straightforward; the bulk of the work is the golden fixture (one canonical sample, blessed) and the `--regenerate-golden` plumbing if pytest hasn't seen it yet.

---

## Open Questions

- [ ] Should the `lang="ko"` be configurable via a renderer arg or a token? Lean **defer** — not a v1.1 need.
- [ ] Should we add an `og:` meta block for nicer Telegram link previews (CR-0002)? Lean **defer** to CR-0002; Telegram's default card is fine.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | HYL | Story created from CR-0001 (Item 3) via `/sdlc-studio cr action`. |

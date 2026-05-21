# US0024: Design tokens + Jinja2 component partials

> **Status:** Ready
> **Epic:** [EP0005: Common HTML Rendering (Web + Email)](../epics/EP0005-common-html-rendering.md)
> **Change Request:** [CR-0001](../change-requests/CR0001-common-html-rendering.md) (Item 2)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-21
> **Promoted to Ready:** 2026-05-21 (RV0001)

## User Story

**As** the web and email renderers
**I want** a single source of truth for visual tokens (colors, fonts, spacing) and for the per-block component markup (deep dive, quick mention)
**So that** the web page and the email never drift apart visually and a design tweak is one edit, not two.

## Context

### Persona Reference
**Researcher Subscriber** — indirect. They see consistent typography between the inbox newsletter and the linked web archive.
**HYL** — direct. One file to change when the design needs a tweak.

### Background
Per CR-0001 Item 2, both `html_web` and `html_email` must share the same visual identity. Without shared tokens and component partials, each renderer would maintain its own CSS literals → drift, double-edit, regression risk. This story is pure scaffolding: no renderer is wired in yet (that happens in US0025 / US0026). Output is just the tokens module + two Jinja2 partials, both backed by unit tests.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| EP0005 AC | Tokens | `COLORS`, `FONT`, `LAYOUT` dicts exported | Templates import only these |
| EP0005 AC | Components | Both web and email templates `{% include %}` same partials | Component markup must be agnostic to wrapper context |
| EP0004 Email | Email constraints | Inline-CSS via premailer (US0026) | Partials use class names that premailer can target later |
| CR-0001 | Out of scope | No images, no flexbox in email path | Components stay table-friendly |

---

## Acceptance Criteria

### AC1: `tokens.py` exports the three dicts
- **Given** the module `techletter.delivery.renderers.tokens`
- **When** imported
- **Then** it exports module-level dicts:
  - `COLORS: dict[str, str]` with at least: `bg`, `fg`, `muted`, `accent`, `border`, `tag_bg`
  - `FONT: dict[str, str]` with at least: `family`, `mono`, `size_body`, `size_h1`, `size_h2`, `size_h3`
  - `LAYOUT: dict[str, str]` with at least: `max_width`, `padding`
- **And** all values are valid CSS strings (e.g., `#1a1a1a`, `16px`, `680px`)
- **And** `__all__` lists exactly `["COLORS", "FONT", "LAYOUT"]`

### AC2: Components live under a discoverable path
- **Given** the package `techletter.delivery`
- **When** the renderer constructs a Jinja2 `Environment` with `PackageLoader("techletter.delivery", "templates")`
- **Then** the loader finds `components/deep_dive.html.j2` and `components/quick_mention.html.j2`

### AC3: `deep_dive.html.j2` renders required structure
- **Given** a Jinja2 render of `components/deep_dive.html.j2` with context `{"dd": <DeepDive>, "colors": COLORS, "font": FONT, "layout": LAYOUT}`
- **When** rendered with a `DeepDive(item_kind="paper", title="X", body_md="...", primary_url="https://e.com", source_count=1)`
- **Then** the output contains an `<h2>` with the title (exact text, HTML-escaped if needed)
- **And** the output contains an `<a href="https://e.com">` link tag
- **And** the output contains the item-kind label rendered as text (e.g., `paper`)
- **And** the output contains a `class="tag"` element with the item kind
- **And** the body section is HTML-converted from `body_md` (via a `dd.body_html` context var, computed upstream in US0025/26)

### AC4: `quick_mention.html.j2` renders required structure
- **Given** a render with `{"qm": <QuickMention>}`
- **When** rendered with `QuickMention(title="Y", url="https://e.com/y", source="arxiv", item_kind="paper", one_liner="Z")`
- **Then** the output is wrapped in `<li>`
- **And** contains `<a href="https://e.com/y">Y</a>`
- **And** contains the one-liner text " — Z" (em dash separator)
- **And** contains the item-kind tag

### AC5: HTML-special characters are escaped
- **Given** a `DeepDive(title="A < B & C")`
- **When** the partial is rendered
- **Then** the output contains `A &lt; B &amp; C` (escaped) — NOT `A < B & C` (raw)
- **And** by Jinja2 default `autoescape=True` is enabled when the env is constructed (verified in the test fixture's env builder)

### AC6: Tokens are referenced, not duplicated
- **Given** the two partial files
- **When** read as text
- **Then** no hex color literal (`#[0-9a-fA-F]{3,8}`) appears in the file
- **And** no hardcoded `px`/`em` size literal appears (sizes come from `font.size_h2`, `layout.padding`, etc.)
- **And** all CSS values come from Jinja vars resolving to `COLORS`/`FONT`/`LAYOUT`

### AC7: Same partial in two wrapper contexts produces same visible content
- **Given** the partial included under a `<div>` wrapper and under a `<table><tr><td>` wrapper
- **When** both rendered with the same `DeepDive`
- **Then** the inner HTML structure produced by the partial is **byte-identical** in both contexts (only the wrappers differ)
- **And** the unit test fixture demonstrates both inclusions

---

## Scope

### In Scope
- `techletter/delivery/renderers/__init__.py` (empty package init)
- `techletter/delivery/renderers/tokens.py`
- `techletter/delivery/templates/__init__.py` (so PackageLoader can find it)
- `techletter/delivery/templates/components/deep_dive.html.j2`
- `techletter/delivery/templates/components/quick_mention.html.j2`
- `tests/delivery/renderers/test_tokens.py`
- `tests/delivery/renderers/test_components.py`
- `pyproject.toml` add `jinja2` to deps; `uv lock`.

### Out of Scope
- The actual `html_web.py` and `html_email.py` renderers (US0025, US0026).
- Markdown-to-HTML conversion of `body_md` (the partial assumes a precomputed `dd.body_html` is passed in; the converter lands in US0025).
- Premailer integration (US0026).
- Email-specific table wrappers (US0026 owns the email shell).

---

## Technical Notes

- Token philosophy: **everything that could plausibly change for a redesign goes here.** Anything truly invariant (e.g., the `<h2>` tag itself) stays in the partial.
- Jinja2 `Environment` for tests:

  ```python
  env = Environment(
      loader=PackageLoader("techletter.delivery", "templates"),
      autoescape=select_autoescape(["html", "j2", "html.j2"]),
      undefined=StrictUndefined,
  )
  ```
  `StrictUndefined` is important — a typo in a token name should fail loudly in tests, not silently render an empty string.

- The body conversion is left for US0025 to provide as a precomputed `dd.body_html` string; the partial uses `{{ dd.body_html|safe }}` (safe because the conversion is trusted, controlled by us).

### Sample partial sketch (illustrative, not normative)

`components/deep_dive.html.j2`:

```jinja
<section class="deep-dive" style="margin-bottom: {{ layout.padding }};">
  <h2 style="font-size: {{ font.size_h2 }}; color: {{ colors.fg }};">{{ dd.title }}</h2>
  <p class="meta" style="color: {{ colors.muted }};">
    <span class="tag" style="background: {{ colors.tag_bg }};">{{ dd.item_kind }}</span>
    {% if dd.maturity %}<span class="tag" style="background: {{ colors.tag_bg }};">{{ dd.maturity }}</span>{% endif %}
    · <a href="{{ dd.primary_url }}" style="color: {{ colors.accent }};">원문</a>
    · {{ dd.source_count }} sources
  </p>
  <div class="body">{{ dd.body_html|safe }}</div>
</section>
```

`components/quick_mention.html.j2`:

```jinja
<li style="margin-bottom: 6px;">
  <span class="tag" style="background: {{ colors.tag_bg }};">{{ qm.item_kind }}</span>
  <a href="{{ qm.url }}" style="color: {{ colors.accent }};">{{ qm.title }}</a>
  <span style="color: {{ colors.muted }};"> — {{ qm.one_liner }}</span>
</li>
```

(`style=""` is added inline already so that the email path doesn't depend on premailer for the *partial* — premailer in US0026 will pick up `<style>` rules from the email wrapper, and the inline styles win for client compatibility. AC6 says no *literal* CSS values; inline `style=""` is allowed only when the values come from token vars.)

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Token key missing at render | `StrictUndefined` raises immediately in tests; production code would never hit this since the env is shared with the renderer |
| `DeepDive.body_html` not provided | Caller bug; raise `UndefinedError`. The partial does not synthesize HTML from `body_md`. |
| `DeepDive` title contains HTML | Auto-escaped per Jinja env config (AC5) |
| `DeepDive.maturity` is None | The `{% if %}` skips the maturity tag cleanly |
| `QuickMention.one_liner` is very long | Renders as-is; CSS handles truncation if any |

---

## Test Scenarios

- [ ] `tokens.py` exports all three dicts and required keys; values match expected types.
- [ ] `Environment(...)` finds both component partials.
- [ ] Render `deep_dive.html.j2` with a fixture `DeepDive` → asserts on title, link, item-kind tag, body presence.
- [ ] Render `quick_mention.html.j2` with a fixture `QuickMention` → asserts on `<li>`, `<a>`, one-liner text, tag.
- [ ] Inject `< > &` in title; assert escaped output.
- [ ] Grep partial files: no `#[0-9a-fA-F]` hex color literals, no `\d+px` size literals.
- [ ] Same partial inside two different wrapper templates → identical inner HTML (modulo whitespace).
- [ ] `StrictUndefined`: pass a context missing `colors` → raises.

---

## Dependencies

### Story Dependencies

None upstream within EP0005. US0025 and US0026 depend on this story.

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `jinja2` | new pip dep | to add in this story |

---

## Estimation

**Story Points:** 2
**Complexity:** Low. Pure templating + unit tests. The only judgment call is which CSS properties live on the partial inline (style="") vs in the wrapper's `<style>` block — defer the heavy CSS to wrappers (US0025/US0026), keep token-driven essentials on the partial.

---

## Open Questions

_Resolved during RV0001 (2026-05-21): "lock token set now" — committed. AC1's explicit key list is binding; new keys land as follow-up edits, not blockers for US0025/26._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | HYL | Story created from CR-0001 (Item 2) via `/sdlc-studio cr action`. |

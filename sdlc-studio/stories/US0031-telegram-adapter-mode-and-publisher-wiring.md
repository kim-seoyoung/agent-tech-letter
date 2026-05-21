# US0031: Telegram adapter `mode` + publisher wiring

> **Status:** Done
> **Epic:** [EP0006: GitHub Pages Publisher + Telegram Link Mode](../epics/EP0006-github-pages-and-telegram-link-mode.md)
> **Change Request:** [CR-0002](../change-requests/CR0002-github-pages-and-telegram-link-mode.md) (Item 4)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-21

## User Story

**As** the Researcher Subscriber
**I want** the Telegram bot to send me one short message with a link to the full read
**So that** I never see the awkward `[Part 2/3]` split messages again, and I can decide in 5 seconds whether to tap through.

## Context

### Persona Reference
**Researcher Subscriber** — primary. The user-visible flip lands here: chat goes from N split messages to 1 teaser + 1 link preview.
**HYL** — secondary. Wants the legacy `inline_html` path preserved as a safety net while the new mode is observed in the wild.

### Background
US0028/29 produce a `Publisher` and a `GitHubPagesPublisher`. US0030 produces the teaser renderer. This story wires them into `TelegramAdapter` with a `mode` parameter. Default is `teaser_link`; `inline_html` remains for regression safety. Channels.yaml gains a `publishers:` block and a per-channel `mode` / `publisher:` reference, both pydantic-validated.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| EP0004 | ChannelAdapter | `send(issue, recipients) -> SendReport` unchanged | External contract preserved |
| EP0004 TC0247 | Security | Bot token never in logs | Extended to publisher errors and teaser exceptions |
| EP0006 | Default mode | New installs get `teaser_link` automatically; can opt out to `inline_html` | `channels.yaml` defaults; CLI doesn't require migration |
| US0028 | Protocol | Adapter calls `publisher.publish(issue)` only — knows nothing about backend | No `isinstance` check for GitHub Pages; works for any future publisher |
| US0030 | Teaser | `telegram_teaser.render(issue, url=url)` produces the message body | Adapter passes the URL through |

---

## Acceptance Criteria

### AC1: `mode` parameter accepted
- **Given** `TelegramAdapter.__init__`
- **When** called as `TelegramAdapter(bot_token=..., mode="teaser_link", publisher=<GitHubPagesPublisher>)`
- **Then** the instance accepts both new keyword args
- **And** `mode` is a `Literal["teaser_link", "inline_html"]`
- **And** the default value is `"teaser_link"`
- **And** `publisher` defaults to `None` (only required if `mode == "teaser_link"`)

### AC2: Mode mismatch with config raises at construction
- **Given** `mode="teaser_link"` and `publisher=None`
- **When** `TelegramAdapter(...)` is constructed
- **Then** a clear `ValueError` is raised: "TelegramAdapter mode=teaser_link requires a publisher"
- **And** the error happens at construction, not at first `send()`

### AC3: `teaser_link` mode — publisher called exactly once per send
- **Given** `mode="teaser_link"` and N recipients
- **When** `send(issue, recipients)` runs
- **Then** `publisher.publish(issue)` is invoked **exactly 1 time**, not N
- **And** the returned `PublishResult.url` is reused across all N recipient sends
- **And** each Telegram API call uses the teaser body (NOT the inlined issue HTML)

### AC4: `teaser_link` failure — publisher raises → SendReport status=failed, no Bot API calls
- **Given** `mode="teaser_link"` and `publisher.publish(issue)` raises `PublisherError`
- **When** `send(issue, recipients)` runs
- **Then** `SendReport.status == "failed"`
- **And** `SendReport.errors` includes the publisher error message (with any token scrubbed)
- **And** **NO Bot API HTTP calls are made** (verified via the spy/mock on the poster)
- **And** `SendReport.recipient_count` equals `len(recipients)`, with `success_count=0`

### AC5: `inline_html` mode — Bot API payloads behaviorally equivalent to EP0004 (per RV0002 F-2)
- **Given** `mode="inline_html"` and **no** publisher, and the same `issue` + `recipients`
- **When** the adapter's outbound Bot API calls are captured (via the same `poster` injection used by EP0004 tests)
- **Then** the sequence of `(chat_id, text, parse_mode, disable_web_page_preview)` tuples is **identical** to what EP0004's `TelegramAdapter.send` produced for the same inputs
- **And** the existing EP0004 tests (`tests/unit/delivery/test_slack_telegram.py`) still pass without modification
- **And** the publisher is never called (verified by a spy that asserts `publish.call_count == 0`)
- **Note:** "bit-for-bit identical" is intentionally not claimed — the refactor that extracts the legacy code into `_send_inline_html` preserves the *outbound contract*, not internal call graphs.

### AC6: `channels.yaml` schema extension parses cleanly
- **Given** the new schema in `config/channels.yaml`:

  ```yaml
  publishers:
    github_pages:
      enabled: true
      repo_path: "."
      branch: "gh-pages"
      base_url: "https://USER.github.io/REPO"
      author_name: "tech-letter-bot"
      author_email: "bot@example.com"

  telegram:
    enabled: true
    mode: "teaser_link"
    publisher: "github_pages"
  ```

- **When** loaded by `load_channels(...)`
- **Then** the model exposes `channels_cfg.publishers["github_pages"]` and `channels_cfg.telegram.mode == "teaser_link"`
- **And** `channels_cfg.telegram.publisher == "github_pages"` (a string reference)

### AC7: Registry resolves `publisher: "github_pages"` to a `GitHubPagesPublisher` instance
- **Given** the `publishers:` block in config
- **When** `build_channel_registry(channels_cfg, subscribers_cfg)` runs
- **Then** the constructed `TelegramAdapter` (if `mode=teaser_link`) has a real `GitHubPagesPublisher` injected
- **And** missing referenced publisher (`publisher: github_pages` but `publishers.github_pages` is missing) raises a clear `ConfigLoadError` at startup

### AC8: Backward compatibility for existing `channels.yaml` without `mode` / `publishers`
- **Given** an old `channels.yaml` that only contains `email`, `slack`, `telegram` with `enabled: true/false` (and no `publishers:` / no `mode:`)
- **When** loaded
- **Then** `telegram.mode` defaults to `inline_html` (preserves today's behavior — **migration-safe**)
- **And** `telegram.publisher` is `None`
- **And** the registry constructs `TelegramAdapter(mode="inline_html", publisher=None)`

### AC9: Token never in logs across the new code paths
- **Given** publisher failure with a token visible in git's stderr OR teaser render raising with a URL containing the token
- **When** the error is logged or surfaced
- **Then** captured log records (across the full retry path) do NOT contain `TELEGRAM_BOT_TOKEN` or any `GITHUB_TOKEN` substring
- **And** the existing TC0247 assertion is extended to cover this story's code paths

---

## Scope

### In Scope
- Edit `techletter/delivery/telegram.py`:
  - Add `mode: Literal["teaser_link", "inline_html"]` and `publisher: Publisher | None` to `__init__`.
  - Branch in `send()` on `mode`.
  - In `teaser_link` mode: call `publisher.publish(issue)` once; pass URL to `telegram_teaser.render(...)`; send as single message via the existing Bot API path.
  - In `inline_html` mode: keep current code path verbatim.
- Edit `techletter/delivery/config.py` (or wherever `ChannelsConfig` lives):
  - Add `TelegramChannelConfig.mode` (default `"inline_html"` for backward compat).
  - Add `TelegramChannelConfig.publisher` (default `None`).
  - Add `PublishersConfig` block with `github_pages` sub-key.
- Edit `techletter/delivery/registry.py`:
  - When constructing the `TelegramAdapter`, resolve the named publisher from `publishers:` and inject.
  - On missing reference, raise `ConfigLoadError`.
- Update existing `config/channels.yaml`:
  - Document the new schema in a comment block.
  - Default behavior unchanged (no mode → inline_html).
- Tests:
  - Unit tests for the adapter mode dispatch.
  - Unit tests for the registry resolution.
  - Config loader tests for the schema.

### Out of Scope
- `SendRecord.published_url` (US0032).
- README setup docs (US0032).
- Any other channel's mode dispatch.
- Migration script for existing `channels.yaml` files — backward compat handles them silently.

---

## Technical Notes

- Adapter dispatch sketch:

  ```python
  def send(self, issue: RenderedIssue, recipients: list[Recipient]) -> SendReport:
      if self.mode == "teaser_link":
          return self._send_teaser_link(issue, recipients)
      return self._send_inline_html(issue, recipients)  # existing code, refactored under this name

  def _send_teaser_link(self, issue, recipients):
      assert self._publisher is not None  # AC2 prevents None at this point
      try:
          result = self._publisher.publish(issue)
      except Exception as e:
          return SendReport(
              channel=self.name,
              status="failed",
              recipient_count=len(recipients),
              success_count=0,
              failure_count=len(recipients),
              errors=[f"publisher error: {self._scrub(e)}"],
          )

      from techletter.delivery.renderers.telegram_teaser import render as render_teaser
      body = render_teaser(issue, url=result.url)
      # Reuse the existing single-message send path; len(body) ≤ 4096 by US0030 contract
      ...
  ```

- The legacy `_send_inline_html` is the existing method body, renamed; no behavior change.
- The `publisher` injection is a constructor-only choice; once an adapter is constructed, its mode is fixed.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `mode="teaser_link"` and `publisher=None` | `ValueError` at construction (AC2) |
| `mode="teaser_link"` and `recipients=[]` | Return `SendReport(status="ok", recipient_count=0, ...)`; publisher is NOT called (no work to do) |
| `mode="inline_html"` and `publisher` provided | Publisher is silently ignored; no behavior change |
| Publisher returns a `PublishResult` with empty URL | Construction guards against this (US0028 AC2); if it somehow slips through, the teaser raises ValueError (US0030 AC), which AC4 captures |
| `channels.yaml` has `mode: "teaser_link"` but no `publisher:` reference | `ConfigLoadError` at startup |
| `channels.yaml` has `publisher: "ghpages"` (typo) but `publishers.ghpages` doesn't exist | `ConfigLoadError("publisher 'ghpages' referenced by telegram but not defined under publishers:")` |

---

## Test Scenarios

- [ ] `TelegramAdapter(mode="teaser_link", publisher=None)` raises ValueError.
- [ ] `TelegramAdapter(mode="inline_html")` constructs without a publisher.
- [ ] Mode dispatch: `teaser_link` calls `publisher.publish` once on N=10 recipients (spy/mock).
- [ ] Publisher exception → `SendReport.status="failed"`, zero Bot API calls (spy on the poster).
- [ ] `inline_html` mode produces same Bot API call sequence as EP0004 baseline (snapshot test).
- [ ] `channels.yaml` with `mode: teaser_link` + `publisher: github_pages` loads cleanly.
- [ ] `channels.yaml` with `mode: teaser_link` but no `publisher:` → ConfigLoadError.
- [ ] `channels.yaml` with `publisher: "unknown"` → ConfigLoadError naming the missing key.
- [ ] Old `channels.yaml` with no `mode`/`publishers` → defaults `mode=inline_html`, `publisher=None` (regression).
- [ ] Token-scrub: publisher error containing `GITHUB_TOKEN` substring is replaced with `[REDACTED]` before reaching SendReport / logs.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0028](US0028-publisher-protocol-and-publish-result.md) | Schema | `Publisher` Protocol + `PublishResult` | Draft |
| [US0029](US0029-github-pages-publisher.md) | Implementation | A real `Publisher` to wire in for integration tests | Draft |
| [US0030](US0030-telegram-teaser-renderer.md) | Renderer | `telegram_teaser.render(issue, url=...)` | Draft |

### External Dependencies

None new.

---

## Estimation

**Story Points:** 3
**Complexity:** Low–Medium. The dispatch and config schema are mechanical; the work is in keeping the legacy `inline_html` path bit-equivalent (snapshot test) while introducing the new mode.

---

## Open Questions

- [ ] Should we add an info-level log on publish success (`telegram: published <url>`) so operators see the URL in `send.yml` output? Lean yes — but be careful not to log it twice (once here, once in US0032's audit record).

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | HYL | Story created from CR-0002 (Item 4) via `/sdlc-studio cr action`. |

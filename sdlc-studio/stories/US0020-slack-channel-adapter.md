# US0020: Slack channel adapter (Incoming Webhook, message splitting)

> **Status:** Done
> **Epic:** [EP0004: Multi-channel Delivery](../epics/EP0004-multichannel-delivery.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** the Researcher Subscriber who reads the newsletter in a Slack channel
**I want** each weekly issue posted as a clean, readable message in Slack
**So that** I can see the issue inline in my workspace and click through to the linked sources without leaving Slack.

## Context

### Persona Reference
**Researcher Subscriber** — beneficiary. The expectation: clean rendering in Slack's `mrkdwn` (not raw CommonMark), no broken code blocks across message splits, links work.
[Persona details](../personas/stakeholders/users/researcher-subscriber.md)

### Background
Slack supports its own markdown dialect called `mrkdwn`. Major differences from CommonMark: `*bold*` instead of `**bold**`, no headings (use `*bold*` for emphasis), `<url|text>` for inline links. Slack's payload limit is generous (~40,000 chars), but messages over ~4,000 chars become unreadable; the adapter splits at paragraph/section boundaries.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Protocol | Implements `ChannelAdapter` from US0018 | Adapter must be protocol-conformant |
| PRD | Transport | Incoming Webhook URL | One webhook per Slack workspace (= one "recipient") |
| Epic | Splitter | Long issues split across multiple messages | Split on paragraph boundaries; never mid–code block |
| Epic | Failure isolation | Per-recipient (per-webhook) failure logged; others proceed | Try/except per webhook |
| Epic | Reliability | tenacity-wrapped retries | Backoff on 429 / 5xx |

---

## Acceptance Criteria

### AC1: Adapter is discoverable and conformant
- **Given** the package `techletter.delivery.slack` exists
- **When** an engineer imports `from techletter.delivery.slack import SlackAdapter`
- **Then** `SlackAdapter(config: SlackConfig)` is the constructor
- **And** `adapter.name == "slack"` and `adapter.send(issue, recipients) -> SendReport` matches the `ChannelAdapter` protocol
- **And** the `recipients` argument is interpreted as a list of webhook URLs

### AC2: CommonMark → Slack `mrkdwn` conversion
- **Given** an issue's markdown body
- **When** the adapter renders for Slack
- **Then** these conversions are applied:
  - Headings (`# ...`, `## ...`, etc.) → `*<heading text>*` followed by blank line (Slack has no native headings)
  - `**bold**` → `*bold*`
  - `_italic_` and `*italic*` (CommonMark) → `_italic_` (Slack)
  - `[text](url)` → `<url|text>`
  - Fenced code blocks (triple-backtick) → triple-backtick blocks (Slack supports them as-is)
  - Inline code (single backtick) → inline code (preserved)
  - Bullets and numbered lists → preserved

### AC3: Message splitting at paragraph boundaries
- **Given** an issue body that, when converted to Slack mrkdwn, exceeds 3,500 chars (a safe headroom under Slack's 4,000-char practical limit per message)
- **When** the adapter prepares to send
- **Then** the body is split into N messages, each ≤ 3,500 chars
- **And** splits occur at paragraph boundaries (`\n\n`) — never mid-paragraph, mid-list-item, or mid-code-block
- **And** messages are posted in order; each subsequent message starts with `(continued, N/N)` prefix for reader orientation

### AC4: One POST per webhook per split chunk
- **Given** N webhooks configured and the issue requires M chunks
- **When** the adapter sends
- **Then** N × M POST requests are made (one per webhook per chunk)
- **And** chunks per webhook are sent sequentially (preserve order in Slack)
- **And** across different webhooks, the adapter is allowed to interleave (one webhook's delay doesn't block others)

### AC5: Webhook 4xx error → that webhook fails, others proceed
- **Given** 3 webhooks configured; the second returns 404 ("invalid webhook")
- **When** the adapter sends
- **Then** webhooks 1 and 3 receive all chunks
- **And** webhook 2's failure is logged as a single failure entry in `SendReport.failures` (one entry per webhook, not per chunk)
- **And** `SendReport.status = "partial"` (success=2, failure=1)

### AC6: 429 rate limit triggers backoff
- **Given** Slack returns 429 with a `Retry-After` header
- **When** the adapter encounters this
- **Then** tenacity respects the `Retry-After` (or falls back to exponential backoff if header missing)
- **And** the request is retried up to 5 times
- **And** if still rate-limited after retries, that webhook is marked failed for this issue

### AC7: Empty recipient list → no-op
- **Given** no Slack webhooks configured
- **When** `send` is called with `recipients=[]`
- **Then** no HTTP requests are made; `SendReport(recipients_count=0, status="ok")` is returned

### AC8: Code-block integrity preserved through splits
- **Given** an issue body containing a code block that is followed by enough other content to require a split *after* the code block
- **When** the body is split
- **Then** the code block remains intact within one chunk (the splitter does not cut inside the triple-backtick fences)
- **And** if a single code block is itself > 3,500 chars, the adapter logs WARN and sends the oversized message anyway (Slack will truncate; HYL/PR review catches this rare case)

---

## Scope

### In Scope
- `techletter/delivery/slack.py` defining `SlackAdapter`.
- `commonmark_to_mrkdwn(markdown_text: str) -> str` helper (unit-testable function).
- `split_for_slack(text: str, limit_chars: int = 3500) -> list[str]` splitter helper.
- HTTP POST via `httpx` to webhook URL.
- tenacity decorators for retries.
- Unit tests for conversion, splitting, and the adapter's `send` against a fake HTTP server.

### Out of Scope
- Slack Blocks API (rich formatting blocks) — v1 uses plain `mrkdwn` text payloads (`{"text": "..."}`).
- Slack thread replies / reactions / @mentions.
- Per-channel customisation beyond the webhook URL.
- File uploads (e.g., issue as a snippet).
- A Slack bot with slash commands.

---

## Technical Notes

- The Slack webhook payload is JSON: `{"text": "<message>"}`. No auth header — the webhook URL itself is the secret.
- `commonmark_to_mrkdwn` is a small regex-based transformer. It's fine if it's not 100% spec-correct; issue bodies are HYL-edited at PR time before merge, so edge cases are caught.
- The splitter uses a paragraph tokenizer: split on `\n\n`, accumulate until adding the next paragraph would exceed the limit, then start a new chunk. Edge cases: code blocks span paragraph boundaries; the splitter tracks "inside code block" state.
- Sequential posts per webhook: necessary for order preservation. A short delay (~100ms) between chunk posts avoids Slack's rate limits.

### API Contracts
- `SlackAdapter(config: SlackConfig)` — constructor.
- `send(issue, recipients) -> SendReport`.
- `commonmark_to_mrkdwn(text) -> str` — pure helper.
- `split_for_slack(text, limit_chars) -> list[str]` — pure helper.

### Data Requirements
- Webhook URLs in `SubscribersConfig.slack`.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Empty recipient list | No-op, `status="ok"` |
| Webhook URL malformed | Caught at config validation (US0018); never reaches the adapter |
| Webhook revoked (404) | That webhook failed; others proceed |
| Webhook returns 200 with `"error"` body | Treat as success (Slack returns 200 for accepted; "error" bodies are rare and inconsistent — log WARN but accept) |
| Network timeout | tenacity retries; final failure marks that webhook failed |
| Issue body has a 4,000-char code block | Splitter emits the oversized chunk with a WARN log; Slack may truncate display but doesn't error |
| Issue body has Unicode characters (emoji, CJK, etc.) | Slack handles UTF-8 natively; pass-through |
| `commonmark_to_mrkdwn` encounters a markdown construct it doesn't know (e.g., a table) | Pass it through unchanged with a WARN log; Slack will render it as plain text |
| Issue body has a markdown image `![alt](url)` | Convert to a link `<url|alt>` (Slack doesn't render markdown images in webhook payloads) |
| Slack rate-limits with no `Retry-After` header | tenacity exponential backoff (1s, 2s, 4s, 8s, 16s) |
| Same webhook URL appears twice in config (duplicate) | Adapter sends to each independently (dedupe at registry, US0022) |
| Webhook returns 200 OK for some chunks but 4xx for a later chunk | Subsequent chunks for that webhook stop; failure recorded; other webhooks unaffected |
| The whole issue is ≤ 3,500 chars (no split needed) | Single message; no `(continued, 1/1)` prefix |
| The whole issue is empty (extreme edge) | Single message with `(empty issue)` placeholder; log WARN |

---

## Test Scenarios

- [ ] `SlackAdapter()` assignable to `ChannelAdapter` per pyright.
- [ ] `commonmark_to_mrkdwn("**bold**")` → `"*bold*"`.
- [ ] `commonmark_to_mrkdwn("[link](url)")` → `"<url|link>"`.
- [ ] `commonmark_to_mrkdwn("# Heading\n\nbody")` → `"*Heading*\n\nbody"` (or similar).
- [ ] `split_for_slack` with text < limit → returns single chunk.
- [ ] `split_for_slack` with text spanning 5,000 chars → returns 2 chunks; each ≤ 3,500.
- [ ] `split_for_slack` with code block spanning a paragraph boundary → keeps code block intact.
- [ ] Send to 2 webhooks, fake HTTP returns 200 for both → `success=2, status="ok"`.
- [ ] Send to 2 webhooks, one returns 404 → `success=1, failure=1, status="partial"`.
- [ ] tenacity: webhook returns 429 with `Retry-After: 2` × 2 then 200 → success.
- [ ] tenacity: webhook returns 429 × 5 → failed.
- [ ] Empty recipients → no HTTP calls, `status="ok"`.
- [ ] One chunk-and-only POST per webhook for short issues; multiple POSTs per webhook for long issues; verify count.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0018](US0018-channel-adapter-protocol-and-config-loaders.md) | Schema | `ChannelAdapter`, `SendReport`, `SlackConfig` | Draft |
| [US0011](US0011-compose-blog-quick-mentions-and-issue-assembly.md) | Schema | `RenderedIssue` (for the markdown body) | Draft |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `httpx` library | Library | Already added |
| `tenacity` library | Library | Already added |
| Slack webhook URL(s) GitHub Secret (`SLACK_WEBHOOK_URLS`) | Secret | Optional — only needed if Slack channel is enabled |

---

## Estimation

**Story Points:** 3
**Complexity:** Low-Medium. The transformer and splitter are the interesting parts; both are pure functions with comprehensive unit tests. Network layer is small.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0004. |

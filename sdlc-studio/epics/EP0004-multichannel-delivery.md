# EP0004: Multi-channel Delivery

> **Status:** Done
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19
> **Target Release:** v1.0 (first issue shipped)

## Summary

Deliver a `RenderedIssue` to subscribers via three channels (Email, Slack, Telegram), all behind a common `ChannelAdapter` protocol. Subscribers live in `config/subscribers.yaml` grouped by channel; adding a recipient is a single config edit. Each channel handles its own protocol-specific concerns (SMTP multipart, Slack payload size split, Telegram 4096-char split). Per-recipient failures isolate — one bad address doesn't abort the run.

## Inherited Constraints

| Source | Type | Constraint | Impact |
|--------|------|------------|--------|
| PRD | Channels | Email (SMTP), Slack (webhook), Telegram (Bot API) | Three concrete adapters required |
| PRD | Subscribers | Static `config/subscribers.yaml`, per-channel; no signup/unsubscribe API in v1 | Adapter loads from yaml; no auth flow |
| PRD | Scale | 10–100 subscribers | SMTP via Gmail (500/day limit) is comfortable; no batch send required |
| PRD | Email rendering | Jinja2 template at `templates/email.html.j2`; HTML + plain-text multipart | No MJML in v1 |
| PRD | Failure isolation | Per-recipient send failure is logged; does not abort the run | Each channel iterates recipients with per-iteration error handling |
| TRD | Architecture | Adapter pattern (ADR-002); `ChannelAdapter` protocol | Each channel is one module; pipeline iterates a registry |
| TRD | Reliability | tenacity-wrapped network calls (ADR-004) | Webhook + SMTP + Telegram all retryable |
| TRD | Security | Secrets only in GitHub Secrets (ADR-003 implied; PRD §5) | SMTP creds, Slack webhook URLs, Telegram bot token via Actions Secrets |

---

## Business Context

### Problem Statement
A `RenderedIssue` that doesn't reach anyone has no value. Subscribers want delivery in whichever venue they actually read — for some, email; for others, Slack or Telegram. The system must support all three out of the box for v1.

**PRD Reference:** [§3 Feature Inventory — F-05, F-06, F-07, F-08](../prd.md#3-feature-inventory)

### Value Proposition
This epic is the "the newsletter actually arrives" half of the system. The composition pipeline (EP0002) determines whether subscribers stay; this epic determines whether they ever see anything in the first place.

### Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Subscribers reachable on supported channels | n/a | 100% (each on at least one channel) | Successful delivery in `logs/sends.jsonl` |
| Per-recipient failure rate | n/a | < 1% (after retry) | `SendRecord.failure_count / recipients_count` |
| Slack / Telegram payload-limit errors | n/a | 0 (split logic handles it) | `logs/sends.jsonl` status |

---

## Scope

### In Scope
- `ChannelAdapter` protocol (`name`, `send(issue, recipients) -> SendReport`).
- `subscribers.yaml` schema with `email`, `slack`, `telegram` keys; pydantic-validated loader.
- Email adapter: SMTP, HTML + plain-text multipart via `email.mime` and Jinja2 template; per-recipient try/except + log.
- Slack adapter: posts via Incoming Webhook URL; splits long issues into multiple messages (Slack payload limit handling).
- Telegram adapter: posts via Bot API `sendMessage` with `parse_mode=HTML` or `MarkdownV2`; splits messages to respect 4096-char limit.
- Per-channel enable flags (`config/channels.yaml`) so a channel can be turned off temporarily without code changes.
- Returns aggregated `SendReport` (success/partial/failed) consumed by `send.yml` (EP0003).

### Out of Scope
- Subscriber signup / unsubscribe flow (PRD-decided drop for v1).
- Newsletter platforms (Buttondown, Resend) — alternative covered as a future CR if scale grows.
- A 4th channel (Discord, RSS-out, etc.) — adapter pattern supports it; not in v1.
- Idempotency check itself — owned by EP0003; this epic returns honest `SendReport`s and lets the orchestration layer decide.

### Affected Personas
- **Researcher Subscriber:** primary — they read the newsletter in whichever channel they prefer. Quality of delivery (correctly rendered, no broken markdown, no message split mid-sentence) is what they notice.
- **HYL:** secondary — needs delivery to "just work" so they don't have to babysit sends.

---

## Acceptance Criteria (Epic Level)

- [ ] `ChannelAdapter` protocol defined; all three adapters implement it.
- [ ] `config/subscribers.yaml` schema documented and validated at load (pydantic). Missing/empty channel keys are valid (channel just gets zero recipients).
- [ ] Email adapter sends HTML + plain-text multipart via SMTP using credentials from `SMTP_HOST` / `SMTP_USER` / `SMTP_PASS` / `SMTP_FROM`. Plain-text falls back to a markdown-stripped version of the issue.
- [ ] Slack adapter posts to each configured webhook URL; messages exceeding payload size are split into a sequence of messages with chronological order preserved.
- [ ] Telegram adapter posts to each configured chat ID; messages are split to respect the 4096-char limit; uses HTML parse mode.
- [ ] Per-recipient failure is caught and logged; other recipients still get the issue. `SendReport` aggregates: `success_count`, `failure_count`, `status` ∈ {`ok`, `partial`, `failed`}.
- [ ] tenacity-wrapped network calls on all three adapters with exponential backoff (max 5 attempts).
- [ ] `config/channels.yaml` enable flags work: disabling a channel skips that adapter entirely (no error).

---

## Dependencies

### Blocked By

| Dependency | Type | Status | Owner |
|------------|------|--------|-------|
| EP0001 Content Ingestion | Epic | Draft | HYL |
| EP0002 Composition Pipeline | Epic | Draft | HYL |

(`RenderedIssue` model needs to exist before delivery can consume it.)

### Blocking

| Item | Type | Impact |
|------|------|--------|
| EP0003 Orchestration | Epic | `send.yml` workflow calls into channel adapters |

---

## Risks & Assumptions

### Assumptions
- Gmail (or AWS SES) is acceptable as the SMTP provider for v1 at ≤100 subscribers/week. Daily Gmail send limits are well above one weekly issue × ≤100 recipients.
- Slack Incoming Webhook URLs are stable and rotateable through admin UI.
- Telegram Bot API rate limit (30 msg/sec) is non-binding at our scale.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SMTP marked as spam (no SPF/DKIM/DMARC on the From-domain) | M | M | Document SPF/DKIM/DMARC setup in README; include unsubscribe instructions in email footer (manual reply-and-ask, since no signup flow). Switch to Resend/SES if Gmail won't deliver reliably. |
| Slack webhook URL rotated/revoked → adapter silently fails | L | M | Webhook 4xx surfaces as `SendRecord` failure; HYL sees it in next-day audit |
| Long issues exceed Slack/Telegram limits mid-codeblock → ugly split | M | L | Split on paragraph boundaries; never split inside fenced code blocks; unit-test the splitter |
| Telegram MarkdownV2 escaping bugs (special chars need escaping) | M | L | Prefer HTML parse mode (simpler escape rules); unit-test escape function |
| Subscribers.yaml typo silently drops recipients | L | M | pydantic validation at load; missing-required-field is a load-time error, not a silent miss |

---

## Technical Considerations

### Architecture Impact
This epic implements the **delivery-side adapter pattern** symmetric to EP0001's source-side adapter pattern. Adding a future channel (Discord, RSS-out, a hosted newsletter platform) is a new module under `techletter/delivery/`.

### Integration Points
- **SMTP** via `smtplib` (stdlib) over TLS.
- **Slack** via HTTPS POST to webhook URL (no SDK needed).
- **Telegram Bot API** via HTTPS POST (no SDK strictly needed; `python-telegram-bot` available if helpful).
- **Jinja2** for email HTML template rendering (template path from TRD §6).
- **`config/subscribers.yaml`** and **`config/channels.yaml`** loaders.

---

## Sizing

**Story Points:** ~13
**Estimated Story Count:** 5

**Complexity Factors:**
- Three adapters but each has different protocol-specific gotchas (SMTP multipart, Slack split, Telegram escape).
- Email HTML template iteration likely needs back-and-forth checking across Gmail/Apple Mail/Outlook rendering.
- Splitter logic (Slack and Telegram) needs to be careful around code blocks and link integrity.

---

## Story Breakdown

Stories generated 2026-05-19. See [Story Index](../stories/_index.md) for full details.

- [x] [US0018](../stories/US0018-channel-adapter-protocol-and-config-loaders.md) — `ChannelAdapter` protocol + config loaders (3 pts)
- [x] [US0019](../stories/US0019-email-channel-adapter.md) — Email adapter (SMTP multipart, Jinja2) (5 pts)
- [x] [US0020](../stories/US0020-slack-channel-adapter.md) — Slack adapter (webhook + splitter) (3 pts)
- [x] [US0021](../stories/US0021-telegram-channel-adapter.md) — Telegram adapter (Bot API + splitter) (3 pts)
- [x] [US0022](../stories/US0022-channel-registry-and-send-aggregation.md) — Channel registry + `SendReport` aggregation (3 pts)

**Total:** 17 story points across 5 stories.

---

## Test Plan

**Test Spec:** [TS0004](../test-specs/TS0004-multichannel-delivery.md) — 63 test cases (TC0198–TC0260), 38/38 ACs covered.

- Unit: example-based + parametric for the splitters (`split_for_slack`, `split_for_telegram`) and the escapers (`commonmark_to_mrkdwn`, `commonmark_to_telegram_html`) and the markdown→plain-text stripper — all pure functions held to ≥95% line + branch.
- **Unit (property-based, TSD-mandated):** four `hypothesis` properties — `split_for_slack` invariants (TC0229), `commonmark_to_mrkdwn` invariants (TC0230), `split_for_telegram` invariants (TC0243), `commonmark_to_telegram_html` escape ordering (TC0244). 200 examples per property on PRs; nightly slow profile to 2000.
- Integration: `aiosmtpd` in-process SMTP server for email adapter (multipart structure, per-recipient 550 isolation, single connection per batch); `pytest-httpx` for Slack webhooks and Telegram Bot API (429 Retry-After, 4xx/403 per-channel isolation, payload-shape assertions).
- Security: dedicated test (TC0247) verifies the bot token never appears in any captured log record across the full retry path — pairs with the TSD secret-leak grep at CI level.
- Manual smoke: first real send to HYL's own addresses on each channel — owned by `draft.yml`'s smoke-send step (US0015), not by this spec.

---

## Open Questions

_None._ All design decisions inherited from PRD v0.4.0 and TRD v0.3.0.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial epic created from PRD v0.4.0 F-05, F-06, F-07, F-08. |
| 2026-05-19 | HYL | Story breakdown linked: 5 stories (US0018–US0022, 17 pts total). |
| 2026-05-19 | HYL | Test plan linked to [TS0004](../test-specs/TS0004-multichannel-delivery.md) — 63 TCs, 38/38 ACs covered, 4 hypothesis property tests per TSD. |

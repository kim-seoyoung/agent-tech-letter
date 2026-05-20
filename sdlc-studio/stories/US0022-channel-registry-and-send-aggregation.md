# US0022: Channel registry + enable flags + `SendReport` aggregation

> **Status:** Draft
> **Epic:** [EP0004: Multi-channel Delivery](../epics/EP0004-multichannel-delivery.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a `ChannelRegistry` that loads `channels.yaml`, constructs enabled channel adapters, dispatches a `RenderedIssue` to each, and aggregates `SendReport`s
**So that** the `techletter send` CLI sub-command has a single entry point — `registry.send_all(issue)` — and turning a channel off is a one-line config edit.

## Context

### Persona Reference
**HYL (Author/Editor)** — symmetric to their EP0001 expectation: "adding a channel / turning one off should be config, not code." This story is the user-facing surface of the delivery-side adapter pattern.
[Persona details](../personas/stakeholders/users/hyl-author.md)

### Background
The capstone of EP0004. Mirrors US0005 (the source registry). After this story, `techletter send` can call `registry.send_all(issue)` and get back a list of per-channel `SendReport`s for `logs/sends.jsonl`.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Reliability | Per-channel failure does not block other channels | Registry catches per-adapter exceptions |
| PRD | Config-first | Channel enable flag in `channels.yaml` | Registry reads it; disabled channels are skipped |
| Epic | Failure isolation | `SendReport.status` aggregated honestly | Each channel reports independently; not rolled up to a single "global" status |
| TRD | Architecture | Adapter pattern (ADR-002) | Registry uses explicit name→class mapping |
| Epic | Idempotency boundary | Idempotency itself lives in EP0003 | Registry returns honest `SendReport`s; CLI in EP0003 calls `already_sent` before invoking the registry |

---

## Acceptance Criteria

### AC1: `ChannelRegistry` is defined
- **Given** the module `techletter.delivery.registry` exists
- **When** an engineer imports `from techletter.delivery.registry import ChannelRegistry, build_registry`
- **Then** `build_registry(subscribers: SubscribersConfig, channels: ChannelsConfig) -> ChannelRegistry` is the public constructor
- **And** the returned registry has `registry.adapters: dict[str, ChannelAdapter]` keyed by channel name
- **And** the registry has `registry.send_all(issue: RenderedIssue) -> list[SendReport]`

### AC2: Only enabled channels are constructed
- **Given** `channels.yaml` has `email.enabled: true`, `slack.enabled: false`, `telegram.enabled: true`
- **When** `build_registry(...)` is called
- **Then** `registry.adapters` contains keys `"email"` and `"telegram"` only
- **And** no Slack adapter is instantiated (its secrets are not consulted, no construction-time errors raised)

### AC3: Channel-secret missing → channel skipped, others proceed
- **Given** `email.enabled: true` but `SMTP_HOST` env is unset (so `EmailAdapter` construction raises `SmtpCredsError`)
- **When** `build_registry(...)` is called
- **Then** the email adapter is omitted from `registry.adapters`
- **And** a WARN is logged: `"channel 'email' could not be constructed (SmtpCredsError); skipping"`
- **And** the registry is still returned with the other enabled+constructable channels

### AC4: `send_all` dispatches to each adapter
- **Given** a registry with email and telegram adapters
- **When** `registry.send_all(issue)` is called
- **Then** `email_adapter.send(issue, email_recipients)` is called
- **And** `telegram_adapter.send(issue, telegram_recipients)` is called
- **And** the result is `[SendReport(channel="email", ...), SendReport(channel="telegram", ...)]` — one per adapter

### AC5: Recipients are deduplicated per channel
- **Given** `subscribers.yaml` has `email: [a@x.com, b@x.com, a@x.com]` (duplicate)
- **When** the registry dispatches to email
- **Then** the email adapter receives `["a@x.com", "b@x.com"]` (order-preserving deduplication)
- **And** `SendReport.recipients_count == 2`

### AC6: Per-channel adapter exception → that channel "failed", others proceed
- **Given** the email adapter raises `RuntimeError("connection refused")` from `send()` (not just per-recipient failures, but a global adapter exception)
- **When** `registry.send_all(issue)` is called
- **Then** the registry catches the exception and returns a `SendReport(channel="email", recipients_count=N, success_count=0, failure_count=N, status="failed", failures=[{recipient: "<all>", error: "RuntimeError: connection refused"}])`
- **And** other channels' sends proceed normally
- **And** `send_all` itself does not raise

### AC7: Empty enabled-channels list → returns empty list
- **Given** all channels are `enabled: false`
- **When** `build_registry(...)` is called and `send_all(issue)` invoked
- **Then** `registry.adapters` is empty
- **And** `send_all` returns `[]`
- **And** a single INFO log records "no channels enabled; nothing to send"

### AC8: Channel iteration is order-stable
- **Given** the registry has multiple adapters
- **When** `send_all` is called repeatedly with the same inputs
- **Then** the returned list order is stable (e.g., always email → slack → telegram)
- **And** the order matches the explicit declaration order in the channel name → class map

---

## Scope

### In Scope
- `techletter/delivery/registry.py` defining `ChannelRegistry` and `build_registry`.
- The explicit name→class map: `{"email": EmailAdapter, "slack": SlackAdapter, "telegram": TelegramAdapter}`.
- Per-recipient deduplication (order-preserving) inside `send_all` before invoking adapters.
- Per-channel exception catching in `send_all` with WARN logging.
- Unit tests using `FakeChannel` instances and explicit registry construction.

### Out of Scope
- The actual idempotency check (`already_sent`) — that lives in EP0003 / US0013 and the CLI calls it before invoking the registry.
- Parallel send across channels — sequential is fine for v1 (3 channels × <2 min each = <6 min total, well under the 5-min draft target and 2-min send target).
- A dynamic channel discovery mechanism — the name→class map is explicit and immutable.
- Per-recipient idempotency (skip-already-sent individual addresses) — out of scope.

---

## Technical Notes

- `build_registry` is a factory; the registry itself is data + thin behaviour. Keep this small (~50 lines).
- Recipient deduplication uses `dict.fromkeys(recipients)` to preserve order.
- The name→class map is in a module-level constant for grep-ability:
  ```python
  ADAPTER_CLASSES: dict[str, type[ChannelAdapter]] = {
      "email": EmailAdapter,
      "slack": SlackAdapter,
      "telegram": TelegramAdapter,
  }
  ```
- The "channel exception → synthesised failed `SendReport`" behaviour is defensive — adapters are *supposed* to return `SendReport(status="failed", ...)` themselves on global failure (e.g., SMTP can't connect to anyone), but the registry is the safety net if an adapter throws.

### API Contracts
- `build_registry(subscribers: SubscribersConfig, channels: ChannelsConfig) -> ChannelRegistry`
- `ChannelRegistry.adapters: dict[str, ChannelAdapter]`
- `ChannelRegistry.send_all(issue: RenderedIssue) -> list[SendReport]`

### Data Requirements
None persistent (results flow to `logs/sends.jsonl` via the CLI in EP0003).

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Both configs valid, all channels enabled and constructable | Full registry; `send_all` dispatches to all three |
| One channel enabled but its construction raises (missing creds) | Registry omits that channel; WARN logged; others present |
| All channels disabled | Empty registry; `send_all` returns `[]` |
| Adapter `send` returns a `SendReport` (success or partial or failed) | Registry passes it through unchanged |
| Adapter `send` raises | Registry synthesises a `SendReport(status="failed", failure_count=N, failures=[{recipient: "<all>", error: ...}])` |
| Recipient list for a channel is empty | Adapter still invoked; returns `SendReport(recipients_count=0, status="ok")`; registry returns it as-is |
| Recipient list contains duplicates | Deduplicated before passing to adapter |
| Subscribers config has a `slack` list but `channels.yaml` has `slack.enabled: false` | Slack adapter never constructed; the recipients in subscribers are simply unused (no error) |
| Channels config has `email.enabled: true` but subscribers config has no `email` key (no recipients) | Adapter is constructed; `send` is called with `[]`; `SendReport(recipients_count=0, status="ok")` |
| Concurrent calls to `send_all` on the same registry | Adapter implementations are stateless within a call; registry doesn't share state; safe but not used concurrently in v1 |
| Unknown channel name in name→class map (theoretically impossible — but for safety) | Skipped with WARN |
| One adapter is extremely slow (e.g., 10 minutes) | Sequential dispatch means other channels wait; acceptable for v1 (workflow timeout is 6h) |
| Channels are sent in stable order (e.g., email → slack → telegram) | Yes, per AC8 |

---

## Test Scenarios

- [ ] `build_registry` with all three channels enabled → registry contains all three adapters.
- [ ] `build_registry` with `slack.enabled: false` → registry omits slack.
- [ ] `build_registry` with email construction raising → email omitted, WARN logged.
- [ ] `build_registry` with all channels disabled → empty registry.
- [ ] `send_all` with three fake adapters → returns three `SendReport`s in stable order.
- [ ] `send_all` with one adapter throwing → that channel synthesised as failed; others succeed.
- [ ] `send_all` with empty registry → returns `[]`.
- [ ] Duplicate email addresses in subscribers → deduplicated before adapter call.
- [ ] Registry instance is reusable across multiple `send_all` calls.
- [ ] Type check: `ChannelRegistry` and `build_registry` pass pyright.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0018](US0018-channel-adapter-protocol-and-config-loaders.md) | Schema | `ChannelAdapter`, `SendReport`, configs | Draft |
| [US0019](US0019-email-channel-adapter.md) | Service | `EmailAdapter` (or fakes for testing) | Draft |
| [US0020](US0020-slack-channel-adapter.md) | Service | `SlackAdapter` (or fakes) | Draft |
| [US0021](US0021-telegram-channel-adapter.md) | Service | `TelegramAdapter` (or fakes) | Draft |

(In practice the registry can be unit-tested with fake adapters; the real adapters need to exist before the CLI invokes the registry end-to-end.)

### External Dependencies
None new.

---

## Estimation

**Story Points:** 3
**Complexity:** Low-Medium. Mirrors US0005 (source registry). The interesting parts are per-channel exception isolation and recipient deduplication.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0004. |

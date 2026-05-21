# US0018: `ChannelAdapter` protocol + `subscribers.yaml` / `channels.yaml` schemas

> **Status:** Done
> **Epic:** [EP0004: Multi-channel Delivery](../epics/EP0004-multichannel-delivery.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a uniform `ChannelAdapter` protocol and two typed config files — `subscribers.yaml` (recipients per channel) and `channels.yaml` (per-channel enable flags + channel-specific config)
**So that** every delivery channel — present and future — implements one interface, and turning a channel on/off or editing recipients is a one-line config edit.

## Context

### Persona Reference
**HYL (Author/Editor)** — same "adding/changing should be config, not code" expectation that drove EP0001's source registry.
[Persona details](../personas/stakeholders/users/hyl-author.md)

### Background
This story is the foundational story for EP0004, symmetric to US0001 (which defined `SourceAdapter` + `Item`). It defines:
- `ChannelAdapter` protocol
- `SendReport` model (per-channel result)
- `subscribers.yaml` schema (recipients, keyed by channel)
- `channels.yaml` schema (per-channel enable + config)
- Loaders for both files

The three concrete adapters (email/slack/telegram) and the registry depend on this story.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Architecture | Adapter pattern (TRD ADR-002); `ChannelAdapter` protocol | Defined here |
| Epic | Subscribers | Static `config/subscribers.yaml`, per-channel | Schema groups by channel |
| Epic | Failure isolation | Per-recipient failure logged; doesn't abort | `SendReport` carries success / partial / failed status |
| TRD | Tech stack | `pydantic` v2 + `pyyaml` | Schemas use pydantic; loaders use yaml |
| TRD | Models | `SendReport` carries `recipients_count`, `success_count`, `failure_count`, `status` | Matches `SendRecord` audit-log fields from US0013 |

---

## Acceptance Criteria

### AC1: `ChannelAdapter` protocol is defined
- **Given** the package `techletter.delivery.base` exists
- **When** an engineer imports `from techletter.delivery.base import ChannelAdapter, SendReport`
- **Then** `ChannelAdapter` is a `typing.Protocol` with:
  - `name: str` (class attribute, e.g., `"email"`)
  - `send(self, issue: RenderedIssue, recipients: list[str]) -> SendReport`
- **And** `SendReport` is a pydantic v2 model (frozen) with:
  - `channel: Literal["email","slack","telegram"]`
  - `recipients_count: int`
  - `success_count: int`
  - `failure_count: int`
  - `status: Literal["ok","partial","failed"]`
  - `failures: list[FailureDetail]` (a list of `{recipient: str, error: str}` records)

### AC2: `subscribers.yaml` schema is defined and validated
- **Given** the loader `techletter.config.load_subscribers(path)`
- **When** called on a valid `config/subscribers.yaml`
- **Then** the file conforms to this schema:
  ```yaml
  email:
    - alice@example.com
    - bob@example.com
  slack:
    # Slack adapter uses webhook URLs as "recipients"; one per Slack workspace
    - https://hooks.slack.com/services/T.../B.../X...
  telegram:
    # Telegram adapter uses chat ids as "recipients"
    - "-1001234567890"
    - "987654321"
  ```
- **And** missing top-level keys default to empty list (the channel is loadable but has no recipients)
- **And** unknown top-level keys cause `ValidationError` (`extra="forbid"`)
- **And** email entries are validated against `pydantic.EmailStr`
- **And** Slack entries are validated as URLs starting with `https://hooks.slack.com/`
- **And** Telegram entries are validated as strings of digits (optionally prefixed with `-` for channel/group IDs)

### AC3: `channels.yaml` schema is defined and validated
- **Given** the loader `techletter.config.load_channels(path)`
- **When** called on a valid `config/channels.yaml`
- **Then** the file conforms to this schema:
  ```yaml
  email:
    enabled: true
    from_name: "Tech-Letter for HYL"
    subject_template: "Tech-Letter Issue {{ issue_id }}"
  slack:
    enabled: true
  telegram:
    enabled: true
    parse_mode: "HTML"  # or "MarkdownV2"
  ```
- **And** missing top-level keys default to `enabled: false` for that channel
- **And** unknown top-level keys cause `ValidationError`

### AC4: Loaders raise `ConfigLoadError` on failure
- **Given** either config file is missing, contains invalid YAML, or fails schema validation
- **When** the loader is called
- **Then** it raises `ConfigLoadError` with a message identifying the file and the underlying cause (chained as `__cause__`)
- **And** `ConfigLoadError` is the same class introduced in US0005 (reuse, don't duplicate)

### AC5: A trivial test adapter implements the protocol
- **Given** a fixture adapter `FakeChannel` with `name = "fake"` and a stubbed `send` returning a fixed `SendReport`
- **When** pyright type-checks code assigning `FakeChannel()` to a variable typed `ChannelAdapter`
- **Then** type checking passes with no errors

### AC6: `SendReport.status` is derivable from counts
- **Given** a `SendReport` instance
- **When** the `status` field is examined
- **Then** the value matches this rule:
  - `success_count > 0 and failure_count == 0` → `"ok"`
  - `success_count > 0 and failure_count > 0` → `"partial"`
  - `success_count == 0 and failure_count > 0` → `"failed"`
  - `recipients_count == 0` (no one configured) → `"ok"` (vacuously; not a failure)
- **And** a validator on the model enforces this consistency (raises `ValidationError` if construction violates it)

---

## Scope

### In Scope
- `techletter/delivery/base.py` defining `ChannelAdapter`, `SendReport`, `FailureDetail`.
- `techletter/config/subscribers.py` defining `SubscribersConfig` and the loader.
- `techletter/config/channels.py` defining `ChannelsConfig` (with sub-models per channel: `EmailConfig`, `SlackConfig`, `TelegramConfig`) and the loader.
- Default `config/subscribers.yaml.example` and `config/channels.yaml` shipped at repo root.
- Reuse of `ConfigLoadError` from US0005.
- Unit tests covering schema validation, loaders, `SendReport` consistency.

### Out of Scope
- The three concrete adapters (US0019/US0020/US0021).
- The registry (US0022).
- Hot-reload of config — re-run the CLI to pick up changes.
- Per-recipient preference flags (e.g., HTML vs plain-text per email subscriber) — out of scope for v1.

---

## Technical Notes

- `SubscribersConfig` and `ChannelsConfig` are separate files so subscribers can be changed (additions/removals) without touching channel behaviour, and vice versa.
- `subscribers.yaml.example` is committed; the real `subscribers.yaml` is also committed (PRD-decided: subscriber list lives in repo for v1).
- `SendReport.failures` keeps per-recipient error info for diagnosis; not surfaced in `logs/sends.jsonl` (that's just the rollup status) but written to workflow logs.
- The `SendReport`-status consistency validator is a pydantic `model_validator(mode='after')`.

### API Contracts
- `ChannelAdapter` — typing.Protocol with `name: str` and `send(issue, recipients) -> SendReport`.
- `SendReport(channel, recipients_count, success_count, failure_count, status, failures) -> SendReport`
- `load_subscribers(path) -> SubscribersConfig`
- `load_channels(path) -> ChannelsConfig`

### Data Requirements
`config/subscribers.yaml` and `config/channels.yaml` at repo root.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `subscribers.yaml` missing | `ConfigLoadError` |
| `channels.yaml` missing | `ConfigLoadError` |
| Subscribers file has `email: []` (empty list) | Loadable; email adapter constructed but has no recipients |
| Subscribers file has unknown channel key (e.g., `discord:`) | `ValidationError` (forbid extra) |
| Channels file has `email.enabled: true` but subscribers has no `email` key | Email adapter still constructable; sends to zero recipients; `SendReport.status = "ok"` (vacuously) |
| Email entry malformed (not a valid email address) | `ValidationError`; loader fails |
| Slack URL not starting with `https://hooks.slack.com/` | `ValidationError` |
| Telegram chat id contains non-digit chars (other than leading `-`) | `ValidationError` |
| Subscribers list duplicates same recipient | Loader allows duplicates; downstream adapter is responsible for dedupe (do dedupe in registry, US0022) |
| `SendReport` constructed with `success_count + failure_count != recipients_count` | `ValidationError` from consistency validator |
| `SendReport` with `recipients_count = 0, success_count = 0, failure_count = 0` | Valid; `status = "ok"` (vacuously) |
| Attempt to mutate a `SendReport` after construction | `ValidationError` (frozen) |
| Attempt to use a channel name outside `{"email","slack","telegram"}` | `ValidationError` |

---

## Test Scenarios

- [ ] Load valid `subscribers.yaml` → returns `SubscribersConfig` with expected recipients.
- [ ] Load with unknown top-level key → `ConfigLoadError` chaining `ValidationError`.
- [ ] Load with invalid email → `ConfigLoadError`.
- [ ] Load with `email:` key missing → loadable; email list is empty.
- [ ] Load `channels.yaml` with `email.enabled: false` → email config carries the flag.
- [ ] `SendReport(recipients_count=10, success_count=10, failure_count=0, status="ok")` → valid.
- [ ] `SendReport(... success=5, failure=5, status="partial")` → valid.
- [ ] `SendReport(... success=5, failure=0, status="partial")` → `ValidationError` (status mismatch).
- [ ] `SendReport(... 0/0/0)` → valid, status `"ok"`.
- [ ] `FakeChannel()` assignable to `ChannelAdapter` per pyright.
- [ ] `ConfigLoadError` is the same class imported from `techletter.config` (no duplication with US0005).

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0005](US0005-source-registry-and-config-loader.md) | Shared | `ConfigLoadError` exception class | Draft |
| [US0011](US0011-compose-blog-quick-mentions-and-issue-assembly.md) | Schema | `RenderedIssue` model (for the protocol signature) | Draft |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `pydantic[email]` extras for `EmailStr` | Library | Add to dependencies |

---

## Estimation

**Story Points:** 3
**Complexity:** Low. Mostly schema definition + loaders + a consistency validator. The interesting part is `SendReport.status` derivation rules — worth a careful unit test.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0004. |

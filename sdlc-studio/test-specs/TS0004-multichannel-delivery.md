# TS0004: Multi-channel Delivery

> **Status:** Ready
> **Epic:** [EP0004: Multi-channel Delivery](../epics/EP0004-multichannel-delivery.md)
> **Created:** 2026-05-19
> **Last Updated:** 2026-05-19
> **TC Range:** TC0198–TC0260

## Overview

Test specification for the delivery-side adapter pattern — the `ChannelAdapter` protocol, the three concrete channel adapters (email/Slack/Telegram), and the `ChannelRegistry` that ties them together. This is the spec where the TSD-mandated `hypothesis` properties on the two splitters (`split_for_slack`, `split_for_telegram`) and two escapers (`commonmark_to_mrkdwn`, `commonmark_to_telegram_html`) finally land — example-based tests catch the easy bugs; property-based tests catch the splitting/escaping invariants that examples miss.

Three external-service strategies are used here (per TSD):

1. **`aiosmtpd`** — an in-process SMTP server fixture for the email adapter (US0019). Real SMTP semantics, no Gmail credentials needed.
2. **`pytest-httpx`** — explicit HTTP response queues for Slack webhooks (US0020) and Telegram Bot API (US0021). Failure injection (429, 403, 5xx) is trivial here; live HTTP never happens.
3. **`FakeChannel`** — for the registry tests (US0022), individual channel adapters are stubbed entirely so the registry's aggregation and isolation logic can be tested without dragging in the per-adapter machinery.

The TSD's pure-helper coverage tier (≥95% line + branch) applies with force to this epic:

- `techletter.delivery.slack::commonmark_to_mrkdwn` and `::split_for_slack`
- `techletter.delivery.telegram::commonmark_to_telegram_html` and `::split_for_telegram`
- The markdown→plain-text stripper in `techletter.delivery.email`
- `SendReport`'s consistency validator in `techletter.delivery.base`

Adapter shells (the `send()` methods themselves) ride on the ≥85% overall floor.

## Scope

### Stories Covered

| Story | Title | Priority |
|-------|-------|----------|
| [US0018](../stories/US0018-channel-adapter-protocol-and-config-loaders.md) | `ChannelAdapter` protocol + config loaders | P0 (foundation) |
| [US0019](../stories/US0019-email-channel-adapter.md) | Email adapter (SMTP multipart + Jinja2) | P0 |
| [US0020](../stories/US0020-slack-channel-adapter.md) | Slack adapter (webhook + splitter) | P0 |
| [US0021](../stories/US0021-telegram-channel-adapter.md) | Telegram adapter (Bot API + splitter) | P0 |
| [US0022](../stories/US0022-channel-registry-and-send-aggregation.md) | Channel registry + send aggregation | P0 |

### AC Coverage Matrix

| Story | AC | Description | Test Cases | Status |
|-------|-----|-------------|------------|--------|
| US0018 | AC1 | `ChannelAdapter` protocol + `SendReport` model | TC0198, TC0199 | Covered |
| US0018 | AC2 | `subscribers.yaml` schema + per-channel validators | TC0200, TC0201, TC0202 | Covered |
| US0018 | AC3 | `channels.yaml` schema + per-channel sub-models | TC0203 | Covered |
| US0018 | AC4 | `ConfigLoadError` reused (not duplicated) | TC0204 | Covered |
| US0018 | AC5 | `FakeChannel` satisfies protocol per pyright | TC0205 | Covered |
| US0018 | AC6 | `SendReport.status` derivable from counts (validator) | TC0206 | Covered |
| US0019 | AC1 | `EmailAdapter` conformant + constructor signature | TC0208 | Covered |
| US0019 | AC2 | `SmtpCreds` from env; missing → `SmtpCredsError` | TC0209, TC0210 | Covered |
| US0019 | AC3 | Jinja2 HTML template rendered with documented context | TC0211 | Covered |
| US0019 | AC4 | Plain-text fallback strips markdown markers | TC0212 | Covered |
| US0019 | AC5 | Multipart structure (`text/plain` + `text/html`) | TC0213 | Covered |
| US0019 | AC6 | One SMTP connection per batch | TC0214 | Covered |
| US0019 | AC7 | Per-recipient failure isolation (550 mid-batch) | TC0215 | Covered |
| US0019 | AC8 | Empty recipients → no SMTP connection | TC0216 | Covered |
| US0020 | AC1 | `SlackAdapter` conformant | TC0221 | Covered |
| US0020 | AC2 | CommonMark → mrkdwn conversions | TC0222 | Covered |
| US0020 | AC3 | Message splitting at paragraph boundaries (≤3500) | TC0223 | Covered |
| US0020 | AC4 | N×M POSTs (webhooks × chunks) | TC0224 | Covered |
| US0020 | AC5 | 4xx webhook → that webhook fails, others proceed | TC0225 | Covered |
| US0020 | AC6 | 429 → tenacity backoff respecting `Retry-After` | TC0226 | Covered |
| US0020 | AC7 | Empty recipients → no HTTP | TC0227 | Covered |
| US0020 | AC8 | Code-block integrity preserved across splits | TC0228 | Covered |
| US0021 | AC1 | `TelegramAdapter` conformant | TC0235 | Covered |
| US0021 | AC2 | Bot token from env; masking in logs | TC0236, TC0247 | Covered |
| US0021 | AC3 | CommonMark → Telegram HTML (escape-first ordering) | TC0237 | Covered |
| US0021 | AC4 | Splitting at 3900 chars; never mid-tag | TC0238 | Covered |
| US0021 | AC5 | One POST per chat per chunk; correct payload shape | TC0239 | Covered |
| US0021 | AC6 | `disable_web_page_preview` config flag honoured | TC0240 | Covered |
| US0021 | AC7 | Per-chat failure isolation (403 Forbidden mid-batch) | TC0241 | Covered |
| US0021 | AC8 | Empty recipients → no HTTP | TC0242 | Covered |
| US0022 | AC1 | `ChannelRegistry` + `build_registry` signature | TC0250 | Covered |
| US0022 | AC2 | Only enabled channels constructed | TC0251 | Covered |
| US0022 | AC3 | Channel construction failure → omitted with WARN | TC0252 | Covered |
| US0022 | AC4 | `send_all` dispatches to every adapter | TC0253 | Covered |
| US0022 | AC5 | Recipients deduplicated order-preserving | TC0254 | Covered |
| US0022 | AC6 | Adapter exception → synthesised `failed` `SendReport` | TC0255 | Covered |
| US0022 | AC7 | All disabled → empty list, INFO log | TC0256 | Covered |
| US0022 | AC8 | Stable iteration order across calls | TC0257 | Covered |

**Coverage:** 38 / 38 ACs covered. **Uncovered: 0.** Spec eligible to move Draft → Ready.

### Test Types Required

| Type | Required | Rationale |
|------|----------|-----------|
| Unit | Yes | Splitters, escapers, plain-text stripper, `SendReport` validator — all pure functions held to the ≥95% line+branch tier |
| Unit (property-based) | **Yes (TSD-mandated)** | `split_for_slack`, `split_for_telegram`, `commonmark_to_mrkdwn`, `commonmark_to_telegram_html` get hypothesis tests for the invariants examples can't reach |
| Integration (in-process fake servers) | Yes | `aiosmtpd` for SMTP; `pytest-httpx` for Slack + Telegram. Real protocol semantics, no live network. |
| E2E | No | The TSD's `tests/pipeline/test_full_run.py` already exercises the full draft path with stubbed channels; per-channel real send is the production E2E and lives in the smoke send (draft.yml). |

---

## Environment

| Requirement | Details |
|-------------|---------|
| Prerequisites | Python 3.11+, pytest ≥ 8.0, pytest-cov, **hypothesis ≥ 6.0**, **pytest-httpx ≥ 0.30**, **aiosmtpd ≥ 1.4**, freezegun, jinja2, pydantic[email] |
| External Services | **None.** SMTP → `aiosmtpd` in-process; HTTPS → `pytest-httpx` response queue; LLM is not used in this epic at all |
| Test Data | Fixture `subscribers.yaml` / `channels.yaml` under `tests/fixtures/delivery/`; fixture `RenderedIssue` instances of varying lengths (short < 3500, medium 3500–8000, long with code-block-spanning content) |
| Clock | Frozen at `2026-05-19T00:00:00Z` so the demo-issue id is deterministic |
| Env vars | `SMTP_HOST`/`SMTP_USER`/`SMTP_PASS`/`SMTP_FROM` monkey-patched per test (never real values); `TELEGRAM_BOT_TOKEN` set to a synthetic value `bot:fake-test-token` whose pattern matches the real one shape — TC0247 verifies it never escapes into logs |

### Hypothesis strategies

Four custom strategies, defined in `tests/conftest.py`:

1. `markdown_safe_strategy` — generates well-formed CommonMark fragments (random bold/italic/headings/links/code blocks). Used by `commonmark_to_*` property tests.
2. `mixed_text_strategy` — random Unicode text with a sprinkling of `&`, `<`, `>`, backticks, asterisks, brackets. Used to stress-test escape ordering.
3. `splittable_text_strategy` — generates 0–20000-char text composed of paragraphs and code blocks at random boundaries. Used by `split_for_*` property tests.
4. `recipient_list_strategy` — generates random recipient lists with controlled rates of duplicates. Used by registry tests.

Each strategy has `max_examples=200` by default; the `slow` marker raises it to `2000` for nightly runs (the splitters are the strategies most worth exhausting).

---

## Test Cases

### TC0198: `ChannelAdapter` protocol + `SendReport` model have documented shape

**Type:** Unit | **Priority:** P0 | **Story:** US0018 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.delivery.base import ChannelAdapter, SendReport, FailureDetail` | Imports succeed |
| When | `SendReport(channel="email", recipients_count=2, success_count=2, failure_count=0, status="ok", failures=[])` constructed | Validates |
| Then | `ChannelAdapter` is a `typing.Protocol` with `name: str` and `send(...) -> SendReport`; `SendReport` is frozen | Pyright sees the protocol |

**Assertions:**
- [ ] `ChannelAdapter` is identified as a Protocol by `typing.get_type_hints` / runtime introspection
- [ ] `SendReport.model_config["frozen"] is True`

---

### TC0199: `FailureDetail` model has documented shape

**Type:** Unit | **Priority:** P2 | **Story:** US0018 (AC1, AC6 support)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.delivery.base import FailureDetail` | Import succeeds |
| When | `FailureDetail(recipient="alice@x.com", error="SMTP 550")` constructed | Validates |
| Then | Both fields are required `str` | n/a |

**Assertions:**
- [ ] Missing `recipient` raises `ValidationError`
- [ ] Missing `error` raises `ValidationError`

---

### TC0200: `load_subscribers` reads a valid `subscribers.yaml` into `SubscribersConfig`

**Type:** Unit | **Priority:** P0 | **Story:** US0018 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fixture `subscribers_valid.yaml` (email/slack/telegram each populated) | n/a |
| When | `load_subscribers(path)` | Returns `SubscribersConfig` |
| Then | All three lists have the expected values; missing channel keys default to `[]` | n/a |

**Assertions:**
- [ ] `config.email == ["alice@example.com", "bob@example.com"]`
- [ ] `config.slack[0].startswith("https://hooks.slack.com/")`
- [ ] `config.telegram == ["-1001234567890", "987654321"]`

---

### TC0201: Unknown top-level key in `subscribers.yaml` → `ConfigLoadError` (extra="forbid")

**Type:** Unit | **Priority:** P1 | **Story:** US0018 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | YAML containing `discord: ["foo"]` | n/a |
| When | `load_subscribers(path)` | Raises `ConfigLoadError` |
| Then | `__cause__` is `pydantic.ValidationError`; message mentions `"discord"` | n/a |

**Assertions:**
- [ ] `pytest.raises(ConfigLoadError)` with message containing `"discord"`
- [ ] `isinstance(exc.__cause__, pydantic.ValidationError)`

---

### TC0202: Per-channel recipient validation (parametric)

**Type:** Unit (parametric) | **Priority:** P1 | **Story:** US0018 (AC2)

**Parametrisation:**

| Channel | Bad entry | Expected |
|---------|-----------|----------|
| email | `"not-an-email"` | `ValidationError` (EmailStr) |
| slack | `"https://example.com/webhook"` | `ValidationError` (must start with `https://hooks.slack.com/`) |
| slack | `"http://hooks.slack.com/x"` | `ValidationError` (https only) |
| telegram | `"abc123"` | `ValidationError` (non-digit after optional `-`) |
| telegram | `"-1001234567890"` | Valid (negative for groups/channels) |
| telegram | `"987654321"` | Valid (positive for private chats) |

**Assertions:**
- [ ] Each bad case raises; each valid case loads cleanly

---

### TC0203: `load_channels` reads a valid `channels.yaml`; sub-models populated

**Type:** Unit | **Priority:** P0 | **Story:** US0018 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `channels.yaml` with all three channels enabled, `email.subject_template` set, `telegram.parse_mode` set | n/a |
| When | `load_channels(path)` | Returns `ChannelsConfig` |
| Then | `config.email.enabled is True`; `config.email.subject_template == "Tech-Letter Issue {{ issue_id }}"`; `config.telegram.parse_mode == "HTML"` | Missing top-level keys default to `enabled: false` |

**Assertions:**
- [ ] All sub-model fields populated as expected
- [ ] A config with `email:` block omitted → `config.email.enabled is False`

---

### TC0204: Missing config file → `ConfigLoadError` chaining `FileNotFoundError`

**Type:** Unit | **Priority:** P1 | **Story:** US0018 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A path that doesn't exist | n/a |
| When | `load_subscribers(missing_path)` | Raises `ConfigLoadError` |
| Then | `__cause__` is `FileNotFoundError`; message mentions the path; the exception is the **same `ConfigLoadError` class as US0005** | n/a |

**Assertions:**
- [ ] `pytest.raises(ConfigLoadError)`
- [ ] `isinstance(exc.__cause__, FileNotFoundError)`
- [ ] `ConfigLoadError` is imported from the same module as US0005's loader (identity check via module path)

---

### TC0205: `FakeChannel` satisfies the `ChannelAdapter` protocol per pyright

**Type:** Unit (pyright invocation) | **Priority:** P1 | **Story:** US0018 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A `class FakeChannel` with `name = "fake"` and `def send(self, issue, recipients): return SendReport(...)` | n/a |
| When | A protocol-assertion module assigns `FakeChannel()` to `channel: ChannelAdapter`, then `pyright --outputjson` runs | Zero diagnostics |
| Then | At runtime, `FakeChannel().send(issue, [])` returns `SendReport(recipients_count=0, status="ok")` | n/a |

**Assertions:**
- [ ] Pyright reports 0 errors / 0 warnings
- [ ] Runtime call returns the documented stub `SendReport`

---

### TC0206: `SendReport.status` consistency validator (parametric)

**Type:** Unit (parametric) | **Priority:** P0 | **Story:** US0018 (AC6)

**Parametrisation:**

| Counts | Status declared | Expected |
|--------|----------------|----------|
| recipients=10, success=10, failure=0 | `"ok"` | Validates |
| recipients=10, success=5, failure=5 | `"partial"` | Validates |
| recipients=10, success=0, failure=10 | `"failed"` | Validates |
| recipients=0, success=0, failure=0 | `"ok"` | Validates (vacuous) |
| recipients=10, success=5, failure=0 | `"ok"` | `ValidationError` (success+failure ≠ recipients) |
| recipients=10, success=5, failure=5 | `"ok"` | `ValidationError` (status mismatch) |
| recipients=10, success=10, failure=0 | `"partial"` | `ValidationError` |
| recipients=10, success=0, failure=10 | `"ok"` | `ValidationError` |

**Assertions:**
- [ ] Each valid case constructs without error
- [ ] Each invalid case raises `ValidationError`

---

### TC0207: `SendReport` frozen — mutation raises

**Type:** Unit | **Priority:** P2 | **Story:** US0018 (AC1, frozen)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A valid `SendReport` | n/a |
| When | `report.success_count = 99` | Raises |
| Then | Original `report.success_count` unchanged | n/a |

**Assertions:**
- [ ] Mutation raises `ValidationError`
- [ ] Original value unchanged

---

### TC0208: `EmailAdapter()` is a valid `ChannelAdapter` per pyright

**Type:** Unit | **Priority:** P0 | **Story:** US0019 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.delivery.email import EmailAdapter, SmtpCreds, SmtpCredsError` | Imports succeed |
| When | `adapter = EmailAdapter(config=fixture_email_config, smtp_creds=fixture_creds)` | Constructor succeeds |
| Then | `adapter.name == "email"`; pyright accepts assignment to `ChannelAdapter` | n/a |

**Assertions:**
- [ ] `adapter.name == "email"`
- [ ] Pyright protocol assertion passes

---

### TC0209: `SmtpCreds.from_env()` — all 4 required vars

**Type:** Unit (monkeypatch) | **Priority:** P0 | **Story:** US0019 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | All of `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` set in env | n/a |
| When | `SmtpCreds.from_env()` | Returns valid `SmtpCreds` |
| Then | Removing any one of the four → `SmtpCredsError` at the next call | The error message names the missing var |

**Assertions:**
- [ ] Parametrised over `["SMTP_HOST", "SMTP_USER", "SMTP_PASS", "SMTP_FROM"]`: each missing → `SmtpCredsError`
- [ ] Error message contains the missing variable's name

---

### TC0210: `SMTP_PORT` defaults to 587 when unset

**Type:** Unit | **Priority:** P2 | **Story:** US0019 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | All required vars set; `SMTP_PORT` unset | n/a |
| When | `SmtpCreds.from_env()` | Returns creds with `port == 587` |
| Then | Setting `SMTP_PORT=465` → `port == 465` | n/a |

**Assertions:**
- [ ] Default 587 when unset
- [ ] Custom value used when set

---

### TC0211: Jinja2 template loaded once at init; called per recipient with documented context

**Type:** Integration (aiosmtpd + spied jinja env) | **Priority:** P1 | **Story:** US0019 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `templates/email.html.j2` exists; `jinja2.Environment.get_template` is patched to record calls | n/a |
| When | `adapter = EmailAdapter(...)`, then `adapter.send(issue, ["a@x", "b@x"])` | n/a |
| Then | `get_template` called once (at init or first render, then cached); each render receives at least `{issue_id, markdown, meta, front_matter}` in context | n/a |

**Assertions:**
- [ ] Template loaded once per adapter lifetime
- [ ] Each rendered HTML contains the issue_id (verifiable by string-match)
- [ ] Render context has all four keys

---

### TC0212: Markdown → plain-text stripper (parametric)

**Type:** Unit (parametric) | **Priority:** P0 | **Story:** US0019 (AC4)

**Parametrisation:**

| Input | Expected output |
|-------|-----------------|
| `"**bold**"` | `"bold"` |
| `"*italic*"` | `"italic"` |
| `"# Heading\n\nbody"` | `"Heading\n\nbody"` (heading on own line, no `#`) |
| `"[link text](https://x.com)"` | `"link text (https://x.com)"` |
| ` "```\ncode\n```" ` | `"code"` (fences removed, contents kept) |
| ` "`inline`" ` | `"inline"` (inline backticks stripped) |
| `"plain text"` | `"plain text"` |

**Assertions:**
- [ ] All 7 cases produce the expected output

---

### TC0213: Multipart structure: `text/plain` + `text/html` under `multipart/alternative`

**Type:** Integration (aiosmtpd) | **Priority:** P0 | **Story:** US0019 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | aiosmtpd fake server running; adapter constructed | n/a |
| When | `adapter.send(issue, ["alice@x.com"])` | Server receives one message |
| Then | The captured `EmailMessage` has `Content-Type: multipart/alternative`; a `text/plain` part and a `text/html` part; `From` matches `SMTP_FROM` with `from_name` prefix; `Subject` is rendered from `subject_template` | n/a |

**Assertions:**
- [ ] Message structure includes both parts
- [ ] `From` header contains `from_name` and `SMTP_FROM` email
- [ ] `Subject` matches the rendered template

---

### TC0214: One SMTP connection per `send()` batch, 50 recipients → 50 messages

**Type:** Integration (aiosmtpd) | **Priority:** P1 | **Story:** US0019 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fake SMTP server tracking `connection_count`; 50 fixture recipients | n/a |
| When | `adapter.send(issue, 50_recipients)` | n/a |
| Then | `connection_count == 1`; server received 50 distinct messages, each `To:` one recipient (never BCC) | n/a |

**Assertions:**
- [ ] Server's connection count is exactly 1
- [ ] Server received 50 messages, each with a single `To:` address
- [ ] No BCC header in any message (privacy)

---

### TC0215: Per-recipient failure (550) — 9 ok, 1 failed, status "partial"

**Type:** Integration (aiosmtpd with rejection hook) | **Priority:** P0 | **Story:** US0019 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fake SMTP server configured to return `550 5.1.1` for recipient #4; 10 recipients total | n/a |
| When | `adapter.send(issue, 10_recipients)` | Returns `SendReport` |
| Then | `success_count == 9`, `failure_count == 1`, `status == "partial"`; `failures` has one entry naming recipient #4 | Server received the other 9 messages successfully |

**Assertions:**
- [ ] `report.success_count == 9 and report.failure_count == 1`
- [ ] `report.status == "partial"`
- [ ] `len(report.failures) == 1` and `report.failures[0].recipient == recipients[3]`

---

### TC0216: Empty recipient list → no SMTP connection opened, `status="ok"`

**Type:** Integration (aiosmtpd with connection counter) | **Priority:** P1 | **Story:** US0019 (AC8)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fake server with `connection_count = 0` | n/a |
| When | `adapter.send(issue, [])` | Returns `SendReport(recipients_count=0, status="ok")` |
| Then | Server's connection count is still 0 | n/a |

**Assertions:**
- [ ] `report.recipients_count == 0 and report.status == "ok"`
- [ ] Server connection count remains 0

---

### TC0217: SMTP connect fails twice then succeeds — tenacity retries succeed

**Type:** Integration (smtplib mock) | **Priority:** P1 | **Story:** US0019 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `smtplib.SMTP.__init__` patched to raise `ConnectionRefusedError` twice then succeed | n/a |
| When | `adapter.send(issue, ["a@x"])` | Returns success |
| Then | 3 connection attempts observed; final send succeeded | n/a |

**Assertions:**
- [ ] Mock observed 3 init attempts
- [ ] `report.status == "ok"`

---

### TC0218: SMTP connect fails 3× → status="failed", all recipients listed as failed

**Type:** Integration (smtplib mock) | **Priority:** P1 | **Story:** US0019 (AC6, edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Connection raises on all 3 attempts | n/a |
| When | `adapter.send(issue, 5_recipients)` | Returns `SendReport` |
| Then | `status == "failed"`; `failures` has 5 entries (one per recipient), all with the connection error | n/a |

**Assertions:**
- [ ] `report.status == "failed"`
- [ ] `len(report.failures) == 5`
- [ ] All failure entries reference the connection error

---

### TC0219: Jinja2 template missing → `FileNotFoundError` at adapter init

**Type:** Unit | **Priority:** P2 | **Story:** US0019 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `templates/email.html.j2` deleted from `tmp_path` | n/a |
| When | `EmailAdapter(config, creds)` constructed | Raises `FileNotFoundError` |
| Then | Message names the expected template path | n/a |

**Assertions:**
- [ ] `pytest.raises(FileNotFoundError)` with `"email.html.j2"` in message

---

### TC0220: Empty `subject_template` → fallback `"Tech-Letter Issue {issue_id}"` used

**Type:** Unit | **Priority:** P2 | **Story:** US0019 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `EmailConfig(subject_template="")` | n/a |
| When | `adapter.send(issue, ["a@x"])` | Server receives a message |
| Then | `Subject` header is the fallback string with `issue_id` interpolated | n/a |

**Assertions:**
- [ ] Subject equals `"Tech-Letter Issue 2026-05-19"` (or close)

---

### TC0221: `SlackAdapter()` is a valid `ChannelAdapter` per pyright

**Type:** Unit | **Priority:** P0 | **Story:** US0020 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.delivery.slack import SlackAdapter` | Import succeeds |
| When | `SlackAdapter(config=fixture_slack_config)` | Constructor succeeds |
| Then | `adapter.name == "slack"`; pyright accepts | n/a |

**Assertions:**
- [ ] `adapter.name == "slack"`
- [ ] Pyright protocol check passes

---

### TC0222: `commonmark_to_mrkdwn` — example-based conversions (parametric)

**Type:** Unit (parametric) | **Priority:** P0 | **Story:** US0020 (AC2)

**Parametrisation:**

| Input | Expected output |
|-------|-----------------|
| `"**bold**"` | `"*bold*"` |
| `"_italic_"` | `"_italic_"` |
| `"*italic*"` (CommonMark) | `"_italic_"` (Slack) |
| `"[text](https://x.com)"` | `"<https://x.com|text>"` |
| `"# Heading\n\nbody"` | `"*Heading*\n\nbody"` |
| `"## Subheading"` | `"*Subheading*"` |
| ` "`inline`" ` | ` "`inline`" ` (preserved) |
| ` "```\nx\n```" ` | ` "```\nx\n```" ` (preserved) |
| `"- bullet"` | `"- bullet"` (preserved) |
| `"![alt](u)"` | `"<u|alt>"` (image converted to link) |

**Assertions:**
- [ ] All 10 cases produce expected output

---

### TC0223: `split_for_slack` — long text → multiple chunks, ≤3500 each, paragraph boundaries

**Type:** Unit | **Priority:** P0 | **Story:** US0020 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A 5000-char text made of 10 paragraphs separated by `\n\n` | n/a |
| When | `split_for_slack(text, limit_chars=3500)` | Returns N chunks |
| Then | Each chunk ≤ 3500 chars; chunks join to recover the original (or differ only in chunk-prefix marker) | No chunk starts mid-paragraph |

**Assertions:**
- [ ] All chunks satisfy `len(chunk) <= 3500`
- [ ] Each chunk except the first starts with `(continued, X/N)` prefix
- [ ] Joining chunks (stripping prefixes) yields the original text

---

### TC0224: N webhooks × M chunks → N × M POSTs in correct order

**Type:** Integration (pytest-httpx) | **Priority:** P1 | **Story:** US0020 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 2 webhooks; issue body that splits into 3 chunks; all webhooks return 200 | n/a |
| When | `adapter.send(issue, 2_webhooks)` | n/a |
| Then | Mock observed 6 POSTs (2×3); per webhook, the 3 chunks went in chronological order | n/a |

**Assertions:**
- [ ] `len(httpx_mock.get_requests()) == 6`
- [ ] Per webhook URL: requests are sequential (timestamps strictly increasing) and chunk prefixes are `1/3`, `2/3`, `3/3` in order

---

### TC0225: One webhook returns 404 → that webhook fails, others proceed

**Type:** Integration (pytest-httpx) | **Priority:** P0 | **Story:** US0020 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 3 webhooks; #2 returns 404 on every chunk; #1 and #3 return 200 | n/a |
| When | `adapter.send(issue, 3_webhooks)` | Returns `SendReport` |
| Then | `success_count == 2`, `failure_count == 1`, `status == "partial"`; `failures` has exactly one entry naming webhook #2 (not per chunk) | n/a |

**Assertions:**
- [ ] `report.success_count == 2 and report.failure_count == 1`
- [ ] `report.status == "partial"`
- [ ] `len(report.failures) == 1`
- [ ] The failure entry's `recipient` matches webhook #2's URL

---

### TC0226: 429 with `Retry-After: 2` — tenacity respects header

**Type:** Integration (pytest-httpx) | **Priority:** P1 | **Story:** US0020 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Webhook returns 429 with `Retry-After: 2` twice, then 200 (mock `time.sleep` to instant) | n/a |
| When | `adapter.send(issue, [webhook])` | Returns `SendReport` |
| Then | Final state is success; mock observed 3 attempts; `time.sleep(2)` was called twice (tenacity respected the header) | n/a |

**Assertions:**
- [ ] `report.status == "ok"`
- [ ] 3 requests observed
- [ ] Sleep mock called with 2.0 at least once (or close tolerance)

---

### TC0227: Empty Slack recipients → no HTTP requests

**Type:** Integration (pytest-httpx) | **Priority:** P1 | **Story:** US0020 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | No webhooks queued | n/a |
| When | `adapter.send(issue, [])` | Returns `SendReport(recipients_count=0, status="ok")` |
| Then | `httpx_mock.get_requests() == []` | n/a |

**Assertions:**
- [ ] `report.recipients_count == 0 and report.status == "ok"`
- [ ] Zero HTTP requests observed

---

### TC0228: Code block spanning a paragraph boundary stays intact across split

**Type:** Unit | **Priority:** P1 | **Story:** US0020 (AC8)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Text with a code block (triple-backtick) starting in one paragraph and ending in the next, followed by enough additional paragraphs to force a split | n/a |
| When | `split_for_slack(text, limit_chars=3500)` | Returns N chunks |
| Then | The code block is contained entirely within one chunk; no chunk contains an unclosed triple-backtick | n/a |

**Assertions:**
- [ ] For every chunk: count of opening fences equals count of closing fences (i.e., balanced)
- [ ] The original code block's content appears verbatim in exactly one chunk

---

### TC0229: Hypothesis property — `split_for_slack` invariants

**Type:** Unit (property-based) | **Priority:** P0 | **Story:** US0020 (AC3, AC8 — TSD-mandated)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `@given(splittable_text_strategy)` and a randomised `limit_chars` between 1000 and 8000 | `max_examples=200` |
| When | `split_for_slack(text, limit_chars)` runs for each generated input | Returns `list[str]` |
| Then | **Invariants:** (a) every chunk is `≤ limit_chars`; (b) joining chunks (after stripping `(continued, X/N)` prefixes) yields the original text or a documented superset (only added prefixes); (c) no chunk contains an unbalanced code-block fence | n/a |

**Assertions:**
- [ ] All three invariants hold for every generated example
- [ ] No `Falsified` outcome from hypothesis

---

### TC0230: Hypothesis property — `commonmark_to_mrkdwn` round-trip-ish invariants

**Type:** Unit (property-based) | **Priority:** P1 | **Story:** US0020 (AC2 — TSD-mandated)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `@given(markdown_safe_strategy)` | `max_examples=200` |
| When | `commonmark_to_mrkdwn(input)` runs | Returns string |
| Then | **Invariants:** (a) non-empty input → non-empty output; (b) no double-asterisks `**` survive in output (Slack uses single `*`); (c) every CommonMark link `[text](url)` produces a Slack `<url|text>` in output; (d) output is valid UTF-8 | n/a |

**Assertions:**
- [ ] All invariants hold
- [ ] No `**` substring in any output

---

### TC0231: Webhook 429 × 5 → that webhook marked failed

**Type:** Integration (pytest-httpx) | **Priority:** P2 | **Story:** US0020 (AC6, edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Webhook returns 429 with `Retry-After: 1` on every attempt; tenacity max 5 attempts | n/a |
| When | `adapter.send(issue, [webhook])` | Returns `SendReport(status="failed")` |
| Then | Mock observed exactly 5 attempts; failure recorded with rate-limit error | n/a |

**Assertions:**
- [ ] 5 requests observed
- [ ] `report.status == "failed"`
- [ ] Failure entry mentions rate limit

---

### TC0232: Markdown image `![alt](url)` → Slack link `<url|alt>`

**Type:** Unit | **Priority:** P2 | **Story:** US0020 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `commonmark_to_mrkdwn("![diagram](https://x.com/a.png)")` | n/a |
| When | Called | n/a |
| Then | Output is `"<https://x.com/a.png|diagram>"` (image rendered as a link, since Slack webhook payloads don't render images inline) | n/a |

**Assertions:**
- [ ] Output exactly `"<https://x.com/a.png|diagram>"`

---

### TC0233: Single oversized code block (4000+ chars) → WARN logged, sent anyway

**Type:** Integration (pytest-httpx + log capture) | **Priority:** P2 | **Story:** US0020 (AC8, edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Issue body containing one code block of 4000 chars; webhook returns 200 | n/a |
| When | `adapter.send(...)` | Returns `SendReport` |
| Then | One WARN log line mentions oversized chunk; HTTP request still made (let Slack truncate display) | n/a |

**Assertions:**
- [ ] WARN log line emitted
- [ ] HTTP request observed
- [ ] `report.status == "ok"` (we didn't fail the send)

---

### TC0234: Short issue (< 3500 chars) → single message, no `(continued)` prefix

**Type:** Integration (pytest-httpx) | **Priority:** P2 | **Story:** US0020 (AC3 boundary)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Issue body 1000 chars; one webhook | n/a |
| When | `adapter.send(...)` | One POST observed |
| Then | The POST body's `text` does NOT contain `"(continued"` | n/a |

**Assertions:**
- [ ] Exactly 1 HTTP request
- [ ] `"(continued"` substring absent from the POST body

---

### TC0235: `TelegramAdapter()` is a valid `ChannelAdapter` per pyright

**Type:** Unit | **Priority:** P0 | **Story:** US0021 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.delivery.telegram import TelegramAdapter` | Import succeeds |
| When | `TelegramAdapter(config, bot_token="bot:fake-test-token")` | Constructor succeeds |
| Then | `adapter.name == "telegram"`; pyright protocol check passes | n/a |

**Assertions:**
- [ ] `adapter.name == "telegram"`

---

### TC0236: `from_env()` reads `TELEGRAM_BOT_TOKEN`; missing → clear error

**Type:** Unit (monkeypatch) | **Priority:** P1 | **Story:** US0021 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `TELEGRAM_BOT_TOKEN` set | n/a |
| When | `TelegramAdapter.from_env(config)` | Returns adapter |
| Then | After `monkeypatch.delenv`, the same call raises a clear construction-time error | n/a |

**Assertions:**
- [ ] With token set: adapter constructs
- [ ] Without token: clear exception (no `KeyError` leakage)

---

### TC0237: `commonmark_to_telegram_html` — escape-first ordering (parametric)

**Type:** Unit (parametric) | **Priority:** P0 | **Story:** US0021 (AC3 — load-bearing)

**Parametrisation:**

| Input | Expected output |
|-------|-----------------|
| `"&<>"` | `"&amp;&lt;&gt;"` (`&` escaped before `<`/`>`) |
| `"**bold**"` | `"<b>bold</b>"` |
| `"_italic_"` | `"<i>italic</i>"` |
| `"*italic*"` (CommonMark) | `"<i>italic</i>"` |
| ` "`inline`" ` | `"<code>inline</code>"` |
| ` "```\ncode & <stuff>\n```" ` | `"<pre>code &amp; &lt;stuff&gt;</pre>"` (escapes inside `pre`) |
| `"# Heading\n\nbody"` | `"<b>Heading</b>\n\nbody"` |
| `"[text & x](https://x.com?a=1&b=2)"` | `'<a href="https://x.com?a=1&amp;b=2">text &amp; x</a>'` |
| `"![alt](u)"` | `'<a href="u">alt</a>'` (image → link, alt as link text) |

**Assertions:**
- [ ] All 9 cases produce expected output exactly
- [ ] The first case (raw `&<>`) is the canonical escape-order check — `&amp;lt;` (double-escaped) means a bug

---

### TC0238: `split_for_telegram` — chunks ≤ 3900 chars, never mid-tag

**Type:** Unit | **Priority:** P0 | **Story:** US0021 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 5000 chars of HTML with `<b>...</b>`, `<a href=...>...</a>`, `<pre>...</pre>` tags interspersed with text | n/a |
| When | `split_for_telegram(html_text, limit_chars=3900)` | Returns N chunks |
| Then | Each chunk ≤ 3900 chars; no chunk contains an unbalanced tag (every opening has a closing within the same chunk) | n/a |

**Assertions:**
- [ ] All chunks satisfy `len(chunk) <= 3900`
- [ ] For every chunk: counts of `<b>`/`</b>`, `<i>`/`</i>`, `<a>`/`</a>`, `<pre>`/`</pre>` all balance
- [ ] Concatenation recovers the original (modulo per-chunk prefix markers)

---

### TC0239: Per chat per chunk → 1 POST with documented payload shape

**Type:** Integration (pytest-httpx) | **Priority:** P1 | **Story:** US0021 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 2 chats; issue splits into 3 chunks; mock returns 200 for all | n/a |
| When | `adapter.send(issue, 2_chats)` | n/a |
| Then | 6 POSTs observed; each body is JSON with `chat_id`, `text`, `parse_mode: "HTML"`, `disable_web_page_preview` | URL format `https://api.telegram.org/bot<token>/sendMessage` |

**Assertions:**
- [ ] `len(httpx_mock.get_requests()) == 6`
- [ ] Each request body has all four documented keys
- [ ] URL path matches `/bot<token>/sendMessage`

---

### TC0240: `disable_web_page_preview` config flag is honoured

**Type:** Integration (pytest-httpx, parametric) | **Priority:** P2 | **Story:** US0021 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | (A) `disable_web_page_preview: False` (default); (B) `True` | n/a |
| When | `adapter.send(...)` | n/a |
| Then | Captured POST body's `disable_web_page_preview` matches the config value | n/a |

**Assertions:**
- [ ] (A): body has `"disable_web_page_preview": false`
- [ ] (B): body has `"disable_web_page_preview": true`

---

### TC0241: One chat returns 403 Forbidden mid-batch → that chat fails, others proceed

**Type:** Integration (pytest-httpx) | **Priority:** P0 | **Story:** US0021 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 3 chats; chat #2 returns 403 with body `{"ok": false, "description": "Forbidden: bot was blocked by the user"}` for every chunk | n/a |
| When | `adapter.send(issue, 3_chats)` | Returns `SendReport` |
| Then | `success_count == 2`, `failure_count == 1`, `status == "partial"`; failure entry mentions "Forbidden" | n/a |

**Assertions:**
- [ ] `report.success_count == 2 and report.failure_count == 1`
- [ ] `report.status == "partial"`
- [ ] Failure entry contains `"Forbidden"` and the offending chat id

---

### TC0242: Empty Telegram recipient list → no HTTP

**Type:** Integration (pytest-httpx) | **Priority:** P1 | **Story:** US0021 (AC8)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | n/a | n/a |
| When | `adapter.send(issue, [])` | Returns `SendReport(recipients_count=0, status="ok")` |
| Then | Zero HTTP requests observed | n/a |

**Assertions:**
- [ ] `httpx_mock.get_requests() == []`
- [ ] `report.status == "ok"`

---

### TC0243: Hypothesis property — `split_for_telegram` invariants

**Type:** Unit (property-based) | **Priority:** P0 | **Story:** US0021 (AC4 — TSD-mandated)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `@given(splittable_text_strategy)` rendered through `commonmark_to_telegram_html` first | `max_examples=200` |
| When | `split_for_telegram(html, limit_chars=3900)` | Returns chunks |
| Then | **Invariants:** (a) every chunk ≤ 3900; (b) every chunk has balanced HTML tag counts; (c) joining chunks (after stripping prefixes) yields the original HTML; (d) no chunk contains an unclosed `<pre>` or `<code>` | n/a |

**Assertions:**
- [ ] All invariants hold across 200 examples
- [ ] No `Falsified` outcome

---

### TC0244: Hypothesis property — `commonmark_to_telegram_html` escape ordering

**Type:** Unit (property-based) | **Priority:** P0 | **Story:** US0021 (AC3 — TSD-mandated)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `@given(mixed_text_strategy)` generating random text with `&`, `<`, `>`, backticks, brackets | `max_examples=200` |
| When | `commonmark_to_telegram_html(input)` runs | Returns escaped HTML |
| Then | **Invariants:** (a) `&amp;lt;` (double-escape) never appears; (b) any raw `<` in input becomes `<` in *output content* only (not as a tag opening unless followed by a known HTML tag); (c) output round-trips through Telegram-safe HTML structure — every opening tag has a closing tag | n/a |

**Assertions:**
- [ ] `"&amp;lt;"` and `"&amp;gt;"` never appear in any output
- [ ] Tag balance holds for every example

---

### TC0245: 429 with `parameters.retry_after` in response body → tenacity respects it

**Type:** Integration (pytest-httpx) | **Priority:** P1 | **Story:** US0021 (AC6 — Telegram-specific)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Mock returns `429 {"ok": false, "parameters": {"retry_after": 3}}` twice, then 200 | n/a |
| When | `adapter.send(...)` | Returns success |
| Then | `time.sleep(3)` called twice; final response is 200 | n/a |

**Assertions:**
- [ ] 3 attempts observed
- [ ] Sleep called with 3.0 (or close)
- [ ] Final `report.status == "ok"`

---

### TC0246: HTTP 200 with `ok: false` body → treated as failure for that chat

**Type:** Integration (pytest-httpx) | **Priority:** P2 | **Story:** US0021 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Mock returns `200 {"ok": false, "description": "Bad Request: can't parse entities"}` | n/a |
| When | `adapter.send(issue, [chat])` | Returns `SendReport(status="failed")` |
| Then | Failure entry mentions the description | This is the case where Telegram accepts the HTTP request but rejects the content |

**Assertions:**
- [ ] `report.status == "failed"`
- [ ] Failure entry's `error` contains `"can't parse entities"` (or close)

---

### TC0247: Bot token NEVER appears in any log output

**Type:** Integration (pytest-httpx + log capture) | **Priority:** P0 | **Story:** US0021 (security — TSD secret-leak rule)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `bot_token = "bot:fake-test-token-1234567890abcdefghijklmnop"`; adapter sends to 3 chats; all 429 retry paths exercised | n/a |
| When | All logs are captured (DEBUG level) | n/a |
| Then | The full token string does NOT appear in any captured log record; masked form `"bot:fa...mnop"` (or similar) may appear | This pairs with the TSD's `secret-leak` grep at CI level |

**Assertions:**
- [ ] `"bot:fake-test-token-1234567890abcdefghijklmnop"` substring NOT in any log record
- [ ] At least one log record contains the masked form (proves logging is happening, not just suppressed)

---

### TC0248: Negative-prefixed chat id (group/channel) passes through unchanged

**Type:** Integration (pytest-httpx) | **Priority:** P2 | **Story:** US0021 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | One chat id `"-1001234567890"` (a Telegram group/channel) | n/a |
| When | `adapter.send(issue, [chat])` | n/a |
| Then | POST body's `chat_id` is the string `"-1001234567890"` exactly (no munging, no quotes-stripping) | n/a |

**Assertions:**
- [ ] Request body's `chat_id` equals `"-1001234567890"` exactly

---

### TC0249: HTML-special chars in link text are escaped; link still works

**Type:** Unit | **Priority:** P1 | **Story:** US0021 (AC3, edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `"[A&B<C](https://x.com?q=1&r=2)"` | n/a |
| When | `commonmark_to_telegram_html(input)` | Returns `'<a href="https://x.com?q=1&amp;r=2">A&amp;B&lt;C</a>'` |
| Then | Both the link text AND the href are correctly escaped; the link tag is syntactically valid | n/a |

**Assertions:**
- [ ] Output exactly matches the expected string
- [ ] The output parses as valid HTML (e.g., via `html.parser`)

---

### TC0250: `ChannelRegistry` + `build_registry` signature

**Type:** Unit | **Priority:** P0 | **Story:** US0022 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.delivery.registry import ChannelRegistry, build_registry` | Imports succeed |
| When | `build_registry(subscribers_config, channels_config)` | Returns `ChannelRegistry` |
| Then | `registry.adapters` is a dict keyed by channel name; `registry.send_all(issue)` is callable | Pyright accepts the signature |

**Assertions:**
- [ ] `isinstance(registry.adapters, dict)`
- [ ] `callable(registry.send_all)`

---

### TC0251: Only enabled channels are constructed

**Type:** Unit (FakeChannel) | **Priority:** P0 | **Story:** US0022 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `channels.yaml` with `email.enabled: True, slack.enabled: False, telegram.enabled: True`; constructors spied | n/a |
| When | `build_registry(...)` | n/a |
| Then | `registry.adapters` has keys `{"email", "telegram"}`; SlackAdapter constructor was never called (its secret was never consulted) | n/a |

**Assertions:**
- [ ] `set(registry.adapters) == {"email", "telegram"}`
- [ ] Slack constructor spy recorded zero invocations

---

### TC0252: Channel construction failure → omitted with WARN

**Type:** Unit | **Priority:** P0 | **Story:** US0022 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | EmailAdapter constructor patched to raise `SmtpCredsError("SMTP_HOST missing")` | n/a |
| When | `build_registry(...)` with email enabled | Returns registry without email |
| Then | `"email" not in registry.adapters`; WARN log mentions email and `SmtpCredsError` | Other enabled adapters still present |

**Assertions:**
- [ ] `"email" not in registry.adapters`
- [ ] WARN log line emitted with `"email"` and the error class name

---

### TC0253: `send_all` dispatches to every adapter, returns one `SendReport` each

**Type:** Unit (FakeChannel) | **Priority:** P0 | **Story:** US0022 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Registry with three `FakeChannel` instances, each returning `SendReport(status="ok")` | n/a |
| When | `registry.send_all(issue)` | Returns `list[SendReport]` of length 3 |
| Then | Each fake's `send(issue, recipients)` was called once with the channel's configured recipients | n/a |

**Assertions:**
- [ ] `len(result) == 3`
- [ ] Every fake recorded exactly one `send()` call
- [ ] Every result `SendReport.status == "ok"`

---

### TC0254: Recipients deduplicated order-preserving before adapter call

**Type:** Unit | **Priority:** P1 | **Story:** US0022 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Subscribers config: `email: ["a@x.com", "b@x.com", "a@x.com"]`; FakeChannel records the recipients arg | n/a |
| When | `registry.send_all(issue)` | n/a |
| Then | The email adapter received `["a@x.com", "b@x.com"]` (first occurrence wins; order preserved); `SendReport.recipients_count == 2` | n/a |

**Assertions:**
- [ ] Fake email channel recorded `["a@x.com", "b@x.com"]` (exact list equality)

---

### TC0255: Adapter `send` raises → registry synthesises a `failed` SendReport

**Type:** Unit (FakeChannel) | **Priority:** P0 | **Story:** US0022 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | One FakeChannel whose `send` raises `RuntimeError("connection refused")`; two others return `ok` | n/a |
| When | `registry.send_all(issue)` | Returns list of 3 `SendReport`s |
| Then | The raising channel's `SendReport.status == "failed"`; `failures` contains one entry with `recipient="<all>"` and the error; other two are unchanged; `send_all` itself **does not raise** | n/a |

**Assertions:**
- [ ] `send_all` returns successfully (no exception)
- [ ] Raising channel's result has `status == "failed"` and `failure_count == recipients_count`
- [ ] The error appears in `failures[0].error`

---

### TC0256: All channels disabled → empty list, INFO log

**Type:** Unit | **Priority:** P1 | **Story:** US0022 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `channels.yaml` with all three disabled | n/a |
| When | `build_registry(...)`; `registry.send_all(issue)` | n/a |
| Then | `registry.adapters == {}`; `send_all(issue) == []`; one INFO log: "no channels enabled; nothing to send" | n/a |

**Assertions:**
- [ ] `registry.adapters == {}`
- [ ] `send_all(issue) == []`
- [ ] INFO log line emitted

---

### TC0257: Iteration order is stable across repeated `send_all` calls

**Type:** Unit (FakeChannel) | **Priority:** P1 | **Story:** US0022 (AC8)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Registry with three FakeChannels | n/a |
| When | `send_all` called 5 times in succession | n/a |
| Then | All 5 result lists have identical channel-name sequences (e.g., always `["email", "slack", "telegram"]`); matches the documented `ADAPTER_CLASSES` declaration order | n/a |

**Assertions:**
- [ ] All 5 result lists have identical `[r.channel for r in result]`
- [ ] That order matches the `ADAPTER_CLASSES` dict key order

---

### TC0258: Slack in subscribers but disabled in channels → recipients silently unused

**Type:** Unit | **Priority:** P2 | **Story:** US0022 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `subscribers.yaml` has 2 slack webhooks; `channels.yaml` has `slack.enabled: False` | n/a |
| When | `build_registry(...)`; `send_all(issue)` | n/a |
| Then | No slack adapter constructed; no error; `send_all` result has no slack entry | The 2 unused webhooks are not an error condition |

**Assertions:**
- [ ] No `SendReport` with `channel == "slack"` in the result
- [ ] No exception
- [ ] No WARN log about unused recipients (this is normal)

---

### TC0259: Email enabled but no email recipients → adapter constructed, `send([])` called, status "ok"

**Type:** Unit (FakeChannel) | **Priority:** P2 | **Story:** US0022 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `channels.yaml` has `email.enabled: True`; `subscribers.yaml` has no `email:` key | n/a |
| When | `send_all(issue)` | n/a |
| Then | Email adapter exists in `registry.adapters`; its `send` was called with `recipients=[]`; result includes `SendReport(channel="email", recipients_count=0, status="ok")` | n/a |

**Assertions:**
- [ ] Email adapter present
- [ ] Email adapter recorded `send(issue, [])`
- [ ] Result has email entry with `recipients_count == 0` and `status == "ok"`

---

### TC0260: Registry is reusable across multiple `send_all` calls

**Type:** Unit (FakeChannel) | **Priority:** P2 | **Story:** US0022 (edge — statelessness)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Registry with three FakeChannels | n/a |
| When | `send_all(issue_a)` followed by `send_all(issue_b)` followed by `send_all(issue_a)` again | All three calls succeed |
| Then | Each fake records 3 separate `send()` calls; results are independent; no state leaks between calls | n/a |

**Assertions:**
- [ ] Each FakeChannel recorded exactly 3 calls
- [ ] All 3 returned `SendReport` lists have the same structure
- [ ] No exception across the three calls

---

## Fixtures

```yaml
# tests/fixtures/delivery/subscribers_valid.yaml
subscribers_valid:
  email: ["alice@example.com", "bob@example.com"]
  slack: ["https://hooks.slack.com/services/T0/B0/X0"]
  telegram: ["-1001234567890", "987654321"]

# tests/fixtures/delivery/channels_valid.yaml
channels_valid:
  email:
    enabled: true
    from_name: "Tech-Letter for HYL"
    subject_template: "Tech-Letter Issue {{ issue_id }}"
  slack:
    enabled: true
  telegram:
    enabled: true
    parse_mode: "HTML"
    disable_web_page_preview: false

# tests/fixtures/delivery/issue_short.yaml — ~1000 chars, exercises no-split paths
# tests/fixtures/delivery/issue_medium.yaml — ~5000 chars, exercises 2-chunk splits
# tests/fixtures/delivery/issue_with_code_blocks.yaml — has a code block straddling a paragraph boundary
# tests/fixtures/delivery/issue_oversized_code_block.yaml — single 4000-char code block

# tests/fixtures/delivery/markdown_to_mrkdwn_cases.yaml — drives TC0222
markdown_to_mrkdwn_cases:
  - { input: "**bold**", expected: "*bold*" }
  - { input: "_italic_", expected: "_italic_" }
  - { input: "*italic*", expected: "_italic_" }
  - { input: "[t](https://x.com)", expected: "<https://x.com|t>" }
  - { input: "# H\n\nbody", expected: "*H*\n\nbody" }
  - { input: "## S", expected: "*S*" }
  - { input: "`x`", expected: "`x`" }
  - { input: "```\nx\n```", expected: "```\nx\n```" }
  - { input: "- bullet", expected: "- bullet" }
  - { input: "![alt](u)", expected: "<u|alt>" }

# tests/fixtures/delivery/markdown_to_telegram_cases.yaml — drives TC0237
markdown_to_telegram_cases:
  - { input: "&<>", expected: "&amp;&lt;&gt;" }
  - { input: "**bold**", expected: "<b>bold</b>" }
  - { input: "_italic_", expected: "<i>italic</i>" }
  - { input: "*italic*", expected: "<i>italic</i>" }
  - { input: "`x`", expected: "<code>x</code>" }
  - { input: "```\nx & <y>\n```", expected: "<pre>x &amp; &lt;y&gt;</pre>" }
  - { input: "# H\n\nbody", expected: "<b>H</b>\n\nbody" }
  # link cases omitted for brevity — TC0237 has them inline
```

**Hypothesis strategies** (defined in `tests/conftest.py`, not in the spec body):

- `markdown_safe_strategy` → drives TC0230
- `mixed_text_strategy` → drives TC0244
- `splittable_text_strategy` → drives TC0229, TC0243

---

## Automation Status

| TC | Title | Status | Implementation |
|----|-------|--------|----------------|
| TC0198 | ChannelAdapter protocol + SendReport surface | Pending | - |
| TC0199 | FailureDetail model | Pending | - |
| TC0200 | load_subscribers valid | Pending | - |
| TC0201 | Unknown channel key → ConfigLoadError | Pending | - |
| TC0202 | Per-channel recipient validation (parametric) | Pending | - |
| TC0203 | load_channels valid | Pending | - |
| TC0204 | Missing file → ConfigLoadError chained | Pending | - |
| TC0205 | FakeChannel protocol conformance | Pending | - |
| TC0206 | SendReport.status validator (parametric) | Pending | - |
| TC0207 | SendReport frozen | Pending | - |
| TC0208 | EmailAdapter protocol conformance | Pending | - |
| TC0209 | SmtpCreds.from_env — missing var parametric | Pending | - |
| TC0210 | SMTP_PORT default 587 | Pending | - |
| TC0211 | Jinja2 template loaded once, context shape | Pending | - |
| TC0212 | Markdown→plain-text stripper (parametric) | Pending | - |
| TC0213 | Multipart structure | Pending | - |
| TC0214 | One SMTP connection per batch (50 recipients) | Pending | - |
| TC0215 | Per-recipient 550 isolation | Pending | - |
| TC0216 | Empty recipients no-op | Pending | - |
| TC0217 | SMTP connect 2 fails then succeeds | Pending | - |
| TC0218 | SMTP connect 3 fails — status failed | Pending | - |
| TC0219 | Missing Jinja2 template → FileNotFoundError | Pending | - |
| TC0220 | Empty subject_template → fallback | Pending | - |
| TC0221 | SlackAdapter protocol conformance | Pending | - |
| TC0222 | commonmark_to_mrkdwn (parametric) | Pending | - |
| TC0223 | split_for_slack chunks ≤3500, paragraph boundaries | Pending | - |
| TC0224 | N×M POSTs in order | Pending | - |
| TC0225 | One webhook 404 → others proceed | Pending | - |
| TC0226 | 429 Retry-After respected | Pending | - |
| TC0227 | Empty Slack recipients no-op | Pending | - |
| TC0228 | Code block intact across splits | Pending | - |
| TC0229 | **Hypothesis: split_for_slack invariants** | Pending | - |
| TC0230 | **Hypothesis: commonmark_to_mrkdwn invariants** | Pending | - |
| TC0231 | 429 × 5 → webhook failed | Pending | - |
| TC0232 | Image markdown → link | Pending | - |
| TC0233 | Oversized code block → WARN + send | Pending | - |
| TC0234 | Short issue — no continued prefix | Pending | - |
| TC0235 | TelegramAdapter protocol conformance | Pending | - |
| TC0236 | from_env missing token → clear error | Pending | - |
| TC0237 | commonmark_to_telegram_html escape-first (parametric) | Pending | - |
| TC0238 | split_for_telegram ≤3900, never mid-tag | Pending | - |
| TC0239 | Per chat per chunk — payload shape | Pending | - |
| TC0240 | disable_web_page_preview flag (parametric) | Pending | - |
| TC0241 | 403 Forbidden mid-batch isolation | Pending | - |
| TC0242 | Empty Telegram recipients no-op | Pending | - |
| TC0243 | **Hypothesis: split_for_telegram invariants** | Pending | - |
| TC0244 | **Hypothesis: commonmark_to_telegram_html escape ordering** | Pending | - |
| TC0245 | 429 retry_after in body respected | Pending | - |
| TC0246 | 200 ok=false → failure | Pending | - |
| TC0247 | Bot token NEVER in logs | Pending | - |
| TC0248 | Negative chat id passes through | Pending | - |
| TC0249 | HTML-special chars in link text escaped | Pending | - |
| TC0250 | ChannelRegistry signature | Pending | - |
| TC0251 | Only enabled channels constructed | Pending | - |
| TC0252 | Construction failure → omitted + WARN | Pending | - |
| TC0253 | send_all dispatches to every adapter | Pending | - |
| TC0254 | Recipients deduplicated order-preserving | Pending | - |
| TC0255 | Adapter raises → synthesised failed report | Pending | - |
| TC0256 | All disabled → empty list + INFO | Pending | - |
| TC0257 | Iteration order stable | Pending | - |
| TC0258 | Slack disabled but subscribers present | Pending | - |
| TC0259 | Email enabled, no recipients | Pending | - |
| TC0260 | Registry reusable across calls | Pending | - |

---

## Test Files Plan

```text
tests/
  unit/
    delivery/
      test_base.py                  # TC0198, TC0199, TC0206, TC0207
      test_subscribers_config.py    # TC0200, TC0201, TC0202
      test_channels_config.py       # TC0203
      test_config_errors.py         # TC0204
      test_protocol_conformance.py  # TC0205 (pyright invocation)
      email/
        test_email_creds.py         # TC0209, TC0210
        test_email_stripper.py      # TC0212
      slack/
        test_mrkdwn_conversion.py   # TC0222, TC0232
        test_slack_splitter.py      # TC0223, TC0228, TC0234
        test_slack_property.py      # TC0229, TC0230
      telegram/
        test_telegram_escape.py     # TC0237, TC0249
        test_telegram_splitter.py   # TC0238
        test_telegram_property.py   # TC0243, TC0244
      registry/
        test_build_registry.py      # TC0250, TC0251, TC0252, TC0256
        test_send_all.py            # TC0253, TC0254, TC0255, TC0257
        test_registry_edges.py      # TC0258, TC0259, TC0260
  integration/
    delivery/
      email/
        test_smtp_aiosmtpd.py       # TC0208, TC0211, TC0213, TC0214, TC0215, TC0216, TC0219, TC0220
        test_smtp_retry.py          # TC0217, TC0218
      slack/
        test_slack_adapter.py       # TC0221, TC0224, TC0225, TC0226, TC0227, TC0231, TC0233
      telegram/
        test_telegram_adapter.py    # TC0235, TC0236, TC0239, TC0240, TC0241, TC0242, TC0245, TC0246, TC0248
        test_telegram_secret_leak.py # TC0247 (security)
  fixtures/
    delivery/
      subscribers_valid.yaml
      channels_valid.yaml
      issue_short.yaml
      issue_medium.yaml
      issue_with_code_blocks.yaml
      issue_oversized_code_block.yaml
      markdown_to_mrkdwn_cases.yaml
      markdown_to_telegram_cases.yaml
  conftest.py                       # Hypothesis strategies, aiosmtpd fixture, pytest-httpx defaults, frozen clock
```

**Per-module ≥95% line + branch floor** (TSD):

- `techletter/delivery/base.py` — exercised by `test_base.py` (validator branches)
- `techletter/delivery/slack.py::commonmark_to_mrkdwn` + `::split_for_slack` — exercised by example tests + hypothesis
- `techletter/delivery/telegram.py::commonmark_to_telegram_html` + `::split_for_telegram` — same
- `techletter/delivery/email.py::markdown_to_plaintext` — exercised by TC0212

**Hypothesis run profile:**

- Default `max_examples=200` for PR runs (~few seconds per property)
- A `slow` marker bumps to `max_examples=2000` for nightly; not part of the PR gate
- Each property test has a `deadline=None` (or a generous value); these are fast functions but hypothesis sometimes overcounts

---

## Traceability

| Artefact | Reference |
|----------|-----------|
| PRD | [sdlc-studio/prd.md](../prd.md) |
| Epic | [EP0004](../epics/EP0004-multichannel-delivery.md) |
| TSD | [sdlc-studio/tsd.md](../tsd.md) |
| Upstream | [TS0001](TS0001-content-ingestion.md) (sources), [TS0002](TS0002-composition-pipeline.md) (RenderedIssue), [TS0003](TS0003-orchestration-and-dx.md) (`SendRecord` audit) |
| Stories | [US0018](../stories/US0018-channel-adapter-protocol-and-config-loaders.md), [US0019](../stories/US0019-email-channel-adapter.md), [US0020](../stories/US0020-slack-channel-adapter.md), [US0021](../stories/US0021-telegram-channel-adapter.md), [US0022](../stories/US0022-channel-registry-and-send-aggregation.md) |

---

## Open Questions

_None._ Inherits all decisions from PRD v0.4.0, TRD v0.3.0, TSD v0.1.0, EP0004. The author-only smoke send to HYL's real channels (TSD-mandated, runs inside `draft.yml`) is the production E2E for this epic; it is owned by US0015's workflow YAML, not by any TC in this spec.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial spec authored from EP0004 stories US0018–US0022. 63 test cases across 38 ACs (full coverage). Includes 4 hypothesis property tests on splitters and escapers per TSD. |
| 2026-05-19 | HYL | Reviewed and promoted Draft → Ready: 38/38 ACs, 63 TCs incl. 4 hypothesis properties. **Notes for automation step:** (a) prefix TC0247's synthetic Telegram token with `TEST-FAKE-` so any leak into real logs is unmistakable; (b) author self-tests for the three hypothesis strategies (`markdown_safe_strategy`, `mixed_text_strategy`, `splittable_text_strategy`) — a strategy that doesn't generate what we expect silently weakens the property tests. |

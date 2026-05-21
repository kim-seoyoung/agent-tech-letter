# US0019: Email channel adapter (SMTP, HTML + plain-text multipart)

> **Status:** Done
> **Epic:** [EP0004: Multi-channel Delivery](../epics/EP0004-multichannel-delivery.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** the Researcher Subscriber
**I want** to receive the weekly issue as an email I can read inline
**So that** Tech-Letter for HYL fits into my normal Monday-morning inbox routine without me having to log into another tool.

## Context

### Persona Reference
**Researcher Subscriber** — direct beneficiary. They read on email; the rendering quality (HTML inline, clean fallback to plain text on minimal email clients) is what they notice.
[Persona details](../personas/stakeholders/users/researcher-subscriber.md)

**HYL (Author/Editor)** — wants delivery to "just work" so they don't have to babysit sends.

### Background
Email is the primary channel. SMTP via Gmail (or AWS SES later) is the v1 transport. Jinja2 template at `templates/email.html.j2` renders HTML; markdown is stripped to plain text for the multipart fallback. Per-recipient errors are isolated.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Protocol | Implements `ChannelAdapter` from US0018 | Adapter must be protocol-conformant |
| PRD | Transport | SMTP (Gmail / AWS SES); HTML + plain-text multipart | `EmailMessage` with both parts |
| PRD | Template | Jinja2 at `templates/email.html.j2` | Template loaded at adapter init |
| Epic | Failure isolation | Per-recipient try/except + log | Loop with per-iteration error handling |
| Epic | Reliability | tenacity-wrapped network calls | Decorator on the SMTP connect/send |
| TRD | Library | `smtplib` (stdlib) + `jinja2` | No alternative |

---

## Acceptance Criteria

### AC1: Adapter is discoverable and conformant
- **Given** the package `techletter.delivery.email` exists
- **When** an engineer imports `from techletter.delivery.email import EmailAdapter`
- **Then** `EmailAdapter(config: EmailConfig, smtp_creds: SmtpCreds)` is the constructor
- **And** `adapter.name == "email"` and `adapter.send(issue, recipients) -> SendReport` matches the `ChannelAdapter` protocol
- **And** pyright confirms protocol conformance

### AC2: SMTP credentials come from environment
- **Given** the construction-time `SmtpCreds` pydantic model
- **When** loaded from env vars
- **Then** these env vars are required: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`
- **And** `SMTP_PORT` is optional (default 587)
- **And** missing required vars cause `SmtpCredsError` at adapter construction (failed channel rather than runtime crash)

### AC3: HTML body rendered via Jinja2 template
- **Given** a `RenderedIssue` and the template `templates/email.html.j2`
- **When** `send` is called
- **Then** the HTML body is rendered with the template, receiving these context vars at minimum: `issue_id`, `markdown`, `meta`, `front_matter`
- **And** the template is loaded once at adapter init (not per-recipient) and cached

### AC4: Plain-text fallback rendered from markdown
- **Given** the `RenderedIssue.markdown`
- **When** `send` is called
- **Then** the plain-text body is the markdown text with light stripping:
  - Markdown headings → plain text on their own line
  - Markdown links `[text](url)` → `text (url)`
  - Markdown bold/italic → plain text (markers stripped)
  - Code fences → plain text inside, fences removed
- **And** the plain-text body is the `text/plain` part of the multipart message

### AC5: Multipart message structure
- **Given** the constructed `EmailMessage`
- **When** it is sent via SMTP
- **Then** the message has these MIME parts:
  - `text/plain; charset=utf-8` — the plain-text fallback
  - `text/html; charset=utf-8` — the rendered HTML
- **And** `From` = `SMTP_FROM`, `To` = single recipient, `Subject` = rendered from `EmailConfig.subject_template` (default: `"Tech-Letter Issue {issue_id}"`)
- **And** the body uses `multipart/alternative` so email clients pick the right part

### AC6: One SMTP connection per send batch
- **Given** the adapter sends to 50 recipients
- **When** `send` is called
- **Then** one SMTP connection is opened, 50 emails sent over it (one per recipient — *not* a single email to a BCC list — for privacy), then connection closed
- **And** if connection fails partway through, remaining recipients are logged as failures with a network-level error
- **And** the SMTP send is tenacity-wrapped (max 3 attempts on connect; per-recipient send is *not* retried inside one batch — a flaky recipient stays flaky for this run)

### AC7: Per-recipient failure isolation
- **Given** sending to 10 recipients where the 4th rejects with a 550 (mailbox not found)
- **When** `send` is called
- **Then** recipients 1–3 receive the email, recipient 4 is logged as failed, recipients 5–10 still receive the email
- **And** `SendReport.success_count == 9`, `failure_count == 1`, `status == "partial"`
- **And** `SendReport.failures` contains one entry: `{recipient: "alice@...", error: "SMTP 550: ..."}`

### AC8: Empty recipient list is a no-op
- **Given** `send` is called with `recipients=[]`
- **When** the adapter runs
- **Then** no SMTP connection is opened
- **And** `SendReport(recipients_count=0, success_count=0, failure_count=0, status="ok")` is returned

---

## Scope

### In Scope
- `techletter/delivery/email.py` defining `EmailAdapter`, `SmtpCreds`, `SmtpCredsError`.
- `templates/email.html.j2` Jinja2 template (initial version — simple, mobile-friendly HTML).
- Markdown → plain-text stripper.
- Subject-line templating from `EmailConfig.subject_template`.
- tenacity retries on SMTP-level errors.
- Unit tests against a fake SMTP server (e.g., `aiosmtpd`) or via stubbed `smtplib`.

### Out of Scope
- Open tracking pixels / link tracking (privacy-respecting newsletter).
- Bounce / complaint handling (SES feature, future CR if scale needs it).
- MJML or other email-specific rendering frameworks (PRD-decided: simple Jinja2 only).
- DKIM/SPF setup (documented in README, not code).
- Sending to BCC lists (PRD-decided: per-recipient sends, for privacy and personalisation).
- Per-recipient personalisation (e.g., `{{ recipient_name }}`) — out of scope for v1.

---

## Technical Notes

- Use `smtplib.SMTP_SSL` (port 465) or `SMTP` + `starttls()` (port 587). Gmail and SES both support 587; that's the default.
- The `EmailMessage` is built with `email.message.EmailMessage` (stdlib, Python 3.6+). Cleaner than `MIMEMultipart` for v1.
- Markdown stripper is a small helper. Could use `markdown` library to render-then-strip-HTML, but a pure-regex approach is enough for our markdown shape (no nested HTML, no tables, no math).
- The Jinja2 template should be designed for the *worst* clients (Outlook, Apple Mail dark mode). v1 keeps it minimal: max width 600px, inline styles for critical formatting, no JavaScript.
- `From` header uses `EmailConfig.from_name` + `SMTP_FROM`: `"Tech-Letter for HYL" <hyl@example.com>`.

### API Contracts
- `EmailAdapter(config: EmailConfig, smtp_creds: SmtpCreds)` — constructor.
- `send(issue: RenderedIssue, recipients: list[str]) -> SendReport`.
- `SmtpCreds.from_env() -> SmtpCreds` — class method to construct from env.

### Data Requirements
- Reads `templates/email.html.j2` at construction.
- Reads `SMTP_*` env vars at construction.
- Reads `EmailConfig` (passed in, sourced from `channels.yaml`).

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `SMTP_HOST` env var missing | `SmtpCredsError` at construction; channel skipped at runtime (registry handles) |
| SMTP `connect` fails (network down) | tenacity retries 3 times; on final failure, `SendReport.status="failed"`, `failures` lists all recipients as failed due to connection error |
| SMTP `auth` fails | All recipients fail with auth-error; status `"failed"` |
| One recipient address malformed (gets past schema validation somehow) | smtplib raises; caught per-recipient; logged as failure; others proceed |
| SMTP server rate-limits (e.g., Gmail's "550 5.4.5 Daily user sending limit exceeded") | First few recipients succeed, rest fail with the rate-limit error; status `"partial"` |
| Jinja2 template missing | Construction fails with `FileNotFoundError` |
| Jinja2 template has a syntax error | Caught at adapter init; raises descriptive error |
| Jinja2 template fails at render time (variable not provided) | Per-call error; entire send fails; `SendReport.status="failed"` with template error in `failures` (one row per recipient since none received the email) |
| `RenderedIssue.markdown` contains no headings | Plain-text body still renders; HTML body looks plain but valid |
| HTML body contains content that fails Outlook rendering | Acceptable for v1; HYL/subscribers can complain → switch to MJML as future CR |
| Recipient list has duplicates | Adapter sends to all (registry-level dedup is in US0022) |
| Template uses a context variable not provided | Jinja2 raises `UndefinedError`; tests catch this in the contract |
| Subject template renders to empty string | Use a fallback `"Tech-Letter Issue {issue_id}"` |
| TLS handshake fails (cert issues) | `ssl.SSLError`; tenacity retries; eventually failure |
| Recipient has a non-ASCII email (e.g., Cyrillic local part) | `EmailMessage` handles via IDNA; passes through |
| Issue body contains attachments-worth of inline images | None in v1 (markdown-text issues only); not a concern |

---

## Test Scenarios

- [ ] `EmailAdapter()` is a valid `ChannelAdapter` per pyright.
- [ ] Construction fails clean when `SMTP_HOST` is missing.
- [ ] Send to 3 fixture recipients via fake SMTP server → all 3 receive multipart messages with HTML + plain text parts.
- [ ] Plain-text body strips markdown markers correctly (`**bold**` → `bold`, `[link](url)` → `link (url)`, headings → bare text).
- [ ] Subject line rendered from template (`subject_template = "[TL] {{ issue_id }}"` → `[TL] 2026-05-19`).
- [ ] Send to 5 recipients where #3 rejects with 550 → `success_count=4`, `failure_count=1`, `status="partial"`.
- [ ] Empty recipient list → no SMTP connection, `status="ok"`.
- [ ] tenacity: simulate SMTP `connect` failing 2× then succeeding → final result is success.
- [ ] tenacity: simulate `connect` failing all 3 attempts → `status="failed"` with connection error.
- [ ] Jinja2 template missing → `FileNotFoundError` at adapter init.
- [ ] `EmailMessage.preamble` is `multipart/alternative` (or equivalent structural assertion).
- [ ] One SMTP connection per `send` call (verified by counting `smtplib.SMTP.__init__` invocations).

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0018](US0018-channel-adapter-protocol-and-config-loaders.md) | Schema | `ChannelAdapter` protocol, `SendReport`, `EmailConfig` | Draft |
| [US0011](US0011-compose-blog-quick-mentions-and-issue-assembly.md) | Schema | `RenderedIssue` model | Draft |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `jinja2` library | Library | Already added |
| `tenacity` library | Library | Already added |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` GitHub Secrets | Secrets | Must be set before send works |
| Optional `aiosmtpd` for test fake SMTP server | Test-only library | Added if useful |

---

## Estimation

**Story Points:** 5
**Complexity:** Medium. SMTP wiring is mechanical, but the multipart structure + Jinja2 template + plain-text stripper are three concerns sharing one story. Template iteration likely takes a couple of PR cycles before HYL is happy with rendering.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0004. |

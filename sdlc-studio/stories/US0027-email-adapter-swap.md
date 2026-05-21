# US0027: `EmailAdapter` swap (drop `_wrap_html`)

> **Status:** Ready
> **Epic:** [EP0005: Common HTML Rendering (Web + Email)](../epics/EP0005-common-html-rendering.md)
> **Change Request:** [CR-0001](../change-requests/CR0001-common-html-rendering.md) (Item 5)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-21
> **Promoted to Ready:** 2026-05-21 (RV0001)

## User Story

**As** the Researcher Subscriber
**I want** the email I receive each week to be the new properly-rendered HTML (US0026's output) — not the `<pre>`-wrapped raw markdown
**So that** the headline outcome of CR-0001 actually reaches my inbox.

## Context

### Persona Reference
**Researcher Subscriber** — primary. This is the story that flips the user-visible behavior.
**HYL** — secondary. Wants to ship the rendering work without breaking the privacy/idempotency contracts EP0004 already established.

### Background
US0026 produced `html_email.render(issue)`. This story rewires `EmailAdapter` (`techletter/delivery/email.py`) to call it instead of `_wrap_html`. The privacy invariant (no BCC, one MIME per recipient) is unchanged. The plain-text alternative still derives from `strip_markdown(body_md)`. The HTML body is computed **once per `send()`** and shared across all recipients (the SMTP loop must not call the renderer N times).

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| EP0004 TC0214 | Privacy | One MIMEMultipart per recipient; To header is the single recipient; no BCC | Unchanged — adapter loop structure preserved |
| EP0004 | SMTP | One SMTP connection per send pass | Unchanged |
| EP0005 AC | Perf | `html_email.render(issue)` called exactly once per `send()` | HTML body cached before the recipient loop |
| EP0004 | Plain-text fallback | `strip_markdown(body_md)` | Unchanged |
| US0026 | Renderer | `html_email.render(issue) -> str` available | Wire in this story |

---

## Acceptance Criteria

### AC1: `_wrap_html` is removed
- **Given** `techletter/delivery/email.py`
- **When** searched
- **Then** the symbol `_wrap_html` does NOT exist (not as method, not as function, not as import)
- **And** no `<pre>`-wrapping HTML construction logic remains in `EmailAdapter`

### AC2: HTML body comes from `html_email.render`
- **Given** `EmailAdapter.send(issue, recipients)` with `len(recipients) >= 1`
- **When** called
- **Then** `html_email.render(issue)` is invoked
- **And** the returned string is the `text/html` MIME part of every outgoing message

### AC3: Renderer called exactly once per `send()`
- **Given** `EmailAdapter.send(issue, recipients=[r1, r2, ..., r10])`
- **When** the adapter sends to all 10 recipients
- **Then** `html_email.render(issue)` is called exactly **1** time, not 10
- **And** the result is held in a local variable and reused per recipient
- **And** the test asserts via a spy/mock on the renderer that `call_count == 1`

### AC4: Privacy invariant preserved (TC0214)
- **Given** sending to multiple recipients
- **When** messages are sent
- **Then** each `EmailMessage.To` header contains exactly one recipient address
- **And** no `Cc:` or `Bcc:` headers are set on any message
- **And** the existing EP0004 privacy test for `EmailAdapter` still passes

### AC5: Plain-text alternative unchanged
- **Given** the constructed multipart message
- **When** inspected
- **Then** the `text/plain` part equals `strip_markdown(issue.body_md)` (same as EP0004)
- **And** the `text/html` part equals `html_email.render(issue)`
- **And** the MIME structure is `multipart/alternative` (plain first, then HTML, per RFC 2046 recommendation)

### AC6: SMTP loop structure preserved
- **Given** a fake SMTP server / in-process server
- **When** sending to 5 recipients
- **Then** exactly **1** SMTP connection is opened and closed
- **And** `smtp.send_message` is called exactly 5 times
- **And** per-recipient errors still isolate (EP0004 AC7 regression)

### AC7: SendReport stays correct
- **Given** sending to 5 where 1 fails with 550
- **When** `send` returns
- **Then** `SendReport.success_count == 4`, `failure_count == 1`, `status == "partial"`
- **And** the failure entry references the correct recipient

### AC8: Idempotency / `content_sha256` invariant
- **Given** an issue sent twice with the same `body_md`
- **When** `SendRecord` is appended
- **Then** `content_sha256` matches across runs (regression-pinned with golden hash)
- **And** the renderer change has not moved the hash

### AC9: Manual cross-client smoke check
- **Given** HYL configures `SMTP_*` env vars to a personal Gmail (or test) account
- **When** `uv run techletter send --issue issue-2026-05-21 --draft-path drafts/issue-2026-05-21.md` runs against a one-recipient `subscribers.yaml`
- **Then** the received email shows: properly typeset title, clickable links, rendered Markdown (no `**` or `##` visible), reasonable line-spacing on Gmail web and one mobile client
- **And** HYL captures a screenshot and adds it to the README per EP0005 AC

---

## Scope

### In Scope
- Edit `techletter/delivery/email.py`:
  - Delete `_wrap_html` method.
  - Import `html_email.render`.
  - Compute HTML body before the recipient loop.
- Update existing tests in `tests/delivery/test_email.py` that asserted on `_wrap_html` output (replace with assertions against the renderer mock and against MIME structure).
- Update existing fixtures if they depended on the old `<pre>` output shape.
- README screenshot of the new email (paired with the web screenshot from US0025/26).

### Out of Scope
- Changing the plain-text alternative (still `strip_markdown`).
- Changing SMTP connection logic, retry policy, error mapping.
- Slack or Telegram adapter changes.
- Adding new email-specific config (subject template, footer text, unsubscribe link) — separate future stories if needed.

---

## Technical Notes

- Diff sketch (illustrative, not normative):

  ```python
  # Before (email.py around line 124)
  html_body = self._wrap_html(issue.body_md)

  # After
  from techletter.delivery.renderers import html_email
  html_body = html_email.render(issue)
  ```

  The line moves nowhere — `send()` already computes HTML before the recipient loop (`email.py:124-126`). It's a one-line swap plus the import and the method deletion.

- Tests: change `_wrap_html` assertions to either:
  1. Mock `html_email.render` to a known string and assert MIME parts hold it; OR
  2. Use a real render and snapshot-assert the email body (golden coupling — only if we want CI to also enforce email body parity).

  Prefer #1 for unit; the golden fixture from US0026 already covers renderer output. The adapter unit test only needs to verify wiring + privacy + perf-cache (AC3).

- `from techletter.delivery.renderers import html_email` — top of module to keep import-time costs predictable; premailer initializes once per process.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `html_email.render` raises (template missing, bad input) | The adapter's existing top-level try/except surfaces it as `SendReport.status="failed"` with the error; SMTP connection not opened |
| `recipients = []` | Early return (existing EP0004 behavior); renderer is NOT called (no work to do) |
| SMTP failure mid-loop | Existing EP0004 isolation: remaining recipients still processed; HTML body already computed, no re-render needed |
| Plain-text strip output differs from previous run | Acceptable if `strip_markdown` is unchanged; this story does not touch it |
| Body large (≤102 KB cap from US0026) | SMTP send fine; no concern at our scale (≤100 recipients) |

---

## Test Scenarios

- [ ] `_wrap_html` symbol removed from module.
- [ ] `html_email.render` invoked once per `send()` regardless of recipient count (mock spy with `assert_called_once`).
- [ ] Each `EmailMessage.To` has exactly one address; no Cc/Bcc.
- [ ] `text/plain` part matches `strip_markdown(issue.body_md)`.
- [ ] `text/html` part matches the renderer output.
- [ ] Multipart structure is `multipart/alternative`.
- [ ] One SMTP connection per `send()` call; `send_message` invoked once per recipient.
- [ ] Per-recipient 550 → partial status, isolation preserved.
- [ ] `content_sha256` matches frozen golden hash (EP0004 regression).
- [ ] Manual smoke: HYL receives the email and visually verifies AC9; screenshot captured.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0026](US0026-html-email-renderer-and-premailer-inlining.md) | Implementation | `html_email.render(issue)` callable | Draft |
| [US0023](US0023-sidecar-json-persistence.md) | Schema | `RenderedIssue.deep_dives`/`.quick_mentions` non-empty when adapter receives the issue | Draft |

### External Dependencies

None new. `jinja2`, `markdown-it-py`, `premailer` are pulled in by US0024–US0026.

---

## Estimation

**Story Points:** 3
**Complexity:** Low for the code edit; the work is verifying nothing regresses against EP0004's existing tests (privacy, isolation, retries) and the manual cross-client smoke check. Plan one round of "ugh, Outlook" tweaks before declaring AC9 satisfied.

---

## Open Questions

- [ ] Should we ship a one-time "format has changed" banner in the first email after this lands? Not in scope here — call it out in the release commit message; subscribers will notice immediately.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | HYL | Story created from CR-0001 (Item 5) via `/sdlc-studio cr action`. |

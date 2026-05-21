# US0032: `SendRecord.published_url` + README setup + E2E smoke

> **Status:** Done
> **Epic:** [EP0006: GitHub Pages Publisher + Telegram Link Mode](../epics/EP0006-github-pages-and-telegram-link-mode.md)
> **Change Request:** [CR-0002](../change-requests/CR0002-github-pages-and-telegram-link-mode.md) (Item 5)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-21

## User Story

**As** HYL operating the pipeline
**I want** the `sends.jsonl` audit log to record the URL of each published page, and the README to walk me through the one-time GitHub Pages setup
**So that** I can trace any subscriber report back to a specific URL, and a future fork-of-this-project can be brought up with zero folklore.

## Context

### Persona Reference
**HYL** — primary. Operator + onboarder. Owns the one-time `gh-pages` orphan branch and Pages UI toggle.
**Researcher Subscriber** — indirect. Their bug reports ("link broken on 2026-05-21 issue") become resolvable via the audit log.

### Background
US0031 wires the publisher into the adapter. This last story closes the loop: the audit log captures the URL the bot just sent, and the README contains the one-time setup recipe so future operators don't have to reverse-engineer it. End-to-end smoke is HYL-owned but documented here as the exit gate.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| EP0003 | Audit | `sends.jsonl` is append-only; one record per (issue_id, channel) send | Add field, don't restructure |
| EP0003 | Schema | `SendRecord` is pydantic-validated; missing field on old records = backward compat | New field is `Optional[str] = None` |
| US0031 | Wiring | Adapter returns `SendReport`; no current path for `published_url` to reach `SendRecord` | Adapter's report or registry must surface the URL |
| EP0006 | Documentation | README is the operator's manual; new ops must succeed without reading source | One-time setup is a numbered recipe |

---

## Acceptance Criteria

### AC1: `SendRecord.published_url` field added
- **Given** the `SendRecord` pydantic model in `techletter/audit.py`
- **When** an engineer imports it
- **Then** it has a new optional field: `published_url: str | None = None`
- **And** `extra="forbid"` is preserved (no other fields snuck in)
- **And** existing JSONL records without this field still parse cleanly (`None` is the loaded value)

### AC2: `published_url` populated for `teaser_link` mode sends
- **Given** `mode="teaser_link"` and `publisher.publish(issue)` succeeds with `PublishResult.url = "https://..."`
- **When** `send` writes the `SendRecord` for the telegram channel
- **Then** the JSONL line includes `"published_url": "https://..."` for that record
- **And** the value matches the URL the bot put in the teaser message (cross-check possible)

### AC3: `published_url` is `null` (omitted or `None`) for `inline_html` mode and for non-publisher channels
- **Given** `mode="inline_html"` (legacy) OR a different channel (email, slack)
- **When** `SendRecord` is written
- **Then** `published_url` is `null` or absent
- **And** no spurious URL leaks into the field

### AC4: README documents one-time GitHub Pages setup
- **Given** `README.md`
- **When** a new operator reads the setup section
- **Then** the README contains a numbered "First-time GitHub Pages setup" recipe with:
  1. Create the orphan `gh-pages` branch (exact command)
  2. Push it to `origin`
  3. Enable Pages in the GitHub UI (`Settings → Pages → Source: gh-pages branch / root`)
  4. Verify `https://<user>.github.io/<repo>/` resolves (404 is fine until first publish)
  5. Set env vars (`GITHUB_REPO`, `TELEGRAM_BOT_TOKEN`, and the SMTP_* set if email is enabled)
  6. Update `channels.yaml` to enable `teaser_link` mode + `publisher: github_pages`
- **And** the section includes a clear note: "Pages on GitHub Free are world-readable. URL contains a 16-hex content hash, but is not authenticated."

### AC5: README documents the `channels.yaml` schema
- **Given** the README
- **When** a new operator looks for config docs
- **Then** the README contains an annotated example `channels.yaml` showing `publishers:` + per-channel `mode` + `publisher:` reference

### AC6: E2E smoke recipe documented (HYL-runnable)
- **Given** the README
- **When** HYL or any operator wants to verify the full flow
- **Then** the README has an "End-to-end verification" section with the exact commands:
  1. `uv run techletter draft --output-dir drafts/` — generates `.md` + `.json` sidecar
  2. Open PR, merge (or `cp drafts/<id>.md ...` for local-only)
  3. `uv run techletter send --issue <id> --draft-path drafts/<id>.md`
  4. Confirm in `logs/sends.jsonl`: latest telegram record has `published_url` set
  5. Open the URL in browser — page renders
  6. Check Telegram bot inbox — preview card visible, tappable

### AC7: E2E smoke executed at least once by HYL
- **Given** HYL has a real `TELEGRAM_BOT_TOKEN`, a configured `gh-pages` branch, push permissions, and a subscriber `chat_id`
- **When** HYL runs the recipe end-to-end
- **Then** a Telegram message arrives with a working link
- **And** the link opens a styled web page (EP0005 web template) in a browser
- **And** the `logs/sends.jsonl` line contains `published_url`
- **And** HYL adds a screenshot to the README (or marks AC7 as personally verified — manual sign-off)

### AC8: `sends.jsonl` schema documentation updated
- **Given** the README's "Audit log" section
- **When** the schema is described
- **Then** `published_url: string | null` is included in the field list with a short description

---

## Scope

### In Scope
- `techletter/audit.py`: add `SendRecord.published_url: str | None = None`.
- Wire `published_url` from `TelegramAdapter` to `SendRecord` write site. Concretely:
  - Adapter exposes `published_url` on the `SendReport` it returns (extend the existing `SendReport` model with an optional field), OR
  - The orchestrator/registry knows the URL via the publisher and threads it through.
  Lean on extending `SendReport` since the adapter is the natural source.
- `README.md` update: setup recipe + schema example + audit-log field doc + E2E smoke recipe.
- Manual E2E smoke owned by HYL (AC7).

### Out of Scope
- A `--verify-pages` flag that probes the URL post-publish.
- A backfill script that adds `published_url` to old records.
- Migrating Slack / Email channels to publishers (no need; they don't link).
- Custom domain documentation.

---

## Technical Notes

- **SendReport extension**: The cleanest path is to add an optional `published_url: str | None = None` to `SendReport` (the existing pydantic model in `delivery/base.py`). The Telegram adapter sets it on the report it returns. The orchestrator's `make_record(...)` helper forwards it into the `SendRecord`. No new arguments need to thread through.
- **README structure**: Add the new sections after the existing "Quick start" / before "Troubleshooting" (or wherever the project structure suggests). Keep the privacy note prominent — operators *will* be surprised that GitHub Free Pages are world-readable.
- **Snapshot test**: A snapshot/golden test of one JSONL line with `published_url` set + one without ensures both shapes parse stably.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Old `sends.jsonl` line without `published_url` | Parses cleanly with `published_url=None` |
| Publisher succeeds but Bot API call fails | `published_url` still recorded (the page IS live; audit reflects reality) |
| Publisher fails | `published_url` is None; `SendRecord.status="failed"` carries the publisher error |
| `inline_html` mode | `published_url` is None |
| README out-of-date with code (e.g., flag rename) | Operator confusion. Mitigation: smoke recipe in README must be the commands actually shipped; treat doc drift as a regression. |

---

## Test Scenarios

- [ ] `SendRecord(published_url="https://e.com")` constructs.
- [ ] Old JSONL line without `published_url` parses (loaded as None).
- [ ] After `teaser_link` mode send, the new JSONL line has `published_url` set to the publisher's URL.
- [ ] After `inline_html` mode send, the new JSONL line has `published_url` as null/None.
- [ ] After email/slack send, `published_url` is null/None.
- [ ] README contains the "First-time GitHub Pages setup" heading and 6 steps.
- [ ] README contains the privacy note about Pages being world-readable.
- [ ] HYL has run the E2E smoke at least once (manual sign-off in the story).

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0031](US0031-telegram-adapter-mode-and-publisher-wiring.md) | Wiring | Adapter must produce a URL to record | Draft |
| [US0028](US0028-publisher-protocol-and-publish-result.md) | Schema | `PublishResult.url` | Draft |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| Real `gh-pages` branch on `origin` | One-time setup | Documented in this story |
| HYL's actual `TELEGRAM_BOT_TOKEN`, subscriber `chat_id`, push creds | Runtime secrets | Operator-supplied for the smoke run |

---

## Estimation

**Story Points:** 2
**Complexity:** Low. The code edit is small (one optional field, one wiring path). The doc work is real but bounded. The E2E smoke (AC7) is HYL-owned and the only "soft" gate.

---

## Open Questions

- [ ] Should the README's E2E recipe live in a separate `docs/operations.md` to keep `README.md` tight? Lean **inline in README** for v1.2 — the project is small enough that splitting hurts discoverability.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | HYL | Story created from CR-0002 (Item 5) via `/sdlc-studio cr action`. |

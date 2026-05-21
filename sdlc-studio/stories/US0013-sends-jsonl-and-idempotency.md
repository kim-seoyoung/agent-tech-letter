# US0013: `logs/sends.jsonl` schema, append helper, and idempotency check

> **Status:** Done
> **Epic:** [EP0003: Orchestration & Developer Experience](../epics/EP0003-orchestration-and-dx.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** an append-only `logs/sends.jsonl` audit log with a typed `SendRecord` schema, a safe append helper, and an idempotency check that prevents the same (issue, channel) pair from sending twice
**So that** I have a permanent, searchable record of every send and the system cannot accidentally double-send if a workflow gets re-triggered.

## Context

### Persona Reference
**HYL (Author/Editor)** — explicit "auto-send without merge" red flag in persona. Idempotency is the second line of defense (the merge gate is the first). HYL would notice a duplicate send in their own inbox and lose trust in the system.
[Persona details](../personas/stakeholders/users/hyl-author.md)

### Background
The `SendRecord` schema is defined in TRD §6. This story owns its concrete implementation: a Python module that appends records, and a check function that filters out already-sent (issue, channel) pairs before fan-out. The log file itself is committed to `main` by US0016 (the send workflow).

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Storage | `logs/sends.jsonl` committed to `main`; append-only | Append helper does atomic appends; never rewrites the file |
| Epic | Idempotency | Same (issue_id, channel) never sends twice | `already_sent(issue_id, channel)` is the gate |
| TRD | Model | `SendRecord` per TRD §6 | Schema defined here matches exactly |
| TRD | Concurrency | Two send workflows could theoretically race | Append uses `O_APPEND` (atomic for the OS); the workflow uses concurrency group to serialise |

---

## Acceptance Criteria

### AC1: `SendRecord` model is defined
- **Given** the module `techletter.audit` exists
- **When** an engineer imports `from techletter.audit import SendRecord`
- **Then** `SendRecord` is a pydantic v2 model with these fields:
  - `issue_id: str` (format `YYYY-MM-DD`, validated)
  - `channel: Literal["email", "slack", "telegram"]`
  - `recipients_count: int` (≥ 0)
  - `success_count: int` (≥ 0)
  - `failure_count: int` (≥ 0)
  - `status: Literal["ok", "partial", "failed"]`
  - `timestamp: datetime` (tz-aware UTC, default `datetime.now(UTC)`)
  - `model_config = ConfigDict(frozen=True)` — records are immutable

### AC2: `append_send_record` writes one line per record
- **Given** the function `append_send_record(record: SendRecord, log_path: Path = Path("logs/sends.jsonl"))` exists
- **When** the function is called
- **Then** one JSON-encoded line is appended to the log file (`record.model_dump_json()` + `\n`)
- **And** the file is opened with `mode="a"` (atomic append on POSIX)
- **And** the function creates the parent directory if missing

### AC3: `already_sent` check
- **Given** the function `already_sent(issue_id: str, channel: str, log_path: Path = ...) -> bool` exists
- **When** the function is called with a (issue_id, channel) pair that appears in any record in the log with `status` in `{"ok", "partial"}`
- **Then** the function returns `True`
- **And** when no such record exists, or the only matching record has `status="failed"`, returns `False`
- **And** when the log file doesn't exist, returns `False` (no-op for first run)

### AC4: `load_records` reads the full log
- **Given** the function `load_records(log_path: Path = ...) -> list[SendRecord]` exists
- **When** the function is called
- **Then** all lines in the log are parsed into `SendRecord`s
- **And** lines that fail to parse (corrupt JSON or schema mismatch) are skipped with a WARN log; remaining records returned
- **And** an empty or missing file returns `[]`

### AC5: Failed sends do not block retry
- **Given** a previous run appended a `SendRecord` with `status="failed"` for (issue=`2026-05-19`, channel=`email`)
- **When** `already_sent("2026-05-19", "email")` is called
- **Then** the function returns `False` — failed sends can be retried
- **And** a successful retry appends a new `SendRecord` (the failed record is preserved as history)

### AC6: Partial sends are treated as completed
- **Given** a `SendRecord` with `status="partial"` (some recipients succeeded, some failed)
- **When** `already_sent(...)` is called for the same (issue, channel)
- **Then** returns `True` — we do not retry partial sends because that would re-send to the recipients who already received it
- **And** the partial-failure recipients are surfaced in workflow logs and the operator (HYL) decides whether to manually re-send to specific addresses (out of scope for v1; future CR).

### AC7: Schema validation on append
- **Given** an attempt to append a malformed `SendRecord` (e.g., negative `success_count`)
- **When** the model is constructed
- **Then** pydantic raises `ValidationError`
- **And** the append never happens (no half-written line)

---

## Scope

### In Scope
- `techletter/audit.py` defining `SendRecord`, `append_send_record`, `already_sent`, `load_records`.
- `logs/sends.jsonl` initial file (empty / one-line header optional — prefer empty).
- Unit tests covering: model validation, append + reload round-trip, idempotency check across all three statuses, missing/empty file behaviour, corrupt-line tolerance.

### Out of Scope
- Concurrency lock between processes — the GitHub Actions concurrency group (US0016) serialises sends; in-process append uses `O_APPEND` atomicity. No file locks beyond OS guarantees in v1.
- Retention / rotation — `sends.jsonl` grows ~52 lines/year at 3 channels; small. Revisit if it grows past 10k lines.
- Resending to *specific failed recipients* within a `partial` send — manual operation in v1.

---

## Technical Notes

- `SendRecord.model_dump_json()` produces a stable JSON form (pydantic v2 default). One record per line.
- `already_sent` reads the full log on each call. At our scale (≤ thousands of lines), this is microseconds. If it ever becomes a bottleneck, add an in-memory index — premature for v1.
- The "failed → retry, partial → don't retry" semantics is the trickiest piece of the spec and worth a dedicated unit test.

### API Contracts
- `SendRecord.model_validate(dict) -> SendRecord`
- `append_send_record(record, log_path) -> None`
- `already_sent(issue_id, channel, log_path) -> bool`
- `load_records(log_path) -> list[SendRecord]`

### Data Requirements
`logs/sends.jsonl` — append-only file, committed to `main`. Schema validated on read and write.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Log file missing | `already_sent` returns `False`; `load_records` returns `[]`; `append_send_record` creates the file and its parent dir |
| Log file contains a corrupt line (e.g., truncated JSON) | `load_records` logs WARN, skips that line, returns the rest |
| Log file is empty | `load_records` returns `[]`; first append starts a clean file |
| Concurrent appends from two processes (rare; concurrency group should prevent in CI) | OS `O_APPEND` guarantees no torn writes; both records land cleanly |
| `SendRecord` with `recipients_count=0` | Valid (channel was enabled but had no recipients) |
| Many records for same (issue, channel) — e.g., many retry attempts | `already_sent` walks them all; finds the most-recent `ok`/`partial` and returns True |
| `timestamp` already set explicitly | Used as-is |
| `timestamp` not provided | Default factory sets `datetime.now(UTC)` |
| `channel` value is not one of the three allowed | `ValidationError` |
| Attempt to mutate a `SendRecord` after construction | `ValidationError` (frozen) |
| File contains records from a future schema version | Unknown fields ignored by pydantic if `extra="ignore"` (default); model is forward-compatible enough for v1 |

---

## Test Scenarios

- [ ] Construct + append + load round-trip → fields match.
- [ ] Construct with `recipients_count = -1` → `ValidationError`.
- [ ] Construct with `channel = "discord"` → `ValidationError`.
- [ ] Frozen: `record.status = "ok"` → raises.
- [ ] `already_sent` returns `True` after an `ok` record.
- [ ] `already_sent` returns `True` after a `partial` record.
- [ ] `already_sent` returns `False` after only `failed` records.
- [ ] `already_sent` returns `False` when no records exist.
- [ ] `load_records` skips corrupt lines, returns rest.
- [ ] `append_send_record` creates parent dir if missing.
- [ ] Two records appended sequentially → both readable as separate lines.
- [ ] Type check: module passes pyright.

---

## Dependencies

### Story Dependencies
_None._ This is the simplest story in EP0003 — independent of CLI scaffolding.

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `pydantic` v2 | Library | Already added (US0001) |

---

## Estimation

**Story Points:** 3
**Complexity:** Low. The interesting behaviour is the failed-vs-partial-vs-ok semantics in `already_sent`. Worth a careful unit test.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0003. |

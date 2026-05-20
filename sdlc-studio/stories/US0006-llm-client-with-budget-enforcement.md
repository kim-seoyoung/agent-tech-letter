# US0006: LLM client wrapper with token counting and budget enforcement

> **Status:** Draft
> **Epic:** [EP0002: Composition Pipeline](../epics/EP0002-composition-pipeline.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a thin LLM client wrapper around the Anthropic SDK that counts tokens, enforces a 200K per-run budget, and aborts *before* the compose step if projected usage would exceed it
**So that** a runaway week (flood of items, regressed prompt) cannot quietly burn LLM credits and a single budget knob is the lever that bounds my monthly cost.

## Context

### Persona Reference
**HYL (Author/Editor)** — explicit "unbounded cost surface" red flag in their persona. This story is the load-bearing mitigation for that concern.
[Full persona details](../personas/stakeholders/users/hyl-author.md)

### Background
Every LLM call in EP0002 (cluster, rank, compose-paper, compose-repo, compose-blog) goes through this wrapper. The wrapper is also responsible for the *projected* budget check before the compose step starts — once compose begins, several calls happen in quick succession and aborting mid-compose leaves a half-finished issue. Better to abort before compose with a clean failure.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Cost | 200K token budget per run; abort before compose if projected to exceed | Pre-flight check before compose phase, not just per-call accounting |
| Epic | Reliability | tenacity-wrapped LLM calls; abort run if unrecoverably down | tenacity decorator around the SDK call; 3–5 retries |
| TRD | Provider | Anthropic Claude Sonnet-class (e.g., `claude-sonnet-4-6`) | SDK is `anthropic`; model id is configurable |
| TRD | Pluggable | Abstracted behind internal interface for future provider swap | Wrapper exposes a provider-neutral surface (`generate(...)`), not Anthropic-specific |
| TRD | Observability | Token usage per run is logged | Each call appends to a usage ledger held in the wrapper instance |

---

## Acceptance Criteria

### AC1: Public surface is provider-neutral
- **Given** the module `techletter.llm.client` exists
- **When** an engineer imports `from techletter.llm.client import LlmClient`
- **Then** `LlmClient(budget_tokens: int = 200_000, model: str = "claude-sonnet-4-6")` is the constructor
- **And** the public method is `generate(prompt: str, *, max_output_tokens: int, response_format: Literal["text","json"] = "text") -> LlmResponse`
- **And** `LlmResponse` is a dataclass/pydantic model with `text: str`, `input_tokens: int`, `output_tokens: int`

### AC2: Per-call token usage is recorded
- **Given** an `LlmClient` instance has been used for two `generate()` calls returning `(in=1000, out=500)` and `(in=2000, out=300)`
- **When** the caller reads `client.usage`
- **Then** the returned object has `input_tokens_used == 3000`, `output_tokens_used == 800`, `total_tokens_used == 3800`

### AC3: Pre-compose budget check (the headline guard)
- **Given** the wrapper exposes `client.check_budget(projected_additional_tokens: int) -> None`
- **When** `total_tokens_used + projected_additional_tokens > budget_tokens` is true
- **Then** the call raises `BudgetExceededError` with a message like `"projected 215000 > budget 200000 (used: 90000, projected additional: 125000)"`
- **And** when the projection fits, the call returns `None` silently

### AC4: Caller signals "about to compose"
- **Given** the pipeline reaches the boundary between rank and compose
- **When** the orchestrator calls `client.check_budget(projected_additional_tokens=N)` where N is the rank step's estimate of compose token use
- **Then** if N fits, compose proceeds
- **And** if N doesn't fit, the run aborts with a clear log line *before* any compose call is made

### AC5: tenacity retries on transient failures
- **Given** the Anthropic API returns a `RateLimitError` (HTTP 429) on the first 2 attempts and succeeds on the 3rd
- **When** `generate()` is called
- **Then** tenacity retries with exponential backoff (1s, 2s, 4s, +/- jitter; max 5 attempts)
- **And** the returned response is from the successful attempt
- **And** each retry attempt is logged with the attempt number and error type

### AC6: Unrecoverable failure raises
- **Given** the Anthropic API returns 429 on all 5 retry attempts
- **When** `generate()` is called
- **Then** the wrapper raises `LlmUnavailableError` (chained from the underlying SDK exception)
- **And** the calling pipeline can decide whether to abort the run (per ADR-004, the compose-step failure aborts; the cluster-step failure aborts; rank-step failure aborts)

### AC7: Usage ledger is emitted at end of run
- **Given** the pipeline finishes (success or abort)
- **When** the orchestrator calls `client.usage_report() -> dict`
- **Then** the returned dict has at minimum: `model`, `budget_tokens`, `input_tokens_used`, `output_tokens_used`, `total_tokens_used`, `budget_remaining`, `calls: list[CallSummary]`
- **And** this report is suitable for inclusion in `RenderedIssue.meta` and for logging at workflow end

---

## Scope

### In Scope
- `techletter/llm/client.py` defining `LlmClient`, `LlmResponse`, `LlmUsage`, `BudgetExceededError`, `LlmUnavailableError`.
- tenacity decorator on the network call.
- Token counting: uses the Anthropic SDK's `count_tokens()` for input estimation and the response object's `usage` field for actual counts post-call.
- Logging at INFO for each call (model, input tokens, output tokens, duration); WARN for retries; ERROR for permanent failures.
- Unit tests against a fake Anthropic client.

### Out of Scope
- Prompt management itself — prompts live in `prompts/*.md` and are loaded by the steps that use them (US0007–US0011).
- Streaming responses — v1 uses synchronous `generate()`.
- Tool-use / multi-turn conversations — single-turn `generate()` is sufficient for cluster/rank/compose.
- Prompt caching (Anthropic feature) — out of scope for v1; revisit when iteration patterns suggest it'd cut costs.
- A second provider — pluggable interface is designed for it; implementation is not.

---

## Technical Notes

- Provider neutrality is achieved by keeping the public surface free of Anthropic-specific types. Internally, `LlmClient` holds an `anthropic.Anthropic()` instance; swapping providers later means subclassing or replacing this attribute.
- The default model id (`claude-sonnet-4-6`) is exposed in `pyproject.toml` config or env (`LLM_MODEL`) so the model can be pinned per run without code changes.
- `usage_report()` is the bridge to TRD §6 `RenderedIssue.meta` — the orchestration layer (EP0003) writes this dict into the front matter.
- The 200K budget is a project-level default. Stored in `config/llm.yaml` or env (`LLM_BUDGET_TOKENS`), overridable per run for backfill / catch-up scenarios.

### API Contracts
- `LlmClient(budget_tokens, model)` — constructor.
- `generate(prompt, *, max_output_tokens, response_format) -> LlmResponse` — main call.
- `check_budget(projected_additional_tokens)` — pre-flight guard; raises on overage.
- `usage_report() -> dict` — end-of-run ledger.
- `LlmResponse(text, input_tokens, output_tokens)` — return type.
- `BudgetExceededError(Exception)` — raised by `check_budget`.
- `LlmUnavailableError(Exception)` — raised after retry exhaustion.

### Data Requirements
No persistent storage. Per-run state held in the `LlmClient` instance; logged at end of run.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `budget_tokens` ≤ 0 | `ValueError` at construction |
| First call already projected to exceed budget (e.g., a 250K-token cluster prompt with budget 200K) | `check_budget` (if called pre-flight) raises; if generate is called directly, it makes the call and exceeds — caller is responsible for pre-flight |
| `generate()` returns a response with `output_tokens = 0` (model produced empty string) | Returned as-is; caller decides whether empty is acceptable |
| `max_output_tokens` is None or 0 | `ValueError` — caller must specify; we don't pick a default for them |
| Network timeout mid-call | tenacity retries; final timeout surfaces as `LlmUnavailableError` |
| Token counter (`count_tokens`) returns a number meaningfully different from actual post-call tokens | Usage ledger uses the post-call actual numbers; `check_budget` uses the estimate, which is acceptable as a heuristic guard (some slack is fine) |
| `usage_report()` called before any `generate()` | Returns a report with zero-valued fields; not an error |
| Multiple `LlmClient` instances in the same process | Each tracks its own usage; project pattern is one client per run |
| API key missing (`ANTHROPIC_API_KEY` unset) | SDK raises at first call; wrapper propagates as `LlmUnavailableError` with a clear message |
| Model id not recognised by Anthropic | SDK 400 response; wrapper propagates after retries exhaust (no point retrying a 400) |
| Concurrency: `generate()` called from two threads on same client | Usage ledger updates must be threadsafe — use a `Lock`; in practice v1 is single-threaded, but the test exercises this |
| `response_format="json"` and model returns invalid JSON | Wrapper returns the raw text; caller is responsible for JSON parsing and its own error handling |

---

## Test Scenarios

- [ ] Two `generate()` calls accumulate correctly in `usage.total_tokens_used`.
- [ ] `check_budget(50_000)` after 160K tokens used raises `BudgetExceededError`.
- [ ] `check_budget(30_000)` after 160K tokens used returns silently.
- [ ] Mock 429 × 2 + 200 → call succeeds with retries logged.
- [ ] Mock 429 × 5 → `LlmUnavailableError` raised.
- [ ] Mock 400 (bad model id) → no retries, immediate raise.
- [ ] `usage_report()` returns expected dict shape with all required fields.
- [ ] `budget_tokens=0` at construction → `ValueError`.
- [ ] `max_output_tokens=0` at `generate()` → `ValueError`.
- [ ] Two-thread concurrent `generate()` → no lost updates to usage ledger.
- [ ] Type check: `LlmClient` and `LlmResponse` are typed; pyright passes.

---

## Dependencies

### Story Dependencies
_None._ This is the foundational story for EP0002.

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `anthropic` Python SDK | Library | Added in this story |
| `tenacity` library | Library | Already added (US0002 / EP0001) |
| `ANTHROPIC_API_KEY` GitHub Secret | Secret | Required for live calls; not needed for unit tests |

---

## Estimation

**Story Points:** 3
**Complexity:** Low-Medium. SDK wrapping is mechanical. The interesting bit is `check_budget`'s projection logic — needs to be a clean separable function.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0002. |

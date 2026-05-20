# TS0002: Composition Pipeline

> **Status:** Ready
> **Epic:** [EP0002: Composition Pipeline](../epics/EP0002-composition-pipeline.md)
> **Created:** 2026-05-19
> **Last Updated:** 2026-05-19
> **TC Range:** TC0056–TC0125

## Overview

Test specification for EP0002 — the editorial intelligence of the pipeline. Six stories cover the LLM client wrapper (with the 200K-token budget guard), the cluster step, the rank step (`item_kind`-aware), three compose prompts (paper / repo / blog), the batch quick-mention composer, and the `RenderedIssue` assembler.

This is the epic where the **`FakeLLMClient` stub** from the [TSD](../tsd.md) pays its rent: every cluster, rank, and compose test runs against canned JSON fixture responses. No live Anthropic API call is made in CI. One optional nightly job (`RUN_LIVE_LLM_TESTS=1`, gated and bounded to ≤10K tokens) catches prompt drift against the real model — that job is not part of the per-PR test suite and is intentionally not in this spec's automation table.

The TSD's tiered coverage targets apply with extra force here:

- **`techletter.llm.client`** (US0006), **`techletter.pipeline.cluster`** (parsing), **`techletter.pipeline.rank`** (sort + budget math), **`techletter.pipeline.compose.format_shipping_signals`** (US0010), **`techletter.pipeline.assemble`** (US0011 — pure rendering, no LLM) → all held to ≥95% line + branch (pure helpers tier).
- Adapter-shell code that just dispatches into the LLM and parses → held to the ≥85% overall floor.

## Scope

### Stories Covered

| Story | Title | Priority |
|-------|-------|----------|
| [US0006](../stories/US0006-llm-client-with-budget-enforcement.md) | LLM client + budget enforcement | P0 (foundation for the epic) |
| [US0007](../stories/US0007-cluster-prompt-and-step.md) | Cluster prompt + step | P0 |
| [US0008](../stories/US0008-rank-prompt-and-step.md) | Rank prompt + step (`item_kind`-aware) | P0 |
| [US0009](../stories/US0009-compose-prompt-for-paper-items.md) | Compose prompt for `paper` items | P0 |
| [US0010](../stories/US0010-compose-prompt-for-repo-items.md) | Compose prompt for `repo` items | P0 |
| [US0011](../stories/US0011-compose-blog-quick-mentions-and-issue-assembly.md) | Compose blog + quick mentions + `RenderedIssue` assembly | P0 |

### AC Coverage Matrix

| Story | AC | Description | Test Cases | Status |
|-------|-----|-------------|------------|--------|
| US0006 | AC1 | `LlmClient` constructor and `generate()` public surface | TC0056 | Covered |
| US0006 | AC2 | Per-call token usage accumulates | TC0057 | Covered |
| US0006 | AC3 | `check_budget` raises on projected overage | TC0058 | Covered |
| US0006 | AC4 | Pre-compose `check_budget` gate (boundary + caller use) | TC0059, TC0060 | Covered |
| US0006 | AC5 | Tenacity retries on transient (429) | TC0061 | Covered |
| US0006 | AC6 | Unrecoverable failure → `LlmUnavailableError` | TC0062 | Covered |
| US0006 | AC7 | `usage_report()` dict shape | TC0063 | Covered |
| US0007 | AC1 | `Cluster` model + `cluster_items` step defined | TC0070 | Covered |
| US0007 | AC2 | Single LLM call; prompt loaded from `prompts/cluster.md` | TC0071 | Covered |
| US0007 | AC3 | Per-item representation truncated in prompt | TC0072 | Covered |
| US0007 | AC4 | Clusters span multiple `item_kind`s | TC0073 | Covered |
| US0007 | AC5 | No item lost; no item duplicated across clusters | TC0074, TC0075 | Covered |
| US0007 | AC6 | Empty input → `[]` without LLM call | TC0076 | Covered |
| US0007 | AC7 | Cluster count outside [3, 30] → WARN, return anyway | TC0077 | Covered |
| US0008 | AC1 | `rank_clusters` + `RankedClusters` defined | TC0080 | Covered |
| US0008 | AC2 | Significance + novelty populated for every scored cluster | TC0081 | Covered |
| US0008 | AC3 | Prompt explicitly carries 3 rubrics (paper / repo / blog) | TC0082 | Covered |
| US0008 | AC4 | Deterministic selection by score with stable tiebreak | TC0083 | Covered |
| US0008 | AC5 | `rationale_by_cluster_id` populated for every selected cluster | TC0084 | Covered |
| US0008 | AC6 | Novelty hedge instructions present in prompt | TC0085 | Covered |
| US0008 | AC7 | Fewer clusters than target → all distributed, no error | TC0086 | Covered |
| US0009 | AC1 | `compose_paper_deep_dive` + `DeepDive` model | TC0091 | Covered |
| US0009 | AC2 | `prompts/compose-paper.md` carries 4-section + anti-hype structure | TC0092 | Covered |
| US0009 | AC3 | Output body contains all four sections | TC0093 | Covered |
| US0009 | AC4 | All contributing items cited | TC0094 | Covered |
| US0009 | AC5 | Production-reality line conditional on signal | TC0095 | Covered |
| US0009 | AC6 | Anti-hype enforced by retry-once + ban list constant | TC0096, TC0097 | Covered |
| US0009 | AC7 | Empty/malformed response → retry → `ComposeParseError` | TC0098 | Covered |
| US0010 | AC1 | `compose_repo_deep_dive` + `maturity_summary` | TC0101 | Covered |
| US0010 | AC2 | `prompts/compose-repo.md` carries 3-section + shared anti-hype | TC0102 | Covered |
| US0010 | AC3 | Output cites concrete shipping signals (numbers, dates) | TC0103 | Covered |
| US0010 | AC4 | `maturity_summary` is a single sentence; "unclear" path | TC0104 | Covered |
| US0010 | AC5 | Mixed-kind cluster routed to repo compose cites all URLs | TC0105 | Covered |
| US0010 | AC6 | Anti-hype lint reuses US0009's `BANNED_HYPE_WORDS` constant | TC0106 | Covered |
| US0010 | AC7 | Empty/malformed → retry → `ComposeParseError` | TC0107 | Covered |
| US0011 | AC1 | `compose_blog_deep_dive` defined | TC0110 | Covered |
| US0011 | AC2 | `prompts/compose-blog.md` 3-section structure | TC0111 | Covered |
| US0011 | AC3 | `compose_quick_mentions` is a batch (single-call) compose | TC0112 | Covered |
| US0011 | AC4 | `RenderedIssue` model + `assemble_issue` function | TC0113 | Covered |
| US0011 | AC5 | Assembled markdown has all required sections in order | TC0114 | Covered |
| US0011 | AC6 | `issue_id` is today's UTC date | TC0115 | Covered |
| US0011 | AC7 | Per-item `item_kind` + `maturity` indicators rendered; unknown omitted | TC0116 | Covered |
| US0011 | AC8 | Deep-dive count flexes 2–5; no padding, no truncation | TC0117 | Covered |
| US0011 | AC9 | Quick-mention count < 10 tolerated; section heading honest | TC0118 | Covered |

**Coverage:** 44 / 44 ACs covered. **Uncovered: 0.** Spec eligible to move Draft → Ready.

### Test Types Required

| Type | Required | Rationale |
|------|----------|-----------|
| Unit | Yes | Budget math (US0006), JSON parse + invariants (US0007/US0008), shipping-signal formatter (US0010), pure markdown assembly (US0011) — all deterministic without LLM in the loop |
| Integration (stubbed LLM) | Yes | Every cluster/rank/compose path is exercised via `FakeLLMClient`. The "integration" here is *internal* — pipeline stage wired to an LLM-interface stub. No HTTP. |
| Integration (live LLM) | No (out of scope for this spec) | Gated nightly job per EP0002 test plan, not part of PR test suite |
| E2E | No | TSD's `tests/pipeline/test_full_run.py` covers the full compose path end-to-end with stubbed sources + stubbed LLM; not duplicated here |

---

## Environment

| Requirement | Details |
|-------------|---------|
| Prerequisites | Python 3.11+, pytest ≥ 8.0, pytest-cov, hypothesis, freezegun, `anthropic` SDK installed but **never called** in CI |
| External Services | **None.** All LLM I/O routed through `FakeLLMClient`. |
| Test Data | Canned `FakeLLMClient` response fixtures under `tests/fixtures/llm/` — one JSON file per scenario (valid cluster, malformed cluster, paper compose, repo compose with full signals, repo compose with missing signals, quick-mention batch of 10, etc.) |
| Clock | Default frozen at `2026-05-19T00:00:00Z` (`freezegun`) so `issue_id` is deterministic |
| Env vars | `ANTHROPIC_API_KEY` is **not** set during the test suite. TC0069 monkeypatches it to assert clean handling. The TSD's secret-leak grep applies to every test run. |

### The `FakeLLMClient` interface

Every test that touches the LLM uses this stub instead of the real `LlmClient`. The stub:

- Implements the same public surface (`generate()`, `check_budget()`, `usage_report()`, `usage`).
- Holds a FIFO queue of canned `LlmResponse` objects + side-effects (raise X on Nth call).
- Records every call (prompt verbatim, `max_output_tokens`, `response_format`) for post-test inspection.
- Counts tokens *deterministically* by character heuristic so budget math is testable (not the real tokenizer).

The stub itself is unit-tested separately as part of `tests/conftest.py` setup; it is not in scope for this spec but the contract above is the assumption every TC below relies on.

---

## Test Cases

### TC0056: `LlmClient` constructor and `generate()` signature match the documented surface

**Type:** Unit | **Priority:** P0 | **Story:** US0006 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.llm.client import LlmClient, LlmResponse` | Import succeeds |
| When | `client = LlmClient(budget_tokens=200_000, model="claude-sonnet-4-6")`; call `client.generate(prompt="hi", max_output_tokens=10, response_format="text")` against a stubbed Anthropic SDK | Returns `LlmResponse` |
| Then | Returned object has `.text: str`, `.input_tokens: int`, `.output_tokens: int` | Pyright accepts the dataclass shape |

**Assertions:**
- [ ] `response.text` is a string
- [ ] `response.input_tokens >= 0` and `response.output_tokens >= 0`
- [ ] Pyright `--outputjson` on a small module that uses the public surface reports 0 errors

---

### TC0057: Two successive `generate()` calls accumulate into `client.usage`

**Type:** Unit | **Priority:** P0 | **Story:** US0006 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Anthropic SDK stubbed to return `(in=1000,out=500)` then `(in=2000,out=300)` | n/a |
| When | `client.generate(...)` is called twice | Two responses |
| Then | `client.usage.input_tokens_used == 3000`, `client.usage.output_tokens_used == 800`, `client.usage.total_tokens_used == 3800` | n/a |

**Assertions:**
- [ ] `client.usage.input_tokens_used == 3000`
- [ ] `client.usage.output_tokens_used == 800`
- [ ] `client.usage.total_tokens_used == 3800`

---

### TC0058: `check_budget` raises `BudgetExceededError` with the projected number

**Type:** Unit | **Priority:** P0 | **Story:** US0006 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Client with `budget_tokens=200_000` and 90K tokens already used (from prior stubbed calls) | n/a |
| When | `client.check_budget(projected_additional_tokens=125_000)` | Raises `BudgetExceededError` |
| Then | Error message includes both the projected total (`215000`) and the budget (`200000`) | `__cause__` is None (this is a planned abort, not a chained failure) |

**Assertions:**
- [ ] `pytest.raises(BudgetExceededError)` succeeds
- [ ] Message contains `"215000"` and `"200000"`
- [ ] Message also contains `"90000"` (used) and `"125000"` (projected additional)

---

### TC0059: `check_budget` returns silently when projection fits

**Type:** Unit | **Priority:** P0 | **Story:** US0006 (AC3, AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Client with 90K tokens used | n/a |
| When | `client.check_budget(projected_additional_tokens=30_000)` (total 120K, well under 200K) | Returns `None` |
| Then | No exception, no log line, no usage mutation | n/a |

**Assertions:**
- [ ] No exception raised
- [ ] Return value is `None`
- [ ] `client.usage.total_tokens_used` unchanged from 90K

---

### TC0060: `check_budget` boundary — projection exactly equal to budget passes

**Type:** Unit | **Priority:** P1 | **Story:** US0006 (AC3, AC4 boundary)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Client with `budget_tokens=200_000` and 100K tokens used | n/a |
| When | `client.check_budget(projected_additional_tokens=100_000)` | Returns silently (`>` not `>=` in the guard) |
| Then | `100_000 + 100_000 = 200_000` is not "exceeded" — only strict `>` raises | Off-by-one safety |

**Assertions:**
- [ ] No exception when `used + projected == budget`
- [ ] Exception when `used + projected == budget + 1`

---

### TC0061: Anthropic 429 × 2 then 200 — tenacity retries succeed

**Type:** Unit (mocked SDK) | **Priority:** P0 | **Story:** US0006 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Anthropic SDK mock raises `anthropic.RateLimitError` twice, then returns a valid response | n/a |
| When | `client.generate(prompt="x", max_output_tokens=100)` | Returns the successful response |
| Then | 3 SDK calls were made; tenacity backoff was respected (verified via mocked time.sleep) | Each retry logged with attempt number |

**Assertions:**
- [ ] Mock observed exactly 3 SDK invocations
- [ ] Response is the one from the third attempt
- [ ] Log records: 2 WARNING lines for retries, 1 INFO line for success

---

### TC0062: Anthropic 429 × 5 → `LlmUnavailableError` (retries exhausted)

**Type:** Unit (mocked SDK) | **Priority:** P0 | **Story:** US0006 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Anthropic SDK mock raises `RateLimitError` indefinitely | n/a |
| When | `client.generate(...)` | Raises `LlmUnavailableError` |
| Then | The original `RateLimitError` is `__cause__` | Mock observed 5 attempts |

**Assertions:**
- [ ] `pytest.raises(LlmUnavailableError)`
- [ ] `isinstance(exc.__cause__, anthropic.RateLimitError)`
- [ ] Mock observed exactly 5 attempts

---

### TC0063: `usage_report()` returns the documented dict shape

**Type:** Unit | **Priority:** P1 | **Story:** US0006 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A client that has made 2 successful calls | n/a |
| When | `client.usage_report()` | Returns a dict |
| Then | Dict has keys `model`, `budget_tokens`, `input_tokens_used`, `output_tokens_used`, `total_tokens_used`, `budget_remaining`, `calls` | `calls` is a list of `CallSummary` |

**Assertions:**
- [ ] `set(report) == {"model","budget_tokens","input_tokens_used","output_tokens_used","total_tokens_used","budget_remaining","calls"}`
- [ ] `report["budget_remaining"] == report["budget_tokens"] - report["total_tokens_used"]`
- [ ] `len(report["calls"]) == 2`

---

### TC0064: `LlmClient(budget_tokens=0)` raises `ValueError` at construction

**Type:** Unit | **Priority:** P2 | **Story:** US0006 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | n/a | n/a |
| When | `LlmClient(budget_tokens=0)` | Raises `ValueError` |
| Then | Parallel case: `budget_tokens=-1` also raises | n/a |

**Assertions:**
- [ ] Both `0` and `-1` raise `ValueError`
- [ ] Message mentions `"budget_tokens"`

---

### TC0065: `generate(max_output_tokens=0)` raises `ValueError` without any SDK call

**Type:** Unit | **Priority:** P2 | **Story:** US0006 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Anthropic SDK mock; no responses queued | n/a |
| When | `client.generate(prompt="x", max_output_tokens=0)` | Raises `ValueError` |
| Then | Mock observed 0 calls (validation happens before the SDK call) | n/a |

**Assertions:**
- [ ] `pytest.raises(ValueError)`
- [ ] SDK mock observed 0 invocations

---

### TC0066: `usage_report()` called before any `generate()` returns zero-valued report (no error)

**Type:** Unit | **Priority:** P2 | **Story:** US0006 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fresh `LlmClient` | n/a |
| When | `client.usage_report()` | Returns dict |
| Then | `total_tokens_used == 0`, `calls == []` | No exception |

**Assertions:**
- [ ] `report["total_tokens_used"] == 0`
- [ ] `report["calls"] == []`

---

### TC0067: Anthropic 400 (bad model id) — no retries, immediate raise

**Type:** Unit (mocked SDK) | **Priority:** P1 | **Story:** US0006 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Anthropic SDK mock raises `BadRequestError` on first attempt | n/a |
| When | `client.generate(...)` | Raises (no retry — retrying a 400 is pointless) |
| Then | Mock observed exactly 1 call | The exception type chosen is documented (e.g., `LlmUnavailableError` chaining the SDK error, *or* the raw `BadRequestError`) — assert whichever the implementation picked, stably |

**Assertions:**
- [ ] Mock observed exactly 1 invocation (no retry)
- [ ] Exception chain reaches the SDK's `BadRequestError`

---

### TC0068: Two-thread concurrent `generate()` — usage ledger has no lost updates

**Type:** Unit (threading) | **Priority:** P2 | **Story:** US0006 (edge: concurrency)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Anthropic SDK mock returns a fixed `(in=100,out=50)` for every call | n/a |
| When | 2 threads each call `client.generate(...)` 100 times concurrently | All 200 calls return |
| Then | `client.usage.total_tokens_used == 200 * 150 == 30000` exactly | No lost updates |

**Assertions:**
- [ ] `client.usage.total_tokens_used == 30_000`
- [ ] `len(client.usage_report()["calls"]) == 200`

---

### TC0069: Missing `ANTHROPIC_API_KEY` → `LlmUnavailableError` with a clear message

**Type:** Unit | **Priority:** P1 | **Story:** US0006 (edge: secret missing)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)` | Env scrubbed |
| When | `client.generate(...)` (SDK raises `AuthenticationError` internally) | Wrapper raises `LlmUnavailableError` |
| Then | Message says the key is missing or unauthenticated; does not echo any partial key value | **Secret-leak check:** captured log contains no `"sk-ant-"` prefix |

**Assertions:**
- [ ] `pytest.raises(LlmUnavailableError)` with message containing `"ANTHROPIC_API_KEY"` or `"authentication"`
- [ ] Captured logs contain no string starting with `"sk-ant-"`

---

### TC0070: `Cluster` model and `cluster_items` step have the documented signature

**Type:** Unit | **Priority:** P0 | **Story:** US0007 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.pipeline.cluster import cluster_items, Cluster` | Import succeeds |
| When | A valid `Cluster` is constructed via `Cluster.model_validate(dict)` | Model accepts `id`, `topic`, `items`, `rationale`; `significance` and `novelty` default to `None` |
| Then | `cluster_items(items, llm) -> list[Cluster]` is callable | Pyright accepts the signature |

**Assertions:**
- [ ] `Cluster` has fields `id`, `topic`, `items`, `rationale`, `significance`, `novelty`
- [ ] `significance is None` and `novelty is None` post-cluster (filled in by rank)
- [ ] `cluster_items([], fake_llm)` returns `[]` (smoke; full empty-input test is TC0076)

---

### TC0071: 50 items → exactly one LLM call; prompt loaded from `prompts/cluster.md`

**Type:** Integration (stubbed LLM) | **Priority:** P0 | **Story:** US0007 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 50 fixture `Item`s spanning all 3 sources; `FakeLLMClient` with one valid cluster JSON response queued | n/a |
| When | `cluster_items(items, fake_llm)` | Returns `list[Cluster]` |
| Then | `fake_llm.calls` has length 1 | The recorded prompt text starts with the content of `prompts/cluster.md` (after Jinja2 rendering) |

**Assertions:**
- [ ] `len(fake_llm.calls) == 1`
- [ ] `fake_llm.calls[0].prompt.startswith(open("prompts/cluster.md").read()[:80])` (or substring match on a stable header)
- [ ] Result is a non-empty `list[Cluster]`

---

### TC0072: Per-item prompt representation is bounded (title ≤ 200, summary ≤ 300)

**Type:** Unit | **Priority:** P1 | **Story:** US0007 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | One item with `title` length 250 and `summary_excerpt` length 1000 | n/a |
| When | The cluster step's internal `_build_prompt(items)` is called | Returns a string |
| Then | The string contains the title truncated to 200 chars and summary truncated to 300 chars (per the spec); total prompt size is logged | n/a |

**Assertions:**
- [ ] Built prompt contains exactly the first 200 chars of the long title
- [ ] Built prompt contains exactly the first 300 chars of the long summary
- [ ] At least one INFO log line records the prompt's total character count

---

### TC0073: Cross-`item_kind` cluster — paper + repo + blog about the same topic

**Type:** Integration (stubbed LLM) | **Priority:** P1 | **Story:** US0007 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 3 items: an arXiv paper (index 0), a GitHub repo (index 1), a Latent Space blog post (index 2), all about "OpenAI Swarm"; `FakeLLMClient` returns `{"clusters":[{"topic":"OpenAI Swarm","rationale":"same framework discussed","item_indices":[0,1,2]}]}` | n/a |
| When | `cluster_items(items, fake_llm)` | Returns 1 cluster |
| Then | That cluster's `items` contains all 3 originals, with their `item_kind` preserved (paper/repo/blog_post) | n/a |

**Assertions:**
- [ ] `len(result) == 1`
- [ ] `{i.item_kind for i in result[0].items} == {"paper","repo","blog_post"}`
- [ ] `result[0].topic == "OpenAI Swarm"`

---

### TC0074: LLM omits one item → `ClusterParseError` (union must equal input set)

**Type:** Integration (stubbed LLM) | **Priority:** P0 | **Story:** US0007 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 5 input items; `FakeLLMClient` returns a response covering only indices 0,1,2,3 (omits 4) — both on the first call and the retry | n/a |
| When | `cluster_items(items, fake_llm)` | Raises `ClusterParseError` |
| Then | Exception message mentions the omitted item's URL or index | n/a |

**Assertions:**
- [ ] `pytest.raises(ClusterParseError)`
- [ ] Message contains the omitted item's URL or `index 4`
- [ ] `fake_llm.calls` has length 2 (initial + 1 retry)

---

### TC0075: LLM duplicates an item across clusters → `ClusterParseError`

**Type:** Integration (stubbed LLM) | **Priority:** P0 | **Story:** US0007 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 5 items; LLM response assigns item 0 to both cluster A and cluster B (on first call and retry) | n/a |
| When | `cluster_items(items, fake_llm)` | Raises `ClusterParseError` |
| Then | Exception message lists the duplicated item | n/a |

**Assertions:**
- [ ] `pytest.raises(ClusterParseError)`
- [ ] Message mentions the duplicated item's URL or `index 0`

---

### TC0076: Empty input → `[]` without any LLM call

**Type:** Unit | **Priority:** P1 | **Story:** US0007 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fresh `FakeLLMClient` with no responses queued | n/a |
| When | `cluster_items([], fake_llm)` | Returns `[]` |
| Then | `fake_llm.calls == []` (no call made) | INFO log line says "no items to cluster" |

**Assertions:**
- [ ] `result == []`
- [ ] `fake_llm.calls == []`
- [ ] INFO log mentions "skipping" or "no items"

---

### TC0077: Cluster count of 1 for 50 items → WARN log, result still returned

**Type:** Integration (stubbed LLM) | **Priority:** P2 | **Story:** US0007 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 50 items; LLM returns a single cluster containing all 50 indices (valid invariants, just too coarse) | n/a |
| When | `cluster_items(items, fake_llm)` | Returns `[cluster]` (length 1) |
| Then | WARN log mentions "1 cluster for 50 items" or "outside [3, 30]" | No exception |

**Assertions:**
- [ ] `len(result) == 1`
- [ ] WARN log records the count of 1 (or > 30 in the parallel case)

---

### TC0078: Invalid JSON → retry once → still invalid → raise

**Type:** Integration (stubbed LLM) | **Priority:** P1 | **Story:** US0007 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | LLM returns `"not json {"` twice | n/a |
| When | `cluster_items(items, fake_llm)` | Raises `ClusterParseError` |
| Then | `fake_llm.calls` has length 2 | Second prompt explicitly mentions "your output was invalid JSON" |

**Assertions:**
- [ ] `pytest.raises(ClusterParseError)`
- [ ] `len(fake_llm.calls) == 2`
- [ ] `"invalid JSON"` (case-insensitive) appears in the second prompt

---

### TC0079: LLM hallucinates an index out of range → `ClusterParseError`

**Type:** Integration (stubbed LLM) | **Priority:** P2 | **Story:** US0007 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 50 items; LLM returns a response with `item_indices: [60, 70]` (out of range) | n/a |
| When | `cluster_items(items, fake_llm)` | Raises `ClusterParseError` |
| Then | Message includes the offending indices | n/a |

**Assertions:**
- [ ] `pytest.raises(ClusterParseError)`
- [ ] Message contains `"60"` or `"out of range"`

---

### TC0080: `rank_clusters` + `RankedClusters` have the documented signature

**Type:** Unit | **Priority:** P0 | **Story:** US0008 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.pipeline.rank import rank_clusters, RankedClusters` | Import succeeds |
| When | `result = rank_clusters(clusters, fake_llm, top_deep=3, top_quick=10)` (with stubbed LLM) | Returns `RankedClusters` |
| Then | `RankedClusters` has fields `deep`, `quick`, `unselected`, `rationale_by_cluster_id` | Pyright accepts the signature |

**Assertions:**
- [ ] All four fields exist with correct types
- [ ] `len(result.deep) <= 3` and `len(result.quick) <= 10`

---

### TC0081: Every scored cluster has `significance` and `novelty` in [0, 1]

**Type:** Integration (stubbed LLM) | **Priority:** P0 | **Story:** US0008 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 10 clusters; LLM returns scores in [0, 1] for each | n/a |
| When | `rank_clusters(clusters, fake_llm)` | Each cluster in `deep + quick + unselected` has `significance: float` and `novelty: float` |
| Then | Both fields are populated (no `None` left over from US0007) | All values clamped/validated to [0, 1] |

**Assertions:**
- [ ] Every cluster in any output list has `significance is not None and novelty is not None`
- [ ] `0.0 <= cluster.significance <= 1.0`
- [ ] `0.0 <= cluster.novelty <= 1.0`

---

### TC0082: `prompts/rank.md` contains all three `item_kind` rubrics (string-match check)

**Type:** Unit | **Priority:** P1 | **Story:** US0008 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The prompt file `prompts/rank.md` | File exists |
| When | The file body is read into a string | n/a |
| Then | The body contains paper-rubric phrases (e.g., `"methodological substance"`, `"cross-citation"`), repo-rubric phrases (e.g., `"shipping signals"`, `"stars"`), and blog-rubric phrases (e.g., `"author authority"`, `"corroboration"`) | n/a |

**Assertions:**
- [ ] `"methodological substance"` (or equivalent) in the prompt
- [ ] `"shipping signals"` (or equivalent) in the prompt
- [ ] `"author authority"` (or equivalent) in the prompt

---

### TC0083: Deterministic top-3 selection by score, stable sort on ties

**Type:** Unit | **Priority:** P0 | **Story:** US0008 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 20 clusters with stubbed LLM returning specific scores including 3 ties at significance=0.7 | n/a |
| When | `rank_clusters(clusters, fake_llm, top_deep=3, top_quick=10)` | Returns RankedClusters |
| Then | `deep` contains the 3 highest-significance clusters; tied clusters preserve input order | Running twice with same input produces identical lists |

**Assertions:**
- [ ] `[c.id for c in result.deep]` matches the expected ordering exactly
- [ ] Running `rank_clusters` twice with identical inputs produces identical `deep` and `quick` orderings
- [ ] `len(result.unselected) == 7`

---

### TC0084: `rationale_by_cluster_id` populated for every selected cluster

**Type:** Integration (stubbed LLM) | **Priority:** P1 | **Story:** US0008 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 10 clusters; LLM returns rationale text for each | n/a |
| When | `rank_clusters(clusters, fake_llm)` | n/a |
| Then | Every `result.deep[i].id` and `result.quick[i].id` has a non-empty entry in `result.rationale_by_cluster_id` | Rationale length 1–3 sentences (not asserted strictly, but presence is required) |

**Assertions:**
- [ ] For every `c` in `result.deep + result.quick`: `c.id in result.rationale_by_cluster_id`
- [ ] For every selected cluster: `len(result.rationale_by_cluster_id[c.id]) > 0`

---

### TC0085: `prompts/rank.md` contains the documented novelty hedge instruction

**Type:** Unit | **Priority:** P2 | **Story:** US0008 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The prompt file | n/a |
| When | The body is read | n/a |
| Then | Contains hedge phrasing: `"training cutoff"` and `"default to 0.3"` (or close paraphrase from the AC) | n/a |

**Assertions:**
- [ ] `"training cutoff"` substring present (case-insensitive)
- [ ] `"0.3"` or `"low confidence"` substring present

---

### TC0086: 4 clusters with `top_deep=3, top_quick=10` → 3 deep + 1 quick + 0 unselected

**Type:** Integration (stubbed LLM) | **Priority:** P1 | **Story:** US0008 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 4 clusters; LLM provides scores for each | n/a |
| When | `rank_clusters(clusters, fake_llm, top_deep=3, top_quick=10)` | n/a |
| Then | `len(result.deep) == 3 and len(result.quick) == 1 and len(result.unselected) == 0` | No error |

**Assertions:**
- [ ] `len(result.deep) == 3`
- [ ] `len(result.quick) == 1`
- [ ] `len(result.unselected) == 0`
- [ ] No exception

---

### TC0087: LLM returns score 1.5 (out of [0, 1]) → clamped to 1.0 with WARN

**Type:** Integration (stubbed LLM) | **Priority:** P2 | **Story:** US0008 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 3 clusters; LLM returns significance=1.5 for cluster A and -0.2 for cluster B | n/a |
| When | `rank_clusters(...)` | A's significance becomes 1.0; B's becomes 0.0 |
| Then | Two WARN log lines mention out-of-range scores | No exception |

**Assertions:**
- [ ] Cluster A: `significance == 1.0`
- [ ] Cluster B: `significance == 0.0`
- [ ] At least 2 WARN log lines about clamping

---

### TC0088: LLM omits a cluster id in scoring response → `RankParseError`

**Type:** Integration (stubbed LLM) | **Priority:** P1 | **Story:** US0008 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 5 clusters; LLM scores only 4 of them | n/a |
| When | `rank_clusters(...)` | Raises `RankParseError` |
| Then | Message lists the missing cluster id | n/a |

**Assertions:**
- [ ] `pytest.raises(RankParseError)`
- [ ] Message contains the omitted cluster's id

---

### TC0089: Pre-compose budget projection too high → `BudgetExceededError`

**Type:** Integration (stubbed LLM) | **Priority:** P0 | **Story:** US0008 (interaction with US0006)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Real `LlmClient` semantics via FakeLLMClient with `budget_tokens=50_000` and 40K used; `rank_clusters` projects compose cost as 20K | Total projected 60K > 50K |
| When | `rank_clusters(...)` calls `llm.check_budget(20_000)` before returning | Raises `BudgetExceededError` |
| Then | The exception propagates out of `rank_clusters` to the orchestrator | No compose call ever happens |

**Assertions:**
- [ ] `pytest.raises(BudgetExceededError)` at the call to `rank_clusters`
- [ ] No subsequent LLM calls observed after the budget check

---

### TC0090: Empty cluster list → empty `RankedClusters`; no LLM call

**Type:** Unit | **Priority:** P1 | **Story:** US0008 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fresh `FakeLLMClient` with no responses queued | n/a |
| When | `rank_clusters([], fake_llm)` | Returns empty `RankedClusters` |
| Then | `result.deep == result.quick == result.unselected == []` | `fake_llm.calls == []` |

**Assertions:**
- [ ] All three output lists are empty
- [ ] `fake_llm.calls == []`

---

### TC0091: `compose_paper_deep_dive` + `DeepDive` model exist with documented shape

**Type:** Unit | **Priority:** P0 | **Story:** US0009 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.pipeline.compose import compose_paper_deep_dive, DeepDive` | Import succeeds |
| When | `compose_paper_deep_dive(cluster, "rat", fake_llm)` runs with a stub response | Returns `DeepDive` |
| Then | `DeepDive` has fields `topic`, `body_markdown`, `cited_urls`, `item_kind`, `maturity_summary`; `item_kind == "paper"` | Pyright accepts the signature |

**Assertions:**
- [ ] `result.item_kind == "paper"`
- [ ] `isinstance(result.cited_urls, list)`

---

### TC0092: `prompts/compose-paper.md` carries the documented structure

**Type:** Unit | **Priority:** P1 | **Story:** US0009 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The prompt file | n/a |
| When | The body is read | n/a |
| Then | Contains all four section headers ("what was shown", "method/eval", "caveats", "production reality") (case-insensitive substring match); contains the anti-hype instruction list (at least 3 banned words); contains length bound mention (`"300 words"` or `"two paragraphs"`) | n/a |

**Assertions:**
- [ ] All 4 section keywords present
- [ ] At least 3 of `["groundbreaking","revolutionary","breakthrough"]` appear in the ban list
- [ ] Length bound is mentioned

---

### TC0093: Output body contains all four sections

**Type:** Integration (stubbed LLM) | **Priority:** P0 | **Story:** US0009 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Paper cluster; `FakeLLMClient` returns markdown containing the 4 section markers | n/a |
| When | `compose_paper_deep_dive(...)` runs | Returns `DeepDive` |
| Then | `body_markdown.lower()` contains all four of `"what was shown"`, `"method"`, `"caveats"`, and either `"production reality"` or `"no production signal yet"` | Body ≤ 500 words (truncation safeguard) |

**Assertions:**
- [ ] All four section markers present (case-insensitive)
- [ ] `len(body_markdown.split()) <= 500`

---

### TC0094: All cluster items appear in `cited_urls`; matches inline links

**Type:** Integration (stubbed LLM) | **Priority:** P1 | **Story:** US0009 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Cluster with 3 paper items at URLs U1, U2, U3; LLM returns body with markdown links to all three | n/a |
| When | `compose_paper_deep_dive(...)` runs | Returns `DeepDive` |
| Then | `set(result.cited_urls) == {U1, U2, U3}` | Each URL appears at least once as `](url)` in body |

**Assertions:**
- [ ] `set(result.cited_urls) == {U1, U2, U3}`
- [ ] For every URL: `"]({url})"` substring present in `body_markdown`

---

### TC0095: Production-reality line conditional on cluster signal

**Type:** Integration (stubbed LLM) | **Priority:** P1 | **Story:** US0009 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Two fixture clusters: (A) raw has cost/latency/replication hints; (B) raw has none. LLM is stubbed differently per case. | n/a |
| When | `compose_paper_deep_dive(...)` runs on each | n/a |
| Then | (A)'s body contains a "production reality" paragraph with concrete signal; (B)'s body says "no production signal yet" explicitly | Neither fabricates a signal |

**Assertions:**
- [ ] (A): body matches `"production reality"` with a concrete sentence after it
- [ ] (B): body contains the literal phrase `"no production signal yet"`
- [ ] (B): body does **not** contain fabricated metrics like `"99% accuracy"` (regex check)

---

### TC0096: Anti-hype retry — `"groundbreaking"` on attempt 1, clean on attempt 2

**Type:** Integration (stubbed LLM) | **Priority:** P1 | **Story:** US0009 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | LLM queue: first response contains `"groundbreaking"`; second response is clean | n/a |
| When | `compose_paper_deep_dive(...)` runs | Returns the clean response |
| Then | `fake_llm.calls` has length 2; second prompt mentions the banned word | No `ComposeStyleError` raised on clean second pass |

**Assertions:**
- [ ] `len(fake_llm.calls) == 2`
- [ ] No banned word in final `body_markdown`
- [ ] Second prompt contains a string indicating retry rationale

---

### TC0097: `BANNED_HYPE_WORDS` constant has ≥ 5 entries and is enforced

**Type:** Unit | **Priority:** P2 | **Story:** US0009 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.pipeline.compose import BANNED_HYPE_WORDS` | Import succeeds |
| When | The constant is inspected | n/a |
| Then | `len(BANNED_HYPE_WORDS) >= 5`; includes at minimum `groundbreaking`, `revolutionary`, `breakthrough` | n/a |

**Assertions:**
- [ ] `len(BANNED_HYPE_WORDS) >= 5`
- [ ] `{"groundbreaking","revolutionary","breakthrough"} <= set(BANNED_HYPE_WORDS)`

---

### TC0098: 3-section response → retry → still 3 sections → `ComposeParseError`

**Type:** Integration (stubbed LLM) | **Priority:** P1 | **Story:** US0009 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | LLM queue: two responses, each missing the "caveats" section | n/a |
| When | `compose_paper_deep_dive(...)` runs | Raises `ComposeParseError` |
| Then | `fake_llm.calls` has length 2; second prompt mentions the missing section | n/a |

**Assertions:**
- [ ] `pytest.raises(ComposeParseError)`
- [ ] `len(fake_llm.calls) == 2`
- [ ] Second prompt mentions `"caveats"` (or `"missing section"`)

---

### TC0099: LLM cites URL not in cluster → filtered out of `cited_urls`

**Type:** Integration (stubbed LLM) | **Priority:** P2 | **Story:** US0009 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Cluster items at URLs U1, U2; LLM body cites U1 + an unrelated URL X | n/a |
| When | `compose_paper_deep_dive(...)` runs | Returns `DeepDive` |
| Then | `cited_urls == [U1]` (X dropped); body still contains the offending link string but it's not promoted to `cited_urls` | WARN log mentions the filtered URL |

**Assertions:**
- [ ] `set(result.cited_urls) == {U1}`
- [ ] WARN log mentions the filtered URL `X`

---

### TC0100: `prompts/compose-paper.md` missing → clear startup error

**Type:** Unit | **Priority:** P2 | **Story:** US0009 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `tmp_path` with no `prompts/compose-paper.md`; module's loader pointed at this path | n/a |
| When | `compose_paper_deep_dive(...)` called | Raises `FileNotFoundError` (or wrapped equivalent) at first access |
| Then | Message names the expected path | n/a |

**Assertions:**
- [ ] `pytest.raises(FileNotFoundError)` (or the project's wrapped equivalent)
- [ ] Message contains `"compose-paper.md"`

---

### TC0101: `compose_repo_deep_dive` returns `DeepDive` with `item_kind="repo"` and `maturity_summary` populated

**Type:** Integration (stubbed LLM) | **Priority:** P0 | **Story:** US0010 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Repo cluster with full shipping signals; FakeLLM returns a well-structured response | n/a |
| When | `compose_repo_deep_dive(...)` runs | Returns `DeepDive` |
| Then | `item_kind == "repo"`; `maturity_summary` is a non-empty single sentence (no trailing newline) | n/a |

**Assertions:**
- [ ] `result.item_kind == "repo"`
- [ ] `isinstance(result.maturity_summary, str) and len(result.maturity_summary) > 0`
- [ ] `result.maturity_summary.count(".") == 1` (a single terminal period — proxy for "one sentence")

---

### TC0102: `prompts/compose-repo.md` carries 3-section structure + shared anti-hype constant

**Type:** Unit | **Priority:** P1 | **Story:** US0010 (AC2, AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Prompt file body | n/a |
| When | Inspected | n/a |
| Then | Contains section keywords `"what it does"`, `"maturity"`, `"shipping evidence"` | Carries the same anti-hype words as US0009 (or a placeholder marker that the loader substitutes from `BANNED_HYPE_WORDS`) |

**Assertions:**
- [ ] All 3 section keywords present (case-insensitive)
- [ ] Anti-hype enforcement is delegated to the shared `BANNED_HYPE_WORDS` constant (no per-prompt hardcoded list — verified by ensuring the constant is the single source of truth)

---

### TC0103: Output body cites concrete shipping signals (numbers, dates, demo URL)

**Type:** Integration (stubbed LLM) | **Priority:** P1 | **Story:** US0010 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Repo with `stars=1234`, `last_commit_at="2026-05-15..."`, `has_recent_release=True`, `hosted_demo_url="https://example.com/demo"`; LLM body cites at least two of these | n/a |
| When | `compose_repo_deep_dive(...)` runs | Returns `DeepDive` |
| Then | Body contains the string `"1,234"` (or `"1234"`) and either the demo URL or a date marker | n/a |

**Assertions:**
- [ ] Either `"1,234"` or `"1234"` appears in `body_markdown`
- [ ] At least one of: demo URL, `"2026-05-15"`, `"recent release"` appears
- [ ] Body contains no vague phrases like `"very popular"` or `"super active"` (regex on a small denylist)

---

### TC0104: `maturity_summary` — full signals vs. all-missing

**Type:** Integration (stubbed LLM, two scenarios) | **Priority:** P1 | **Story:** US0010 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | (A) repo with `maturity="beta"` and full signals; (B) repo with `maturity="unknown"` and empty `raw` | n/a |
| When | `compose_repo_deep_dive(...)` runs on each | n/a |
| Then | (A): `maturity_summary` contains concrete numbers (e.g., `"1.2K"`, `"4 days ago"`); (B): `maturity_summary` says `"Maturity unclear"` or similar | n/a |

**Assertions:**
- [ ] (A): `maturity_summary` contains at least one digit and a time-relative phrase
- [ ] (B): `maturity_summary.lower()` contains `"unclear"` or `"unknown"`
- [ ] (B): never fabricates a number (no digit in the summary)

---

### TC0105: Mixed-kind cluster routed to repo compose — all URLs cited

**Type:** Integration (stubbed LLM) | **Priority:** P2 | **Story:** US0010 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Cluster with 1 repo + 1 blog post about it; LLM body cites both | n/a |
| When | `compose_repo_deep_dive(...)` runs | Returns `DeepDive` |
| Then | `cited_urls` contains both URLs | n/a |

**Assertions:**
- [ ] `len(result.cited_urls) == 2`
- [ ] Both repo and blog URLs present

---

### TC0106: Anti-hype constant is imported from US0009's module (single source of truth)

**Type:** Unit | **Priority:** P2 | **Story:** US0010 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The repo compose module and US0009's module | n/a |
| When | `repo_module.BANNED_HYPE_WORDS is paper_module.BANNED_HYPE_WORDS` (identity check) | Either same object or imported from the same name |
| Then | Static check: `grep -r "BANNED_HYPE_WORDS = " techletter/` yields exactly 1 hit | n/a |

**Assertions:**
- [ ] `id(repo.BANNED_HYPE_WORDS) == id(paper.BANNED_HYPE_WORDS)` (same object)
- [ ] At most 1 source line in the package defines `BANNED_HYPE_WORDS = ...`

---

### TC0107: Repo compose missing-section response → retry → `ComposeParseError`

**Type:** Integration (stubbed LLM) | **Priority:** P1 | **Story:** US0010 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | LLM queue: two responses missing the `"shipping evidence"` section | n/a |
| When | `compose_repo_deep_dive(...)` runs | Raises `ComposeParseError` |
| Then | 2 calls observed | n/a |

**Assertions:**
- [ ] `pytest.raises(ComposeParseError)`
- [ ] `len(fake_llm.calls) == 2`

---

### TC0108: `format_shipping_signals` — parametric table

**Type:** Unit (parametric) | **Priority:** P1 | **Story:** US0010 (helper, AC3 support)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Parametrised inputs covering: all fields present; all fields missing; partial fields; malformed `last_commit_at`; `stars=0`; whitespace `hosted_demo_url` | n/a |
| When | `format_shipping_signals(item)` is called | Returns a string per the documented format |
| Then | Each case produces the expected text snippet, with no exception | "Stars: 0" is rendered (not omitted) |

**Parametrisation:**

| Case | Input excerpt | Expected substring |
|------|---------------|--------------------|
| Full | `{stars:1234,last_commit_at:..,has_recent_release:true,hosted_demo_url:"https://..."}` | `"Stars: 1234"`, demo URL line |
| All missing | `raw={}, maturity=None` | `"Maturity: unknown"`, `"no shipping signals available"` |
| stars=0 | `{stars:0}` | `"Stars: 0"` |
| malformed last_commit | `{last_commit_at:"not-a-date"}` | `"Last commit: unknown"` |
| whitespace homepage | `{hosted_demo_url:"   "}` | no `"Hosted demo"` line |

**Assertions:**
- [ ] All 5 parametrised cases produce expected substring(s)
- [ ] No exception raised in any case

---

### TC0109: Malformed `hosted_demo_url` → demo line omitted (no crash)

**Type:** Unit | **Priority:** P2 | **Story:** US0010 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Repo with `hosted_demo_url="not-a-url"` | n/a |
| When | `format_shipping_signals(item)` | Returns string without a `"Hosted demo:"` line |
| Then | No exception | n/a |

**Assertions:**
- [ ] `"Hosted demo"` not in output
- [ ] No exception

---

### TC0110: `compose_blog_deep_dive` returns `DeepDive` with `item_kind="blog_post"`

**Type:** Integration (stubbed LLM) | **Priority:** P0 | **Story:** US0011 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Blog cluster; FakeLLM returns 3-section response | n/a |
| When | `compose_blog_deep_dive(...)` runs | Returns `DeepDive` |
| Then | `item_kind == "blog_post"`; body covers "what's being argued", "cross-source corroboration", "author authority signal" | n/a |

**Assertions:**
- [ ] `result.item_kind == "blog_post"`
- [ ] Body contains all three section markers (case-insensitive)

---

### TC0111: `prompts/compose-blog.md` carries 3-section structure + shared anti-hype

**Type:** Unit | **Priority:** P1 | **Story:** US0011 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Prompt file body | n/a |
| When | Inspected | n/a |
| Then | Contains `"what's being argued"`, `"corroboration"`, `"author authority"` keywords; instructs `"author authority not assessed"` fallback | Anti-hype delegated to shared constant |

**Assertions:**
- [ ] All 3 section keywords present
- [ ] Fallback phrase `"not assessed"` present
- [ ] No local `BANNED_HYPE_WORDS = ...` line (delegated to shared)

---

### TC0112: `compose_quick_mentions` — 10 clusters → 1 LLM call → 10 `QuickMention`s

**Type:** Integration (stubbed LLM) | **Priority:** P0 | **Story:** US0011 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 10 input clusters; FakeLLM returns a batch of 10 one-liners | n/a |
| When | `compose_quick_mentions(clusters, fake_llm)` | Returns `list[QuickMention]` |
| Then | `len(fake_llm.calls) == 1`; `len(result) == 10`; every `one_liner` ≤ 200 chars; every QuickMention has `topic`, `one_liner`, `url`, `item_kind`, `maturity` (maturity may be None) | n/a |

**Assertions:**
- [ ] `len(fake_llm.calls) == 1`
- [ ] `len(result) == 10`
- [ ] `all(len(m.one_liner) <= 200 for m in result)`
- [ ] Every QuickMention has all required fields

---

### TC0113: `RenderedIssue` model + `assemble_issue` function defined

**Type:** Unit | **Priority:** P0 | **Story:** US0011 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.pipeline.assemble import RenderedIssue, assemble_issue` | Import succeeds |
| When | `RenderedIssue(issue_id="2026-05-19", markdown="...", html=None, plaintext=None, meta={...})` constructed | Validates |
| Then | All five fields exist; `html` and `plaintext` accept `None` | Pyright accepts signature |

**Assertions:**
- [ ] Fields `issue_id`, `markdown`, `html`, `plaintext`, `meta` all present
- [ ] `html=None` and `plaintext=None` are accepted

---

### TC0114: Assembled markdown contains all required sections in documented order

**Type:** Unit | **Priority:** P0 | **Story:** US0011 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fixture inputs: 3 DeepDives (one each: paper, repo, blog), 10 QuickMentions, fake usage_report, source_counts | n/a |
| When | `assemble_issue(...)` runs | Returns `RenderedIssue` |
| Then | `markdown` contains, in order: YAML front matter fenced by `---`; H1 title; `## Deep dives`; 3 deep-dive subsections; `## Also worth noting`; 10 bullets; footer with token usage | n/a |

**Assertions:**
- [ ] `markdown.startswith("---\n")` (front matter open)
- [ ] Title line `"# Tech-Letter for HYL"` present
- [ ] `"## Deep dives"` precedes `"## Also worth noting"`
- [ ] `markdown.count("- [")` >= 10 (quick mention bullets)
- [ ] Footer contains token-usage figure from `usage_report`

---

### TC0115: `issue_id` is today's UTC date in ISO format

**Type:** Unit | **Priority:** P0 | **Story:** US0011 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Clock frozen at `2026-05-19T00:00:00Z` (`freezegun`) | n/a |
| When | `assemble_issue(...)` runs | n/a |
| Then | `result.issue_id == "2026-05-19"` and the front matter contains the same value | n/a |

**Assertions:**
- [ ] `result.issue_id == "2026-05-19"`
- [ ] Front matter YAML contains `issue_id: 2026-05-19`

---

### TC0116: Item-kind + maturity indicators — known rendered, unknown omitted

**Type:** Unit | **Priority:** P1 | **Story:** US0011 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A deep dive with `item_kind="repo"`, `maturity_summary` containing `"beta"`; a quick mention with `item_kind="blog_post"`, `maturity=None` | n/a |
| When | `assemble_issue(...)` runs | n/a |
| Then | The deep dive's section shows `[repo · beta]` (or equivalent); the quick mention's bullet shows `[blog_post]` only (no `· unknown`) | Never the literal `"unknown"` string |

**Assertions:**
- [ ] `"[repo · beta]"` (or close variant) in markdown
- [ ] `"[blog_post]"` (no `· `) in markdown
- [ ] `"unknown"` not in any rendered indicator (only in `meta` dict if at all)

---

### TC0117: 4 deep dives → 4 sections, not truncated, not padded

**Type:** Unit | **Priority:** P1 | **Story:** US0011 (AC8)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 4 deep dives provided | n/a |
| When | `assemble_issue(...)` | n/a |
| Then | Exactly 4 deep-dive subsections rendered; no WARN log about count (4 is within flex 2–5) | n/a |

**Assertions:**
- [ ] Count of `^## ` subsection headers under "Deep dives" equals 4
- [ ] No WARN log about deep-dive count

---

### TC0118: 6 quick mentions → 6 bullets, heading text unchanged

**Type:** Unit | **Priority:** P1 | **Story:** US0011 (AC9)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 6 quick mentions provided | n/a |
| When | `assemble_issue(...)` | n/a |
| Then | Exactly 6 `- [` bullets under "Also worth noting"; section heading remains `"## Also worth noting"` (no literal "10") | n/a |

**Assertions:**
- [ ] 6 bullets rendered
- [ ] No occurrence of `"10 quick"` in the heading line

---

### TC0119: Zero deep dives → WARN, empty "Deep dives" section, no exception

**Type:** Unit | **Priority:** P2 | **Story:** US0011 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `assemble_issue(deep_dives=[], quick_mentions=[10 items], ...)` | n/a |
| When | Called | Returns `RenderedIssue` |
| Then | WARN log about "0 deep dives"; "Deep dives" section is present but empty (or omitted, per implementation choice — assert one or the other consistently); no exception | n/a |

**Assertions:**
- [ ] No exception
- [ ] WARN log line about deep-dive count
- [ ] Markdown is still valid (front matter + title + at least the quick section)

---

### TC0120: Zero quick mentions → "Also worth noting" section omitted entirely

**Type:** Unit | **Priority:** P2 | **Story:** US0011 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `assemble_issue(deep_dives=[3 items], quick_mentions=[], ...)` | n/a |
| When | Called | n/a |
| Then | `"Also worth noting"` substring is NOT in the markdown (cleaner than empty section) | n/a |

**Assertions:**
- [ ] `"Also worth noting"` not in `result.markdown`

---

### TC0121: `compose_quick_mentions` LLM returns 7 from 10 input → use 7, WARN logged

**Type:** Integration (stubbed LLM) | **Priority:** P2 | **Story:** US0011 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 10 input clusters; LLM returns 7 one-liners | n/a |
| When | `compose_quick_mentions(clusters, fake_llm)` | Returns list of 7 |
| Then | WARN log mentions "shortfall" or "expected 10, got 7" | No exception |

**Assertions:**
- [ ] `len(result) == 7`
- [ ] WARN log records the shortfall

---

### TC0122: One-liner > 200 chars → truncated to 200 with ellipsis, WARN logged

**Type:** Integration (stubbed LLM) | **Priority:** P2 | **Story:** US0011 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | LLM returns one quick mention with `one_liner` of 250 chars | n/a |
| When | `compose_quick_mentions(...)` runs | Returns list |
| Then | That QuickMention has `one_liner` length exactly 200 (or 200 + ellipsis char); WARN logged | n/a |

**Assertions:**
- [ ] `len(result[bad_index].one_liner) <= 200` (or 201 if ellipsis is counted separately)
- [ ] WARN log about the truncation

---

### TC0123: Blog cluster with one item → body says "no cross-source corroboration"

**Type:** Integration (stubbed LLM) | **Priority:** P2 | **Story:** US0011 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Single-item blog cluster; LLM stub returns body acknowledging it | n/a |
| When | `compose_blog_deep_dive(...)` runs | n/a |
| Then | Body contains the literal phrase `"no cross-source corroboration"` (case-insensitive) | No fabrication of corroborating sources |

**Assertions:**
- [ ] `"no cross-source corroboration"` (case-insensitive) appears in body
- [ ] No URL appears in `cited_urls` other than the single input item's URL

---

### TC0124: Deep-dive body containing `---` fence — front matter remains parseable

**Type:** Unit | **Priority:** P1 | **Story:** US0011 (edge — front-matter ambiguity)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A DeepDive whose `body_markdown` contains a `---` horizontal rule mid-paragraph | n/a |
| When | `assemble_issue(...)` produces markdown; the markdown is then parsed by a YAML front-matter library | n/a |
| Then | The front matter is the FIRST `---`-delimited block, ending at the first closing `---` *before* any deep-dive body; downstream parser extracts a valid YAML dict | The `---` inside the body is preserved as content |

**Assertions:**
- [ ] A YAML front-matter parser (e.g., `python-frontmatter`) extracts a dict with the documented keys
- [ ] The dict's keys are exactly the documented set (`issue_id`, `date`, `tokens_used`, `model`, `sources`)
- [ ] The remaining body still contains the `---` from the deep dive

---

### TC0125: `assemble_issue` is deterministic — byte-identical output for identical inputs

**Type:** Unit | **Priority:** P0 | **Story:** US0011 (idempotency hook for EP0003)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fixed inputs (3 DeepDives, 10 QuickMentions, usage_report, source_counts) | Clock frozen |
| When | `assemble_issue(...)` called 3 times | n/a |
| Then | All three returned `RenderedIssue.markdown` strings are byte-identical | `RenderedIssue.meta` is identical |

**Assertions:**
- [ ] `result1.markdown == result2.markdown == result3.markdown` (exact equality)
- [ ] `result1.meta == result2.meta`
- [ ] `hashlib.sha256(result1.markdown.encode()).hexdigest() == hashlib.sha256(result2.markdown.encode()).hexdigest()`

---

## Fixtures

```yaml
# tests/fixtures/llm/cluster_valid_response.json — drives TC0071, TC0073.
# Returned by FakeLLMClient when cluster_items prompts arrive.
cluster_valid_response: |
  {
    "clusters": [
      {"topic": "OpenAI Swarm: multi-agent orchestration",
       "rationale": "Same framework discussed across paper, repo, and Latent Space.",
       "item_indices": [0, 1, 2]},
      {"topic": "Tool-use benchmarks",
       "rationale": "Methodologically related agent-evaluation papers.",
       "item_indices": [3, 4]}
    ]
  }

# tests/fixtures/llm/cluster_omits_item.json — drives TC0074 (returned twice).
cluster_omits_item: |
  {
    "clusters": [
      {"topic": "X", "rationale": "...", "item_indices": [0, 1, 2, 3]}
    ]
  }

# tests/fixtures/llm/rank_scores_10.json — drives TC0081, TC0083, TC0084.
rank_scores_10:
  clusters:
    - { id: "c1", significance: 0.92, novelty: 0.40, rationale: "Methodologically novel agent benchmark." }
    - { id: "c2", significance: 0.88, novelty: 0.55, rationale: "Active repo with hosted demo." }
    - { id: "c3", significance: 0.85, novelty: 0.30, rationale: "Three independent sources discussing." }
    - { id: "c4", significance: 0.70, novelty: 0.30, rationale: "..." }
    - { id: "c5", significance: 0.70, novelty: 0.40, rationale: "..." }
    # ... 5 more

# tests/fixtures/llm/compose_paper_valid.md — drives TC0093, TC0094, TC0095 (signal-rich variant).
compose_paper_valid: |
  ### What was shown
  The authors introduce X, a benchmark for ...
  ### Method/eval at a glance
  ...
  ### Caveats
  ...
  ### Production reality
  Latency of 1.2s per call; replication script provided.
  
  Citations:
  - [Toolformer paper](https://arxiv.org/abs/2302.04761)
  - [Latent Space coverage](https://www.latent.space/p/toolformer)

# tests/fixtures/llm/compose_paper_no_signal.md — drives TC0095 (no-signal variant).
compose_paper_no_signal: |
  ### What was shown
  ...
  ### Method/eval at a glance
  ...
  ### Caveats
  ...
  (no production signal yet)

# tests/fixtures/llm/compose_repo_full_signals.md — drives TC0103, TC0104(A).
# tests/fixtures/llm/compose_repo_no_signals.md — drives TC0104(B).
# tests/fixtures/llm/compose_blog_3_sections.md — drives TC0110, TC0111.
# tests/fixtures/llm/quick_mentions_10.json — drives TC0112.
# tests/fixtures/llm/quick_mentions_7_from_10.json — drives TC0121.

# tests/fixtures/items/cluster_paper_only.yaml — paper-only cluster used in compose-paper tests.
# tests/fixtures/items/cluster_repo_full.yaml — repo with all shipping fields.
# tests/fixtures/items/cluster_repo_empty_raw.yaml — repo with empty raw, maturity unknown.

# tests/fixtures/usage/usage_report_sample.yaml — drives assemble_issue tests.
usage_report_sample:
  model: "claude-sonnet-4-6"
  budget_tokens: 200000
  input_tokens_used: 45000
  output_tokens_used: 12000
  total_tokens_used: 57000
  budget_remaining: 143000
  calls: []  # detail elided for fixture brevity

# tests/fixtures/sources/source_counts.yaml
source_counts:
  arxiv: 18
  github: 25
  rss: 12
```

---

## Automation Status

| TC | Title | Status | Implementation |
|----|-------|--------|----------------|
| TC0056 | LlmClient constructor + generate signature | Pending | - |
| TC0057 | Two generate() calls accumulate usage | Pending | - |
| TC0058 | check_budget raises over budget | Pending | - |
| TC0059 | check_budget passes under budget | Pending | - |
| TC0060 | check_budget boundary exactly equal | Pending | - |
| TC0061 | 429×2 then 200 — retries succeed | Pending | - |
| TC0062 | 429×5 → LlmUnavailableError | Pending | - |
| TC0063 | usage_report dict shape | Pending | - |
| TC0064 | budget_tokens=0 → ValueError | Pending | - |
| TC0065 | max_output_tokens=0 → ValueError | Pending | - |
| TC0066 | usage_report before any call | Pending | - |
| TC0067 | 400 bad model id — no retries | Pending | - |
| TC0068 | Threadsafe usage ledger | Pending | - |
| TC0069 | Missing ANTHROPIC_API_KEY → LlmUnavailableError | Pending | - |
| TC0070 | Cluster model + cluster_items signature | Pending | - |
| TC0071 | 50 items → 1 LLM call, prompt from file | Pending | - |
| TC0072 | Item prompt representation bounded | Pending | - |
| TC0073 | Cross-item_kind cluster | Pending | - |
| TC0074 | LLM omits item → ClusterParseError | Pending | - |
| TC0075 | LLM duplicates item → ClusterParseError | Pending | - |
| TC0076 | Empty input → [] no LLM call | Pending | - |
| TC0077 | Count outside [3,30] → WARN, return | Pending | - |
| TC0078 | Invalid JSON → retry → raise | Pending | - |
| TC0079 | Hallucinated index out of range | Pending | - |
| TC0080 | rank_clusters + RankedClusters signature | Pending | - |
| TC0081 | Significance + novelty populated | Pending | - |
| TC0082 | Prompt contains 3 rubrics | Pending | - |
| TC0083 | Deterministic top-N selection | Pending | - |
| TC0084 | rationale_by_cluster_id populated | Pending | - |
| TC0085 | Novelty hedge instruction in prompt | Pending | - |
| TC0086 | 4 clusters → 3 deep + 1 quick + 0 unsel | Pending | - |
| TC0087 | Scores out of range → clamped + WARN | Pending | - |
| TC0088 | LLM omits cluster id → RankParseError | Pending | - |
| TC0089 | Pre-compose budget exceeded | Pending | - |
| TC0090 | Empty cluster list → empty result | Pending | - |
| TC0091 | compose_paper_deep_dive signature | Pending | - |
| TC0092 | compose-paper.md structure | Pending | - |
| TC0093 | Output has 4 sections | Pending | - |
| TC0094 | All items cited | Pending | - |
| TC0095 | Production-reality line conditional | Pending | - |
| TC0096 | Anti-hype retry path | Pending | - |
| TC0097 | BANNED_HYPE_WORDS ≥ 5 entries | Pending | - |
| TC0098 | 3-section response → retry → raise | Pending | - |
| TC0099 | URL not in cluster → filtered | Pending | - |
| TC0100 | Missing prompt file → clear error | Pending | - |
| TC0101 | compose_repo_deep_dive + maturity_summary | Pending | - |
| TC0102 | compose-repo.md structure + shared anti-hype | Pending | - |
| TC0103 | Output cites concrete shipping signals | Pending | - |
| TC0104 | maturity_summary full-vs-missing scenarios | Pending | - |
| TC0105 | Mixed-kind cluster — all URLs cited | Pending | - |
| TC0106 | BANNED_HYPE_WORDS shared (single source) | Pending | - |
| TC0107 | Repo missing-section → retry → raise | Pending | - |
| TC0108 | format_shipping_signals parametric | Pending | - |
| TC0109 | Malformed hosted_demo_url omits line | Pending | - |
| TC0110 | compose_blog_deep_dive returns blog_post | Pending | - |
| TC0111 | compose-blog.md structure | Pending | - |
| TC0112 | compose_quick_mentions 10 → 1 call → 10 | Pending | - |
| TC0113 | RenderedIssue model + assemble_issue | Pending | - |
| TC0114 | Markdown sections in documented order | Pending | - |
| TC0115 | issue_id is today's UTC date | Pending | - |
| TC0116 | item_kind + maturity indicators | Pending | - |
| TC0117 | 4 deep dives → 4 sections, no padding | Pending | - |
| TC0118 | 6 quick mentions → 6 bullets | Pending | - |
| TC0119 | Zero deep dives → WARN, no raise | Pending | - |
| TC0120 | Zero quick → "Also worth noting" omitted | Pending | - |
| TC0121 | Quick LLM returns 7 from 10 | Pending | - |
| TC0122 | Quick one-liner truncated to 200 | Pending | - |
| TC0123 | Single-item blog cluster — "no corroboration" | Pending | - |
| TC0124 | --- fence in body — front matter parseable | Pending | - |
| TC0125 | assemble_issue deterministic (byte-identical) | Pending | - |

---

## Test Files Plan

```text
tests/
  unit/
    llm/
      test_client.py            # TC0056–TC0069 (with stubbed Anthropic SDK)
    pipeline/
      test_cluster_parse.py     # TC0070, TC0072, TC0076, TC0078, TC0079
      test_cluster_step.py      # TC0071, TC0073, TC0074, TC0075, TC0077
      test_rank_logic.py        # TC0080, TC0083, TC0085 (prompt-string check), TC0087, TC0090
      test_rank_step.py         # TC0081, TC0082, TC0084, TC0086, TC0088, TC0089
      test_compose_paper.py     # TC0091–TC0100
      test_compose_repo.py      # TC0101–TC0107
      test_format_shipping.py   # TC0108, TC0109
      test_compose_blog.py      # TC0110, TC0111, TC0123
      test_compose_quick.py     # TC0112, TC0121, TC0122
      test_assemble.py          # TC0113–TC0120, TC0124, TC0125
  fixtures/
    llm/{cluster,rank,compose,quick_mentions}_*.json|md
    items/cluster_*.yaml
    usage/usage_report_sample.yaml
    sources/source_counts.yaml
  conftest.py                   # FakeLLMClient fixture, frozen clock, prompt-dir override
```

**Per-module coverage floor** (TSD ≥95% line + branch):

- `techletter/llm/client.py` — exercised by `test_client.py`
- `techletter/pipeline/cluster.py` (parse + invariant code) — `test_cluster_parse.py` + `test_cluster_step.py`
- `techletter/pipeline/rank.py` (sort + clamp + budget projection) — `test_rank_logic.py`
- `techletter/pipeline/compose.py::format_shipping_signals` and the four compose functions' style-lint paths — `test_compose_*`
- `techletter/pipeline/assemble.py` — `test_assemble.py` (this module has **no LLM** so the floor is non-negotiable)

---

## Traceability

| Artefact | Reference |
|----------|-----------|
| PRD | [sdlc-studio/prd.md](../prd.md) |
| Epic | [EP0002](../epics/EP0002-composition-pipeline.md) |
| TSD | [sdlc-studio/tsd.md](../tsd.md) |
| Upstream test spec | [TS0001](TS0001-content-ingestion.md) — produces the `list[Item]` consumed by this epic |
| Stories | [US0006](../stories/US0006-llm-client-with-budget-enforcement.md), [US0007](../stories/US0007-cluster-prompt-and-step.md), [US0008](../stories/US0008-rank-prompt-and-step.md), [US0009](../stories/US0009-compose-prompt-for-paper-items.md), [US0010](../stories/US0010-compose-prompt-for-repo-items.md), [US0011](../stories/US0011-compose-blog-quick-mentions-and-issue-assembly.md) |

---

## Open Questions

_None._ All decisions inherited from PRD v0.4.0, TRD v0.3.0, TSD v0.1.0, and EP0002. The live-LLM gated job referenced in EP0002's test plan is intentionally out of scope for this spec — it does not run on PRs and is owned by a nightly workflow (not authored as part of any story).

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial spec authored from EP0002 stories US0006–US0011. 70 test cases across 44 ACs (full coverage). |
| 2026-05-19 | HYL | Reviewed and promoted Draft → Ready: 44/44 ACs covered, 70 TCs, FakeLLMClient contract well-defined and consumed by every cluster/rank/compose TC. The live-LLM gated nightly job remains explicitly out of scope. |

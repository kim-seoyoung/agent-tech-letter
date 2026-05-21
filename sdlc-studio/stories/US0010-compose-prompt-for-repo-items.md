# US0010: Compose prompt for `repo` items

> **Status:** Done
> **Epic:** [EP0002: Composition Pipeline](../epics/EP0002-composition-pipeline.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a repo-specific deep-dive compose prompt that produces "what it does" + maturity + shipping evidence (recent activity / releases / hosted demo / who's using it)
**So that** when the Researcher Subscriber reads about a trending repo, they can tell in 60 seconds whether it's a serious tool worth trying or a hyped demo with no usage.

## Context

### Persona Reference
**Researcher Subscriber** — the direct beneficiary. Their "has anyone shipped this?" concern lives or dies in this story. The `raw` shipping signals captured in US0003 (GitHub adapter) flow into the prompt here.
[Persona details](../personas/stakeholders/users/researcher-subscriber.md)

**HYL (Author/Editor)** — wants the rendered repo section to be the part of the issue subscribers actually screenshot and share. Will reject anything that reads like a press release.

### Background
This is the second of three `item_kind`-conditioned compose prompts. It shares the `DeepDive` model and `ComposeParseError` / `ComposeStyleError` exceptions introduced in US0009. The substantive difference is the framing: where paper compose surfaces methodology + caveats, repo compose surfaces *shipping evidence* — concrete signals that someone, somewhere, is actually using the thing.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Framing | Repo deep dives include: "what it does" + maturity + shipping evidence | Prompt structure mirrors these three sections |
| Epic | Output shape | 1–2 paragraphs per deep dive | Prompt enforces length bound |
| PRD | Shipping signals | `Item.raw` for repos includes `stars`, `last_commit_at`, `has_recent_release`, `hosted_demo_url`; `Item.maturity` is set by adapter | Prompt receives these and uses them in the body |
| Epic | Voice | No marketing-flavoured writing | Anti-hype word list (shared with US0009) |
| Epic | Cost | One LLM call per deep dive | Same call budget as other compose steps |

---

## Acceptance Criteria

### AC1: Compose function for repo kind is defined
- **Given** the module `techletter.pipeline.compose` exists (introduced in US0009)
- **When** an engineer imports `from techletter.pipeline.compose import compose_repo_deep_dive`
- **Then** the signature is `compose_repo_deep_dive(cluster: Cluster, rationale: str, llm: LlmClient) -> DeepDive`
- **And** the returned `DeepDive` has `item_kind == "repo"` and `maturity_summary` populated (a 1-sentence human-readable summary like "Active beta — 1.2K stars, last commit 4 days ago, no release tag yet").

### AC2: Prompt lives in `prompts/compose-repo.md`
- **Given** the prompt file `prompts/compose-repo.md`
- **When** the compose function loads it
- **Then** the prompt template includes:
  - System role section: writing for a research-aware engineer who wants to know if they should try the repo.
  - Shared anti-hype instruction list (same banned words as US0009 — define them once in code, not in both prompts).
  - Three-section structure: "What it does (in plain terms)", "Maturity", "Shipping evidence".
  - Instructions to surface concrete numbers from `raw` (stars, last commit date, release status, hosted demo URL).
  - Length bound: 1–2 paragraphs (≤300 words target).

### AC3: Output uses concrete shipping signals
- **Given** a repo cluster where the primary item's `raw` is `{"stars": 1234, "last_commit_at": "2026-05-15T...", "has_recent_release": true, "hosted_demo_url": "https://example.com/demo"}`
- **When** `compose_repo_deep_dive(...)` runs
- **Then** the rendered body references the specific numbers (`1,234 stars`, recent commit, hosted demo) — not vague phrases like "popular" or "active"
- **And** the prompt receives these fields in a structured block; the LLM is instructed to cite at least two specific signals

### AC4: Maturity summary is a single human-readable sentence
- **Given** a cluster's primary item has `maturity = "beta"` and shipping signals as above
- **When** the compose function returns
- **Then** `maturity_summary` is a single sentence combining the maturity tag and shipping signals (e.g., `"Active beta — 1.2K stars, last commit 4 days ago, hosted demo available."`)
- **And** when `maturity = "unknown"` or signals are missing, the summary explicitly says so (e.g., `"Maturity unclear — limited shipping signal."`)

### AC5: All contributing items cited
- **Given** a cluster with a primary repo plus a blog post discussing it (a mixed cluster routed to repo compose because repo dominates)
- **When** the compose returns
- **Then** `cited_urls` includes both URLs
- **And** the body cites them inline via markdown links

### AC6: Anti-hype voice (shared lint)
- **Given** the shared `BANNED_HYPE_WORDS` constant from US0009
- **When** the compose output is style-linted
- **Then** the same retry-once-then-WARN behaviour applies as in US0009 (no crash, but flagged)

### AC7: Empty / malformed response handling (shared)
- **Given** the LLM returns a response missing sections or with empty body
- **When** the compose function runs
- **Then** it retries once with an explicit correction prompt; second failure raises `ComposeParseError`

---

## Scope

### In Scope
- `compose_repo_deep_dive` function in `techletter/pipeline/compose.py`.
- `prompts/compose-repo.md`.
- Reuse of `DeepDive`, `ComposeParseError`, `ComposeStyleError`, and the anti-hype word list from US0009.
- `format_shipping_signals(item) -> str` helper that converts `raw` shipping signals into a stable, human-readable string block for the prompt.
- Unit tests with fake LLM returning canned repo-shaped responses.

### Out of Scope
- Paper compose (US0009).
- Blog compose + quick mentions + assembly (US0011).
- Adding new shipping signals to the GitHub adapter (already done in US0003).
- "Plain-language" framings aimed at non-coder readers — explicitly out of scope per ADR-008 (single-tier audience).

---

## Technical Notes

- `format_shipping_signals(item)` is a small pure function: takes `item.raw` and `item.maturity`, returns a Markdown-ish text block like:
  ```
  - Maturity: beta
  - Stars: 1,234
  - Last commit: 2026-05-15 (4 days ago)
  - Recent release: yes
  - Hosted demo: https://example.com/demo
  ```
  This block is interpolated into the prompt verbatim. Stable formatting makes prompt iteration tractable.
- The LLM is instructed to *use* the signals but write naturally — not to bullet-list them in the output (that's a different style decision; can revisit if subscribers want bullets).
- Maturity-summary formatting is mostly templatic; the LLM polishes the sentence rather than inventing it.

### API Contracts
- `compose_repo_deep_dive(cluster: Cluster, rationale: str, llm: LlmClient) -> DeepDive`
- `format_shipping_signals(item: Item) -> str` — helper, internal but unit-tested.

### Data Requirements
None persistent.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Cluster's primary repo has no shipping signals (all `raw` fields missing) | `format_shipping_signals` returns `"Maturity: unknown\n(no shipping signals available)"`; prompt receives that string; LLM produces an honest "maturity unclear" body |
| Multi-repo cluster (rare — two repos clustered as the same topic) | `format_shipping_signals` is called for the highest-starred repo; others' signals available in cited URLs |
| Mixed-kind cluster routed to repo compose because repos dominate | Function still runs; cites all contributing items including blogs/papers |
| `hosted_demo_url` is malformed (not actually a URL) | `format_shipping_signals` omits the demo line; doesn't crash |
| `stars` is `None` or `0` | Renders as `"Stars: 0"` (zero is information, not absence) |
| `last_commit_at` is a malformed string | `format_shipping_signals` falls back to "Last commit: unknown"; no crash |
| LLM produces a body that doesn't reference any concrete signal (despite having them) | Single retry with an explicit "cite at least two specific signals from the block above"; second failure → WARN log, return result (HYL's call at PR time) |
| `maturity_summary` produced by LLM is multi-sentence (e.g., 3 sentences) | Truncate to first sentence; log WARN; this is a style nit, not worth aborting |
| LLM cites a URL not in the cluster | Filtered out of `cited_urls` (same as US0009) |
| LLM produces hype words | Style retry once, then WARN (same as US0009) |
| LLM unavailable | Propagates; orchestrator aborts |

---

## Test Scenarios

- [ ] Fake LLM returns 3-section response over a repo cluster with full shipping signals → `DeepDive` has all sections, `maturity_summary` is one sentence containing specific numbers.
- [ ] Repo cluster with `maturity = "unknown"` and all `raw` signals missing → `maturity_summary` says "Maturity unclear"; body still produced.
- [ ] Repo cluster with `stars = 0` → "Stars: 0" appears in formatted signals; body doesn't claim "no users" without basis.
- [ ] `format_shipping_signals` unit tests cover: all fields present; all fields missing; partial fields; malformed `last_commit_at`.
- [ ] LLM body without concrete signals → retry triggered.
- [ ] LLM body with banned hype words → style retry, then accept on second failure.
- [ ] Mixed-kind cluster: repo + blog → both URLs in `cited_urls`.
- [ ] LLM omits sections → re-prompt; second failure → `ComposeParseError`.
- [ ] `prompts/compose-repo.md` missing → clear startup error.
- [ ] Anti-hype word list is shared, not duplicated (verified by importing the constant from a single module).

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0008](US0008-rank-prompt-and-step.md) | Service | Selected cluster + rationale | Draft |
| [US0009](US0009-compose-prompt-for-paper-items.md) | Schema/Shared | `DeepDive` model, exceptions, anti-hype list | Draft |
| [US0006](US0006-llm-client-with-budget-enforcement.md) | Service | `LlmClient` | Draft |

### External Dependencies
None beyond US0006.

---

## Estimation

**Story Points:** 3
**Complexity:** Low-Medium. Less prompt iteration than US0009 because the `format_shipping_signals` block makes the LLM's job concrete. `maturity_summary` formatting is the main quality lever.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0002. |

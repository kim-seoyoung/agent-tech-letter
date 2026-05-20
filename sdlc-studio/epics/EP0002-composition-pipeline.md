# EP0002: Composition Pipeline

> **Status:** Draft
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19
> **Target Release:** v1.0 (first issue shipped)

## Summary

Turn a list of normalised `Item`s into a `RenderedIssue` — a canonical Markdown issue with 3 deep dives (flex 2–5) and 10 quick mentions, framed differently for paper / blog / repo. Three pipeline stages: cluster items into topics, rank clusters with `item_kind`-aware significance, compose deep-dive and quick-mention copy via LLM prompts that live in `prompts/`. Token usage is bounded by a configurable 200K budget enforced *before* the compose step.

## Inherited Constraints

| Source | Type | Constraint | Impact |
|--------|------|------------|--------|
| PRD | Audience | Single tier: research-aware engineer (PRD v0.4.0) | Composer voice and framing target one reader profile |
| PRD | Output shape | 3 deep dives + 10 quick mentions; flex 2–5 deep dives | Composer must produce within this shape |
| PRD | Per-item rendering | Each item shows `item_kind` and known `maturity`; framing conditioned on `item_kind` | Prompts must branch on `item_kind` |
| PRD | Cost | 200K token budget per run; abort *before* compose if projected to exceed | Budget enforcement is a hard gate, not an aspiration |
| TRD | LLM | Anthropic Claude Sonnet-class (e.g., `claude-sonnet-4-6`) | One provider; pluggable interface for future flexibility |
| TRD | Prompts | `prompts/*.md` files version-controlled; iterable in PRs | Prompts are not inlined in code |
| TRD | Reliability | tenacity-wrapped LLM calls; abort run if LLM is unrecoverably down | Compose-step failure should not produce a half-finished PR |
| TRD | Stateless | No prior-week memory in v1 | "Novelty" criterion stays hedged on state availability |

---

## Business Context

### Problem Statement
A pile of normalised items is not a newsletter. The hard part — and the reason this is more than an RSS aggregator — is turning that pile into a small set of substantive topics, ranked by genuine significance, and writing about each one in a voice that respects the reader's time and technical fluency.

**PRD Reference:** [§3 Feature Inventory — F-02, F-03](../prd.md#3-feature-inventory)

### Value Proposition
This epic is where the editorial intelligence lives. Without it, the project is a "feeds in / lines out" tool. With it, the project is a newsletter that earns subscribers' weekly time.

### Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Issues produced within token budget | n/a | 100% (run aborts otherwise) | `RenderedIssue.meta.tokens_used` ≤ budget |
| Deep dives per issue | n/a | 3 (range 2–5) | Markdown structure check |
| Quick mentions per issue | n/a | 10 | Markdown structure check |
| HYL approval rate (PR merged without major edits) | n/a | ≥ 70% (target; measured anecdotally) | HYL self-report after first 4 issues |

---

## Scope

### In Scope
- LLM client wrapper with token-counting + budget enforcement.
- Cluster prompt + step: groups items into topics.
- Rank prompt + step: `item_kind`-aware significance + (hedged) novelty scoring.
- Compose prompts (one per `item_kind`): paper, repo, blog_post.
- `RenderedIssue` model and Markdown renderer.
- Front-matter generation (issue_id, date, token usage, source counts).
- Prompts directory structure under `prompts/`.

### Out of Scope
- Ingestion (EP0001).
- Approval workflow / PR creation (EP0003).
- Channel delivery (EP0004).
- Prior-week state / true novelty detection — future CR.
- Multi-audience composition — explicitly out per PRD v0.4.0 / ADR-008.

### Affected Personas
- **Researcher Subscriber:** primary — this epic determines whether the rendered issue earns their weekly time. Their concerns (methodology framing, provenance, production reality) live here.
- **HYL:** secondary — composes the draft for HYL to approve. HYL's editorial standard is the quality bar.

---

## Acceptance Criteria (Epic Level)

- [ ] LLM client wrapper tracks token usage per call; pre-compose budget check aborts the run if projected total would exceed the configured budget (default 200K).
- [ ] Cluster step produces clusters spanning multiple sources and `item_kind`s.
- [ ] Rank step applies differentiated rubrics: papers scored on methodological substance + cross-citation; repos scored on shipping signals (recent activity, releases, hosted demo); blog posts scored on author authority + cross-source corroboration.
- [ ] Compose step produces exactly the issue shape: 3 deep dives (range 2–5 acceptable) + 10 quick mentions.
- [ ] Each rendered item shows its `item_kind` and `maturity` (when known).
- [ ] Deep-dive framing is `item_kind`-conditioned per PRD F-03 acceptance criteria.
- [ ] `RenderedIssue` is produced as canonical Markdown with a front matter block (`issue_id`, date, token usage, source counts).
- [ ] All prompts live as `.md` files under `prompts/` and are loaded at runtime — no inline LLM prompts in code.

---

## Dependencies

### Blocked By

| Dependency | Type | Status | Owner |
|------------|------|--------|-------|
| EP0001 Content Ingestion | Epic | Draft | HYL |

### Blocking

| Item | Type | Impact |
|------|------|--------|
| EP0003 Orchestration | Epic | Draft workflow's compose step depends on this epic |
| EP0004 Delivery | Epic | Delivery sends what this epic produces |

---

## Risks & Assumptions

### Assumptions
- Anthropic API is reliable enough that occasional 429/5xx errors are recoverable via tenacity (3–5 retries).
- A Sonnet-class model can produce acceptable cluster + rank + compose results within the 200K budget for typical weekly volumes (50–500 items normalised).
- Prompt iteration is the dominant form of quality work post-launch; the prompts-in-PR pattern supports this.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Token budget too tight on busy weeks | M | M | Truncate item summaries pre-cluster; if still over, drop quick-mention candidates (preserve deep-dive quality); abort before compose with a clear "what blew the budget" log |
| Compose step produces hype-y / marketing voice | M | M | System prompt explicitly bans marketing voice; ban list iterated in PRs; HYL has merge authority and edits before send |
| Cluster step over-merges substantively different papers | M | M | Cluster prompt instructed to keep methodologically different work in separate clusters; HYL catches in PR review |
| LLM produces wrong `item_kind` framing | L | M | Compose prompt receives `item_kind` explicitly and is told which template applies; framing tests assert structure of each `item_kind` case |
| Latency exceeds 5-min draft target | L | M | Cluster and rank are single calls (not item-by-item); compose is one call per deep dive (≤5) plus a batch call for quick mentions. Total LLM round-trips: 7–10. Well under 5 min. |

---

## Technical Considerations

### Architecture Impact
This epic sits between EP0001 (sources) and EP0003 (orchestration). It's the most prompt-heavy and the most likely to evolve post-launch, which is why ADR-002 (adapter pattern) and ADR-005 (dev cache) matter here — both enable rapid iteration on prompts without retesting the whole pipeline.

### Integration Points
- **Anthropic Messages API** via the `anthropic` SDK.
- **Token counting** via SDK's built-in tokenizer for the model in use.
- **Prompts directory** loaded at startup by the LLM wrapper.

---

## Sizing

**Story Points:** ~21
**Estimated Story Count:** 6

**Complexity Factors:**
- LLM prompt design is the highest-uncertainty work in the project.
- Budget enforcement requires *projecting* token usage before the compose step — non-trivial because it requires accounting for prompt + items input + expected output.
- Three `item_kind`-conditioned compose prompts means three prompt files to iterate, each with different acceptance criteria.

---

## Story Breakdown

Stories generated 2026-05-19. See [Story Index](../stories/_index.md) for full details.

- [ ] [US0006](../stories/US0006-llm-client-with-budget-enforcement.md) — LLM client wrapper + budget enforcement (3 pts)
- [ ] [US0007](../stories/US0007-cluster-prompt-and-step.md) — Cluster prompt + step (5 pts)
- [ ] [US0008](../stories/US0008-rank-prompt-and-step.md) — Rank prompt + step (`item_kind`-aware) (5 pts)
- [ ] [US0009](../stories/US0009-compose-prompt-for-paper-items.md) — Compose prompt for `paper` items (5 pts)
- [ ] [US0010](../stories/US0010-compose-prompt-for-repo-items.md) — Compose prompt for `repo` items (3 pts)
- [ ] [US0011](../stories/US0011-compose-blog-quick-mentions-and-issue-assembly.md) — Compose `blog_post` + quick mentions + `RenderedIssue` assembly (8 pts)

**Total:** 29 story points across 6 stories.

---

## Test Plan

**Test Spec:** [TS0002](../test-specs/TS0002-composition-pipeline.md) — 70 test cases (TC0056–TC0125), 44/44 ACs covered.

- Unit: budget math (US0006), JSON parse + invariants (US0007/US0008), `format_shipping_signals` (US0010), and pure markdown `assemble_issue` (US0011) are all deterministic and unit-testable; the assembler has a byte-identical determinism check (TC0125) which feeds EP0003's idempotency story.
- Integration (stubbed LLM): every cluster/rank/compose path runs against `FakeLLMClient`-canned JSON fixtures. No live Anthropic call in CI. Pre-compose budget gate (TC0089) is verified end-to-end through the rank step's projection.
- Integration (live LLM, gated): one nightly/on-demand job against real Anthropic API, `RUN_LIVE_LLM_TESTS=1`, bounded ≤10K tokens. **Owned by a separate nightly workflow — not part of TS0002 or the PR test suite.**

---

## Open Questions

_None._ All design decisions inherited from PRD v0.4.0 and TRD v0.3.0.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial epic created from PRD v0.4.0 F-02 + F-03. |
| 2026-05-19 | HYL | Story breakdown linked: 6 stories (US0006–US0011, 29 pts total). |
| 2026-05-19 | HYL | Test plan linked to [TS0002](../test-specs/TS0002-composition-pipeline.md) — 70 TCs, 44/44 ACs covered. |

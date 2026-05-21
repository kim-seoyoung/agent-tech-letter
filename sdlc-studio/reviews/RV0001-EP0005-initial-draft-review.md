# RV0001: EP0005 Initial Draft Review

> **Reviewer:** Claude (via `/sdlc-studio epic review --epic EP0005`)
> **Date:** 2026-05-21
> **Epic:** [EP0005: Common HTML Rendering (Web + Email)](../epics/EP0005-common-html-rendering.md)
> **Mode:** Initial draft review (no cascade — epic + all stories are fresh Draft, no impl)
> **CR origin:** [CR-0001](../change-requests/CR0001-common-html-rendering.md)

## Scope

- Epic: EP0005 (Draft)
- Stories: US0023, US0024, US0025, US0026, US0027 (all Draft)
- No implementation exists yet; "cascade" is trivially a self-review.

## Summary

**Overall: solid Draft, mostly ready to promote to Ready after resolving 1 blocking inconsistency and 2 small AC refinements.** 16 pts across 5 stories is realistic; mapping from CR-0001 items is clean 1:1; dependency graph is correct and parallelizable. Three issues need fixing before any story is moved to Ready.

---

## Findings

### 🔴 Blocker — internal inconsistency

#### F-1. US0023 AC8 contradicts its own Open Question

- **AC8** asserts `.gitattributes` MUST contain `drafts/*.json linguist-generated` (treats it as a hard requirement).
- **Open Questions** (inherited from CR-0001) still asks whether to do this.

These can't both be true. Either:
- **(a)** Drop the open question (commit to AC8 as written) → recommended; cost is trivial, value is real for PR review experience.
- **(b)** Remove AC8 (mark it as out-of-scope / follow-up) → would weaken the story.

**Recommendation:** Resolve as (a). Edit US0023 to remove the open question; the AC stays.

### 🟡 Should-fix — AC quality

#### F-2. US0026 AC5 ("every visually styled element has a `style=""`") is too broad

Premailer doesn't guarantee inlining for every rule — selectors with no matching element get dropped, `@media` queries are preserved as `<style>` (which would violate AC2), `!important` handling depends on settings. The blanket assertion will be hard to verify and may produce false positives.

**Recommendation:** Tighten to:
> "Representative styled elements (e.g., the deep-dive `<h2>`, the `.tag` span, the body `<a>`) carry a `style="..."` attribute whose computed values match the corresponding token values from `tokens.py`."

Drop the "every" universal claim. The combination of AC2 (no `<style>` blocks survive) + spot-checked elements is sufficient.

#### F-3. US0025 → US0026 helper coupling is implicit

Both stories convert `DeepDive.body_md` to HTML via `markdown-it-py`. US0025 introduces `_body_md_to_html`; US0026 says "extract into `_common.py` if convenient." Convenience-based dedup tends to drift.

**Recommendation:** Make US0026 explicitly depend on US0025's helper:
- Add to US0026 Story Dependencies: "US0025 → reuse `_body_md_to_html` (do not duplicate)."
- Add an AC: "`html_email` imports the markdown-to-HTML helper from US0025's module (or a shared `_common.py`); no second `markdown-it-py` instantiation lives in `html_email.py`."

### 🟡 Should-fix — risk gap

#### F-4. No risk captured for "design token iteration delays US0024"

US0024 sizing is 2 pts assuming the token values are set quickly. Real-world: HYL may iterate visually before locking the palette/spacing, which can stretch US0024 by 1–2 days.

**Recommendation:** Add a row to EP0005 Risks:
> "Designer/HYL iterates on token values during US0024 — Likelihood M / Impact L / Mitigation: lock the *keys* in US0024 (AC1) so US0025/26 can proceed against placeholder values; the actual hex/px refinements can land in a follow-up commit without restructuring."

### 🟢 Acceptable — open questions, defer

These open questions can stay open without blocking Ready, as long as the leaning answer is captured:

- **US0024 OQ1** ("lock token set now or later") → leaning "lock now." Already covered by AC1's explicit key list — the OQ is effectively answered, just remove it.
- **US0025 OQ1** ("`lang="ko"` configurable") → defer is fine; not v1.1.
- **US0025 OQ2** ("`og:` meta for Telegram preview") → defer to CR-0002 epic.
- **US0026 OQ1** ("Outlook `mso-` hacks") → defer until smoke testing reveals concrete breakage.
- **US0026 OQ2** ("premailer cache here vs in adapter") → defer to US0027 as written.
- **US0027 OQ1** ("format-change banner") → defer; release commit message is enough.

**Recommendation:** Remove US0024 OQ1 (answered by AC1). Leave the rest as-is; they're documented forward-deferrals, not blockers.

### 🟢 Strengths (worth keeping)

- **Idempotency invariant explicitly protected** (US0023 AC7, US0027 AC8) — `content_sha256` regression-pinned against a frozen golden. This is the single most important guard for EP0003 compatibility.
- **Privacy invariant carried forward** (US0027 AC4 references TC0214 from EP0004) — no risk of accidental BCC regression.
- **Dependency graph is realistic and parallel-friendly:** US0023 + US0024 in parallel, then US0025 → US0026 → US0027.
- **Renderer determinism is enforced at the AC level** (US0025 AC1/AC6, US0026 AC1) — supports golden-fixture-based CI guards.
- **Out-of-scope is well-drawn** — every "no, not in this epic" boundary (MJML, dark mode, images, Slack Block Kit, GitHub Pages publishing) is named.
- **Sizing is internally consistent** — 16 pts across 5 stories with US0023 (4) and US0026 (4) as the heaviest, US0024 (2) as the lightest. Matches complexity.

---

## Ready Criteria Check

Per `reference-decisions.md#story-ready`:

| Story | Independent | Negotiable | Valuable | Estimable | Small | Testable | Blockers |
|-------|-------------|------------|----------|-----------|-------|----------|----------|
| US0023 | ✓ (with US0024) | ✓ | ✓ | ✓ (4 pts) | ✓ | ✓ | **F-1** |
| US0024 | ✓ | ✓ | ✓ | ✓ (2 pts) | ✓ | ✓ | — |
| US0025 | depends on US0024 | ✓ | ✓ | ✓ (3 pts) | ✓ | ✓ | — |
| US0026 | depends on US0024, US0025 | ✓ | ✓ | ✓ (4 pts) | ✓ | ✓ | **F-2, F-3** |
| US0027 | depends on US0026 | ✓ | ✓ | ✓ (3 pts) | ✓ | ✓ (AC9 manual, declared) | — |

**Verdict:** Three stories (US0024, US0025, US0027) are ready to promote to Ready as-is. US0023 needs F-1 resolved. US0026 needs F-2 and F-3 applied.

---

## Status Consistency

| Artifact | Status | Consistent? |
|----------|--------|-------------|
| CR-0001 | In Progress | ✓ (Linked Epics filled, revision history updated) |
| EP0005 | Draft | ✓ |
| US0023–US0027 | Draft | ✓ |
| `epics/_index.md` | EP0005 = Draft, totals correct | ✓ |
| `stories/_index.md` | 5 new Draft entries, EP0005 subtotal, dep graph | ✓ |
| `change-requests/_index.md` | Proposed 1 / In Progress 1, "Actioned CRs" row | ✓ |
| `prd.md` F-05 description | Annotated with CR-0001 reference | ✓ |

No status drift detected.

---

## Recommended Next Actions

1. **Apply F-1, F-2, F-3, F-4** — small edits across US0023, US0024, US0026, EP0005. Estimated 15 min.
2. Promote US0024, US0025, US0027 to **Ready** immediately.
3. Promote US0023 and US0026 to **Ready** after F-1/F-2/F-3 land.
4. Once all 5 are Ready, run `/sdlc-studio epic plan --epic EP0005` to preview the implementation workflow.
5. Then `/sdlc-studio epic implement --epic EP0005` (sequential is fine — 5 stories, partial parallelism only between US0023 & US0024 in the first wave).

## Review Cache

- Stored at `sdlc-studio/.local/review-state.json` (not written here; this is a first-time review)
- No previous review timestamps to compare against.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | Claude (via /sdlc-studio epic review --epic EP0005) | Initial draft review. 4 findings identified (1 blocker, 3 should-fix); 3/5 stories ready, 2/5 need edits. |
| 2026-05-21 | Claude (auto-mode follow-up) | All 4 findings applied. US0023 OQ1 resolved (linguist-generated committed). US0026 AC5 tightened + AC10 added (helper coupling). US0025 API contract clarified. EP0005 risks gained token-iteration row. US0024 OQ1 resolved (lock now). All 5 stories promoted to Ready. Indexes updated. |

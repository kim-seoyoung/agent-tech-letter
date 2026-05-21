# RV0002: EP0006 Initial Draft Review

> **Reviewer:** Claude (via `/sdlc-studio epic review --epic EP0006`)
> **Date:** 2026-05-21
> **Epic:** [EP0006: GitHub Pages Publisher + Telegram Link Mode](../epics/EP0006-github-pages-and-telegram-link-mode.md)
> **Mode:** Initial draft review (no cascade — epic + all stories are fresh Draft, no impl)
> **CR origin:** [CR-0002](../change-requests/CR0002-github-pages-and-telegram-link-mode.md)

## Scope

- Epic: EP0006 (Draft)
- Stories: US0028, US0029, US0030, US0031, US0032 (all Draft)
- No implementation exists yet.

## Summary

**Overall: tight Draft, mostly ready to promote after resolving 1 cross-story blocker and 3 AC refinements.** 14 pts across 5 stories is sane; mapping from CR-0002 items is 1:1; dependency graph is correct (US0028 → {US0029, US0030 in parallel} → US0031 → US0032). The lessons from RV0001 (helper coupling, overbroad ACs, exception-class ownership) recur here in a different form — fixing them upfront avoids the mid-implementation surprises we hit in EP0005.

---

## Findings

### 🔴 Blocker — cross-story exception class ownership

#### F-1. `PublisherError` is referenced by US0029 but never introduced by US0028

- **US0029 AC5/AC6** require raising `PublisherError` for dirty worktree and push failure.
- **US0029 Technical Notes** say: "Define `PublisherError` in `publishers/base.py` (or a sibling) and re-export."
- **US0028 (the Protocol/schema story)** does NOT mention `PublisherError` anywhere.

If US0028 ships first as written, `PublisherError` doesn't exist. If US0029 tries to introduce it, it has to modify `publishers/base.py` — which US0028 just shipped — creating a hub-file conflict and undermining the "US0028 is pure schema" framing.

This is the exact same shape as RV0001's F-3 (US0025↔US0026 helper coupling), where an implicit cross-story dependency wasn't made explicit.

**Recommendation:** Decide ownership upfront. Two clean options:
- **(a)** Move `PublisherError` to US0028 — extend US0028 AC2 with a new AC: "`PublisherError(Exception)` defined in `publishers/base.py` and re-exported from `publishers/__init__.py`. Used by all `Publisher` implementations to signal backend-side failures."
- **(b)** Move it to US0029 — accept that US0029 adds a small symbol to `publishers/base.py` and document that in US0029's Scope.

Lean **(a)**: pairs naturally with the Protocol; the exception class is part of the same contract.

### 🟡 Should-fix — overbroad AC claim

#### F-2. US0031 AC5 "bit-for-bit identical to EP0004" is too strong

The story's Technical Notes describe extracting the existing `send()` body into a private `_send_inline_html` method. That refactor preserves *behavior* (Bot API payloads) but does not preserve internal call graphs, byte-level Python bytecode, or anything else "bit-for-bit" might mean.

The same shape as RV0001's F-2 (US0026 AC5 "every styled element" was too broad).

**Recommendation:** Rephrase AC5 to:

> **AC5: `inline_html` mode — Bot API payloads behaviorally equivalent to EP0004**
> - **Given** `mode="inline_html"` and the same `issue` + `recipients`
> - **When** the adapter's outbound Bot API calls are captured
> - **Then** the sequence of `(chat_id, text, parse_mode, disable_web_page_preview)` tuples is identical to what EP0004's `TelegramAdapter.send` produced for the same inputs
> - **And** the existing EP0004 tests (`tests/unit/delivery/test_slack_telegram.py`) still pass without modification

Drop the "bit-for-bit" framing. The Bot API call sequence is the contract that matters.

### 🟡 Should-fix — filesystem-level claim that's actually about content

#### F-3. US0029 AC8 "mtime preserved" is the wrong invariant

> AC8 currently: "They are NOT overwritten (mtime preserved when content matches)"

`mtime` is filesystem state and depends on the OS, mount options, and how `git checkout` materializes files. It's not a meaningful test target. What we actually care about is: **the seed files are written exactly once; second-publish doesn't touch them**.

**Recommendation:** Rephrase AC8:

> **AC8: `.nojekyll` and `robots.txt` are written only when missing**
> - **Given** these files exist from a prior publish with the expected content
> - **When** `publish(issue)` runs again
> - **Then** the publisher does **not** call `Path.write_text` / `Path.write_bytes` on them
> - **And** the seed step does NOT contribute to the `git diff --quiet` check (i.e., even if a future change altered `robots.txt`, that change would not be a publish trigger by itself — that's a separate concern)

### 🟡 Should-fix — vague scrubbing scope

#### F-4. US0029 AC6 doesn't name what to scrub

> AC6 currently: "the exception message does NOT contain `GITHUB_TOKEN`, PAT, or SSH key path"

A test of "no `GITHUB_TOKEN` substring" is shallow — git typically embeds the token in HTTPS URLs as `https://x-access-token:ghs_XXXX@github.com/...`. The substring to scrub is the token value, not the env var name. Without naming the patterns, the implementation can pass the test trivially while still leaking.

**Recommendation:** Strengthen AC6:

> **AC6: Push failure surfaces with all credential patterns scrubbed**
> The exception message and any captured log records do NOT contain:
> - The literal value of `os.environ["GITHUB_TOKEN"]` (if set)
> - Any URL of the form `https?://[^@]+@github.com/...` (token-embedded HTTPS push URLs — replace user-info with `[REDACTED]`)
> - Any string matching `ghs_[A-Za-z0-9]{36,}` or `ghp_[A-Za-z0-9]{36,}` (GitHub PAT/installation token prefixes)
> - The full path of `SSH_AUTH_SOCK` or `~/.ssh/*_rsa`

Implementation should run git's stderr through a single regex-based scrubber before bubbling it up.

### 🟢 Acceptable — minor

- **US0028 AC5 "No backend yet"** is essentially a state-of-the-tree assertion that becomes false the moment US0029 runs. Not technically wrong (each story's ACs are evaluated at story completion), but the framing is awkward. Optional rephrase: "After this story alone, the `publishers/` package contains only the schema files." — defer.

### 🟢 Strengths (worth keeping)

- **Dependency graph is realistic and parallel-friendly:** US0028 → {US0029, US0030} → US0031 → US0032.
- **Backward compatibility is intentional and tested** (US0031 AC8): old `channels.yaml` without `mode`/`publishers` defaults to `inline_html`. Subscribers on the upgrade path don't break.
- **Security-by-obscurity is explicit**, not folkloric: 16-hex content hash in URL, `noindex,nofollow` meta, `robots.txt` Disallow, no index page. EP0006 Summary calls out "public by URL" as an intentional limitation.
- **Idempotency invariant carries forward** (US0029 AC3, US0032 schema): same `content_sha256` → same URL → no new commit.
- **Token-scrub invariant explicit** (US0031 AC9 + US0029 AC6) extends TC0247 from EP0004 to the publisher/teaser paths.
- **AC9 honesty** in US0032: E2E smoke is manual / HYL-owned and that's stated up front, not hidden behind a TODO comment.
- **Sizing is internally consistent** — US0029 (5) is the heaviest (git plumbing + test infra), US0028/US0030/US0032 (2 each) are the lightest, US0031 (3) is the wiring story. Matches complexity shape.

---

## Ready Criteria Check

Per `reference-decisions.md#story-ready`:

| Story | Independent | Negotiable | Valuable | Estimable | Small | Testable | Blockers |
|-------|-------------|------------|----------|-----------|-------|----------|----------|
| US0028 | ✓ | ✓ | ✓ | ✓ (2 pts) | ✓ | ✓ | **F-1** (must own `PublisherError`) |
| US0029 | depends on US0028 | ✓ | ✓ | ✓ (5 pts) | ✓ | ✓ (mocked git) | **F-1, F-3, F-4** |
| US0030 | ✓ | ✓ | ✓ | ✓ (2 pts) | ✓ | ✓ (incl. hypothesis) | — |
| US0031 | depends on US0028/29/30 | ✓ | ✓ | ✓ (3 pts) | ✓ | ✓ | **F-2** |
| US0032 | depends on US0031 | ✓ | ✓ | ✓ (2 pts) | ✓ | ✓ (AC7 manual, declared) | — |

**Verdict:** Two stories (US0030, US0032) are ready as-is. US0028/US0029/US0031 need their findings applied before promotion. US0029 carries the most edits.

---

## Status Consistency

| Artifact | Status | Consistent? |
|----------|--------|-------------|
| CR-0002 | In Progress | ✓ (Linked Epics filled, revision history updated) |
| EP0006 | Draft | ✓ |
| US0028–US0032 | Draft | ✓ |
| `epics/_index.md` | EP0006 = Draft, totals correct (5 Done + 1 Draft = 6) | ✓ |
| `stories/_index.md` | 5 new Draft, EP0006 subtotal, dependency graph | ✓ |
| `change-requests/_index.md` | In Progress 1 / Complete 1, "Actioned CRs" row | ✓ |
| `prd.md` F-07 description | Annotated with CR-0002 reference | ✓ |

No status drift detected.

---

## Recommended Next Actions

1. **Apply F-1, F-2, F-3, F-4** — small edits across US0028, US0029, US0031. Estimated ~15 min.
2. Promote US0030 and US0032 to **Ready** immediately.
3. Promote US0028, US0029, US0031 to **Ready** after the findings land.
4. Once all 5 are Ready, run `/sdlc-studio epic plan --epic EP0006` to preview the implementation workflow.
5. Then `/sdlc-studio epic implement --epic EP0006` (sequential — first wave US0028 alone since the Protocol is the foundation; then {US0029, US0030} in parallel; then US0031; then US0032).
6. After implementation, schedule the manual E2E smoke (US0032 AC7) when HYL has 15 minutes + real secrets.

## Review Cache

- This is `RV0002`, immediately following `RV0001` (which covered EP0005 — now Done).
- No previous review for EP0006 to compare against.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | Claude (via /sdlc-studio epic review --epic EP0006) | Initial draft review. 4 findings (1 blocker, 3 should-fix); 2/5 stories ready, 3/5 need edits. Same shapes as RV0001 (cross-story coupling not made explicit; overbroad ACs) recurring — applying the fix once now saves implementation-time surprise. |
| 2026-05-21 | Claude (auto-mode follow-up) | All 4 findings applied. US0028 gained AC4b (PublisherError exception class). US0029 AC6 strengthened with concrete scrub patterns + regex-filter requirement. US0029 AC8 reframed as write-only-if-missing (no mtime semantics). US0031 AC5 reframed as Bot API payload behavioral equivalence (not bit-for-bit). |

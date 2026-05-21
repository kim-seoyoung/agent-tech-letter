# Story Registry

**Last Updated:** 2026-05-20
**Personas Reference:** [Personas Index](../personas/index.md)

## Summary

| Status | Count |
|--------|-------|
| Draft | 0 |
| Ready | 0 |
| Planned | 0 |
| In Progress | 0 |
| Review | 0 |
| Done | 22 |
| **Total** | **22** |

## Stories by Epic

### [EP0001: Content Ingestion](../epics/EP0001-content-ingestion.md)

| ID | Title | Status | Points | Owner |
|----|-------|--------|--------|-------|
| [US0001](US0001-item-model-and-source-adapter-protocol.md) | `Item` model + `SourceAdapter` protocol | Done | 3 | HYL |
| [US0002](US0002-arxiv-source-adapter.md) | arXiv source adapter | Done | 3 | HYL |
| [US0003](US0003-github-trending-source-adapter.md) | GitHub Trending source adapter | Done | 5 | HYL |
| [US0004](US0004-rss-source-adapter.md) | RSS source adapter | Done | 2 | HYL |
| [US0005](US0005-source-registry-and-config-loader.md) | Source registry + `config/sources.yaml` loader | Done | 3 | HYL |

**EP0001 subtotal:** 5 stories, 16 points

### [EP0002: Composition Pipeline](../epics/EP0002-composition-pipeline.md)

| ID | Title | Status | Points | Owner |
|----|-------|--------|--------|-------|
| [US0006](US0006-llm-client-with-budget-enforcement.md) | LLM client with token counting + budget enforcement | Done | 3 | HYL |
| [US0007](US0007-cluster-prompt-and-step.md) | Cluster prompt + step | Done | 5 | HYL |
| [US0008](US0008-rank-prompt-and-step.md) | Rank prompt + step (`item_kind`-aware significance) | Done | 5 | HYL |
| [US0009](US0009-compose-prompt-for-paper-items.md) | Compose prompt for `paper` items | Done | 5 | HYL |
| [US0010](US0010-compose-prompt-for-repo-items.md) | Compose prompt for `repo` items | Done | 3 | HYL |
| [US0011](US0011-compose-blog-quick-mentions-and-issue-assembly.md) | Compose `blog_post` + quick mentions + `RenderedIssue` assembly | Done | 8 | HYL |

**EP0002 subtotal:** 6 stories, 29 points

### [EP0003: Orchestration & Developer Experience](../epics/EP0003-orchestration-and-dx.md)

| ID | Title | Status | Points | Owner |
|----|-------|--------|--------|-------|
| [US0012](US0012-techletter-cli-scaffolding.md) | `techletter` CLI scaffolding (`draft` / `send` / `dry-run`) | Done | 3 | HYL |
| [US0013](US0013-sends-jsonl-and-idempotency.md) | `logs/sends.jsonl` schema + idempotency | Done | 3 | HYL |
| [US0014](US0014-cache-helpers.md) | `.cache/` helpers, CI-disabled | Done | 5 | HYL |
| [US0015](US0015-draft-workflow-yaml.md) | `.github/workflows/draft.yml` | Done | 3 | HYL |
| [US0016](US0016-send-workflow-yaml.md) | `.github/workflows/send.yml` | Done | 5 | HYL |
| [US0017](US0017-readme-quickstart-and-dev-loop.md) | README quickstart + dev loop docs | Done | 2 | HYL |

**EP0003 subtotal:** 6 stories, 21 points

### [EP0004: Multi-channel Delivery](../epics/EP0004-multichannel-delivery.md)

| ID | Title | Status | Points | Owner |
|----|-------|--------|--------|-------|
| [US0018](US0018-channel-adapter-protocol-and-config-loaders.md) | `ChannelAdapter` protocol + config loaders | Done | 3 | HYL |
| [US0019](US0019-email-channel-adapter.md) | Email channel adapter (SMTP multipart) | Done | 5 | HYL |
| [US0020](US0020-slack-channel-adapter.md) | Slack channel adapter (webhook + split) | Done | 3 | HYL |
| [US0021](US0021-telegram-channel-adapter.md) | Telegram channel adapter (Bot API + split) | Done | 3 | HYL |
| [US0022](US0022-channel-registry-and-send-aggregation.md) | Channel registry + `SendReport` aggregation | Done | 3 | HYL |

**EP0004 subtotal:** 5 stories, 17 points

---

**Project totals:** 22 stories, 83 story points across 4 epics.

### EP0003: Orchestration & Developer Experience
_Stories not yet generated. Run `/sdlc-studio story --epic EP0003`._

### EP0004: Multi-channel Delivery
_Stories not yet generated. Run `/sdlc-studio story --epic EP0004`._

## All Stories

| ID | Title | Epic | Status | Points | Persona |
|----|-------|------|--------|--------|---------|
| [US0001](US0001-item-model-and-source-adapter-protocol.md) | `Item` model + `SourceAdapter` protocol | [EP0001](../epics/EP0001-content-ingestion.md) | Done | 3 | HYL |
| [US0002](US0002-arxiv-source-adapter.md) | arXiv source adapter | [EP0001](../epics/EP0001-content-ingestion.md) | Done | 3 | HYL |
| [US0003](US0003-github-trending-source-adapter.md) | GitHub Trending source adapter | [EP0001](../epics/EP0001-content-ingestion.md) | Done | 5 | HYL |
| [US0004](US0004-rss-source-adapter.md) | RSS source adapter | [EP0001](../epics/EP0001-content-ingestion.md) | Done | 2 | HYL |
| [US0005](US0005-source-registry-and-config-loader.md) | Source registry + `config/sources.yaml` loader | [EP0001](../epics/EP0001-content-ingestion.md) | Done | 3 | HYL |
| [US0006](US0006-llm-client-with-budget-enforcement.md) | LLM client + budget enforcement | [EP0002](../epics/EP0002-composition-pipeline.md) | Done | 3 | HYL |
| [US0007](US0007-cluster-prompt-and-step.md) | Cluster prompt + step | [EP0002](../epics/EP0002-composition-pipeline.md) | Done | 5 | HYL |
| [US0008](US0008-rank-prompt-and-step.md) | Rank prompt + step | [EP0002](../epics/EP0002-composition-pipeline.md) | Done | 5 | HYL |
| [US0009](US0009-compose-prompt-for-paper-items.md) | Compose prompt for paper items | [EP0002](../epics/EP0002-composition-pipeline.md) | Done | 5 | HYL/Researcher |
| [US0010](US0010-compose-prompt-for-repo-items.md) | Compose prompt for repo items | [EP0002](../epics/EP0002-composition-pipeline.md) | Done | 3 | HYL/Researcher |
| [US0011](US0011-compose-blog-quick-mentions-and-issue-assembly.md) | Compose blog + quick mentions + assembly | [EP0002](../epics/EP0002-composition-pipeline.md) | Done | 8 | HYL |
| [US0012](US0012-techletter-cli-scaffolding.md) | CLI scaffolding | [EP0003](../epics/EP0003-orchestration-and-dx.md) | Done | 3 | HYL |
| [US0013](US0013-sends-jsonl-and-idempotency.md) | `sends.jsonl` + idempotency | [EP0003](../epics/EP0003-orchestration-and-dx.md) | Done | 3 | HYL |
| [US0014](US0014-cache-helpers.md) | `.cache/` helpers | [EP0003](../epics/EP0003-orchestration-and-dx.md) | Done | 5 | HYL |
| [US0015](US0015-draft-workflow-yaml.md) | `draft.yml` workflow | [EP0003](../epics/EP0003-orchestration-and-dx.md) | Done | 3 | HYL |
| [US0016](US0016-send-workflow-yaml.md) | `send.yml` workflow | [EP0003](../epics/EP0003-orchestration-and-dx.md) | Done | 5 | HYL |
| [US0017](US0017-readme-quickstart-and-dev-loop.md) | README + dev loop docs | [EP0003](../epics/EP0003-orchestration-and-dx.md) | Done | 2 | HYL |
| [US0018](US0018-channel-adapter-protocol-and-config-loaders.md) | `ChannelAdapter` protocol + config | [EP0004](../epics/EP0004-multichannel-delivery.md) | Done | 3 | HYL |
| [US0019](US0019-email-channel-adapter.md) | Email adapter | [EP0004](../epics/EP0004-multichannel-delivery.md) | Done | 5 | HYL/Researcher |
| [US0020](US0020-slack-channel-adapter.md) | Slack adapter | [EP0004](../epics/EP0004-multichannel-delivery.md) | Done | 3 | HYL/Researcher |
| [US0021](US0021-telegram-channel-adapter.md) | Telegram adapter | [EP0004](../epics/EP0004-multichannel-delivery.md) | Done | 3 | HYL/Researcher |
| [US0022](US0022-channel-registry-and-send-aggregation.md) | Channel registry + aggregation | [EP0004](../epics/EP0004-multichannel-delivery.md) | Done | 3 | HYL |

## Dependency Graph for EP0001

```
US0001 (model + protocol) ─┬─► US0002 (arxiv)
                           ├─► US0003 (github)
                           ├─► US0004 (rss)
                           └─► US0005 (registry)
                                  ▲
                                  │ (uses US0002, US0003, US0004 at runtime;
                                  │  can be developed in parallel against fakes)
```

**EP0001 execution order:** US0001 → {US0002, US0003, US0004 in parallel} → US0005.

## Dependency Graph for EP0002

```
US0001 (Item) ──┐
                │
US0006 (LLM client) ─► US0007 (cluster) ─► US0008 (rank) ─┬─► US0009 (compose paper)
                                                          ├─► US0010 (compose repo)
                                                          └─► US0011 (compose blog + assembly)
```

**EP0002 execution order:** US0006 → US0007 → US0008 → {US0009, US0010 in parallel} → US0011 (capstone, depends on shared types from US0009).
US0011 also assembles the final `RenderedIssue`, so it must follow US0009 and US0010.

## Dependency Graph for EP0003

```
US0012 (CLI) ──┬─► US0015 (draft.yml)
               │
               └─► US0016 (send.yml)
                       ▲
US0013 (sends.jsonl) ──┘  (idempotency consumed by send.yml)

US0014 (cache) ─► US0012 (dry-run sub-command uses cache)

US0017 (README) ─► depends on the above being functional
```

**EP0003 execution order:** {US0012, US0013, US0014 in any order — they're independent} → {US0015, US0016 in parallel} → US0017 last. In practice: scaffold US0012 first as a stub, fill in US0013 and US0014 alongside, then YAMLs, then docs.

## Dependency Graph for EP0004

```
US0018 (protocol + config) ─┬─► US0019 (email)   ──┐
                            ├─► US0020 (slack)   ──┤
                            └─► US0021 (telegram)──┴─► US0022 (registry)
```

**EP0004 execution order:** US0018 → {US0019, US0020, US0021 in parallel} → US0022. Symmetric to EP0001: the registry can be unit-tested against fake adapters in parallel with the real adapter stories.

## Notes

- Stories are numbered globally (US0001, US0002, …) per SDLC Studio convention.
- All EP0001 stories name **HYL (Author/Editor)** as the user — they are internal-pipeline stories whose direct beneficiary is the author who depends on reliable ingestion. The Researcher Subscriber is a transitive beneficiary.
- All stories are in **Draft** status; promote to **Ready** when the AC pass the Ready criteria check (`reference-decisions.md#story-ready`).

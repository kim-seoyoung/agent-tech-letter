# PL0005: Source registry + config loader — Implementation Plan

> **Status:** Done
> **Story:** [US0005](../stories/US0005-source-registry-and-config-loader.md)
> **Epic:** [EP0001: Content Ingestion](../epics/EP0001-content-ingestion.md)
> **Test Spec:** [TS0009](../test-specs/TS0009-source-registry-and-config-loader.md) → TS0001 TC0047–TC0055
> **Created:** 2026-05-20
> **Approach:** TDD

## Approach

TDD. Closes EP0001 by tying the 3 concrete adapters (US0002/US0003/US0004) together. pydantic config schema + adapter-class dict + `fetch_all` aggregation with per-source isolation + URL dedup.

## Implementation Tasks

| # | Task                                                                       | File                                       | Status |
| - | -------------------------------------------------------------------------- | ------------------------------------------ | ------ |
| 1 | Write failing tests for config loader + registry (TC0047–TC0055)           | `tests/unit/config/test_sources.py`, `tests/unit/sources/test_registry.py` | [x]    |
| 2 | Define pydantic config schemas (SourcesConfig, ArxivConfig, GithubConfig, RssConfig) | `techletter/config/sources.py`             | [x]    |
| 3 | Implement `load_sources(path) -> SourcesConfig` with ConfigLoadError       | `techletter/config/__init__.py`            | [x]    |
| 4 | Implement `build_registry(config) -> SourceRegistry`                       | `techletter/sources/registry.py`           | [x]    |
| 5 | Implement `SourceRegistry.fetch_all(window_days)` with per-source isolation + dedup | `techletter/sources/registry.py`           | [x]    |
| 6 | Ship default `config/sources.yaml`                                         | `config/sources.yaml`                      | [x]    |
| 7 | Run all quality gates — green                                              | n/a                                        | [x]    |

## AC Coverage

| AC  | Test Scenarios                                                                |
| --- | ----------------------------------------------------------------------------- |
| AC1 | Valid YAML → SourcesConfig structure                                          |
| AC2 | build_registry omits disabled sources                                         |
| AC3 | fetch_all aggregates with dedup, stable order                                 |
| AC4 | One adapter raises → other two still return items                             |
| AC5 | All adapters raise → returns [], warning logged                               |
| AC6 | Malformed YAML / typo'd source key → ConfigLoadError                          |
| AC7 | New feed URL in sources.yaml → included in fetch_all without code change      |

## Revision History

| Date       | Author | Change                                                       |
| ---------- | ------ | ------------------------------------------------------------ |
| 2026-05-20 | Claude | Initial plan for Wave 4 execution (final story in EP0001).   |

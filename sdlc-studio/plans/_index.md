# Plan Registry

**Last Updated:** 2026-05-20

## Summary

| Status      | Count |
| ----------- | ----- |
| Draft       | 0     |
| In Progress | 0     |
| Done        | 3     |
| **Total**   | **3** |

## Plans

| ID                                                                                | Story                                                                              | Title                                            | Status | Approach |
| --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------ | ------ | -------- |
| [PL0001](PL0001-item-model-and-source-adapter-protocol.md) | [US0001](../stories/US0001-item-model-and-source-adapter-protocol.md) | `Item` model + `SourceAdapter` protocol         | Done   | TDD      |
| [PL0002](PL0002-arxiv-source-adapter.md) | [US0002](../stories/US0002-arxiv-source-adapter.md) | arXiv source adapter                            | Done   | TDD      |
| [PL0004](PL0004-rss-source-adapter.md) | [US0004](../stories/US0004-rss-source-adapter.md) | RSS source adapter                              | Done   | TDD      |

## Notes

- Plan IDs are globally sequential (one per story implementation). Next available: **PL0002**.
- `Status` values: Draft → In Progress → Done. Created via `/sdlc-studio story plan`; flipped to In Progress when `code implement` begins; flipped to Done when all task checkboxes are ticked and the story reaches its terminal status.
- `Approach` is set from the plan's "Recommended Approach" section; can be overridden via `story implement --tdd` / `--no-tdd`.

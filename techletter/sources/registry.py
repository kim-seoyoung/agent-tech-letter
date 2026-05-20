"""Source registry: builds adapters from config and aggregates their results.

Provides `build_registry(config)` to construct one adapter instance per
enabled source in `SourcesConfig`, and `SourceRegistry.fetch_all(window_days)`
to call each adapter, isolate per-source failures, deduplicate by URL
(first-occurrence wins), and return the aggregated `list[Item]` in stable
order.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

from techletter.config.sources import SourcesConfig
from techletter.models import Item
from techletter.sources.arxiv import ArxivAdapter
from techletter.sources.base import SourceAdapter
from techletter.sources.github import GitHubTrendingAdapter
from techletter.sources.rss import RssAdapter

__all__ = ["SourceRegistry", "build_registry"]

logger = logging.getLogger(__name__)


@dataclass
class SourceRegistry:
    """Dispatcher across configured source adapters."""

    adapters: Mapping[str, SourceAdapter] = field(default_factory=lambda: {})

    def fetch_all(self, window_days: int) -> list[Item]:
        """Fetch from every adapter; isolate per-source failures.

        - Deduplicates by `Item.url` (first occurrence wins).
        - Stable order: adapters are iterated by insertion order; items
          within an adapter preserve their fetch order.
        - On per-source failure, logs a warning naming the source and
          continues with the others. If all sources fail, returns `[]`
          with a final "all sources failed" warning.
        """
        aggregated: list[Item] = []
        seen_urls: set[str] = set()
        failures = 0
        total = len(self.adapters)

        for source_name, adapter in self.adapters.items():
            try:
                items = adapter.fetch(window_days)
            except Exception as e:
                logger.warning("source %r failed: %s", source_name, e)
                failures += 1
                continue

            for item in items:
                url_key = str(item.url)
                if url_key in seen_urls:
                    continue
                seen_urls.add(url_key)
                aggregated.append(item)

        if total > 0 and failures == total:
            logger.warning("all sources failed; no items fetched")

        return aggregated


# Explicit adapter registry: source name → adapter class.
# Explicit (not auto-discovery) so imports are grep-able + pyright-checkable.
_ADAPTER_CLASSES: Mapping[str, type[SourceAdapter]] = {
    "arxiv": ArxivAdapter,
    "github": GitHubTrendingAdapter,
    "rss": RssAdapter,
}


def build_registry(config: SourcesConfig) -> SourceRegistry:
    """Construct a SourceRegistry from a loaded SourcesConfig.

    Only includes adapters whose section has `enabled: true`. Constructor
    failures (e.g., a config-valid value that an adapter rejects) are
    caught and logged; that source is omitted from the registry and the
    others proceed.
    """
    adapters: dict[str, SourceAdapter] = {}

    if config.arxiv.enabled:
        try:
            adapters["arxiv"] = ArxivAdapter(
                categories=config.arxiv.categories,
                keywords=config.arxiv.keywords,
            )
        except Exception as e:
            logger.warning("source %r failed to construct: %s", "arxiv", e)

    if config.github.enabled:
        try:
            adapters["github"] = GitHubTrendingAdapter(
                spoken_language=config.github.spoken_language,
                period=config.github.period,
            )
        except Exception as e:
            logger.warning("source %r failed to construct: %s", "github", e)

    if config.rss.enabled:
        try:
            adapters["rss"] = RssAdapter(feeds=[str(f) for f in config.rss.feeds])
        except Exception as e:
            logger.warning("source %r failed to construct: %s", "rss", e)

    return SourceRegistry(adapters=adapters)

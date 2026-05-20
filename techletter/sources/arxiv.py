"""arXiv source adapter.

Fetches recent papers from arXiv categories (default: cs.AI, cs.CL) filtered
by an LLM-agent keyword list. Implements `SourceAdapter`. Wraps the upstream
call in tenacity retries; raises `SourceFetchError` after exhausting attempts.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from techletter.models import Item
from techletter.sources.base import SourceFetchError

__all__ = ["DEFAULT_CATEGORIES", "DEFAULT_KEYWORDS", "ArxivAdapter"]

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES: list[str] = ["cs.AI", "cs.CL"]

DEFAULT_KEYWORDS: list[str] = [
    "agent",
    "agentic",
    "tool-use",
    "tool use",
    "llm agent",
    "react",
    "planning",
]

MAX_SUMMARY_LEN = 1000
MAX_WINDOW_DAYS = 365


class _ArxivClient(Protocol):
    """Structural type for the arxiv.Client surface we use."""

    def results(self, search: Any) -> Iterable[Any]: ...


def _default_client_factory() -> _ArxivClient:
    """Lazily import the real arxiv client so tests don't require the lib."""
    import arxiv  # type: ignore[import-untyped]

    return arxiv.Client()


class ArxivAdapter:
    """SourceAdapter implementation for arXiv."""

    name: str = "arxiv"

    def __init__(
        self,
        categories: list[str] | None = None,
        keywords: list[str] | None = None,
        client_factory: Callable[[], _ArxivClient] | None = None,
    ) -> None:
        self.categories: list[str] = list(categories) if categories else list(DEFAULT_CATEGORIES)
        self.keywords: list[str] = list(keywords) if keywords else list(DEFAULT_KEYWORDS)
        self._client_factory: Callable[[], _ArxivClient] = (
            client_factory if client_factory is not None else _default_client_factory
        )

    def fetch(self, window_days: int) -> list[Item]:
        """Fetch recent arXiv papers matching the configured filters.

        Raises:
            ValueError: if window_days < 0
            SourceFetchError: if all retries against the arXiv API fail
        """
        if window_days < 0:
            raise ValueError(f"window_days must be >= 0, got {window_days}")

        if window_days > MAX_WINDOW_DAYS:
            logger.warning(
                "arxiv: window_days=%d exceeds MAX_WINDOW_DAYS=%d; clamping to %d",
                window_days,
                MAX_WINDOW_DAYS,
                MAX_WINDOW_DAYS,
            )
            window_days = MAX_WINDOW_DAYS

        cutoff = datetime.now(UTC) - timedelta(days=window_days)

        try:
            results = self._fetch_results()
        except RetryError as e:
            raise SourceFetchError(f"arxiv: exhausted retries: {e.last_attempt.exception()}") from e
        except (ConnectionError, TimeoutError) as e:
            raise SourceFetchError(f"arxiv: {e}") from e

        items: list[Item] = []
        kw_lower = [k.lower() for k in self.keywords]

        for r in results:
            published = self._coerce_published(r)
            if published is None:
                continue
            if published < cutoff:
                continue

            haystack = f"{r.title}\n{r.summary}".lower()
            if not any(kw in haystack for kw in kw_lower):
                continue

            try:
                items.append(
                    Item.model_validate(
                        {
                            "source": "arxiv",
                            "source_subtype": r.primary_category,
                            "title": str(r.title).strip(),
                            "url": str(r.entry_id),
                            "summary_excerpt": str(r.summary).strip()[:MAX_SUMMARY_LEN],
                            "published_at": published,
                            "item_kind": "paper",
                            "raw": self._serialize_raw(r),
                        }
                    )
                )
            except Exception as e:
                logger.warning(
                    "arxiv: skipped malformed paper %r: %s", getattr(r, "entry_id", "?"), e
                )

        return items

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=False,
    )
    def _fetch_results(self) -> list[Any]:
        client = self._client_factory()
        # Lazy-import arxiv only when really needed
        try:
            import arxiv  # type: ignore[import-untyped]

            query = " OR ".join(f"cat:{c}" for c in self.categories)
            search = arxiv.Search(
                query=query,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
                max_results=100,
            )
        except ImportError:
            # In tests with a FakeClient, the real arxiv lib isn't required.
            search = None
        return list(client.results(search))

    @staticmethod
    def _coerce_published(r: Any) -> datetime | None:
        pub = getattr(r, "published", None)
        if pub is None:
            return None
        if isinstance(pub, datetime):
            return pub if pub.tzinfo is not None else pub.replace(tzinfo=UTC)
        return None

    @staticmethod
    def _serialize_raw(r: Any) -> dict[str, object]:
        keys = ("entry_id", "title", "summary", "primary_category")
        return {k: getattr(r, k, None) for k in keys}

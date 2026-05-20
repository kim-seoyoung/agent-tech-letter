"""RSS source adapter.

Fetches a list of RSS/Atom feed URLs (from config), parses with feedparser,
normalises to `list[Item]` with `source="rss"`, `item_kind="blog_post"`.
Per-feed try/except for isolation; tenacity-wrapped fetch per feed.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import feedparser  # type: ignore[import-untyped]
import httpx
from pydantic import ValidationError
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from techletter.models import Item
from techletter.sources.base import SourceFetchError

__all__ = ["RssAdapter"]

logger = logging.getLogger(__name__)

MAX_SUMMARY_LEN = 1000
HTTP_TIMEOUT = 10.0


def _default_fetcher(url: str) -> bytes:
    response = httpx.get(url, timeout=HTTP_TIMEOUT, follow_redirects=True)
    response.raise_for_status()
    return response.content


class RssAdapter:
    """SourceAdapter implementation for RSS/Atom feeds."""

    name: str = "rss"

    def __init__(
        self,
        feeds: list[str],
        http_fetcher: Callable[[str], bytes] | None = None,
    ) -> None:
        self.feeds: list[str] = list(feeds)
        self._http_fetcher: Callable[[str], bytes] = (
            http_fetcher if http_fetcher is not None else _default_fetcher
        )

    def fetch(self, window_days: int) -> list[Item]:
        """Fetch items from all configured feeds.

        Per-feed failures (after retries exhausted) are logged and skipped;
        items from successful feeds are still returned.

        Raises:
            ValueError: if window_days < 0
        """
        if window_days < 0:
            raise ValueError(f"window_days must be >= 0, got {window_days}")

        cutoff = datetime.now(UTC) - timedelta(days=window_days)
        items: list[Item] = []

        for feed_url in self.feeds:
            try:
                items.extend(self._fetch_one(feed_url, cutoff))
            except SourceFetchError as e:
                logger.warning("rss: feed %s failed: %s", feed_url, e)

        return items

    def _fetch_one(self, feed_url: str, cutoff: datetime) -> list[Item]:
        try:
            body = self._fetch_body(feed_url)
        except RetryError as e:
            raise SourceFetchError(
                f"rss feed {feed_url}: exhausted retries: {e.last_attempt.exception()}"
            ) from e

        feed: Any = feedparser.parse(body)  # pyright: ignore[reportUnknownMemberType]
        if getattr(feed, "bozo", False):
            logger.warning("rss: feed %s has bozo flag: %s", feed_url, feed.get("bozo_exception"))

        entries = getattr(feed, "entries", []) or []
        out: list[Item] = []

        for entry in entries:
            title = (getattr(entry, "title", "") or "").strip()
            if not title:
                continue

            published = self._coerce_published(entry)
            if published is None:
                logger.warning(
                    "rss: skipping item without published date in %s (title=%r)", feed_url, title
                )
                continue
            if published < cutoff:
                continue

            link = getattr(entry, "link", None)
            if not link:
                logger.warning("rss: skipping item without link in %s (title=%r)", feed_url, title)
                continue

            summary_src = (
                getattr(entry, "summary", None) or getattr(entry, "description", None) or ""
            )
            summary_excerpt = str(summary_src).strip()[:MAX_SUMMARY_LEN]

            try:
                out.append(
                    Item.model_validate(
                        {
                            "source": "rss",
                            "source_subtype": feed_url,
                            "title": title,
                            "url": str(link),
                            "summary_excerpt": summary_excerpt,
                            "published_at": published,
                            "item_kind": "blog_post",
                            "raw": self._serialize_entry(entry),
                        }
                    )
                )
            except ValidationError as e:
                logger.warning(
                    "rss: skipping malformed item in %s (title=%r): %s", feed_url, title, e
                )

        return out

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, httpx.HTTPError, OSError)),
        reraise=False,
    )
    def _fetch_body(self, feed_url: str) -> bytes:
        return self._http_fetcher(feed_url)

    @staticmethod
    def _coerce_published(entry: Any) -> datetime | None:
        parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
        if parsed is None:
            return None
        try:
            return datetime(*parsed[:6], tzinfo=UTC)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _serialize_entry(entry: Any) -> dict[str, object]:
        # feedparser entries are dict-like; capture safe scalar fields.
        keys = ("title", "link", "id", "summary", "description", "author")
        return {k: getattr(entry, k, None) for k in keys}

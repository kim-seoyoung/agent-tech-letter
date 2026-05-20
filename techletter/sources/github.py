"""GitHub Trending source adapter.

Scrapes the GitHub Trending page (weekly) for the configured spoken language,
enriches each repo via the GitHub REST API with shipping signals (stars,
last_commit_at, has_recent_release, hosted_demo_url), and infers `maturity`
from those signals. Fails soft on scrape failure (returns []); per-repo
enrichment failure (404) skips that repo.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

import httpx
from pydantic import ValidationError
from selectolax.parser import HTMLParser
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from techletter.models import Item, Maturity
from techletter.sources.base import SourceFetchError

__all__ = ["GitHubTrendingAdapter", "RepoStub", "infer_maturity", "parse_trending_html"]

logger = logging.getLogger(__name__)

TRENDING_URL_FMT = "https://github.com/trending?since={period}&spoken_language_code={language}"
REST_REPO_URL_FMT = "https://api.github.com/repos/{owner}/{name}"
REST_RELEASES_URL_FMT = "https://api.github.com/repos/{owner}/{name}/releases?per_page=1"

HTTP_TIMEOUT = 15.0
HTTP_USER_AGENT = "techletter-bot/0.1 (+https://github.com/kim-seoyoung/agent-tech-letter)"

# Maturity thresholds (per US0003 AC4)
PRODUCTION_READY_MIN_STARS = 500
BETA_MIN_STARS = 50
RECENT_COMMIT_DAYS = 30
STALE_COMMIT_DAYS = 90

HtmlFetcher = Callable[[str, Mapping[str, str] | None], bytes]
RestClient = Callable[[str, Mapping[str, str] | None], dict[str, Any]]


@dataclass(frozen=True)
class RepoStub:
    """Lightweight repo identity extracted from the trending HTML."""

    owner: str
    name: str
    description: str


def parse_trending_html(html: bytes) -> list[RepoStub]:
    """Parse the trending HTML page into a list of RepoStub objects.

    If the selectors don't match (e.g., GitHub redesigns the page) this
    returns `[]` rather than raising. Callers should treat `[]` as a
    soft-failure signal and log accordingly.
    """
    try:
        tree = HTMLParser(html.decode("utf-8", errors="replace"))
    except Exception as e:
        logger.warning("github: failed to parse trending HTML: %s", e)
        return []

    stubs: list[RepoStub] = []
    for article in tree.css("article.Box-row"):
        link_node = article.css_first("h2 a")
        if link_node is None:
            continue
        href = link_node.attributes.get("href", "")
        if not href or "/" not in href.strip("/"):
            continue
        parts = href.strip("/").split("/")
        if len(parts) < 2:
            continue
        owner, name = parts[0], parts[1]
        desc_node = article.css_first("p.color-fg-muted")
        description = (desc_node.text(strip=True) if desc_node else "").strip()
        stubs.append(RepoStub(owner=owner, name=name, description=description))

    return stubs


def infer_maturity(metadata: Mapping[str, object]) -> Maturity:
    """Infer Maturity from enriched repo metadata.

    Rules (from US0003 AC4):
      - production-ready: has_recent_release AND last_commit < 30 days AND stars >= 500
      - beta:              last_commit < 30 days AND stars >= 50
      - experimental:      last_commit > 90 days OR stars < 50
      - unknown:           any required field missing
    """
    stars = metadata.get("stars")
    last_commit_at = metadata.get("last_commit_at")
    has_recent_release = metadata.get("has_recent_release")

    if stars is None or last_commit_at is None or has_recent_release is None:
        return "unknown"
    if not isinstance(stars, int) or not isinstance(last_commit_at, str):
        return "unknown"

    try:
        last_commit_dt = datetime.fromisoformat(last_commit_at.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"

    days_since_commit = (datetime.now(UTC) - last_commit_dt).days

    if (
        bool(has_recent_release)
        and days_since_commit <= RECENT_COMMIT_DAYS
        and stars >= PRODUCTION_READY_MIN_STARS
    ):
        return "production-ready"
    if days_since_commit <= RECENT_COMMIT_DAYS and stars >= BETA_MIN_STARS:
        return "beta"
    if days_since_commit > STALE_COMMIT_DAYS or stars < BETA_MIN_STARS:
        return "experimental"
    return "beta"


def _default_html_fetcher(url: str, headers: Mapping[str, str] | None = None) -> bytes:
    response = httpx.get(
        url,
        timeout=HTTP_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": HTTP_USER_AGENT, **(headers or {})},
    )
    response.raise_for_status()
    return response.content


def _default_rest_client(url: str, headers: Mapping[str, str] | None = None) -> dict[str, Any]:
    response = httpx.get(
        url,
        timeout=HTTP_TIMEOUT,
        follow_redirects=True,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": HTTP_USER_AGENT,
            **(headers or {}),
        },
    )
    response.raise_for_status()
    parsed: Any = response.json()
    # Wrap a JSON list response in a synthetic dict so the adapter has one type to handle
    if isinstance(parsed, list):
        return {"_list": cast(list[Any], parsed)}
    if isinstance(parsed, dict):
        return cast(dict[str, Any], parsed)
    return {"_value": parsed}


class GitHubTrendingAdapter:
    """SourceAdapter implementation for GitHub Trending."""

    name: str = "github"

    def __init__(
        self,
        spoken_language: str = "en",
        period: Literal["daily", "weekly", "monthly"] = "weekly",
        html_fetcher: HtmlFetcher | None = None,
        rest_client: RestClient | None = None,
    ) -> None:
        self.spoken_language = spoken_language
        self.period: Literal["daily", "weekly", "monthly"] = period
        self._html_fetcher: HtmlFetcher = html_fetcher or _default_html_fetcher
        self._rest_client: RestClient = rest_client or _default_rest_client

    def fetch(self, window_days: int) -> list[Item]:
        """Fetch trending repos + enrich + return as list[Item].

        Raises:
            ValueError: if window_days < 0
            SourceFetchError: if REST API persistently fails (rate-limit etc.)
        """
        if window_days < 0:
            raise ValueError(f"window_days must be >= 0, got {window_days}")

        trending_url = TRENDING_URL_FMT.format(period=self.period, language=self.spoken_language)

        try:
            html = self._fetch_trending_html(trending_url)
        except RetryError as e:
            logger.warning(
                "github: trending scrape failed after retries: %s; returning []",
                e.last_attempt.exception(),
            )
            return []
        except (httpx.HTTPError, ConnectionError, TimeoutError, OSError) as e:
            logger.warning("github: trending scrape failed: %s; returning []", e)
            return []

        stubs = parse_trending_html(html)
        if not stubs:
            logger.warning("github: trending page parsed 0 repos (selector mismatch?)")
            return []

        items: list[Item] = []
        for stub in stubs:
            try:
                item = self._enrich_and_build(stub)
            except _SkipRepo as e:
                logger.warning("github: skipped %s/%s: %s", stub.owner, stub.name, e)
                continue
            if item is not None:
                items.append(item)

        return items

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, httpx.HTTPError)),
        reraise=False,
    )
    def _fetch_trending_html(self, url: str) -> bytes:
        return self._html_fetcher(url, None)

    def _enrich_and_build(self, stub: RepoStub) -> Item | None:
        try:
            repo_meta = self._rest_get(REST_REPO_URL_FMT.format(owner=stub.owner, name=stub.name))
            releases_resp = self._rest_get(
                REST_RELEASES_URL_FMT.format(owner=stub.owner, name=stub.name)
            )
        except httpx.HTTPStatusError as e:
            raise _SkipRepo(f"REST error: {e}") from e
        except RetryError as e:
            raise SourceFetchError(
                f"github: REST exhausted retries for {stub.owner}/{stub.name}: "
                f"{e.last_attempt.exception()}"
            ) from e

        releases_raw: object = releases_resp.get("_list") if "_list" in releases_resp else []
        releases: list[Any] = (
            cast(list[Any], releases_raw) if isinstance(releases_raw, list) else []
        )

        stars_raw = repo_meta.get("stargazers_count", 0)
        stars: int = int(stars_raw) if isinstance(stars_raw, int | float | str) else 0

        pushed_at = repo_meta.get("pushed_at")
        last_commit_at = str(pushed_at) if pushed_at else None

        has_recent_release = False
        if releases:
            first = releases[0]
            if isinstance(first, dict):
                first_dict = cast(dict[str, Any], first)
                published_at_raw = first_dict.get("published_at")
                if isinstance(published_at_raw, str):
                    try:
                        published = datetime.fromisoformat(published_at_raw.replace("Z", "+00:00"))
                        has_recent_release = (datetime.now(UTC) - published) <= timedelta(days=90)
                    except ValueError:
                        has_recent_release = False

        homepage = repo_meta.get("homepage")
        hosted_demo_url: str | None = None
        if isinstance(homepage, str) and homepage.strip().startswith(("http://", "https://")):
            hosted_demo_url = homepage.strip()

        raw: dict[str, object] = {
            "stars": stars,
            "last_commit_at": last_commit_at,
            "has_recent_release": has_recent_release,
            "hosted_demo_url": hosted_demo_url,
        }

        maturity = infer_maturity(raw) if last_commit_at is not None else "unknown"
        published_at = self._coerce_published(last_commit_at)
        if published_at is None:
            published_at = datetime.now(UTC)

        summary = stub.description or f"Trending repo {stub.owner}/{stub.name}"

        try:
            return Item.model_validate(
                {
                    "source": "github",
                    "source_subtype": self.period,
                    "title": f"{stub.owner}/{stub.name}",
                    "url": f"https://github.com/{stub.owner}/{stub.name}",
                    "summary_excerpt": summary[:1000],
                    "score": float(stars),
                    "published_at": published_at,
                    "item_kind": "repo",
                    "maturity": maturity,
                    "raw": raw,
                }
            )
        except ValidationError as e:
            raise _SkipRepo(f"validation error: {e}") from e

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=False,
    )
    def _rest_get(self, url: str) -> dict[str, Any]:
        headers = self._auth_headers()
        return self._rest_client(url, headers)

    @staticmethod
    def _auth_headers() -> Mapping[str, str] | None:
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            return {"Authorization": f"Bearer {token}"}
        return None

    @staticmethod
    def _coerce_published(iso_string: str | None) -> datetime | None:
        if iso_string is None:
            return None
        try:
            dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
        except ValueError:
            return None


class _SkipRepo(Exception):
    """Internal sentinel: skip this repo, continue with the rest of the batch."""

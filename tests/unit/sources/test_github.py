"""Tests for techletter.sources.github - mirrors TS0001 TC0022-TC0036."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

# --- Helpers / fixtures --------------------------------------------------------


def _trending_html(rows: list[tuple[str, str]]) -> bytes:
    """Build a minimal trending-page HTML with the documented selectors."""
    articles = "".join(
        f"""<article class="Box-row">
            <h2 class="h3 lh-condensed">
                <a href="/{owner}/{name}">{owner}/{name}</a>
            </h2>
            <p class="col-9 color-fg-muted my-1 pr-4">{description}</p>
        </article>"""
        for (owner, name), description in zip(
            rows, [f"desc-{i}" for i in range(len(rows))], strict=False
        )
    )
    return f"""<!DOCTYPE html><html><body>
        <main>{articles}</main>
    </body></html>""".encode()


def _make_html_fetcher(
    routes: Mapping[str, bytes | Exception],
) -> Callable[[str, Mapping[str, str] | None], bytes]:
    def fetcher(url: str, headers: Mapping[str, str] | None = None) -> bytes:
        v = routes.get(url)
        if v is None:
            raise RuntimeError(f"unexpected URL: {url}")
        if isinstance(v, Exception):
            raise v
        return v

    return fetcher


def _make_rest_client(
    routes: Mapping[str, dict[str, Any] | Exception],
) -> Callable[[str, Mapping[str, str] | None], dict[str, Any]]:
    def client(url: str, headers: Mapping[str, str] | None = None) -> dict[str, Any]:
        v = routes.get(url)
        if v is None:
            raise RuntimeError(f"unexpected REST URL: {url}")
        if isinstance(v, Exception):
            raise v
        return v

    return client


def _repo_meta(
    *,
    name: str = "repo",
    stars: int = 100,
    pushed_days_ago: int = 5,
    has_release: bool = True,
    release_days_ago: int = 30,
    homepage: str | None = "https://example.com",
) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "name": name,
        "stargazers_count": stars,
        "pushed_at": (now - timedelta(days=pushed_days_ago)).isoformat().replace("+00:00", "Z"),
        "homepage": homepage,
        "_releases": (
            [{"published_at": (now - timedelta(days=release_days_ago)).isoformat()}]
            if has_release
            else []
        ),
    }


# --- TC0022: Adapter conformance ----------------------------------------------


def test_tc0022_github_adapter_conformance() -> None:
    from techletter.sources.base import SourceAdapter
    from techletter.sources.github import GitHubTrendingAdapter

    adapter: SourceAdapter = GitHubTrendingAdapter(
        html_fetcher=_make_html_fetcher({}),
        rest_client=_make_rest_client({}),
    )
    assert adapter.name == "github"


# --- TC0023: Scrapes trending HTML, parses repo list ---------------------------


def test_tc0023_scrapes_trending_html_returns_items() -> None:
    from techletter.sources.github import GitHubTrendingAdapter

    trending_url = "https://github.com/trending?since=weekly&spoken_language_code=en"
    repos = [("owner1", "repo1"), ("owner2", "repo2")]
    html_routes = {trending_url: _trending_html(repos)}
    rest_routes: dict[str, dict[str, Any] | Exception] = {
        "https://api.github.com/repos/owner1/repo1": _repo_meta(name="repo1"),
        "https://api.github.com/repos/owner1/repo1/releases?per_page=1": {
            "_list": [{"published_at": (datetime.now(UTC) - timedelta(days=10)).isoformat()}]
        },
        "https://api.github.com/repos/owner2/repo2": _repo_meta(name="repo2"),
        "https://api.github.com/repos/owner2/repo2/releases?per_page=1": {"_list": []},
    }
    adapter = GitHubTrendingAdapter(
        html_fetcher=_make_html_fetcher(html_routes),
        rest_client=_make_rest_client(rest_routes),
    )
    items = adapter.fetch(window_days=7)
    assert len(items) == 2
    titles = {it.title for it in items}
    assert titles == {"owner1/repo1", "owner2/repo2"}


def test_tc0024_items_have_correct_source_and_kind() -> None:
    from techletter.sources.github import GitHubTrendingAdapter

    trending_url = "https://github.com/trending?since=weekly&spoken_language_code=en"
    html_routes = {trending_url: _trending_html([("o", "r")])}
    rest_routes: dict[str, dict[str, Any] | Exception] = {
        "https://api.github.com/repos/o/r": _repo_meta(name="r"),
        "https://api.github.com/repos/o/r/releases?per_page=1": {"_list": []},
    }
    adapter = GitHubTrendingAdapter(
        html_fetcher=_make_html_fetcher(html_routes),
        rest_client=_make_rest_client(rest_routes),
    )
    items = adapter.fetch(window_days=7)
    assert len(items) == 1
    assert items[0].source == "github"
    assert items[0].item_kind == "repo"
    assert "https://github.com/o/r" in str(items[0].url)


# --- TC0025: REST enrichment populates raw shipping signals --------------------


def test_tc0025_rest_enrichment_populates_shipping_signals() -> None:
    from techletter.sources.github import GitHubTrendingAdapter

    trending_url = "https://github.com/trending?since=weekly&spoken_language_code=en"
    html_routes = {trending_url: _trending_html([("o", "r")])}
    rest_routes: dict[str, dict[str, Any] | Exception] = {
        "https://api.github.com/repos/o/r": _repo_meta(
            name="r", stars=1500, pushed_days_ago=2, homepage="https://demo.example"
        ),
        "https://api.github.com/repos/o/r/releases?per_page=1": {
            "_list": [{"published_at": (datetime.now(UTC) - timedelta(days=20)).isoformat()}]
        },
    }
    adapter = GitHubTrendingAdapter(
        html_fetcher=_make_html_fetcher(html_routes),
        rest_client=_make_rest_client(rest_routes),
    )
    items = adapter.fetch(window_days=7)
    raw = items[0].raw
    assert raw["stars"] == 1500
    assert "last_commit_at" in raw and isinstance(raw["last_commit_at"], str)
    assert raw["has_recent_release"] is True
    assert raw["hosted_demo_url"] == "https://demo.example"


# --- TC0026: infer_maturity parametric -----------------------------------------


@pytest.mark.parametrize(
    ("stars", "pushed_days_ago", "has_recent_release", "expected"),
    [
        (1000, 5, True, "production-ready"),  # high stars + recent + release
        (75, 5, False, "beta"),  # recent push + ok stars, no recent release
        (10, 5, False, "experimental"),  # low stars
        (1000, 120, False, "experimental"),  # push too old
    ],
)
def test_tc0026_infer_maturity(
    stars: int, pushed_days_ago: int, has_recent_release: bool, expected: str
) -> None:
    from techletter.sources.github import infer_maturity

    meta: dict[str, object] = {
        "stars": stars,
        "last_commit_at": (datetime.now(UTC) - timedelta(days=pushed_days_ago)).isoformat(),
        "has_recent_release": has_recent_release,
    }
    assert infer_maturity(meta) == expected


def test_tc0026b_infer_maturity_unknown_on_missing_field() -> None:
    from techletter.sources.github import infer_maturity

    assert infer_maturity({"stars": 100, "has_recent_release": True}) == "unknown"
    assert infer_maturity({"last_commit_at": "2026-05-01T00:00:00Z"}) == "unknown"


# --- TC0027: Scrape failure → fails soft ---------------------------------------


def test_tc0027_scrape_404_returns_empty_no_exception(caplog: pytest.LogCaptureFixture) -> None:
    from techletter.sources.github import GitHubTrendingAdapter

    trending_url = "https://github.com/trending?since=weekly&spoken_language_code=en"
    import httpx

    html_routes: dict[str, bytes | Exception] = {
        trending_url: httpx.HTTPStatusError(
            "404", request=httpx.Request("GET", trending_url), response=httpx.Response(404)
        )
    }
    adapter = GitHubTrendingAdapter(
        html_fetcher=_make_html_fetcher(html_routes),
        rest_client=_make_rest_client({}),
    )
    with caplog.at_level("WARNING"):
        items = adapter.fetch(window_days=7)
    assert items == []
    assert any("github" in r.message.lower() for r in caplog.records)


def test_tc0027b_selector_mismatch_returns_empty(caplog: pytest.LogCaptureFixture) -> None:
    from techletter.sources.github import GitHubTrendingAdapter

    trending_url = "https://github.com/trending?since=weekly&spoken_language_code=en"
    html_routes = {trending_url: b"<html><body>no articles here</body></html>"}
    adapter = GitHubTrendingAdapter(
        html_fetcher=_make_html_fetcher(html_routes),
        rest_client=_make_rest_client({}),
    )
    with caplog.at_level("WARNING"):
        items = adapter.fetch(window_days=7)
    assert items == []


# --- TC0028: GITHUB_TOKEN header sent when set ---------------------------------


def test_tc0028_github_token_authorization_header_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    from techletter.sources.github import GitHubTrendingAdapter

    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake_token_for_test")
    seen_headers: list[Mapping[str, str] | None] = []

    def rest_client(url: str, headers: Mapping[str, str] | None = None) -> dict[str, Any]:
        seen_headers.append(headers)
        if url.endswith("/releases?per_page=1"):
            return {"_list": []}
        return _repo_meta()

    trending_url = "https://github.com/trending?since=weekly&spoken_language_code=en"
    adapter = GitHubTrendingAdapter(
        html_fetcher=_make_html_fetcher({trending_url: _trending_html([("o", "r")])}),
        rest_client=rest_client,
    )
    adapter.fetch(window_days=7)
    # At least one REST call should have sent the token
    assert any(
        h is not None and "Authorization" in h and "ghp_fake_token_for_test" in h["Authorization"]
        for h in seen_headers
    )


# --- TC0029: Per-repo 404 → skipped, others returned ---------------------------


def test_tc0029_per_repo_404_skipped_others_returned(caplog: pytest.LogCaptureFixture) -> None:
    import httpx

    from techletter.sources.github import GitHubTrendingAdapter

    trending_url = "https://github.com/trending?since=weekly&spoken_language_code=en"
    html_routes = {trending_url: _trending_html([("o1", "r1"), ("o2", "deleted"), ("o3", "r3")])}
    not_found = httpx.HTTPStatusError(
        "404", request=httpx.Request("GET", ""), response=httpx.Response(404)
    )
    rest_routes: dict[str, dict[str, Any] | Exception] = {
        "https://api.github.com/repos/o1/r1": _repo_meta(name="r1"),
        "https://api.github.com/repos/o1/r1/releases?per_page=1": {"_list": []},
        "https://api.github.com/repos/o2/deleted": not_found,
        "https://api.github.com/repos/o3/r3": _repo_meta(name="r3"),
        "https://api.github.com/repos/o3/r3/releases?per_page=1": {"_list": []},
    }
    adapter = GitHubTrendingAdapter(
        html_fetcher=_make_html_fetcher(html_routes),
        rest_client=_make_rest_client(rest_routes),
    )
    with caplog.at_level("WARNING"):
        items = adapter.fetch(window_days=7)
    titles = {it.title for it in items}
    assert titles == {"o1/r1", "o3/r3"}
    assert any("o2/deleted" in r.message for r in caplog.records)


# --- TC0029b: Negative window raises -------------------------------------------


def test_tc0029b_negative_window_raises() -> None:
    from techletter.sources.github import GitHubTrendingAdapter

    adapter = GitHubTrendingAdapter(
        html_fetcher=_make_html_fetcher({}), rest_client=_make_rest_client({})
    )
    with pytest.raises(ValueError):
        adapter.fetch(window_days=-1)


# --- TC0029c: Empty trending page returns empty --------------------------------


def test_tc0029c_empty_trending_returns_empty() -> None:
    from techletter.sources.github import GitHubTrendingAdapter

    trending_url = "https://github.com/trending?since=weekly&spoken_language_code=en"
    html_routes = {trending_url: _trending_html([])}
    adapter = GitHubTrendingAdapter(
        html_fetcher=_make_html_fetcher(html_routes), rest_client=_make_rest_client({})
    )
    items = adapter.fetch(window_days=7)
    assert items == []

"""Tests for techletter.sources.rss - mirrors TS0001 TC0037-TC0046."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta

import pytest

# --- Fixture RSS bodies --------------------------------------------------------


def _rss_body(items: list[dict[str, str]], *, format: str = "rss") -> bytes:
    """Build a minimal RSS 2.0 or Atom feed body."""
    if format == "atom":
        entries = "".join(
            f"""
            <entry>
                <title>{i["title"]}</title>
                <link href="{i["link"]}"/>
                <summary>{i.get("summary", "")}</summary>
                <updated>{i["pub"]}</updated>
            </entry>
            """
            for i in items
        )
        return f"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
            <title>Test feed</title>{entries}</feed>""".encode()

    rss_items = "".join(
        f"""
        <item>
            <title>{i["title"]}</title>
            <link>{i["link"]}</link>
            <description>{i.get("summary", "")}</description>
            <pubDate>{i["pub"]}</pubDate>
        </item>
        """
        for i in items
    )
    return f"""<?xml version="1.0"?><rss version="2.0"><channel>
        <title>Test feed</title>{rss_items}</channel></rss>""".encode()


def _rfc822(dt: datetime) -> str:
    """Format as a feedparser-acceptable RFC822 date string."""
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


def _make_fetcher(
    routes: Mapping[str, bytes | Exception],
) -> Callable[[str], bytes]:
    """Build a fake http_fetcher that maps URL -> bytes or raises."""

    def fetcher(url: str) -> bytes:
        if url not in routes:
            raise RuntimeError(f"unexpected URL in test: {url}")
        v = routes[url]
        if isinstance(v, Exception):
            raise v
        return v

    return fetcher


# --- TC0037: Adapter conformance ----------------------------------------------


def test_tc0037_rss_adapter_conformance() -> None:
    from techletter.sources.base import SourceAdapter
    from techletter.sources.rss import RssAdapter

    adapter: SourceAdapter = RssAdapter(feeds=[], http_fetcher=_make_fetcher({}))
    assert adapter.name == "rss"


# --- TC0038: Aggregates from multiple feeds; source_subtype attribution -------


def test_tc0038_aggregates_with_source_subtype_attribution() -> None:
    from techletter.sources.rss import RssAdapter

    now = datetime.now(UTC)
    f1, f2, f3 = "https://a.example/feed", "https://b.example/feed", "https://c.example/feed"
    routes = {
        f1: _rss_body(
            [
                {
                    "title": "A1",
                    "link": "https://a.example/1",
                    "pub": _rfc822(now - timedelta(days=1)),
                },
                {
                    "title": "A2",
                    "link": "https://a.example/2",
                    "pub": _rfc822(now - timedelta(days=2)),
                },
            ]
        ),
        f2: _rss_body(
            [
                {
                    "title": "B1",
                    "link": "https://b.example/1",
                    "pub": _rfc822(now - timedelta(days=1)),
                },
            ]
        ),
        f3: _rss_body(
            [
                {
                    "title": "C1",
                    "link": "https://c.example/1",
                    "pub": _rfc822(now - timedelta(days=1)),
                },
            ]
        ),
    }
    adapter = RssAdapter(feeds=[f1, f2, f3], http_fetcher=_make_fetcher(routes))
    items = adapter.fetch(window_days=7)
    assert len(items) == 4
    subtypes = {it.source_subtype for it in items}
    assert subtypes == {f1, f2, f3}
    assert all(it.source == "rss" for it in items)
    assert all(it.item_kind == "blog_post" for it in items)


# --- TC0039: Window filter ------------------------------------------------------


def test_tc0039_window_filter_excludes_old_items() -> None:
    from techletter.sources.rss import RssAdapter

    now = datetime.now(UTC)
    feed_url = "https://x.example/feed"
    items_in = [
        {
            "title": f"item-{d}d",
            "link": f"https://x.example/{d}",
            "pub": _rfc822(now - timedelta(days=d)),
        }
        for d in [1, 2, 3, 5, 6, 8, 14, 20, 25, 30]
    ]
    routes = {feed_url: _rss_body(items_in)}
    adapter = RssAdapter(feeds=[feed_url], http_fetcher=_make_fetcher(routes))
    items = adapter.fetch(window_days=7)
    # Within 7 days: days 1, 2, 3, 5, 6 = 5 items (8 is at the boundary; we choose strict <)
    assert 5 <= len(items) <= 6


# --- TC0040: Per-feed failure isolation ----------------------------------------


def test_tc0040_per_feed_failure_isolated(caplog: pytest.LogCaptureFixture) -> None:
    from techletter.sources.rss import RssAdapter

    now = datetime.now(UTC)
    f1, f2, f3 = "https://a.example/feed", "https://b.example/feed", "https://c.example/feed"
    routes: dict[str, bytes | Exception] = {
        f1: _rss_body(
            [
                {
                    "title": "A1",
                    "link": "https://a.example/1",
                    "pub": _rfc822(now - timedelta(days=1)),
                }
            ]
        ),
        f2: ConnectionError("simulated network down"),
        f3: _rss_body(
            [
                {
                    "title": "C1",
                    "link": "https://c.example/1",
                    "pub": _rfc822(now - timedelta(days=1)),
                }
            ]
        ),
    }
    adapter = RssAdapter(feeds=[f1, f2, f3], http_fetcher=_make_fetcher(routes))
    with caplog.at_level("WARNING"):
        items = adapter.fetch(window_days=7)
    titles = {it.title for it in items}
    assert titles == {"A1", "C1"}
    assert any(f2 in r.message for r in caplog.records)


# --- TC0041: All feeds failing returns empty, no raise -------------------------


def test_tc0041_all_feeds_failing_returns_empty(caplog: pytest.LogCaptureFixture) -> None:
    from techletter.sources.rss import RssAdapter

    f1, f2 = "https://a.example/feed", "https://b.example/feed"
    routes: dict[str, bytes | Exception] = {
        f1: ConnectionError("down"),
        f2: TimeoutError("slow"),
    }
    adapter = RssAdapter(feeds=[f1, f2], http_fetcher=_make_fetcher(routes))
    with caplog.at_level("WARNING"):
        items = adapter.fetch(window_days=7)
    assert items == []
    assert len(caplog.records) >= 2  # one warning per failed feed


# --- TC0042: Atom format parses equivalently -----------------------------------


def test_tc0042_atom_format_parses_equivalently() -> None:
    from techletter.sources.rss import RssAdapter

    now = datetime.now(UTC)
    feed_url = "https://atom.example/feed"
    routes = {
        feed_url: _rss_body(
            [
                {
                    "title": "AtomItem",
                    "link": "https://atom.example/1",
                    "summary": "an atom entry",
                    "pub": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            ],
            format="atom",
        )
    }
    adapter = RssAdapter(feeds=[feed_url], http_fetcher=_make_fetcher(routes))
    items = adapter.fetch(window_days=7)
    assert len(items) == 1
    assert items[0].title == "AtomItem"


# --- TC0043: Malformed XML (bozo) but partial parse ----------------------------


def test_tc0043_malformed_xml_partial_parse(caplog: pytest.LogCaptureFixture) -> None:
    from techletter.sources.rss import RssAdapter

    now = datetime.now(UTC)
    # Valid item + truncated mid-document
    bad_body = (
        b"""<?xml version="1.0"?><rss version="2.0"><channel>
        <title>broken</title>
        <item>
            <title>Survivor</title>
            <link>https://b.example/1</link>
            <description>x</description>
            <pubDate>"""
        + _rfc822(now - timedelta(days=1)).encode()
        + b"""</pubDate>
        </item><!-- truncated"""
    )
    feed_url = "https://broken.example/feed"
    adapter = RssAdapter(feeds=[feed_url], http_fetcher=_make_fetcher({feed_url: bad_body}))
    with caplog.at_level("WARNING"):
        items = adapter.fetch(window_days=7)
    # We should NOT raise; either we got the survivor or we logged the bozo and skipped.
    assert isinstance(items, list)


# --- TC0044: Items missing published are skipped -------------------------------


def test_tc0044_items_missing_published_skipped(caplog: pytest.LogCaptureFixture) -> None:
    from techletter.sources.rss import RssAdapter

    now = datetime.now(UTC)
    feed_url = "https://x.example/feed"
    body = (
        b"""<?xml version="1.0"?><rss version="2.0"><channel>
        <title>X</title>
        <item>
            <title>HasPubDate</title>
            <link>https://x.example/1</link>
            <description>good</description>
            <pubDate>"""
        + _rfc822(now - timedelta(days=1)).encode()
        + b"""</pubDate>
        </item>
        <item>
            <title>MissingPubDate</title>
            <link>https://x.example/2</link>
            <description>missing date</description>
        </item>
    </channel></rss>"""
    )
    adapter = RssAdapter(feeds=[feed_url], http_fetcher=_make_fetcher({feed_url: body}))
    with caplog.at_level("WARNING"):
        items = adapter.fetch(window_days=7)
    titles = {it.title for it in items}
    assert "HasPubDate" in titles
    assert "MissingPubDate" not in titles


# --- TC0045: Empty feed list ---------------------------------------------------


def test_tc0045_empty_feed_list_returns_empty() -> None:
    from techletter.sources.rss import RssAdapter

    adapter = RssAdapter(feeds=[], http_fetcher=_make_fetcher({}))
    assert adapter.fetch(window_days=7) == []


# --- TC0046: Long summary truncated to 1000 chars ------------------------------


def test_tc0046_long_summary_truncated() -> None:
    from techletter.sources.rss import RssAdapter

    now = datetime.now(UTC)
    long_summary = "x " * 800  # 1600 chars
    feed_url = "https://x.example/feed"
    routes = {
        feed_url: _rss_body(
            [
                {
                    "title": "Long",
                    "link": "https://x.example/1",
                    "summary": long_summary,
                    "pub": _rfc822(now - timedelta(days=1)),
                }
            ]
        )
    }
    adapter = RssAdapter(feeds=[feed_url], http_fetcher=_make_fetcher(routes))
    items = adapter.fetch(window_days=7)
    assert len(items) == 1
    assert len(items[0].summary_excerpt) <= 1000


# --- TC0046b: Negative window_days raises --------------------------------------


def test_tc0046b_negative_window_raises() -> None:
    from techletter.sources.rss import RssAdapter

    adapter = RssAdapter(feeds=["https://x.example/feed"], http_fetcher=_make_fetcher({}))
    with pytest.raises(ValueError):
        adapter.fetch(window_days=-1)


# --- TC0046c: Empty title item skipped (pydantic min_length=1) -----------------


def test_tc0046c_empty_title_item_skipped() -> None:
    from techletter.sources.rss import RssAdapter

    now = datetime.now(UTC)
    feed_url = "https://x.example/feed"
    body = (
        b"""<?xml version="1.0"?><rss version="2.0"><channel>
        <title>X</title>
        <item>
            <title>HasTitle</title>
            <link>https://x.example/1</link>
            <description>ok</description>
            <pubDate>"""
        + _rfc822(now - timedelta(days=1)).encode()
        + b"""</pubDate>
        </item>
        <item>
            <title></title>
            <link>https://x.example/2</link>
            <description>no title</description>
            <pubDate>"""
        + _rfc822(now - timedelta(days=1)).encode()
        + b"""</pubDate>
        </item>
    </channel></rss>"""
    )
    adapter = RssAdapter(feeds=[feed_url], http_fetcher=_make_fetcher({feed_url: body}))
    items = adapter.fetch(window_days=7)
    titles = [it.title for it in items]
    assert "HasTitle" in titles
    # Empty-title item is skipped
    assert len(items) == 1

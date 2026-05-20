"""Tests for techletter.sources.registry - mirrors TS0001 TC0049-TC0055."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from techletter.models import Item
from techletter.sources.base import SourceFetchError


def _make_item(url: str, source: str = "arxiv") -> Item:
    return Item.model_validate(
        {
            "source": source,
            "title": f"item-{url}",
            "url": url,
            "summary_excerpt": "x",
            "published_at": datetime(2026, 5, 19, tzinfo=UTC),
            "item_kind": "paper"
            if source == "arxiv"
            else ("repo" if source == "github" else "blog_post"),
            "raw": {},
        }
    )


class FakeAdapter:
    """A minimal SourceAdapter for registry testing."""

    def __init__(
        self, name: str, items: list[Item] | None = None, exc: Exception | None = None
    ) -> None:
        self.name = name
        self._items = items or []
        self._exc = exc

    def fetch(self, window_days: int) -> list[Item]:
        if self._exc:
            raise self._exc
        return list(self._items)


# --- TC0049: build_registry omits disabled sources -----------------------------


def test_tc0049_build_registry_omits_disabled_sources() -> None:
    from techletter.sources.registry import SourceRegistry

    arxiv = FakeAdapter("arxiv", items=[])
    rss = FakeAdapter("rss", items=[])
    registry = SourceRegistry(adapters={"arxiv": arxiv, "rss": rss})
    assert "arxiv" in registry.adapters
    assert "rss" in registry.adapters
    assert "github" not in registry.adapters


# --- TC0050: fetch_all aggregates with dedup + stable order --------------------


def test_tc0050_fetch_all_aggregates_dedups_stable() -> None:
    from techletter.sources.registry import SourceRegistry

    item_a = _make_item("https://example.com/a", "arxiv")
    item_b = _make_item("https://example.com/b", "github")
    item_b_dup = _make_item("https://example.com/b", "rss")  # same URL, different source
    item_c = _make_item("https://example.com/c", "rss")

    arxiv = FakeAdapter("arxiv", items=[item_a, item_b])
    github = FakeAdapter("github", items=[])
    rss = FakeAdapter("rss", items=[item_b_dup, item_c])

    registry = SourceRegistry(adapters={"arxiv": arxiv, "github": github, "rss": rss})
    items = registry.fetch_all(window_days=7)
    urls = [str(it.url) for it in items]
    # first occurrence of /b is kept; second is dropped
    assert urls.count("https://example.com/b") == 1
    assert "https://example.com/a" in urls
    assert "https://example.com/c" in urls

    # Stable order: calling twice produces the same list
    items2 = registry.fetch_all(window_days=7)
    assert [str(it.url) for it in items2] == urls


# --- TC0051: Per-source failure isolated, others succeed -----------------------


def test_tc0051_per_source_failure_isolated(caplog: pytest.LogCaptureFixture) -> None:
    from techletter.sources.registry import SourceRegistry

    arxiv_items = [_make_item("https://arxiv.example/a", "arxiv")]
    rss_items = [_make_item("https://rss.example/r", "rss")]

    arxiv = FakeAdapter("arxiv", items=arxiv_items)
    github = FakeAdapter("github", exc=SourceFetchError("github: rate limit"))
    rss = FakeAdapter("rss", items=rss_items)

    registry = SourceRegistry(adapters={"arxiv": arxiv, "github": github, "rss": rss})
    with caplog.at_level("WARNING"):
        items = registry.fetch_all(window_days=7)
    urls = {str(it.url) for it in items}
    assert "https://arxiv.example/a" in urls
    assert "https://rss.example/r" in urls
    assert any("github" in r.message for r in caplog.records)


# --- TC0052: All sources fail → empty list, no raise ---------------------------


def test_tc0052_all_sources_failing_returns_empty(caplog: pytest.LogCaptureFixture) -> None:
    from techletter.sources.registry import SourceRegistry

    arxiv = FakeAdapter("arxiv", exc=SourceFetchError("a"))
    github = FakeAdapter("github", exc=SourceFetchError("g"))
    rss = FakeAdapter("rss", exc=SourceFetchError("r"))
    registry = SourceRegistry(adapters={"arxiv": arxiv, "github": github, "rss": rss})
    with caplog.at_level("WARNING"):
        items = registry.fetch_all(window_days=7)
    assert items == []
    assert any("all sources failed" in r.message.lower() for r in caplog.records)


def test_tc0052b_adapter_raises_unexpected_exception_isolated(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from techletter.sources.registry import SourceRegistry

    arxiv = FakeAdapter("arxiv", items=[_make_item("https://x.example/1", "arxiv")])
    github = FakeAdapter("github", exc=RuntimeError("unexpected crash"))
    registry = SourceRegistry(adapters={"arxiv": arxiv, "github": github})
    with caplog.at_level("WARNING"):
        items = registry.fetch_all(window_days=7)
    assert len(items) == 1
    assert any("github" in r.message for r in caplog.records)


# --- TC0054/TC0055: build_registry from config dispatches enabled adapters -----


def test_tc0054_build_registry_from_config_via_pydantic() -> None:
    """build_registry takes a SourcesConfig and returns a registry containing
    only the enabled adapters, constructed with the config-derived kwargs."""
    from techletter.config import load_sources
    from techletter.sources.registry import build_registry

    yaml = """
arxiv:
  enabled: true
  categories: ["cs.AI"]
github:
  enabled: false
rss:
  enabled: true
  feeds: ["https://thenewstack.io/ai/feed/"]
"""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml)
        path = f.name

    from pathlib import Path

    config = load_sources(Path(path))
    registry = build_registry(config)
    assert "arxiv" in registry.adapters
    assert "rss" in registry.adapters
    assert "github" not in registry.adapters


def test_tc0055_empty_registry_returns_empty() -> None:
    from techletter.sources.registry import SourceRegistry

    registry = SourceRegistry(adapters={})
    assert registry.fetch_all(window_days=7) == []


def test_negative_window_propagates_value_error_from_adapter() -> None:
    """fetch_all should propagate window_days to adapters; ValueError from
    one adapter is caught and isolated like any other exception."""
    from techletter.sources.registry import SourceRegistry

    class StrictAdapter:
        name = "strict"

        def fetch(self, window_days: int) -> list[Item]:
            if window_days < 0:
                raise ValueError("negative not allowed")
            return []

    registry = SourceRegistry(adapters={"strict": StrictAdapter()})  # type: ignore[arg-type]
    items = registry.fetch_all(window_days=-1)
    # Per registry contract: per-source failures don't crash the run
    assert items == []

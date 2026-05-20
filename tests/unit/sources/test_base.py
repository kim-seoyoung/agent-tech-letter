"""Tests for techletter.sources.base — SourceAdapter Protocol + SourceFetchError."""

from __future__ import annotations

from datetime import UTC, datetime


# A baseline valid Item dict reusable across these tests.
def _item_dict() -> dict[str, object]:
    return {
        "source": "arxiv",
        "title": "Paper",
        "url": "https://arxiv.org/abs/2026.00001",
        "summary_excerpt": "abstract",
        "published_at": datetime(2026, 5, 15, 12, 0, 0, tzinfo=UTC),
        "item_kind": "paper",
        "raw": {},
    }


# --- AC2 / AC3: SourceAdapter Protocol + structural conformance ----------------


def test_source_adapter_protocol_importable() -> None:
    from techletter.sources.base import SourceAdapter

    # Protocol is a class; it has the expected members in __annotations__/dir.
    # We don't need @runtime_checkable for this — pyright handles conformance.
    assert hasattr(SourceAdapter, "fetch")


def test_fake_adapter_assignable_to_source_adapter() -> None:
    """AC3: a class with the right shape can be assigned to SourceAdapter."""
    from techletter.models import Item
    from techletter.sources.base import SourceAdapter

    class FakeAdapter:
        name = "fake"

        def fetch(self, window_days: int) -> list[Item]:
            return [Item.model_validate(_item_dict()), Item.model_validate(_item_dict())]

    adapter: SourceAdapter = FakeAdapter()  # pyright-asserted assignment
    items = adapter.fetch(window_days=7)
    assert len(items) == 2
    assert all(isinstance(i, Item) for i in items)
    assert adapter.name == "fake"


def test_fake_adapter_with_empty_fetch_is_valid() -> None:
    """A FakeAdapter returning [] is treated as a valid (empty) result."""
    from techletter.models import Item
    from techletter.sources.base import SourceAdapter

    class EmptyAdapter:
        name = "empty"

        def fetch(self, window_days: int) -> list[Item]:
            return []

    adapter: SourceAdapter = EmptyAdapter()
    assert adapter.fetch(7) == []


# --- SourceFetchError ----------------------------------------------------------


def test_source_fetch_error_is_exception() -> None:
    """SourceFetchError must be a subclass of Exception so downstream adapters
    (US0002, US0003, US0005) can raise/catch it as a normal exception."""
    from techletter.sources.base import SourceFetchError

    assert issubclass(SourceFetchError, Exception)


def test_source_fetch_error_can_be_raised_and_caught() -> None:
    from techletter.sources.base import SourceFetchError

    try:
        raise SourceFetchError("arxiv: 503 after 5 attempts")
    except SourceFetchError as e:
        assert "arxiv" in str(e)

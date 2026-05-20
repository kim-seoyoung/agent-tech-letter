"""Tests for techletter.models.Item - mirrors TS0001 TC0001-TC0011 + TC0010."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

# --- Helpers --------------------------------------------------------------------


def _minimal_dict(**overrides: object) -> dict[str, object]:
    """A baseline valid Item dict that individual tests mutate via overrides."""
    base: dict[str, object] = {
        "source": "arxiv",
        "title": "An LLM Agent Survey",
        "url": "https://arxiv.org/abs/2026.01234",
        "summary_excerpt": "We survey LLM agents.",
        "published_at": datetime(2026, 5, 15, 12, 0, 0, tzinfo=UTC),
        "item_kind": "paper",
        "raw": {},
    }
    base.update(overrides)
    return base


# --- TC0001: Item constructs with all required fields ---------------------------


def test_tc0001_item_constructs_with_required_fields() -> None:
    from techletter.models import Item

    item = Item.model_validate(_minimal_dict())
    assert item.source == "arxiv"
    assert item.title == "An LLM Agent Survey"
    assert str(item.url) == "https://arxiv.org/abs/2026.01234"
    assert item.summary_excerpt == "We survey LLM agents."
    assert item.published_at.tzinfo is not None
    assert item.item_kind == "paper"
    assert item.raw == {}
    # Optional fields default sensibly
    assert item.source_subtype is None
    assert item.score is None
    assert item.maturity is None


# --- TC0002: ValidationError on missing `url` -----------------------------------


def test_tc0002_validation_error_on_missing_url() -> None:
    from techletter.models import Item

    d = _minimal_dict()
    del d["url"]
    with pytest.raises(ValidationError) as exc_info:
        Item.model_validate(d)
    # pydantic surfaces the offending field name in the error
    assert "url" in str(exc_info.value)


# --- TC0003: parametric ValidationError on missing required field ---------------


@pytest.mark.parametrize(
    "missing_field",
    ["source", "title", "url", "summary_excerpt", "published_at", "item_kind", "raw"],
)
def test_tc0003_validation_error_on_missing_required_field(missing_field: str) -> None:
    from techletter.models import Item

    d = _minimal_dict()
    del d[missing_field]
    with pytest.raises(ValidationError) as exc_info:
        Item.model_validate(d)
    assert missing_field in str(exc_info.value)


# --- TC0004: tz-aware UTC datetime accepted -------------------------------------


def test_tc0004_tz_aware_datetime_accepted() -> None:
    from techletter.models import Item

    item = Item.model_validate(
        _minimal_dict(published_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=UTC))
    )
    assert item.published_at.tzinfo is not None


# --- TC0005: tz-naive datetime rejected -----------------------------------------


def test_tc0005_tz_naive_datetime_rejected() -> None:
    from techletter.models import Item

    naive = datetime(2026, 5, 19, 12, 0, 0)  # no tzinfo
    with pytest.raises(ValidationError) as exc_info:
        Item.model_validate(_minimal_dict(published_at=naive))
    msg = str(exc_info.value).lower()
    assert "tz" in msg or "timezone" in msg or "aware" in msg


# --- TC0006: HttpUrl rejects non-http(s) schemes --------------------------------


@pytest.mark.parametrize(
    "bad_url",
    ["ftp://example.com/file", "file:///etc/passwd", "javascript:alert(1)"],
)
def test_tc0006_http_url_rejects_non_http_schemes(bad_url: str) -> None:
    from techletter.models import Item

    with pytest.raises(ValidationError):
        Item.model_validate(_minimal_dict(url=bad_url))


# --- TC0007: summary_excerpt > 1000 chars rejected ------------------------------


def test_tc0007_summary_excerpt_exceeding_1000_chars_rejected() -> None:
    from techletter.models import Item

    too_long = "x" * 1001
    with pytest.raises(ValidationError):
        Item.model_validate(_minimal_dict(summary_excerpt=too_long))


def test_tc0007_summary_excerpt_exactly_1000_chars_accepted() -> None:
    """Boundary: exactly 1000 chars is the highest valid value."""
    from techletter.models import Item

    exact = "x" * 1000
    item = Item.model_validate(_minimal_dict(summary_excerpt=exact))
    assert len(item.summary_excerpt) == 1000


# --- TC0008: Unknown item_kind value rejected -----------------------------------


def test_tc0008_unknown_item_kind_rejected() -> None:
    from techletter.models import Item

    with pytest.raises(ValidationError):
        Item.model_validate(_minimal_dict(item_kind="video"))


# --- TC0009: maturity outside allowed set rejected ------------------------------


@pytest.mark.parametrize(
    "bad_maturity",
    ["mature", "stable", "alpha", "draft"],
)
def test_tc0009_unknown_maturity_rejected(bad_maturity: str) -> None:
    from techletter.models import Item

    with pytest.raises(ValidationError):
        Item.model_validate(_minimal_dict(maturity=bad_maturity))


def test_tc0009_valid_maturities_accepted() -> None:
    from techletter.models import Item

    for m in ["experimental", "beta", "production-ready", "unknown"]:
        item = Item.model_validate(_minimal_dict(maturity=m))
        assert item.maturity == m


# --- TC0010: mutation on frozen Item raises -------------------------------------


def test_tc0010_frozen_item_mutation_raises() -> None:
    from techletter.models import Item

    item = Item.model_validate(_minimal_dict())
    with pytest.raises(ValidationError):
        item.title = "Mutated"  # type: ignore[misc]


# --- TC0010b: raw must be a dict, not list --------------------------------------


def test_tc0010b_raw_non_dict_rejected() -> None:
    from techletter.models import Item

    with pytest.raises(ValidationError):
        Item.model_validate(_minimal_dict(raw=["not", "a", "dict"]))


# --- TC0010c: empty title rejected ----------------------------------------------


def test_tc0010c_empty_title_rejected() -> None:
    from techletter.models import Item

    with pytest.raises(ValidationError):
        Item.model_validate(_minimal_dict(title=""))


# --- TC0011: hypothesis Item round-trip -----------------------------------------


@settings(max_examples=50, deadline=None)
@given(
    title=st.text(min_size=1, max_size=120),
    summary=st.text(min_size=0, max_size=1000),
    score=st.one_of(st.none(), st.floats(min_value=-100.0, max_value=100.0, allow_nan=False)),
    item_kind=st.sampled_from(["paper", "blog_post", "repo"]),
    source=st.sampled_from(["arxiv", "github", "rss"]),
    maturity=st.one_of(
        st.none(), st.sampled_from(["experimental", "beta", "production-ready", "unknown"])
    ),
)
def test_tc0011_item_round_trip(
    title: str,
    summary: str,
    score: float | None,
    item_kind: str,
    source: str,
    maturity: str | None,
) -> None:
    """JSON round-trip preserves equality."""
    from techletter.models import Item

    original = Item.model_validate(
        _minimal_dict(
            source=source,
            title=title,
            summary_excerpt=summary,
            score=score,
            item_kind=item_kind,
            maturity=maturity,
        )
    )
    dumped = original.model_dump(mode="json")
    restored = Item.model_validate(dumped)
    assert restored == original
    assert restored.published_at.tzinfo is not None  # tz preserved through JSON

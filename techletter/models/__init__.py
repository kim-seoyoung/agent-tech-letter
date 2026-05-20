"""Core data models for Tech-Letter for HYL.

This module exposes the `Item` model — the canonical normalised shape every
`SourceAdapter` produces — and the `Maturity` Literal alias used by
GitHub-trending repos (and any future source that infers shipping maturity).

`Item` is frozen (immutable post-construction) to prevent accidental mutation
as items flow through the cluster → rank → compose pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

__all__ = ["Item", "Maturity"]


# A shared Literal alias so US0003's `infer_maturity` and other downstream
# code can `from techletter.models import Maturity` without redefining it.
Maturity = Literal["experimental", "beta", "production-ready", "unknown"]


class Item(BaseModel):
    """A normalised item from any source (arxiv, github, rss).

    Frozen by config — once constructed, attributes cannot be mutated.
    `published_at` MUST be timezone-aware (UTC convention enforced by
    a field validator; naive datetimes are rejected at validation time).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: Literal["arxiv", "github", "rss"]
    source_subtype: str | None = None
    title: Annotated[str, Field(min_length=1)]
    url: HttpUrl
    summary_excerpt: Annotated[str, Field(max_length=1000)]
    score: float | None = None
    published_at: datetime
    item_kind: Literal["paper", "blog_post", "repo"]
    maturity: Maturity | None = None
    raw: dict[str, object]

    @field_validator("published_at")
    @classmethod
    def _published_at_must_be_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError(
                "published_at must be timezone-aware (UTC convention); naive datetimes are rejected"
            )
        return v

"""Shared types for the compose layer (Wave 4 + Wave 5).

Defined here in US0008's wave so that US0009/US0010/US0011 can
`from techletter.compose.types import DeepDive, QuickMention,
BANNED_HYPE_WORDS` without redefining them and without racing to
hub-conflict on a shared file.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from techletter.models import Maturity

__all__ = [
    "BANNED_HYPE_WORDS",
    "DeepDive",
    "QuickMention",
]


# BANNED_HYPE_WORDS is intentionally a frozenset so the *identity* check in
# TC0106 (single source of truth across paper/repo/blog compose modules)
# can compare via `is` if needed. All compose modules import this exact
# symbol — do not redefine.
BANNED_HYPE_WORDS: frozenset[str] = frozenset(
    {
        "revolutionary",
        "groundbreaking",
        "game-changing",
        "game changing",
        "cutting-edge",
        "cutting edge",
        "unprecedented",
        "ai-powered",
        "ai powered",
        "10x",
        "blazing fast",
        "next-generation",
        "next generation",
        "paradigm shift",
        "world-class",
        "world class",
        "best-in-class",
        "best in class",
        "synergy",
        "leverage",  # corporate hype-y verb, not the financial term
    }
)


class DeepDive(BaseModel):
    """A long-form section in the rendered issue (2-5 per issue, target 3).

    Framed differently per `item_kind` — see prompts/compose_{paper,repo,blog}.md.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    cluster_id: str
    title: str = Field(min_length=1, max_length=200)
    body_md: str = Field(min_length=1)
    item_kind: Literal["paper", "blog_post", "repo"]
    maturity: Maturity | None = None
    primary_url: HttpUrl
    source_count: int = Field(ge=1)


class QuickMention(BaseModel):
    """A one-line mention in the quick-mentions section (10 per issue)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    url: HttpUrl
    source: Literal["arxiv", "github", "rss"]
    item_kind: Literal["paper", "blog_post", "repo"]
    one_liner: str = Field(min_length=1, max_length=300)

"""Source configuration schemas.

Defines the pydantic schema for `config/sources.yaml`. The schema uses
`extra="forbid"` so typos in top-level keys (e.g., `reddit:` instead of
`rss:`) raise `ValidationError` at load time rather than silently no-op.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, HttpUrl

__all__ = [
    "ArxivConfig",
    "GithubConfig",
    "RssConfig",
    "SourcesConfig",
]


class _StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ArxivConfig(_StrictBase):
    enabled: bool = False
    categories: list[str] = ["cs.AI", "cs.CL"]
    keywords: list[str] = ["agent", "tool-use", "LLM agent"]


class GithubConfig(_StrictBase):
    enabled: bool = False
    spoken_language: str = "en"
    period: Literal["daily", "weekly", "monthly"] = "weekly"


class RssConfig(_StrictBase):
    enabled: bool = False
    feeds: list[HttpUrl] = []


class SourcesConfig(_StrictBase):
    """Top-level configuration for the source layer.

    Extra keys (e.g., typo'd source names) are forbidden — they raise
    ValidationError at load time. Missing keys default to `enabled=False`
    for that source.
    """

    arxiv: ArxivConfig = ArxivConfig()
    github: GithubConfig = GithubConfig()
    rss: RssConfig = RssConfig()

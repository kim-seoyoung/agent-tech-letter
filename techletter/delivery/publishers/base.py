"""US0028: `Publisher` Protocol, `PublishResult` model, `PublisherError`.

Per RV0002 F-1: `PublisherError` lives in this story (the schema layer)
rather than being introduced ad-hoc by US0029. This keeps the contract
boundary clean — implementations only need to raise the shared class.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from techletter.compose.issue import RenderedIssue

__all__ = ["PublishResult", "Publisher", "PublisherError"]


class PublisherError(Exception):
    """Raised by `Publisher` implementations on backend-side failures.

    Examples (US0029): dirty worktree, push failure after retries,
    missing `gh-pages` branch on origin. Channel adapters catch this
    and surface it as `SendReport.status="failed"`.
    """


class PublishResult(BaseModel):
    """Outcome of one `publish(issue)` call.

    `commit_sha` is publisher-backend-specific (only meaningful for
    git-based publishers). `publisher_name` echoes the publisher's
    `name` attribute so audit logs can identify which backend emitted
    a given URL.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str = Field(min_length=1)
    path: str = Field(min_length=1)
    published_at: datetime
    publisher_name: str = Field(min_length=1)
    commit_sha: str | None = None


class Publisher(Protocol):
    """Structural contract every publisher implements.

    Members:
        name: short identifier (e.g., 'github_pages').
        publish(issue): write the rendered issue somewhere public;
                        return a `PublishResult` carrying the URL.
                        On failure, raise `PublisherError`.
    """

    name: str

    def publish(self, issue: RenderedIssue) -> PublishResult: ...

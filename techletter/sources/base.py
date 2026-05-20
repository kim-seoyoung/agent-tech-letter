"""Base types for source adapters.

This module defines the `SourceAdapter` Protocol every concrete adapter
(arXiv, GitHub Trending, RSS) must structurally conform to, plus
`SourceFetchError` — the canonical exception raised when an adapter
exhausts its retries on a transient or permanent failure.

`SourceAdapter` is a `typing.Protocol`, not an ABC. Concrete adapters
do not inherit from it; conformance is checked structurally at static
analysis time by pyright. We deliberately do NOT decorate with
`@runtime_checkable` — runtime isinstance checks against this Protocol
would silently pass on the wrong shape, hiding bugs that pyright would
catch.
"""

from __future__ import annotations

from typing import Protocol

from techletter.models import Item

__all__ = ["SourceAdapter", "SourceFetchError"]


class SourceFetchError(Exception):
    """Raised when a source adapter exhausts retries on a transient or
    permanent failure.

    Caught at the registry level (US0005's `fetch_all`) and logged with
    the source name + final error message; isolation is enforced there
    so one source failing does not abort the weekly run.
    """


class SourceAdapter(Protocol):
    """The structural contract every source adapter implements.

    Members:
        name: A short identifier (e.g., ``"arxiv"``, ``"github"``, ``"rss"``)
              set as a class attribute on the concrete adapter.
        fetch(window_days): Returns a list of normalised ``Item`` objects
              produced from the source's upstream API or feed, scoped to the
              given lookback window (``0`` means "today only"; adapters
              may pragmatically cap very large values).
    """

    name: str

    def fetch(self, window_days: int) -> list[Item]: ...

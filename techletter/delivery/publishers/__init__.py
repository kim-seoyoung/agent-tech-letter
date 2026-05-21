"""Publisher layer — emits a `RenderedIssue` as a public URL.

A `Publisher` is the seam between a channel adapter and a hosting
backend. Telegram's `teaser_link` mode (US0031) calls
`publisher.publish(issue)` once per send and embeds the returned URL
into the teaser message.

Currently only `GitHubPagesPublisher` (US0029) ships; the Protocol
leaves room for Telegraph / Cloudflare R2 / etc. without touching
channel adapters.
"""

from techletter.delivery.publishers.base import (
    Publisher,
    PublisherError,
    PublishResult,
)

__all__ = ["PublishResult", "Publisher", "PublisherError"]

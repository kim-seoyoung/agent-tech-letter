"""Channel configuration schemas (per US0018).

Loaded from `config/channels.yaml` (enable flags) + `config/subscribers.yaml`
(per-channel recipient lists).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "ChannelsConfig",
    "EmailConfig",
    "GitHubPagesPublisherConfig",
    "PublishersConfig",
    "SlackConfig",
    "SubscribersConfig",
    "TelegramConfig",
]


class _StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmailConfig(_StrictBase):
    enabled: bool = False
    smtp_host: str | None = None  # falls back to SMTP_HOST env
    smtp_port: int = 587
    use_tls: bool = True
    template: str = "templates/email.html.j2"


class SlackConfig(_StrictBase):
    enabled: bool = False
    max_chars_per_message: int = 3500  # Slack soft-limits at ~4000


class TelegramConfig(_StrictBase):
    enabled: bool = False
    parse_mode: str = "HTML"  # "HTML" or "MarkdownV2"
    max_chars_per_message: int = 4096
    # US0031: delivery mode. Default `inline_html` preserves EP0004 behavior for
    # backward compatibility (old `channels.yaml` files load cleanly).
    mode: Literal["teaser_link", "inline_html"] = "inline_html"
    # Name of a publisher defined under `ChannelsConfig.publishers`.
    # Required when `mode == "teaser_link"`; ignored otherwise.
    publisher: str | None = None


class GitHubPagesPublisherConfig(_StrictBase):
    """`publishers.github_pages` schema (US0029 + US0031)."""

    enabled: bool = False
    repo_path: str = "."
    branch: str = "gh-pages"
    base_url: str = ""
    author_name: str = "tech-letter-bot"
    author_email: str = "bot@example.com"


class PublishersConfig(_StrictBase):
    """`publishers:` top-level block in `channels.yaml`.

    Each known publisher gets its own typed sub-block; lookup by name
    happens in `delivery.registry`.
    """

    github_pages: GitHubPagesPublisherConfig = Field(
        default_factory=lambda: GitHubPagesPublisherConfig()
    )


class ChannelsConfig(_StrictBase):
    """Top-level `config/channels.yaml` shape — enable flags + per-channel options."""

    email: EmailConfig = Field(default_factory=lambda: EmailConfig())
    slack: SlackConfig = Field(default_factory=lambda: SlackConfig())
    telegram: TelegramConfig = Field(default_factory=lambda: TelegramConfig())
    publishers: PublishersConfig = Field(default_factory=lambda: PublishersConfig())

    @model_validator(mode="after")
    def _validate_publisher_references(self) -> ChannelsConfig:
        """US0031 AC7: missing publisher reference is a load error."""
        if self.telegram.mode == "teaser_link":
            ref = self.telegram.publisher
            if not ref:
                raise ValueError(
                    "telegram.mode=teaser_link requires telegram.publisher "
                    "(reference name of a block under publishers:)"
                )
            if not hasattr(self.publishers, ref):
                raise ValueError(
                    f"telegram.publisher='{ref}' references an undefined publisher; "
                    f"add a `publishers.{ref}:` block to channels.yaml"
                )
        return self


class SubscribersConfig(_StrictBase):
    """Top-level `config/subscribers.yaml` shape.

    Each list contains channel-specific recipient strings. Missing or empty
    lists are valid (channel just gets zero recipients).
    """

    email: list[str] = Field(default_factory=lambda: [])
    slack: list[str] = Field(default_factory=lambda: [])  # webhook URLs
    telegram: list[str] = Field(default_factory=lambda: [])  # chat IDs

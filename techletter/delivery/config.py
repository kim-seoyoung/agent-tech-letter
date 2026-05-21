"""Channel configuration schemas (per US0018).

Loaded from `config/channels.yaml` (enable flags) + `config/subscribers.yaml`
(per-channel recipient lists).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ChannelsConfig",
    "EmailConfig",
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


class ChannelsConfig(_StrictBase):
    """Top-level `config/channels.yaml` shape — enable flags + per-channel options."""

    email: EmailConfig = Field(default_factory=lambda: EmailConfig())
    slack: SlackConfig = Field(default_factory=lambda: SlackConfig())
    telegram: TelegramConfig = Field(default_factory=lambda: TelegramConfig())


class SubscribersConfig(_StrictBase):
    """Top-level `config/subscribers.yaml` shape.

    Each list contains channel-specific recipient strings. Missing or empty
    lists are valid (channel just gets zero recipients).
    """

    email: list[str] = Field(default_factory=lambda: [])
    slack: list[str] = Field(default_factory=lambda: [])  # webhook URLs
    telegram: list[str] = Field(default_factory=lambda: [])  # chat IDs

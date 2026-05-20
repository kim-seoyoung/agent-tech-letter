"""Configuration loaders for Tech-Letter for HYL."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from techletter.config.sources import (
    ArxivConfig,
    GithubConfig,
    RssConfig,
    SourcesConfig,
)

__all__ = [
    "ArxivConfig",
    "ConfigLoadError",
    "GithubConfig",
    "RssConfig",
    "SourcesConfig",
    "load_sources",
]


class ConfigLoadError(Exception):
    """Raised when a config file fails to load, parse, or validate.

    Wraps the underlying yaml.YAMLError / pydantic.ValidationError / OSError
    via `__cause__` so the original error remains inspectable.
    """


def load_sources(path: Path) -> SourcesConfig:
    """Load and validate a `sources.yaml` file.

    Raises:
        ConfigLoadError: on file not found, YAML parse failure, or
            pydantic ValidationError. The underlying exception is chained
            via `__cause__`.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise ConfigLoadError(f"sources config file not found: {path}") from e
    except OSError as e:
        raise ConfigLoadError(f"could not read sources config {path}: {e}") from e

    try:
        data: Any = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ConfigLoadError(f"malformed YAML in {path}: {e}") from e

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigLoadError(f"sources config {path} must be a mapping at the top level")

    try:
        return SourcesConfig.model_validate(data)
    except ValidationError as e:
        raise ConfigLoadError(f"sources config {path} failed validation: {e}") from e

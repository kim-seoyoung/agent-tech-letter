"""Tests for techletter.config.sources - mirrors TS0001 TC0047-TC0048."""

from __future__ import annotations

from pathlib import Path

import pytest

# --- TC0047: Valid YAML loads to SourcesConfig --------------------------------


def test_tc0047_valid_sources_yaml_loads(tmp_path: Path) -> None:
    from techletter.config import load_sources

    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
arxiv:
  enabled: true
  categories: ["cs.AI", "cs.CL"]
  keywords: ["agent", "tool-use"]
github:
  enabled: true
  spoken_language: "en"
  period: "weekly"
rss:
  enabled: true
  feeds:
    - "https://thenewstack.io/ai/feed/"
"""
    )
    config = load_sources(yaml_path)
    assert config.arxiv.enabled is True
    assert config.arxiv.categories == ["cs.AI", "cs.CL"]
    assert config.github.enabled is True
    assert config.github.period == "weekly"
    assert config.rss.enabled is True
    assert any(str(f) == "https://thenewstack.io/ai/feed/" for f in config.rss.feeds)


def test_tc0047b_missing_source_defaults_to_disabled(tmp_path: Path) -> None:
    from techletter.config import load_sources

    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
arxiv:
  enabled: true
  categories: ["cs.AI"]
"""
    )
    config = load_sources(yaml_path)
    assert config.arxiv.enabled is True
    assert config.github.enabled is False
    assert config.rss.enabled is False


# --- TC0048: Unknown top-level key raises --------------------------------------


def test_tc0048_unknown_top_level_key_raises(tmp_path: Path) -> None:
    from techletter.config import ConfigLoadError, load_sources

    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
arxiv:
  enabled: true
  categories: ["cs.AI"]
reddit:
  enabled: true
"""
    )
    with pytest.raises(ConfigLoadError):
        load_sources(yaml_path)


# --- TC0053: Malformed YAML raises ConfigLoadError -----------------------------


def test_tc0053_malformed_yaml_raises(tmp_path: Path) -> None:
    from techletter.config import ConfigLoadError, load_sources

    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text("arxiv:\n  enabled: true\n bad: indentation\n")
    with pytest.raises(ConfigLoadError):
        load_sources(yaml_path)


def test_tc0053b_missing_file_raises(tmp_path: Path) -> None:
    from techletter.config import ConfigLoadError, load_sources

    yaml_path = tmp_path / "does-not-exist.yaml"
    with pytest.raises(ConfigLoadError):
        load_sources(yaml_path)


def test_tc0053c_malformed_rss_feed_url_raises(tmp_path: Path) -> None:
    from techletter.config import ConfigLoadError, load_sources

    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
rss:
  enabled: true
  feeds:
    - "not-a-url"
"""
    )
    with pytest.raises(ConfigLoadError):
        load_sources(yaml_path)

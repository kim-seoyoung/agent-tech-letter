"""Tests for README.md - mirrors TS0003 TC0190-TC0197."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
README = _REPO_ROOT / "README.md"


def test_readme_exists_and_non_empty() -> None:
    assert README.exists()
    text = README.read_text(encoding="utf-8")
    assert len(text) > 500


def test_readme_has_quickstart_section() -> None:
    text = README.read_text(encoding="utf-8")
    assert "## Quickstart" in text
    assert "uv sync" in text
    assert "uv run pytest" in text


def test_readme_documents_cli_subcommands() -> None:
    text = README.read_text(encoding="utf-8")
    assert "techletter dry-run" in text
    assert "techletter draft" in text
    assert "techletter send" in text


def test_readme_documents_env_vars() -> None:
    text = README.read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY" in text
    assert "LLM_BUDGET_TOKENS" in text
    assert "LLM_MODEL" in text


def test_readme_mentions_no_inline_secrets() -> None:
    """README must not contain real API keys / tokens."""
    import re

    text = README.read_text(encoding="utf-8")
    # Allow example/placeholder patterns like sk-ant-... but not real keys
    real_key_pattern = re.compile(r"sk-ant-[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16}")
    assert not real_key_pattern.search(text)

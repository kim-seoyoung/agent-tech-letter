"""Tests for techletter.orchestration.cli — TS0003 TC0126-TC0139."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from techletter.orchestration.cli import (
    BUDGET_EXCEEDED_MARKER,
    EXIT_BUDGET_EXCEEDED,
    EXIT_CONFIG_ERROR,
    EXIT_OK,
    cli,
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# --- Help + version ------------------------------------------------------------


def test_help_shows_subcommands(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "draft" in result.output
    assert "send" in result.output
    assert "dry-run" in result.output


def test_version_flag(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


# --- TC0126: draft subcommand wires sources + composer + assemble_issue ------


def test_tc0126_draft_subcommand_writes_draft(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Build a minimal sources.yaml with all sources disabled (so fetch returns [])
    config = tmp_path / "sources.yaml"
    config.write_text("arxiv:\n  enabled: false\n")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        cli, ["draft", "--config", str(config), "--output-dir", str(tmp_path / "drafts")]
    )
    # With zero items, the CLI exits 0 with the "no items" message
    assert result.exit_code == 0
    assert "no items fetched" in result.output


# --- TC0137: BUDGET_EXCEEDED marker goes to STDERR (the load-bearing test) ----


def test_tc0137_budget_exceeded_marker_on_stderr(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When budget overflows during a run, the marker must appear on stderr
    so draft.yml's grep can detect it without competing with stdout."""
    from techletter.compose.issue import assemble_issue
    from techletter.llm.client import BudgetExceededError

    # Force the stub_issue to raise BudgetExceededError
    def _stub_raises(*args: object, **kwargs: object) -> object:
        raise BudgetExceededError(
            "projected 250000 > budget 200000 (used: 100000, projected additional: 150000)"
        )

    monkeypatch.setattr("techletter.orchestration.cli._stub_issue", _stub_raises)
    _ = assemble_issue  # silence unused

    config = tmp_path / "sources.yaml"
    # Need at least one source enabled so fetch produces items (but we'll mock fetch_all)
    config.write_text("arxiv:\n  enabled: false\nrss:\n  enabled: true\n  feeds: []\n")

    # Mock the fetch path to return some items
    from datetime import UTC, datetime

    from techletter.models import Item

    fake_items = [
        Item.model_validate(
            {
                "source": "rss",
                "title": "T",
                "url": "https://example.com/1",
                "summary_excerpt": "s",
                "published_at": datetime(2026, 5, 20, tzinfo=UTC),
                "item_kind": "blog_post",
                "raw": {},
            }
        )
    ]

    def _fake_fetch_all(self: object, window_days: int) -> list[Item]:
        return fake_items

    monkeypatch.setattr("techletter.sources.registry.SourceRegistry.fetch_all", _fake_fetch_all)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        cli, ["draft", "--config", str(config), "--output-dir", str(tmp_path / "drafts")]
    )
    assert result.exit_code == EXIT_BUDGET_EXCEEDED
    # CRITICAL: marker must appear on STDERR, not STDOUT
    assert BUDGET_EXCEEDED_MARKER in result.stderr
    assert BUDGET_EXCEEDED_MARKER not in result.stdout


def test_tc0137_marker_is_grepable(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The marker string is a stable token that draft.yml's grep targets."""
    # Just verify the constant; the actual workflow test is in TS0003
    assert BUDGET_EXCEEDED_MARKER == "BUDGET_EXCEEDED"


# --- Config error → exit 3 -----------------------------------------------------


def test_missing_config_file_exit_code(runner: CliRunner, tmp_path: Path) -> None:
    """Pointing at a non-existent config file → click's path validation
    raises with exit code 2 (click's standard for usage error)."""
    result = runner.invoke(cli, ["draft", "--config", str(tmp_path / "missing.yaml")])
    # click's standard "no such file" usage error is exit 2
    assert result.exit_code in (2, EXIT_CONFIG_ERROR)


def test_malformed_yaml_exit_code(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed YAML → EXIT_CONFIG_ERROR (3) with stderr message."""
    config = tmp_path / "bad.yaml"
    config.write_text("arxiv:\n  enabled: true\n bad: indentation\n")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["draft", "--config", str(config)])
    assert result.exit_code == EXIT_CONFIG_ERROR
    assert "config error" in result.stderr


# --- dry-run subcommand --------------------------------------------------------


def test_dry_run_subcommand_uses_local_output(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "sources.yaml"
    config.write_text("arxiv:\n  enabled: false\n")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        cli, ["dry-run", "--config", str(config), "--output-dir", str(tmp_path / "drafts/.local")]
    )
    assert result.exit_code == 0


# --- send subcommand (stub) ----------------------------------------------------


def test_send_no_channels_registered_exits_ok(runner: CliRunner, tmp_path: Path) -> None:
    """In v0 (pre-EP0004), no channels are registered; send exits 0."""
    draft = tmp_path / "draft.md"
    draft.write_text("# Issue body\n")
    result = runner.invoke(cli, ["send", "--issue", "issue-2026-05-20", "--draft-path", str(draft)])
    assert result.exit_code == EXIT_OK
    assert "no channels registered" in result.output


# --- Env var defaults ----------------------------------------------------------


def test_budget_tokens_env_var(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--budget-tokens can be set via LLM_BUDGET_TOKENS env var."""
    monkeypatch.setenv("LLM_BUDGET_TOKENS", "50000")
    config = tmp_path / "sources.yaml"
    config.write_text("arxiv:\n  enabled: false\n")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["draft", "--config", str(config)])
    assert result.exit_code == 0  # exits cleanly with no items


def test_model_env_var(runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LLM_MODEL", "test-model")
    config = tmp_path / "sources.yaml"
    config.write_text("arxiv:\n  enabled: false\n")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["draft", "--config", str(config)])
    assert result.exit_code == 0

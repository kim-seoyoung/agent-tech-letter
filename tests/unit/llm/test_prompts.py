"""Tests for techletter.llm.prompts."""

from __future__ import annotations

from pathlib import Path

import pytest

from techletter.llm.prompts import PromptLoadError, load_prompt


def test_load_prompt_reads_file(tmp_path: Path) -> None:
    (tmp_path / "cluster.md").write_text("Cluster the items into topics.\n", encoding="utf-8")
    result = load_prompt("cluster", prompts_dir=tmp_path)
    assert "Cluster the items" in result


def test_load_prompt_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(PromptLoadError):
        load_prompt("does-not-exist", prompts_dir=tmp_path)


def test_load_prompt_default_dir_resolves_to_project_prompts() -> None:
    """The default prompts dir resolves to the project's `prompts/` folder.
    Loading a non-existent prompt confirms the path resolution by raising."""
    with pytest.raises(PromptLoadError) as exc_info:
        load_prompt("definitely-not-a-real-prompt-name")
    # The error message should mention the expected path
    assert "prompts" in str(exc_info.value)

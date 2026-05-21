"""Tests for techletter.cache - mirrors TS0003 TC0151-TC0165."""

from __future__ import annotations

from pathlib import Path

import pytest

from techletter.cache import (
    FetchCache,
    LlmCache,
    compute_fetch_key,
    compute_llm_key,
    is_ci_environment,
    reset_ci_warning_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_warning() -> None:
    reset_ci_warning_for_tests()


@pytest.fixture(autouse=True)
def _ensure_no_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make sure tests run as if NOT in CI by default."""
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


# --- Key derivation ------------------------------------------------------------


def test_fetch_key_deterministic() -> None:
    k1 = compute_fetch_key(source="arxiv", window_days=7)
    k2 = compute_fetch_key(source="arxiv", window_days=7)
    assert k1 == k2
    assert len(k1) == 64  # SHA-256 hex


def test_fetch_key_differs_by_source() -> None:
    assert compute_fetch_key(source="arxiv", window_days=7) != compute_fetch_key(
        source="github", window_days=7
    )


def test_fetch_key_differs_by_window() -> None:
    assert compute_fetch_key(source="arxiv", window_days=7) != compute_fetch_key(
        source="arxiv", window_days=14
    )


def test_llm_key_includes_temperature() -> None:
    k1 = compute_llm_key(prompt="hi", model="m", temperature=0.0)
    k2 = compute_llm_key(prompt="hi", model="m", temperature=0.5)
    assert k1 != k2


# --- TC0159: CI guard parametric (the load-bearing test) -----------------------


@pytest.mark.parametrize(
    ("env_var", "value"),
    [
        ("CI", "true"),
        ("CI", "1"),
        ("GITHUB_ACTIONS", "true"),
        ("GITHUB_ACTIONS", "yes"),
    ],
)
def test_tc0159_is_ci_environment_parametric(
    monkeypatch: pytest.MonkeyPatch, env_var: str, value: str
) -> None:
    monkeypatch.setenv(env_var, value)
    assert is_ci_environment() is True


def test_tc0159_not_ci_when_unset() -> None:
    assert is_ci_environment() is False


def test_tc0159_not_ci_when_false_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI", "false")
    monkeypatch.setenv("GITHUB_ACTIONS", "")
    assert is_ci_environment() is False


# --- Cache get/put round-trip --------------------------------------------------


def test_fetch_cache_get_put_roundtrip(tmp_path: Path) -> None:
    cache = FetchCache(cache_dir=tmp_path)
    key = compute_fetch_key(source="arxiv", window_days=7)
    assert cache.get(key) is None  # cold
    cache.put(key, {"items": [{"id": 1}, {"id": 2}]})
    result = cache.get(key)
    assert result == {"items": [{"id": 1}, {"id": 2}]}


def test_llm_cache_get_put_roundtrip(tmp_path: Path) -> None:
    cache = LlmCache(cache_dir=tmp_path)
    key = compute_llm_key(prompt="hello", model="claude")
    cache.put(key, {"text": "world"})
    assert cache.get(key) == {"text": "world"}


# --- CI guard behaviour --------------------------------------------------------


def test_get_in_ci_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    cache = FetchCache(cache_dir=tmp_path)
    key = compute_fetch_key(source="arxiv", window_days=7)
    cache.put(key, {"data": "exists"})  # write while NOT in CI
    monkeypatch.setenv("CI", "true")
    with caplog.at_level("WARNING"):
        assert cache.get(key) is None  # in CI, even an existing entry returns None
    assert any("HARD-DISABLED" in r.message for r in caplog.records)


def test_put_in_ci_is_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    cache = FetchCache(cache_dir=tmp_path)
    key = compute_fetch_key(source="arxiv", window_days=7)
    cache.put(key, {"data": "should not write"})
    # Verify nothing was written to disk
    expected_path = tmp_path / "fetch" / f"{key}.json"
    assert not expected_path.exists()


# --- Namespace isolation -------------------------------------------------------


def test_fetch_and_llm_caches_isolated(tmp_path: Path) -> None:
    """FetchCache and LlmCache live in different subdirectories."""
    fc = FetchCache(cache_dir=tmp_path)
    lc = LlmCache(cache_dir=tmp_path)
    fc.put("samekey", {"from": "fetch"})
    lc.put("samekey", {"from": "llm"})
    assert fc.get("samekey") == {"from": "fetch"}
    assert lc.get("samekey") == {"from": "llm"}


def test_cache_handles_missing_dir_gracefully(tmp_path: Path) -> None:
    """First put() creates the parent directory."""
    deep = tmp_path / "deep" / "nested"
    cache = FetchCache(cache_dir=deep)
    cache.put("k", {"v": 1})
    assert (deep / "fetch" / "k.json").exists()

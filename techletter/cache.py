"""Dev-only caches: FetchCache + LlmCache.

Per US0014 + TRD ADR-005: caches live in `.cache/` (git-ignored),
exist ONLY to speed up local prompt iteration. They are HARD-DISABLED
in CI to prevent stale cache data from drifting between local and prod
runs.

CI detection: CI=true or GITHUB_ACTIONS=true. When detected, `get`
returns None and `put` is a no-op (with a one-time warning per process).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

__all__ = [
    "CACHE_DIR",
    "FetchCache",
    "LlmCache",
    "compute_fetch_key",
    "compute_llm_key",
    "is_ci_environment",
]

logger = logging.getLogger(__name__)

CACHE_DIR = Path(".cache")

_ci_warning_emitted = False


def is_ci_environment() -> bool:
    """True if running in CI (CI=true OR GITHUB_ACTIONS=true).

    Per TC0159: both env vars are checked. Either one set to a truthy
    value disables the cache.
    """
    return _truthy(os.environ.get("CI")) or _truthy(os.environ.get("GITHUB_ACTIONS"))


def _truthy(v: str | None) -> bool:
    if v is None:
        return False
    return v.lower() in ("true", "1", "yes", "on")


def _emit_ci_warning_once() -> None:
    global _ci_warning_emitted
    if not _ci_warning_emitted:
        logger.warning("cache: CI environment detected; cache is HARD-DISABLED for this run")
        _ci_warning_emitted = True


def compute_fetch_key(*, source: str, window_days: int, extra: str = "") -> str:
    """SHA-256 cache key for a source fetch (per source + window + extras)."""
    blob = f"fetch|{source}|window={window_days}|{extra}".encode()
    return hashlib.sha256(blob).hexdigest()


def compute_llm_key(*, prompt: str, model: str, temperature: float = 0.0) -> str:
    """SHA-256 cache key for an LLM call (per prompt + model + temperature)."""
    blob = f"llm|{model}|temp={temperature}|{prompt}".encode()
    return hashlib.sha256(blob).hexdigest()


class _BaseCache:
    """Shared cache machinery (CI guard + JSON-on-disk storage)."""

    namespace: str

    def __init__(self, *, cache_dir: Path | None = None) -> None:
        self._cache_dir = (cache_dir or CACHE_DIR) / self.namespace

    def _path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    def get(self, key: str) -> Any | None:
        if is_ci_environment():
            _emit_ci_warning_once()
            return None
        path = self._path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("cache: failed to read %s: %s", path, e)
            return None

    def put(self, key: str, value: Any) -> None:
        if is_ci_environment():
            _emit_ci_warning_once()
            return
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(json.dumps(value, default=str), encoding="utf-8")
        except OSError as e:
            logger.warning("cache: failed to write %s: %s", path, e)


class FetchCache(_BaseCache):
    """Cache for source fetch results (per source + window)."""

    namespace = "fetch"


class LlmCache(_BaseCache):
    """Cache for LLM responses (per prompt + model + temperature)."""

    namespace = "llm"


def reset_ci_warning_for_tests() -> None:
    """Test-only: reset the one-shot CI warning so each test sees it."""
    global _ci_warning_emitted
    _ci_warning_emitted = False

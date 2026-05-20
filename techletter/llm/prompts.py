"""Prompt loader for Tech-Letter for HYL.

Per EP0002 AC8: all prompts live as `.md` files under `prompts/`,
loaded at runtime — no inline LLM prompts in code. This module is
the one place that knows where prompts live and how to load them.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["PromptLoadError", "load_prompt"]

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class PromptLoadError(Exception):
    """Raised when a prompt file is missing or unreadable."""


def load_prompt(name: str, *, prompts_dir: Path | None = None) -> str:
    """Load `prompts/{name}.md` and return its contents.

    Args:
        name: prompt file stem (e.g., ``"cluster"`` for ``prompts/cluster.md``)
        prompts_dir: override the prompts directory (used by tests)

    Raises:
        PromptLoadError: if the file does not exist or cannot be read
    """
    base = prompts_dir if prompts_dir is not None else _PROMPTS_DIR
    path = base / f"{name}.md"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise PromptLoadError(f"prompt not found: {path}") from e
    except OSError as e:
        raise PromptLoadError(f"could not read prompt {path}: {e}") from e

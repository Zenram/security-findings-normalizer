"""
Prompt loading + versioning (CAPSTONE_PLAN Stage 3: each version is its own file
`prompts/extract_vN.md`, referenced by name in every logged result).

A prompt file contains a single `{source_text}` placeholder where the untrusted
source document is injected inside explicit data boundaries.
"""

from __future__ import annotations

from functools import lru_cache

from src.config import PROMPTS_DIR


class PromptNotFound(Exception):
    pass


@lru_cache(maxsize=None)
def _read_prompt_file(version: str) -> str:
    path = PROMPTS_DIR / f"extract_{version}.md"
    if not path.exists():
        available = sorted(p.stem for p in PROMPTS_DIR.glob("extract_*.md"))
        raise PromptNotFound(
            f"Prompt '{version}' not found at {path}. Available: {available or 'none'}"
        )
    return path.read_text(encoding="utf-8")


def render_prompt(version: str, source_text: str) -> str:
    """Render prompt `version` with the source document injected as data.

    We do NOT use str.format on the whole template (the template contains JSON
    braces); we replace only the explicit `{source_text}` token.
    """
    template = _read_prompt_file(version)
    if "{source_text}" not in template:
        raise PromptNotFound(
            f"Prompt '{version}' is missing the required {{source_text}} placeholder."
        )
    return template.replace("{source_text}", source_text)

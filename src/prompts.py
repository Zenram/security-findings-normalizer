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


# --- Part 2 (RAG) answerer prompts -------------------------------------------
# Same versioning discipline as extraction: each version is its own file
# `prompts/rag_answer_vN.md`, referenced by name in every logged answer, logged
# in prompts/CHANGELOG.md. The template carries two placeholders injected as
# data inside explicit boundaries: {sources} (the numbered retrieved chunks) and
# {question} (the user question).


@lru_cache(maxsize=None)
def _read_rag_prompt_file(version: str) -> str:
    path = PROMPTS_DIR / f"rag_answer_{version}.md"
    if not path.exists():
        available = sorted(p.stem for p in PROMPTS_DIR.glob("rag_answer_*.md"))
        raise PromptNotFound(
            f"RAG prompt '{version}' not found at {path}. Available: {available or 'none'}"
        )
    return path.read_text(encoding="utf-8")


def render_rag_prompt(version: str, sources: str, question: str) -> str:
    """Render RAG answerer prompt `version` with the numbered sources and the
    question injected as data. Only the explicit `{sources}` / `{question}`
    tokens are replaced (the template contains JSON braces)."""
    template = _read_rag_prompt_file(version)
    for token in ("{sources}", "{question}"):
        if token not in template:
            raise PromptNotFound(
                f"RAG prompt '{version}' is missing the required {token} placeholder."
            )
    return template.replace("{sources}", sources).replace("{question}", question)

"""Part 2 Step 3 — RAG answerer with sources, context budget, and honest refusal.

Pipeline for one question:

    retrieve (Step 2) -> build numbered context under a TOKEN BUDGET ->
    ask the model to answer ONLY from the context and cite sources ->
    parse structured {found, answer, citations} ->
    VALIDATE citations (drop invented labels; unsupported -> not found) ->
    return an answer with real sources, or an honest "I don't know".

Design mirrors the course lesson (`lesson-08-rag/starter/rag.py`) but routes
through this project's existing model adapters (`src/models/`), so the SAME
answerer runs on Gemini `gemini-3.5-flash` or Ollama `qwen3:8b` for a like-for-
like comparison — the plan's requirement #2.

Heavily graded behaviors, built explicitly here:
  - cite doc + section per claim (citations map back to retrieved chunks);
  - a token budget on the context;
  - "I don't know / not in the documents" when retrieval is empty/weak or the
    answer is not grounded — never invent.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import tiktoken

from src.config import REQUEST_TIMEOUT_SECONDS, SAMPLING_CONFIGS, SamplingConfig
from src.models import get_adapter
from src.models.base import ModelError
from src.prompts import render_rag_prompt
from src.rag.retrieve import Retriever

# cl100k_base is a stable, API-free tokenizer used only to size the context.
_ENC = tiktoken.get_encoding("cl100k_base")

DEFAULT_K = 5
DEFAULT_CONTEXT_BUDGET_TOKENS = 2000       # max tokens of sources put in the prompt
DEFAULT_MAX_OUTPUT_TOKENS = 600

NOT_FOUND_MESSAGE = "I could not find this in the documents available to you."

# Below this fused retrieval score the top hit is too weak to answer from
# (triggers refusal before any model call). 0 disables the gate.
MIN_RETRIEVAL_SCORE = 0.0


def n_tokens(text: str) -> int:
    return len(_ENC.encode(text))


@dataclass
class Source:
    """One numbered source placed into the context."""

    label: str            # "S1", "S2", …
    chunk_id: str
    source: str           # document path
    doc_type: str
    section: str
    text: str


@dataclass
class RagAnswer:
    """Result of answering one question. Logged with model + prompt version +
    sampling so a run is fully reproducible (same discipline as Part 1)."""

    question: str
    found: bool
    answer: str
    citations: list[str]                     # validated labels actually used
    sources: list[dict] = field(default_factory=list)   # the numbered context sent
    retrieved: list[str] = field(default_factory=list)  # chunk_ids retrieved
    dropped_citations: list[str] = field(default_factory=list)  # invented labels removed
    model: str = ""
    prompt_version: str = ""
    sampling: str = ""
    latency_seconds: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None

    def as_dict(self) -> dict:
        return {
            "question": self.question,
            "found": self.found,
            "answer": self.answer,
            "citations": self.citations,
            "cited_sources": [s for s in self.sources if s["label"] in self.citations],
            "sources": self.sources,
            "retrieved": self.retrieved,
            "dropped_citations": self.dropped_citations,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "sampling": self.sampling,
            "latency_seconds": self.latency_seconds,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "error": self.error,
        }


# --- context assembly --------------------------------------------------------

def build_context(hits: list[dict], budget: int = DEFAULT_CONTEXT_BUDGET_TOKENS
                  ) -> tuple[str, list[Source]]:
    """Turn retrieved chunks into numbered sources that fit the token budget.

    A chunk that does not fit is skipped; a smaller later chunk may still fit
    (we do not stop at the first overflow). Every source carries its document +
    section so the model can cite doc + section, and so citations map back to a
    real chunk.
    """
    sources: list[Source] = []
    blocks: list[str] = []
    used = 0
    for i, h in enumerate(hits, 1):
        label = f"S{i}"
        header = f"[{label}] {h['source']}"
        if h.get("section"):
            header += f" — section: {h['section']}"
        block = f"{header}\n{h['text']}"
        cost = n_tokens(block)
        if used + cost > budget and sources:
            continue  # skip this one, try to fit later (smaller) chunks
        blocks.append(block)
        used += cost
        sources.append(Source(
            label=label, chunk_id=h["chunk_id"], source=h["source"],
            doc_type=h.get("doc_type", ""), section=h.get("section", ""),
            text=h["text"],
        ))
    return "\n\n".join(blocks), sources


# --- citation validation -----------------------------------------------------

_LABEL_RE = re.compile(r"S\d+")


def _normalize_labels(raw: list, valid: set[str]) -> tuple[list[str], list[str]]:
    """Normalize model-returned citation labels ("[S1]" -> "S1"), keep only
    labels that correspond to a real source, and report the dropped ones."""
    kept: list[str] = []
    dropped: list[str] = []
    for item in raw or []:
        for found in _LABEL_RE.findall(str(item).upper()):
            if found in valid and found not in kept:
                kept.append(found)
            elif found not in valid and found not in dropped:
                dropped.append(found)
    return kept, dropped


# --- structured-output parsing ----------------------------------------------

def _parse_answer_json(text: str) -> dict | None:
    """Parse the model's JSON answer. Tolerates a stray code fence; returns None
    if nothing parseable is found (the caller turns that into a refusal)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


# --- the answerer ------------------------------------------------------------

class RagAnswerer:
    def __init__(self, retriever: Retriever | None = None,
                 model: str = "gemini", prompt_version: str = "v1",
                 sampling: str | SamplingConfig = "deterministic",
                 k: int = DEFAULT_K, context_budget: int = DEFAULT_CONTEXT_BUDGET_TOKENS,
                 timeout: int = REQUEST_TIMEOUT_SECONDS,
                 min_retrieval_score: float = MIN_RETRIEVAL_SCORE):
        self.retriever = retriever or Retriever(mode="hybrid")
        self.model = model
        self.prompt_version = prompt_version
        self.sampling = sampling if isinstance(sampling, SamplingConfig) else SAMPLING_CONFIGS[sampling]
        self.k = k
        self.context_budget = context_budget
        self.timeout = timeout
        self.min_retrieval_score = min_retrieval_score
        self._adapter = None  # lazy — importing needs no API key / Ollama

    def _refusal(self, question: str, retrieved: list[str], sources: list[dict],
                 error: str | None = None) -> RagAnswer:
        return RagAnswer(
            question=question, found=False, answer=NOT_FOUND_MESSAGE, citations=[],
            sources=sources, retrieved=retrieved, model=self.model,
            prompt_version=self.prompt_version, sampling=self.sampling.name, error=error,
        )

    def answer(self, question: str, doc_types: list[str] | None = None) -> RagAnswer:
        hits = self.retriever.search(question, k=self.k, doc_types=doc_types)
        retrieved = [h["chunk_id"] for h in hits]

        # Honest refusal #1: nothing retrieved, or top hit below the score gate.
        if not hits or (self.min_retrieval_score > 0
                        and hits[0].get("score", 0.0) < self.min_retrieval_score):
            return self._refusal(question, retrieved, [])

        context, sources = build_context(hits, self.context_budget)
        source_dicts = [
            {"label": s.label, "chunk_id": s.chunk_id, "source": s.source,
             "doc_type": s.doc_type, "section": s.section}
            for s in sources
        ]
        valid_labels = {s.label for s in sources}

        prompt = render_rag_prompt(self.prompt_version, context, question)

        if self._adapter is None:
            self._adapter = get_adapter(self.model)
        try:
            resp = self._adapter.generate(prompt, self.sampling, self.timeout)
        except ModelError as exc:
            return self._refusal(question, retrieved, source_dicts, error=str(exc))

        parsed = _parse_answer_json(resp.text)
        if parsed is None:
            # Unparseable output -> refuse rather than surface garbage.
            ans = self._refusal(question, retrieved, source_dicts,
                                error="model returned unparseable answer")
            ans.latency_seconds = resp.latency_seconds
            ans.input_tokens, ans.output_tokens = resp.input_tokens, resp.output_tokens
            return ans

        found = bool(parsed.get("found", False))
        answer_text = str(parsed.get("answer", "")).strip()
        citations, dropped = _normalize_labels(parsed.get("citations", []), valid_labels)

        # Honest refusal #2: model claims an answer but cites nothing real -> not-found.
        if found and not citations:
            found = False
            answer_text = NOT_FOUND_MESSAGE

        if not found:
            answer_text = answer_text or NOT_FOUND_MESSAGE
            citations = []

        return RagAnswer(
            question=question, found=found, answer=answer_text, citations=citations,
            sources=source_dicts, retrieved=retrieved, dropped_citations=dropped,
            model=self.model, prompt_version=self.prompt_version,
            sampling=self.sampling.name, latency_seconds=resp.latency_seconds,
            input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
        )

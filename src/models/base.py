"""
Shared model-adapter contract. Gemini and Ollama both implement `ModelAdapter`
so the rest of the pipeline is model-agnostic (CAPSTONE_PLAN: "both behind one
shared interface"; DEV_HANDOFF step 3).

An adapter's only job: given a fully-rendered prompt, return raw text + timing +
token usage. It does NOT parse, validate, or normalize — that happens upstream
in extract.py so the logic is identical across models.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Optional

from src.config import SamplingConfig


@dataclass
class ModelResponse:
    """Raw output of one model call (one network round-trip)."""

    text: str
    latency_seconds: float
    # Token usage when the provider reports it; None when unavailable (e.g. the
    # local model does not always surface token counts). Never fabricated.
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    # Free-form provider metadata (model id echoed back, finish reason, etc.).
    meta: dict = field(default_factory=dict)


class ModelError(Exception):
    """Raised when a model call fails irrecoverably (after the adapter's own
    transient handling). The pipeline turns this into a `failed` record rather
    than crashing the whole run."""


class ModelAdapter(abc.ABC):
    """One concrete model behind the shared interface."""

    #: Logical model id used in result logs (e.g. "gemini", "ollama").
    model_id: str
    #: The concrete model name actually called (e.g. "gemini-2.5-flash").
    model_name: str

    @abc.abstractmethod
    def generate(self, prompt: str, sampling: SamplingConfig, timeout: int) -> ModelResponse:
        """Send `prompt` to the model and return its raw text response.

        Must enforce `timeout` (seconds) and apply `sampling` (temperature/top_p).
        Should raise ModelError on unrecoverable failure.
        """
        raise NotImplementedError

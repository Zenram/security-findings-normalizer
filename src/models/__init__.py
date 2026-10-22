"""Model adapters behind one shared interface (CAPSTONE_PLAN Stage 1/2)."""

from __future__ import annotations

from src.config import MODEL_GEMINI, MODEL_OLLAMA
from src.models.base import ModelAdapter, ModelError, ModelResponse
from src.models.gemini_adapter import GeminiAdapter
from src.models.ollama_adapter import OllamaAdapter

__all__ = [
    "ModelAdapter",
    "ModelError",
    "ModelResponse",
    "GeminiAdapter",
    "OllamaAdapter",
    "get_adapter",
]


def get_adapter(model_id: str) -> ModelAdapter:
    """Return the adapter for a logical model id ("gemini" / "ollama")."""
    if model_id == MODEL_GEMINI:
        return GeminiAdapter()
    if model_id == MODEL_OLLAMA:
        return OllamaAdapter()
    raise ValueError(f"Unknown model id '{model_id}'. Expected one of: "
                     f"{MODEL_GEMINI}, {MODEL_OLLAMA}.")

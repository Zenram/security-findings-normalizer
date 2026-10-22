"""
Ollama adapter (local side). Calls the Ollama REST API directly via `requests`
so we control timeout and response shape without an extra client dependency.

Structured output: Ollama's /api/generate accepts `format: "json"`, which
constrains the model to emit valid JSON. Sampling (temperature/top_p) is passed
in `options`. Parsing/validation stays upstream (extract.py), identical to the
Gemini path.

Local models do not report provider-style token usage consistently; when Ollama
returns prompt/eval counts we surface them, otherwise None (never fabricated).
"""

from __future__ import annotations

import time

import requests

from src.config import MODEL_OLLAMA, OLLAMA_HOST, OLLAMA_MODEL, SamplingConfig
from src.models.base import ModelAdapter, ModelError, ModelResponse


class OllamaAdapter(ModelAdapter):
    model_id = MODEL_OLLAMA

    def __init__(self, model_name: str | None = None, host: str | None = None):
        self.model_name = model_name or OLLAMA_MODEL
        self._host = (host or OLLAMA_HOST).rstrip("/")

    def generate(self, prompt: str, sampling: SamplingConfig, timeout: int) -> ModelResponse:
        url = f"{self._host}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",  # constrain to valid JSON
            # Disable "thinking" for reasoning models (qwen3, deepseek-r1, …).
            # Extraction needs the JSON answer, not a long chain-of-thought; this
            # cuts latency dramatically (qwen3:8b: ~116s -> ~a few s per doc).
            # Harmless for non-reasoning models (Ollama ignores it).
            "think": False,
            "options": {
                "temperature": sampling.temperature,
                "top_p": sampling.top_p,
            },
        }

        last_exc: Exception | None = None
        for attempt in range(2):  # 1 try + 1 transient retry
            start = time.perf_counter()
            try:
                resp = requests.post(url, json=payload, timeout=timeout)
            except requests.exceptions.ConnectionError as exc:
                # Ollama not running -> actionable error, no point retrying.
                raise ModelError(
                    f"Cannot reach Ollama at {self._host}. Is it running? "
                    f"(ollama serve) Original error: {exc}"
                ) from exc
            except requests.exceptions.Timeout as exc:
                last_exc = exc
                if attempt == 0:
                    continue
                raise ModelError(
                    f"Ollama call timed out after {timeout}s (model {self.model_name})."
                ) from exc

            if resp.status_code != 200:
                last_exc = ModelError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                if resp.status_code in (503, 500) and attempt == 0:
                    time.sleep(2.0)
                    continue
                raise ModelError(
                    f"Ollama call failed (HTTP {resp.status_code}): {resp.text[:300]}"
                )

            latency = time.perf_counter() - start
            try:
                data = resp.json()
            except ValueError as exc:
                raise ModelError(f"Ollama returned non-JSON envelope: {resp.text[:300]}") from exc

            text = data.get("response", "")
            in_tok = data.get("prompt_eval_count")
            out_tok = data.get("eval_count")
            return ModelResponse(
                text=text,
                latency_seconds=latency,
                input_tokens=in_tok,
                output_tokens=out_tok,
                meta={
                    "model_name": self.model_name,
                    "provider": "ollama",
                    "total_duration_ns": data.get("total_duration"),
                },
            )

        raise ModelError(f"Ollama call failed after retry: {last_exc}")

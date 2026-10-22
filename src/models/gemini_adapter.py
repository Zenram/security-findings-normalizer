"""
Gemini adapter (provider/cloud side). Uses the google-genai client.

Structured output: we request JSON via response_mime_type="application/json" and
pass the schema expectation in the prompt. We keep parsing/validation upstream
(extract.py) so Gemini and Ollama go through identical post-processing.

Timeout + one transient retry on 429/503 are handled here; anything else becomes
a ModelError for the pipeline to record as `failed`.
"""

from __future__ import annotations

import math
import re
import time

from src.config import (
    GEMINI_API_KEY,
    GEMINI_MAX_RETRY_WAIT_SECONDS,
    GEMINI_MODEL,
    MODEL_GEMINI,
    SamplingConfig,
)
from src.models.base import ModelAdapter, ModelError, ModelResponse


def _parse_retry_delay_seconds(error_text: str, default: int = 30) -> int:
    """Pull the server-suggested retry delay out of a 429/503 error string.

    Google returns e.g. "Please retry in 55.286s." and a RetryInfo
    retryDelay: '55s'. We honor that rather than guessing.
    """
    m = re.search(r"retry in\s+(\d+(?:\.\d+)?)s", error_text, re.IGNORECASE)
    if m:
        return max(1, math.ceil(float(m.group(1))))
    m = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", error_text, re.IGNORECASE)
    if m:
        return max(1, math.ceil(float(m.group(1))))
    return default


class GeminiAdapter(ModelAdapter):
    model_id = MODEL_GEMINI

    def __init__(self, model_name: str | None = None, api_key: str | None = None):
        self.model_name = model_name or GEMINI_MODEL
        self._api_key = api_key or GEMINI_API_KEY
        self._client = None  # lazy init so importing the module needs no key

    def _ensure_client(self):
        if self._client is not None:
            return
        if not self._api_key:
            raise ModelError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and fill it in."
            )
        try:
            from google import genai  # imported lazily; optional at import time
        except ImportError as exc:  # pragma: no cover
            raise ModelError(
                "google-genai is not installed. Run: pip install -r requirements.txt"
            ) from exc
        self._client = genai.Client(api_key=self._api_key)

    def generate(self, prompt: str, sampling: SamplingConfig, timeout: int) -> ModelResponse:
        self._ensure_client()

        config = {
            "temperature": sampling.temperature,
            "top_p": sampling.top_p,
            # Ask for raw JSON; prompt still carries the schema + rules.
            "response_mime_type": "application/json",
            # Per-request timeout (milliseconds) enforced by the client.
            "http_options": {"timeout": timeout * 1000},
        }

        # Retry loop: honor the server's retryDelay on 429 (quota) / 503 (load).
        # Free-tier quota windows are ~60s, so a 2s sleep is useless — we wait
        # the suggested delay, bounded by GEMINI_MAX_RETRY_WAIT_SECONDS.
        last_exc: Exception | None = None
        max_attempts = 4
        for attempt in range(max_attempts):
            start = time.perf_counter()
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
            except Exception as exc:  # noqa: BLE001 - classify below
                last_exc = exc
                text = str(exc)
                is_quota = "429" in text or "RESOURCE_EXHAUSTED" in text
                is_load = "503" in text or "UNAVAILABLE" in text or "deadline" in text.lower()
                if (is_quota or is_load) and attempt < max_attempts - 1:
                    # Quota -> honor server delay; load -> short backoff.
                    if is_quota:
                        wait = _parse_retry_delay_seconds(text, default=30)
                    else:
                        wait = min(5 * (attempt + 1), 15)
                    if wait > GEMINI_MAX_RETRY_WAIT_SECONDS:
                        raise ModelError(
                            f"Gemini quota/backoff wait {wait}s exceeds cap "
                            f"{GEMINI_MAX_RETRY_WAIT_SECONDS}s. Raise the cap or "
                            f"use a paid tier / fewer calls. Original: {exc}"
                        ) from exc
                    time.sleep(wait + 0.5)
                    continue
                raise ModelError(f"Gemini call failed: {exc}") from exc

            latency = time.perf_counter() - start
            text = self._extract_text(response)
            in_tok, out_tok = self._extract_usage(response)
            return ModelResponse(
                text=text,
                latency_seconds=latency,
                input_tokens=in_tok,
                output_tokens=out_tok,
                meta={"model_name": self.model_name, "provider": "gemini"},
            )

        raise ModelError(f"Gemini call failed after retry: {last_exc}")

    @staticmethod
    def _extract_text(response) -> str:
        if getattr(response, "text", None):
            return response.text
        parts_text = []
        for candidate in getattr(response, "candidates", None) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                if getattr(part, "text", None):
                    parts_text.append(part.text)
        return "".join(parts_text)

    @staticmethod
    def _extract_usage(response):
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return None, None
        in_tok = getattr(usage, "prompt_token_count", None)
        out_tok = getattr(usage, "candidates_token_count", None)
        return in_tok, out_tok

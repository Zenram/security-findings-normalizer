"""
Central configuration for the Security Findings Normalizer (Stage 1).

Loads from environment (.env via python-dotenv if present). Secrets NEVER live
in source — only `.env.example` is committed. See CAPSTONE_PLAN "Repo Structure
Checklist" and DEV_HANDOFF step 1.

Sampling params are deliberately NOT hardcoded into the model adapters: the eval
harness sets them per-run (Stage 2 "config comparison"). The values here are
defaults used when a caller does not pass an explicit SamplingConfig.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional at runtime
    # python-dotenv not installed or no .env present: fall back to real env.
    pass


# --- Paths -------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"
GOLDEN_DIR = REPO_ROOT / "data" / "golden"
RESULTS_DIR = REPO_ROOT / "results"


# --- Model identity ----------------------------------------------------------

# Provider (cloud) side: Google Gemini / Gemma.
# gemini-2.5-flash is retired for new users; pinned to the current flash-tier
# equivalent. Overridable via GEMINI_MODEL in .env.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

# Local side: Ollama. Candidate qwen2.5:7b (confirm RAM fit on the dev machine).
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")

# Logical model identifiers used throughout the harness / result logs.
MODEL_GEMINI = "gemini"
MODEL_OLLAMA = "ollama"


# --- Run defaults ------------------------------------------------------------

DEFAULT_TEMPERATURE = float(os.environ.get("DEFAULT_TEMPERATURE", "0.0"))
DEFAULT_TOP_P = float(os.environ.get("DEFAULT_TOP_P", "1.0"))
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "60"))

# Max seconds the Gemini adapter will wait out a server-suggested quota/backoff
# delay before giving up. Free-tier windows are ~60s; set generously so a
# rate-limited free key still completes, just slowly.
GEMINI_MAX_RETRY_WAIT_SECONDS = int(os.environ.get("GEMINI_MAX_RETRY_WAIT_SECONDS", "70"))

# Proactive pacing between provider (Gemini/Gemma) calls to respect the
# free-tier per-minute request cap. The free tier shares a ~5 requests/minute
# bucket across models -> ~13s spacing stays safely under it. 0 disables pacing.
# Local (Ollama) calls are never paced.
GEMINI_MIN_SECONDS_BETWEEN_CALLS = float(
    os.environ.get("GEMINI_MIN_SECONDS_BETWEEN_CALLS", "13.0")
)


@dataclass(frozen=True)
class SamplingConfig:
    """Sampling parameters for one extraction call.

    Logged verbatim with every result (Stage 3 logging requirement). `name` is
    a stable label used in the comparison table (model x prompt x sampling).
    """

    name: str
    temperature: float = DEFAULT_TEMPERATURE
    top_p: float = DEFAULT_TOP_P

    def as_log_dict(self) -> dict:
        return {"name": self.name, "temperature": self.temperature, "top_p": self.top_p}


# The >=2 sampling configs the plan requires (Stage 2 "config comparison plan":
# deterministic vs sampled). Externalized here, not buried in adapters.
SAMPLING_CONFIGS: dict[str, SamplingConfig] = {
    "deterministic": SamplingConfig(name="deterministic", temperature=0.0, top_p=1.0),
    "sampled": SamplingConfig(name="sampled", temperature=0.7, top_p=0.95),
}


@dataclass
class RunConfig:
    """What a single `python3 main.py` run sweeps over.

    models x prompt_versions x sampling_configs = the comparison grid. All kept
    as plain lists so the runner stays transparent and the grid is obvious.
    """

    models: list[str] = field(default_factory=lambda: [MODEL_GEMINI, MODEL_OLLAMA])
    prompt_versions: list[str] = field(default_factory=lambda: ["v1", "v2"])
    sampling_configs: list[str] = field(
        default_factory=lambda: ["deterministic", "sampled"]
    )
    request_timeout_seconds: int = REQUEST_TIMEOUT_SECONDS

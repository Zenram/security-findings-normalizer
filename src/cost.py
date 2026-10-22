"""
Cost-per-1000-docs estimation with an HONEST methodology (CAPSTONE_PLAN Stage 2
metric + Open Questions: "do not invent a provider-equivalent price for the
local model").

- Provider (Gemini): cost = tokens x price-per-token, using prices you supply via
  env. If prices are NOT configured, we return None and say so — we do NOT guess
  a price.
- Local (Ollama): there is no per-token invoice. We report cost as None and
  surface the measured signal that IS real: wall-clock latency (and tokens when
  Ollama reports them). The report must state the local-cost methodology
  explicitly rather than fabricate a dollar figure.
"""

from __future__ import annotations

import os
from typing import Optional

# Importing config first ensures .env is loaded (config calls load_dotenv) before
# we read any price env vars.
import src.config  # noqa: F401  (side effect: load .env)


def _price(var: str) -> Optional[str]:
    """Read a price env var at call time (after .env is loaded)."""
    return os.environ.get(var)


def provider_cost_per_1000_docs(
    avg_input_tokens: Optional[float],
    avg_output_tokens: Optional[float],
) -> Optional[float]:
    """USD per 1000 documents for a provider model, or None if prices/tokens are
    unavailable. Never fabricates a price."""
    in_price_raw = _price("GEMINI_INPUT_PRICE_PER_1K")
    out_price_raw = _price("GEMINI_OUTPUT_PRICE_PER_1K")
    if in_price_raw is None or out_price_raw is None:
        return None
    if avg_input_tokens is None or avg_output_tokens is None:
        return None
    try:
        in_price = float(in_price_raw)
        out_price = float(out_price_raw)
    except ValueError:
        return None
    per_doc = (avg_input_tokens / 1000.0) * in_price + (avg_output_tokens / 1000.0) * out_price
    return per_doc * 1000.0


def cost_summary(model_id: str, metrics_dict: dict) -> dict:
    """Return a cost block describing what IS and ISN'T measurable per model."""
    avg_in = metrics_dict.get("avg_input_tokens")
    avg_out = metrics_dict.get("avg_output_tokens")

    if model_id == "gemini":
        usd = provider_cost_per_1000_docs(avg_in, avg_out)
        return {
            "model": model_id,
            "method": "provider token pricing (USD per 1K tokens from env)",
            "cost_per_1000_docs_usd": usd,
            "note": (
                None if usd is not None
                else "Set GEMINI_INPUT_PRICE_PER_1K and GEMINI_OUTPUT_PRICE_PER_1K "
                     "to compute a dollar cost. Not fabricated."
            ),
        }

    # Local model: no invoice. Report the honest measurable signal.
    return {
        "model": model_id,
        "method": "local inference — no per-token invoice",
        "cost_per_1000_docs_usd": None,
        "note": (
            "Local cost is NOT a provider-equivalent price. Compare on measured "
            "latency (p50/p95) and throughput instead. Any machine/amortization "
            "cost must be stated explicitly in REPORT.md, not fabricated here."
        ),
        "latency_p50_seconds": metrics_dict.get("latency_p50"),
        "latency_p95_seconds": metrics_dict.get("latency_p95"),
    }

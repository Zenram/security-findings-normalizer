"""
The shared extraction interface (see CAPSTONE_PLAN Part 1 — Step 2):

    extract(text, model, prompt_version, sampling) -> ExtractionResult

One entry point for both models. Flow per CAPSTONE_PLAN Stage 3:
  render prompt -> call model -> parse+validate+normalize
  -> on failure: ONE repair attempt -> still failing: mark `failed`.

Every result carries its own metadata (model, prompt version, sampling params,
latency, token usage) so results/ files are self-describing for the comparison
report. No silent drops: a failed extraction is recorded, not discarded.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

from src.config import SamplingConfig
from src.models import ModelError, get_adapter
from src.models.base import ModelAdapter
from src.prompts import render_prompt
from src.validate import ValidationOutcome, validate_findings

# Appended to the original prompt output when asking the model to repair its
# own invalid JSON. Kept minimal: we show the error and re-state the contract.
_REPAIR_SUFFIX = """

Your previous response could not be parsed/validated as the required JSON array
of findings. Error:
{error}

Return ONLY a valid JSON array of finding objects following the schema and rules
above. No prose, no markdown fences.
"""


@dataclass
class ExtractionResult:
    """Everything produced by one extract() call. Serialized to results/."""

    # --- identity / provenance (logged every time) ---
    model: str
    model_name: str
    prompt_version: str
    sampling: dict
    source_id: str  # golden entry id or input file stem
    route: str = "llm"  # "llm" | "parser" (D1 routing — reportable result)
    source: Optional[str] = None  # detected source family

    # --- outcome ---
    status: str = "pending"  # set to "ok" | "failed" before returning
    findings: list[dict] = field(default_factory=list)
    repaired: bool = False  # True if the 1 repair attempt was used and succeeded
    error: Optional[str] = None
    normalization_flags: list[str] = field(default_factory=list)

    # --- measurement raw signals (metrics computed later in evaluate.py) ---
    latency_seconds: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


def extract(
    text: str,
    model: str,
    prompt_version: str,
    sampling: SamplingConfig,
    source_id: str = "adhoc",
    timeout: int = 60,
    adapter: Optional[ModelAdapter] = None,
) -> ExtractionResult:
    """Extract findings from `text` with one model/prompt/sampling combination.

    `adapter` can be injected for testing; otherwise resolved from `model`.
    """
    adapter = adapter or get_adapter(model)
    prompt = render_prompt(prompt_version, text)

    base_result = ExtractionResult(
        model=adapter.model_id,
        model_name=adapter.model_name,
        prompt_version=prompt_version,
        sampling=sampling.as_log_dict(),
        source_id=source_id,
    )

    # --- attempt 1 ---
    try:
        response = adapter.generate(prompt, sampling, timeout)
    except ModelError as exc:
        base_result.status = "failed"
        base_result.error = f"model call error: {exc}"
        return base_result

    base_result.latency_seconds = response.latency_seconds
    base_result.input_tokens = response.input_tokens
    base_result.output_tokens = response.output_tokens

    outcome = validate_findings(response.text)
    if outcome.ok:
        _fill_success(base_result, outcome, repaired=False)
        return base_result

    # --- single repair attempt (parse/validate failure only) ---
    repair_prompt = prompt + _REPAIR_SUFFIX.format(error=outcome.error)
    try:
        repair_response = adapter.generate(repair_prompt, sampling, timeout)
    except ModelError as exc:
        base_result.status = "failed"
        base_result.error = f"{outcome.error}; repair model error: {exc}"
        return base_result

    # Repair call latency is additive; record the total spent.
    if base_result.latency_seconds is not None and repair_response.latency_seconds:
        base_result.latency_seconds += repair_response.latency_seconds
    # Prefer the repair call's token usage if the first lacked it.
    base_result.input_tokens = repair_response.input_tokens or base_result.input_tokens
    base_result.output_tokens = repair_response.output_tokens or base_result.output_tokens

    repaired_outcome = validate_findings(repair_response.text)
    if repaired_outcome.ok:
        _fill_success(base_result, repaired_outcome, repaired=True)
        return base_result

    # --- still failing after 1 repair -> mark failed, do not drop ---
    base_result.status = "failed"
    base_result.repaired = True
    base_result.error = (
        f"invalid after repair. first: {outcome.error} | "
        f"second: {repaired_outcome.error}"
    )
    base_result.normalization_flags = repaired_outcome.normalization_flags
    return base_result


def _fill_success(result: ExtractionResult, outcome: ValidationOutcome, repaired: bool) -> None:
    result.status = "ok"
    result.repaired = repaired
    result.findings = outcome.findings_json
    result.normalization_flags = outcome.normalization_flags

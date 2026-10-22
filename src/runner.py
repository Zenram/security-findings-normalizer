"""
End-to-end Stage 1 runner. Single command sweeps the comparison grid
(model x prompt version x sampling), extracts over the golden set, scores with
the D2 harness, and writes everything to results/.

Produces ZERO fabricated numbers: every metric comes from a real model call. If
a model is unreachable (no GEMINI_API_KEY, Ollama not running), that model's
rows are recorded as failed with the reason — the run does not invent output.

Outputs under results/:
  results/raw/<model>__<prompt>__<sampling>.json   per-document extraction results
  results/metrics.json                              aggregated metrics per grid cell
  results/REPORT_DATA.json                          compact table feed for REPORT.md
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.config import RESULTS_DIR, SAMPLING_CONFIGS, RunConfig
from src.config import GEMINI_MIN_SECONDS_BETWEEN_CALLS, MODEL_GEMINI
from src.cost import cost_summary
from src.evaluate import RunMetrics, evaluate_result
from src.extract import extract
from src.routing import route_and_extract
from src.golden import load_golden_set
from src.models import ModelError, get_adapter
import time


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preflight(model_id: str, timeout: int) -> str | None:
    """Return None if the model looks usable, else a human-readable reason.

    We do a cheap construction/connectivity check so an unreachable model yields
    clear failed rows instead of an opaque stack trace mid-run.
    """
    try:
        adapter = get_adapter(model_id)
    except Exception as exc:  # noqa: BLE001
        return f"adapter init failed: {exc}"

    if model_id == "gemini":
        from src.config import GEMINI_API_KEY
        if not GEMINI_API_KEY:
            return "GEMINI_API_KEY not set (copy .env.example to .env)"
    if model_id == "ollama":
        import requests
        from src.config import OLLAMA_HOST
        try:
            r = requests.get(f"{OLLAMA_HOST.rstrip('/')}/api/tags", timeout=5)
            if r.status_code != 200:
                return f"Ollama reachable but returned HTTP {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            return f"Ollama not reachable at {OLLAMA_HOST} ({exc}); run: ollama serve"
    return None


def run(config: RunConfig | None = None, results_dir: Path | None = None) -> dict:
    config = config or RunConfig()
    results_dir = results_dir or RESULTS_DIR
    raw_dir = results_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    golden = load_golden_set()
    print(f"Loaded {len(golden)} golden entries.")

    all_metrics: list[dict] = []

    for model_id in config.models:
        reason = _preflight(model_id, config.request_timeout_seconds)
        model_usable = reason is None
        if not model_usable:
            print(f"[skip-live] model '{model_id}' not usable: {reason}")

        for prompt_version in config.prompt_versions:
            for sampling_name in config.sampling_configs:
                sampling = SAMPLING_CONFIGS[sampling_name]
                cell = f"{model_id}__{prompt_version}__{sampling_name}"
                print(f"=== {cell} ===")

                metrics = RunMetrics(model=model_id, prompt_version=prompt_version,
                                     sampling_name=sampling_name)
                per_doc_results: list[dict] = []

                # Proactive pacing for the provider model to respect free-tier RPM.
                pace = (GEMINI_MIN_SECONDS_BETWEEN_CALLS
                        if (model_usable and model_id == MODEL_GEMINI) else 0.0)
                last_call_ts = 0.0

                for entry in golden:
                    if not model_usable:
                        # Even when the model is down, parser-path docs can still
                        # be extracted deterministically. Route first.
                        from src.routing import detect_source, route_for_source
                        src = detect_source(entry.input_text)
                        if route_for_source(src) == "parser":
                            routed = route_and_extract(
                                text=entry.input_text, model=model_id,
                                prompt_version=prompt_version, sampling=sampling,
                                source_id=entry.entry_id,
                                timeout=config.request_timeout_seconds,
                                raw_reference=entry.input_path.name,
                            )
                            result = routed.result.to_dict()
                            print(f"  [{entry.entry_id}] {result['status']} "
                                  f"({len(result.get('findings', []))} findings) [parser]")
                        else:
                            result = {
                                "model": model_id, "prompt_version": prompt_version,
                                "sampling": sampling.as_log_dict(), "source_id": entry.entry_id,
                                "route": "llm", "source": src,
                                "status": "failed", "findings": [],
                                "error": f"model unavailable: {reason}",
                            }
                    else:
                        # LLM-path docs respect pacing; parser-path docs are instant.
                        from src.routing import detect_source, route_for_source
                        src = detect_source(entry.input_text)
                        if route_for_source(src) == "llm" and pace:
                            elapsed = time.monotonic() - last_call_ts
                            if last_call_ts and elapsed < pace:
                                time.sleep(pace - elapsed)
                            last_call_ts = time.monotonic()
                        routed = route_and_extract(
                            text=entry.input_text,
                            model=model_id,
                            prompt_version=prompt_version,
                            sampling=sampling,
                            source_id=entry.entry_id,
                            timeout=config.request_timeout_seconds,
                            raw_reference=entry.input_path.name,
                        )
                        result = routed.result.to_dict()
                        status = result["status"]
                        n = len(result.get("findings", []))
                        print(f"  [{entry.entry_id}] {status} ({n} findings)"
                              + (f" !repaired" if result.get("repaired") else "")
                              + f" [{routed.route}]")

                    per_doc_results.append(result)
                    evaluate_result(metrics, result, entry.expected)

                # persist per-document raw results for this grid cell
                (raw_dir / f"{cell}.json").write_text(
                    json.dumps(per_doc_results, indent=2), encoding="utf-8"
                )

                mdict = metrics.to_dict()
                mdict["cost"] = cost_summary(model_id, mdict)
                mdict["model_usable"] = model_usable
                mdict["skip_reason"] = reason
                all_metrics.append(mdict)

    payload = {"generated_at": _utc_now(), "grid": all_metrics}
    (results_dir / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_report_data(results_dir, payload)
    _print_summary(all_metrics)
    return payload


def _write_report_data(results_dir: Path, payload: dict) -> None:
    """Compact feed for REPORT.md (Stage 4). Only real cells with data."""
    rows = []
    for m in payload["grid"]:
        rows.append({
            "model": m["model"],
            "prompt_version": m["prompt_version"],
            "sampling": m["sampling"],
            "model_usable": m["model_usable"],
            "pct_valid_json": m["pct_valid_json"],
            "finding_precision": m["finding_precision"],
            "finding_recall": m["finding_recall"],
            "overall_field_accuracy": m["overall_field_accuracy"],
            "hallucination_rate": m["hallucination_rate"],
            "latency_p50": m["latency_p50"],
            "latency_p95": m["latency_p95"],
            "cost_per_1000_docs_usd": m["cost"].get("cost_per_1000_docs_usd"),
        })
    (results_dir / "REPORT_DATA.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _fmt(v, pct=False):
    if v is None:
        return "n/a"
    if pct:
        return f"{v*100:.1f}%"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def _print_summary(all_metrics: list[dict]) -> None:
    print("\n================ SUMMARY ================")
    header = f"{'cell':38} {'valid':>7} {'P':>6} {'R':>6} {'field':>7} {'halluc':>7} {'p50':>7} {'p95':>7}"
    print(header)
    print("-" * len(header))
    for m in all_metrics:
        cell = f"{m['model']}/{m['prompt_version']}/{m['sampling']}"
        print(f"{cell:38} "
              f"{_fmt(m['pct_valid_json'], pct=True):>7} "
              f"{_fmt(m['finding_precision'], pct=True):>6} "
              f"{_fmt(m['finding_recall'], pct=True):>6} "
              f"{_fmt(m['overall_field_accuracy'], pct=True):>7} "
              f"{_fmt(m['hallucination_rate'], pct=True):>7} "
              f"{_fmt(m['latency_p50']):>7} "
              f"{_fmt(m['latency_p95']):>7}")
    print("=========================================")
    print("Full metrics: results/metrics.json | per-doc: results/raw/ | "
          "report feed: results/REPORT_DATA.json")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Security Findings Normalizer — Stage 1 run")
    p.add_argument("--models", nargs="+", default=None,
                   help="Subset of models to run (e.g. --models gemini).")
    p.add_argument("--prompts", nargs="+", default=None,
                   help="Prompt versions to run (e.g. --prompts v1 v2).")
    p.add_argument("--sampling", nargs="+", default=None,
                   help="Sampling configs to run (e.g. --sampling deterministic).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config = RunConfig()
    if args.models:
        config.models = args.models
    if args.prompts:
        config.prompt_versions = args.prompts
    if args.sampling:
        config.sampling_configs = args.sampling
    run(config)
    return 0

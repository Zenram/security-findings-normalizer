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
  results/REPORT_DATA.json                          compact table feed for REPORT_PART1.md
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
                metrics_llm = RunMetrics(model=model_id, prompt_version=prompt_version,
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
                    # A5: the headline model comparison must exclude parser-path
                    # docs (their findings are deterministic and identical for
                    # both models — folding them in flatters/flattens the compare).
                    if result.get("route") != "parser":
                        evaluate_result(metrics_llm, result, entry.expected)

                # persist per-document raw results for this grid cell
                (raw_dir / f"{cell}.json").write_text(
                    json.dumps(per_doc_results, indent=2), encoding="utf-8"
                )

                mdict = metrics.to_dict()
                mdict["cost"] = cost_summary(model_id, mdict)
                mdict["model_usable"] = model_usable
                mdict["skip_reason"] = reason
                # A5: LLM-path-only metrics = the honest model-vs-model comparison.
                mdict["llm_path_only"] = metrics_llm.to_dict()
                all_metrics.append(mdict)

    payload = {"generated_at": _utc_now(), "grid": all_metrics}
    (results_dir / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_report_data(results_dir, payload)
    _print_summary(all_metrics)
    return payload


def _write_report_data(results_dir: Path, payload: dict) -> None:
    """Compact feed for REPORT_PART1.md (Stage 4). Only real cells with data."""
    rows = []
    for m in payload["grid"]:
        llm = m.get("llm_path_only", {})
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
            # A5: LLM-path-only (headline model comparison, excludes parser docs)
            "llm_finding_precision": llm.get("finding_precision"),
            "llm_finding_recall": llm.get("finding_recall"),
            "llm_overall_field_accuracy": llm.get("overall_field_accuracy"),
            "llm_documents": llm.get("documents"),
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
    print("\n================ SUMMARY (all 10 golden docs) ================")
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
    print("\n===== LLM-PATH ONLY (model comparison — excludes parser docs 06/07) =====")
    print(f"{'cell':38} {'P':>6} {'R':>6} {'field':>7} {'docs':>5}")
    print("-" * 65)
    for m in all_metrics:
        llm = m.get("llm_path_only", {})
        cell = f"{m['model']}/{m['prompt_version']}/{m['sampling']}"
        print(f"{cell:38} "
              f"{_fmt(llm.get('finding_precision'), pct=True):>6} "
              f"{_fmt(llm.get('finding_recall'), pct=True):>6} "
              f"{_fmt(llm.get('overall_field_accuracy'), pct=True):>7} "
              f"{str(llm.get('documents','')):>5}")
    print("=========================================")
    print("Full metrics: results/metrics.json | per-doc: results/raw/ | "
          "report feed: results/REPORT_DATA.json")


def rescore(results_dir: Path | None = None) -> dict:
    """Recompute metrics from existing results/raw/*.json WITHOUT calling models.

    Use after changing the scorer (e.g. matcher weights) or to apply route-split
    metrics to an existing run. Reads the golden set for expected findings and
    the per-doc raw outputs; rewrites metrics.json + REPORT_DATA.json.
    """
    from src.golden import load_golden_set

    results_dir = results_dir or RESULTS_DIR
    raw_dir = results_dir / "raw"
    golden = {e.entry_id: e for e in load_golden_set()}

    all_metrics: list[dict] = []
    for raw_file in sorted(raw_dir.glob("*.json")):
        cell = raw_file.stem
        try:
            model_id, prompt_version, sampling_name = cell.split("__")
        except ValueError:
            continue  # skip non-cell files
        per_doc = json.loads(raw_file.read_text(encoding="utf-8"))
        metrics = RunMetrics(model=model_id, prompt_version=prompt_version,
                             sampling_name=sampling_name)
        metrics_llm = RunMetrics(model=model_id, prompt_version=prompt_version,
                                 sampling_name=sampling_name)
        for result in per_doc:
            eid = result.get("source_id")
            if eid not in golden:
                continue
            evaluate_result(metrics, result, golden[eid].expected)
            if result.get("route") != "parser":
                evaluate_result(metrics_llm, result, golden[eid].expected)

        mdict = metrics.to_dict()
        mdict["cost"] = cost_summary(model_id, mdict)
        mdict["model_usable"] = True
        mdict["skip_reason"] = None
        mdict["llm_path_only"] = metrics_llm.to_dict()
        all_metrics.append(mdict)
        print(f"rescored {cell}: all R={_fmt(mdict['finding_recall'], pct=True)} "
              f"| LLM-path R={_fmt(mdict['llm_path_only']['finding_recall'], pct=True)}")

    payload = {"generated_at": _utc_now(), "rescored": True, "grid": all_metrics}
    (results_dir / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_report_data(results_dir, payload)
    _print_summary(all_metrics)
    return payload


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Security Findings Normalizer — Stage 1 run")
    p.add_argument("--models", nargs="+", default=None,
                   help="Subset of models to run (e.g. --models gemini).")
    p.add_argument("--prompts", nargs="+", default=None,
                   help="Prompt versions to run (e.g. --prompts v1 v2).")
    p.add_argument("--sampling", nargs="+", default=None,
                   help="Sampling configs to run (e.g. --sampling deterministic).")
    p.add_argument("--corpus", action="store_true",
                   help="Also process the full unlabeled raw corpus (~30 texts) "
                        "through the pipeline and save outputs to results/corpus/. "
                        "Corpus texts are processed, NOT scored (no golden labels). "
                        "Uses the production config (first model/prompt/sampling).")
    p.add_argument("--corpus-only", action="store_true",
                   help="Process ONLY the raw corpus (skip the golden grid).")
    p.add_argument("--rescore", action="store_true",
                   help="Recompute metrics from existing results/raw/*.json "
                        "without calling any model (applies scorer/route changes).")
    return p


def run_corpus(config: RunConfig | None = None, results_dir: Path | None = None) -> dict:
    """Process the full unlabeled raw corpus (~30 texts) through the pipeline.

    Produces PROCESSING stats only (valid %, latency, cost, routing, finding
    counts) — NOT accuracy, because corpus texts have no golden labels. Writes
    results/corpus/<doc_id>.json and results/corpus_summary.json.
    """
    from src.corpus import load_corpus
    from src.routing import detect_source, route_for_source

    config = config or RunConfig()
    results_dir = results_dir or RESULTS_DIR
    corpus_dir = results_dir / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    # Production config = the first entry of each grid axis.
    model_id = config.models[0]
    prompt_version = config.prompt_versions[0]
    sampling = SAMPLING_CONFIGS[config.sampling_configs[0]]

    reason = _preflight(model_id, config.request_timeout_seconds)
    model_usable = reason is None
    if not model_usable:
        print(f"[corpus] model '{model_id}' not usable: {reason}")

    texts = load_corpus()
    print(f"[corpus] loaded {len(texts)} raw texts "
          f"(config: {model_id}/{prompt_version}/{sampling.name})")

    pace = (GEMINI_MIN_SECONDS_BETWEEN_CALLS
            if (model_usable and model_id == MODEL_GEMINI) else 0.0)
    last_call_ts = 0.0

    processed = 0
    valid = 0
    failed = 0
    total_findings = 0
    latencies: list[float] = []
    in_tokens: list[int] = []
    out_tokens: list[int] = []
    route_counts: dict[str, int] = {"parser": 0, "llm": 0}
    source_counts: dict[str, int] = {}

    for ct in texts:
        src = detect_source(ct.text)
        source_counts[src] = source_counts.get(src, 0) + 1

        if not model_usable and route_for_source(src) == "llm":
            result = {
                "doc_id": ct.doc_id, "origin": ct.origin, "source": src,
                "route": "llm", "status": "failed", "findings": [],
                "error": f"model unavailable: {reason}",
            }
        else:
            if route_for_source(src) == "llm" and pace:
                elapsed = time.monotonic() - last_call_ts
                if last_call_ts and elapsed < pace:
                    time.sleep(pace - elapsed)
                last_call_ts = time.monotonic()
            routed = route_and_extract(
                text=ct.text, model=model_id, prompt_version=prompt_version,
                sampling=sampling, source_id=ct.doc_id,
                timeout=config.request_timeout_seconds, raw_reference=ct.origin,
            )
            result = routed.result.to_dict()
            result["doc_id"] = ct.doc_id
            result["origin"] = ct.origin

        processed += 1
        route_counts[result.get("route", "llm")] = route_counts.get(result.get("route", "llm"), 0) + 1
        if result.get("status") == "ok":
            valid += 1
            total_findings += len(result.get("findings", []))
        else:
            failed += 1
        if result.get("latency_seconds") is not None:
            latencies.append(result["latency_seconds"])
        if result.get("input_tokens") is not None:
            in_tokens.append(result["input_tokens"])
        if result.get("output_tokens") is not None:
            out_tokens.append(result["output_tokens"])

        (corpus_dir / f"{ct.doc_id}.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        print(f"  [{ct.doc_id}] {result.get('status')} "
              f"({len(result.get('findings', []))} findings) [{result.get('route')}]")

    def _pct(a, b):
        return (a / b) if b else None

    def _pctile(data, p):
        if not data:
            return None
        s = sorted(data)
        k = (len(s) - 1) * p
        f = int(k); c = min(f + 1, len(s) - 1)
        return s[f] if f == c else s[f] + (s[c] - s[f]) * (k - f)

    avg_in = (sum(in_tokens) / len(in_tokens)) if in_tokens else None
    avg_out = (sum(out_tokens) / len(out_tokens)) if out_tokens else None

    summary = {
        "generated_at": _utc_now(),
        "config": {"model": model_id, "prompt_version": prompt_version,
                   "sampling": sampling.name},
        "note": ("Corpus texts are UNLABELED: processed, not scored. Accuracy/"
                 "precision/recall are only in metrics.json (golden set)."),
        "texts_processed": processed,
        "valid_json": valid,
        "pct_valid_json": _pct(valid, processed),
        "failed": failed,
        "total_findings": total_findings,
        "route_counts": route_counts,
        "source_counts": source_counts,
        "latency_p50": _pctile(latencies, 0.50),
        "latency_p95": _pctile(latencies, 0.95),
        "avg_input_tokens": avg_in,
        "avg_output_tokens": avg_out,
        "cost": cost_summary(model_id, {"avg_input_tokens": avg_in,
                                        "avg_output_tokens": avg_out,
                                        "latency_p50": _pctile(latencies, 0.50),
                                        "latency_p95": _pctile(latencies, 0.95)}),
    }
    (results_dir / "corpus_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")

    print("\n============ CORPUS SUMMARY ============")
    print(f"texts processed : {processed}")
    print(f"valid JSON      : {valid} ({_fmt(summary['pct_valid_json'], pct=True)})")
    print(f"failed          : {failed}")
    print(f"total findings  : {total_findings}")
    print(f"routing         : {route_counts}")
    print(f"sources         : {source_counts}")
    print(f"latency p50/p95 : {_fmt(summary['latency_p50'])}/{_fmt(summary['latency_p95'])} s")
    cpd = summary['cost'].get('cost_per_1000_docs_usd')
    print(f"cost / 1000     : {('$'+format(cpd,'.2f')) if cpd is not None else 'n/a (local)'}")
    print("========================================")
    print("Per-doc outputs: results/corpus/ | summary: results/corpus_summary.json")
    return summary


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config = RunConfig()
    if args.models:
        config.models = args.models
    if args.prompts:
        config.prompt_versions = args.prompts
    if args.sampling:
        config.sampling_configs = args.sampling

    if args.rescore:
        rescore()
        return 0

    if args.corpus_only:
        run_corpus(config)
        return 0

    run(config)
    if args.corpus:
        run_corpus(config)
    return 0

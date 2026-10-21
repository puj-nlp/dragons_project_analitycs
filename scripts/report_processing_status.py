from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "data" / "processed" / "pilot_variables"
LOGS_DIR = ROOT / "logs" / "variable_processing"
REPORTS_DIR = ROOT / "logs" / "reports"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                loaded = json.loads(line)
            except Exception:
                continue
            if isinstance(loaded, dict):
                yield loaded


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            total += chunk.count(b"\n")
    return total


def process_table() -> list[dict[str, Any]]:
    if sys.platform != "win32":
        try:
            completed = subprocess.run(
                ["ps", "-eo", "pid=,comm=,args="],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except Exception:
            return []
        rows: list[dict[str, Any]] = []
        for raw in completed.stdout.splitlines():
            line = raw.strip()
            if "run_pilot_processing.py" not in line or "report_processing_status.py" in line:
                continue
            parts = line.split(None, 2)
            if len(parts) < 3:
                continue
            rows.append({"ProcessId": int(parts[0]), "Name": parts[1], "CreationDate": None, "CommandLine": parts[2]})
        return rows

    ps = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match 'run_pilot_processing.py' -and ($_.Name -match '^(python|py)(\\.exe)?$') } | "
        "Select-Object ProcessId,Name,CreationDate,CommandLine | ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception:
        return []
    if not completed.stdout.strip():
        return []
    try:
        loaded = json.loads(completed.stdout)
    except Exception:
        return []
    if isinstance(loaded, dict):
        return [loaded]
    return loaded if isinstance(loaded, list) else []


def run_summary(run_dir: Path) -> dict[str, Any]:
    run_id = run_dir.name
    checkpoint = load_json(run_dir / "checkpoint.json")
    run_record = load_json(run_dir / "run_record.json")
    results_path = run_dir / "results_incremental.jsonl"
    log_dir = LOGS_DIR / run_id
    documents_path = log_dir / "documents.jsonl"
    variables_path = log_dir / "variables.jsonl"
    errors_path = log_dir / "errors.jsonl"

    unique_docs: set[str] = set()
    source_counts: Counter[str] = Counter()
    hf_status: Counter[str] = Counter()
    llm_status: Counter[str] = Counter()
    hf_models: Counter[str] = Counter()
    llm_providers: Counter[str] = Counter()
    last_document_id = None
    last_computed_at = None
    for record in iter_jsonl(results_path) or []:
        doc_id = record.get("document_id")
        if doc_id:
            unique_docs.add(str(doc_id))
            last_document_id = str(doc_id)
        source_counts.update([str(record.get("source") or "unknown")])
        hf_meta = record.get("hf_metadata") or {}
        llm_meta = record.get("llm_metadata") or {}
        hf_status.update([str(hf_meta.get("status") or "unknown")])
        llm_status.update([str(llm_meta.get("status") or "unknown")])
        if hf_meta.get("model"):
            hf_models.update([str(hf_meta["model"])])
        if llm_meta.get("provider"):
            llm_providers.update([str(llm_meta["provider"])])
        if record.get("computed_at"):
            last_computed_at = record.get("computed_at")

    target_rows = checkpoint.get("target_rows") or run_record.get("rows_total")
    processed = len(unique_docs) or int(checkpoint.get("rows_total_incremental") or 0)
    percent = round((processed / target_rows) * 100, 2) if target_rows else None

    return {
        "run_id": run_id,
        "status": checkpoint.get("status") or run_record.get("status") or "unknown",
        "target_rows": target_rows,
        "processed_unique_documents": processed,
        "progress_percent": percent,
        "result_lines": count_lines(results_path),
        "document_log_lines": count_lines(documents_path),
        "variable_log_lines": count_lines(variables_path),
        "error_lines": count_lines(errors_path),
        "last_document_id": checkpoint.get("last_document_id") or last_document_id,
        "last_computed_at": last_computed_at,
        "updated_at": checkpoint.get("updated_at") or run_record.get("finished_at"),
        "shard_index": checkpoint.get("shard_index"),
        "shard_count": checkpoint.get("shard_count"),
        "sources": dict(source_counts),
        "hf_status": dict(hf_status),
        "llm_status": dict(llm_status),
        "hf_models": dict(hf_models),
        "llm_providers": dict(llm_providers),
        "results_path": str(results_path.relative_to(ROOT)),
        "log_dir": str(log_dir.relative_to(ROOT)),
    }


def machine_summary() -> dict[str, Any]:
    cpu_count = os.cpu_count() or 1
    result: dict[str, Any] = {"logical_processors": cpu_count}
    try:
        gpu = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,utilization.gpu", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if gpu.stdout.strip():
            result["gpu"] = gpu.stdout.strip()
    except Exception:
        result["gpu"] = None
    return result


def build_report() -> dict[str, Any]:
    runs = [run_summary(path) for path in sorted(RUNS_DIR.iterdir()) if path.is_dir()] if RUNS_DIR.exists() else []
    active = process_table()
    active_run_ids: set[str] = set()
    for process in active:
        command_line = str(process.get("CommandLine") or process.get("commandline") or "")
        match = re.search(r"--run-id\s+([^\s]+)", command_line)
        if match:
            active_run_ids.add(match.group(1))
    for run in runs:
        run["active_process"] = run["run_id"] in active_run_ids
        if run["status"] == "running" and not run["active_process"]:
            run["status"] = "stale_running"
    canonical = canonical_summaries(runs)
    total_target = sum(int(run["target_rows"] or 0) for run in runs if run["run_id"].startswith("full"))
    total_processed = sum(int(run["processed_unique_documents"] or 0) for run in runs if run["run_id"].startswith("full"))
    return {
        "generated_at": utcnow(),
        "machine": machine_summary(),
        "active_prediction_processes": active,
        "active_prediction_process_count": len(active),
        "canonical_progress": canonical,
        "raw_full_runs_sum_note": "Raw sum across full run directories; targets may overlap across baseline, LLM, no-LLM and shard runs.",
        "raw_full_runs_total_target_rows": total_target,
        "raw_full_runs_total_processed_documents": total_processed,
        "raw_full_runs_progress_percent": round((total_processed / total_target) * 100, 2) if total_target else None,
        "runs": runs,
    }


def canonical_summaries(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    no_llm_run_ids = [
        "full_gliner25_multi_no_llm",
        *[run["run_id"] for run in runs if run["run_id"].startswith("full_parallel_gliner25_multi_no_llm_")],
    ]
    llm_run_ids = [
        *[run["run_id"] for run in runs if run["run_id"].startswith("full_by_source_all_variables_llm_")],
        *[run["run_id"] for run in runs if run["run_id"].startswith("full_parallel_all_variables_llm_")],
    ]
    by_id = {run["run_id"]: run for run in runs}
    no_llm_target = int((by_id.get("full_gliner25_multi_no_llm") or {}).get("target_rows") or 0)
    llm_target = sum(
        int((by_id.get(run_id) or {}).get("target_rows") or 0)
        for run_id in [
            "full_by_source_all_variables_llm_bluesky",
            "full_by_source_all_variables_llm_gdelt",
            "full_by_source_all_variables_llm_media_cloud",
        ]
    )

    def summarize(run_ids: list[str], target: int) -> dict[str, Any]:
        selected = [by_id[run_id] for run_id in run_ids if run_id in by_id]
        processed = sum(int(run.get("processed_unique_documents") or 0) for run in selected)
        active = sum(1 for run in selected if run.get("active_process"))
        return {
            "processed_documents": processed,
            "target_documents": target,
            "progress_percent": round((processed / target) * 100, 2) if target else None,
            "active_processes": active,
            "runs_included": [run["run_id"] for run in selected],
        }

    return {
        "no_llm_hf_only": summarize(no_llm_run_ids, no_llm_target),
        "llm_all_variables": summarize(llm_run_ids, llm_target),
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# DRAGONS processing report",
        "",
        f"Generated at UTC: {report['generated_at']}",
        f"Active prediction processes: {report['active_prediction_process_count']}",
        f"Logical processors: {report['machine'].get('logical_processors')}",
    ]
    if report["machine"].get("gpu"):
        lines.append(f"GPU: {report['machine']['gpu']}")
    lines.extend(
        [
            "",
            "Canonical progress:",
            f"- no_llm_hf_only: {report['canonical_progress']['no_llm_hf_only']['processed_documents']} / {report['canonical_progress']['no_llm_hf_only']['target_documents']} ({report['canonical_progress']['no_llm_hf_only']['progress_percent']}%), active processes: {report['canonical_progress']['no_llm_hf_only']['active_processes']}",
            f"- llm_all_variables: {report['canonical_progress']['llm_all_variables']['processed_documents']} / {report['canonical_progress']['llm_all_variables']['target_documents']} ({report['canonical_progress']['llm_all_variables']['progress_percent']}%), active processes: {report['canonical_progress']['llm_all_variables']['active_processes']}",
            "",
            f"Raw full-run directory sum, overlapping targets: {report['raw_full_runs_total_processed_documents']} / {report['raw_full_runs_total_target_rows']} ({report['raw_full_runs_progress_percent']}%)",
            "",
            "| run_id | status | processed | target | progress | errors | variables | updated |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for run in sorted(report["runs"], key=lambda item: str(item.get("updated_at") or ""), reverse=True):
        lines.append(
            "| {run_id} | {status} | {processed_unique_documents} | {target_rows} | {progress_percent}% | {error_lines} | {variable_log_lines} | {updated_at} |".format(
                **run
            )
        )
    lines.append("")
    lines.append("## Models detected")
    for run in report["runs"]:
        if run["hf_models"] or run["llm_providers"]:
            lines.append(f"- {run['run_id']}: HF={run['hf_models']} LLM={run['llm_providers']} LLM status={run['llm_status']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Report DRAGONS variable prediction processing status.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--write", action="store_true", help="Write report files under logs/reports.")
    args = parser.parse_args()

    report = build_report()
    if args.write:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (REPORTS_DIR / "latest_processing_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        (REPORTS_DIR / "latest_processing_report.md").write_text(to_markdown(report), encoding="utf-8")
        (REPORTS_DIR / f"processing_report_{stamp}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        (REPORTS_DIR / f"processing_report_{stamp}.md").write_text(to_markdown(report), encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(to_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

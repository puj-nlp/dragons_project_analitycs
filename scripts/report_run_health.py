#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Report run completion and failure counts from pilot_variables outputs.")
    p.add_argument("--pattern", default="full*", help="Glob pattern for run directories under data/processed/pilot_variables")
    p.add_argument("--only-no-llm", action="store_true", help="Filter to runs containing 'no_llm' in run_id")
    p.add_argument("--show-failures", action="store_true", help="Print per-run rows with failures")
    p.add_argument("--json", action="store_true", help="Emit JSON output")
    return p.parse_args()


def active_run_ids() -> set[str]:
    proc = subprocess.run(["ps", "-eo", "cmd="], capture_output=True, text=True, check=False)
    ids: set[str] = set()
    for line in proc.stdout.splitlines():
        if "run_pilot_processing.py" not in line or "--run-id" not in line:
            continue
        parts = line.split("--run-id", 1)[1].strip().split()
        if parts:
            ids.add(parts[0])
    return ids


def classify_exec_state(status: str, is_active: bool) -> str:
    if status == "completed":
        return "terminated_completed"
    if status == "running" and is_active:
        return "running_active"
    if status == "running" and not is_active:
        return "running_stale"
    return status or "unknown"


def load_rows(base: Path, pattern: str, only_no_llm: bool, active_ids: set[str]) -> list[dict]:
    rows: list[dict] = []
    for d in sorted(base.glob(pattern)):
        if not d.is_dir():
            continue
        run_id = d.name
        if only_no_llm and "no_llm" not in run_id:
            continue

        cp = d / "checkpoint.json"
        inc = d / "results_incremental.jsonl"
        if not cp.exists() or not inc.exists():
            continue

        try:
            c = json.loads(cp.read_text(encoding="utf-8"))
        except Exception:
            c = {}

        status = str(c.get("status") or "unknown")
        target = int(c.get("target_rows") or 0)
        done = int(c.get("rows_total_incremental") or 0)

        hf_failed = 0
        total_docs = 0
        malformed = 0
        with inc.open("r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                total_docs += 1
                try:
                    rec = json.loads(line)
                except Exception:
                    malformed += 1
                    continue
                hf_status = ((rec.get("hf_metadata") or {}).get("status")) or "unknown"
                if hf_status != "success":
                    hf_failed += 1

        exec_state = classify_exec_state(status, run_id in active_ids)
        rows.append(
            {
                "run_id": run_id,
                "exec_state": exec_state,
                "checkpoint_status": status,
                "progress": f"{done}/{target}",
                "rows_total_incremental": done,
                "target_rows": target,
                "hf_failed_docs": hf_failed,
                "total_docs": total_docs,
                "malformed_jsonl_lines": malformed,
                "updated_at": c.get("updated_at"),
                "last_document_id": c.get("last_document_id"),
            }
        )
    return rows


def main() -> int:
    args = parse_args()
    base = Path("data/processed/pilot_variables")
    active_ids = active_run_ids()
    rows = load_rows(base, args.pattern, args.only_no_llm, active_ids)

    summary = Counter()
    for r in rows:
        summary[r["exec_state"]] += 1
        summary["with_failures" if r["hf_failed_docs"] > 0 else "clean"] += 1

    if args.json:
        print(json.dumps({"summary": dict(summary), "rows": rows}, ensure_ascii=False, indent=2))
        return 0

    print("=== RESUMEN ===")
    for k in sorted(summary.keys()):
        print(f"{k}: {summary[k]}")

    print("\n=== RUNS CON FALLAS (hf_failed_docs > 0) ===")
    any_fail = False
    for r in rows:
        if r["hf_failed_docs"] > 0:
            any_fail = True
            print(f"{r['run_id']} | {r['progress']} | failed={r['hf_failed_docs']}/{r['total_docs']} | state={r['exec_state']}")
    if not any_fail:
        print("(none)")

    print("\n=== RUNS TERMINADOS LIMPIOS ===")
    any_done_clean = False
    for r in rows:
        if r["exec_state"] == "terminated_completed" and r["hf_failed_docs"] == 0:
            any_done_clean = True
            print(f"{r['run_id']} | {r['progress']}")
    if not any_done_clean:
        print("(none)")

    if args.show_failures:
        print("\n=== DETALLE RUNS CON FALLAS ===")
        for r in rows:
            if r["hf_failed_docs"] > 0:
                print(json.dumps(r, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

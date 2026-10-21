from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from run_pilot_processing import RunPaths, load_dotenv, setup_run, write_mongo, write_postgres

ROOT = Path(__file__).resolve().parents[1]


def resolve_repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync an existing pilot run to Mongo/Postgres.")
    parser.add_argument("run_id")
    parser.add_argument("--config", default="config/pipeline_config.yml")
    parser.add_argument("--mongo", action="store_true")
    parser.add_argument("--postgres", action="store_true")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    config = yaml.safe_load(resolve_repo_path(args.config).read_text(encoding="utf-8"))
    parquet_dir = resolve_repo_path(config["outputs"]["parquet_dir"]) / args.run_id
    log_dir = resolve_repo_path(config["outputs"]["log_dir"]) / args.run_id
    run_record_path = parquet_dir / "run_record.json"
    raw_path = parquet_dir / "analytics_variable_results_raw_json.parquet"
    if not run_record_path.exists():
        raise FileNotFoundError(run_record_path)
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)

    run_record = json.loads(run_record_path.read_text(encoding="utf-8"))
    raw_df = pd.read_parquet(raw_path)
    results = [json.loads(value) for value in raw_df["record"].tolist()]
    paths = RunPaths(
        run_id=args.run_id,
        log_dir=log_dir,
        parquet_dir=parquet_dir,
        document_log_path=log_dir / "documents.jsonl",
        variable_log_path=log_dir / "variables.jsonl",
        error_log_path=log_dir / "errors.jsonl",
        incremental_results_path=parquet_dir / "results_incremental.jsonl",
        checkpoint_path=parquet_dir / "checkpoint.json",
    )

    outputs = {}
    if args.mongo or not args.postgres:
        outputs["mongo"] = write_mongo(config, paths, results, run_record)
    if args.postgres or not args.mongo:
        outputs["postgres"] = write_postgres(config, paths, results, run_record)
    run_record.setdefault("outputs", {}).update(outputs)
    run_record_path.write_text(json.dumps(run_record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(outputs, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

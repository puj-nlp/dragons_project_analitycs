from __future__ import annotations

import argparse
import json
import math
import os
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pymongo
import psycopg
import yaml
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[1]


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                loaded = json.loads(line)
            except Exception:
                print(f"Skipping malformed JSONL line {line_number} in {path}")
                continue
            if isinstance(loaded, dict):
                yield loaded


def load_run_results(run_dir: Path) -> list[dict[str, Any]]:
    incremental = run_dir / "results_incremental.jsonl"
    raw_parquet = run_dir / "analytics_variable_results_raw_json.parquet"
    records: list[dict[str, Any]] = []
    if incremental.exists():
        records.extend(iter_jsonl(incremental))
    elif raw_parquet.exists():
        raw_df = pd.read_parquet(raw_parquet)
        if "record" not in raw_df.columns:
            print(f"Skipping parquet without record column: {raw_parquet}")
            return []
        records.extend(json.loads(value) for value in raw_df["record"].tolist())
    return records


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def json_sanitize(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {key: json_sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_sanitize(item) for item in value]
    return value


def run_record_for(run_dir: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    run_record = load_json(run_dir / "run_record.json") or load_json(run_dir / "checkpoint.json")
    run_record.setdefault("run_id", run_dir.name)
    run_record.setdefault("status", "partial_synced")
    run_record["synced_from_incremental"] = True
    run_record["synced_at"] = utcnow()
    run_record["rows_synced"] = len(records)
    if records:
        run_record["sources_synced"] = sorted({str(record.get("source") or "unknown") for record in records})
        run_record["last_computed_at_synced"] = records[-1].get("computed_at")
    return run_record


def ensure_parquet_outputs(run_dir: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"status": "skipped", "reason": "no_records"}
    raw_path = run_dir / "analytics_variable_results_raw_json.parquet"
    flat_path = run_dir / "analytics_variable_results_flat.parquet"
    csv_path = run_dir / "analytics_variable_results_flat.csv"

    raw_df = pd.DataFrame([{"record": json.dumps(record, ensure_ascii=False, default=str)} for record in records])
    raw_df.to_parquet(raw_path, index=False)

    flat_rows = []
    for record in records:
        flat_rows.append(
            {
                "result_id": record.get("result_id"),
                "run_id": record.get("run_id"),
                "document_id": record.get("document_id"),
                "source": record.get("source"),
                "country_key": record.get("country_key"),
                "language": record.get("language"),
                "created_at": record.get("created_at"),
                "title": record.get("title"),
                "computed_at": record.get("computed_at"),
                "hf_status": (record.get("hf_metadata") or {}).get("status"),
                "llm_status": (record.get("llm_metadata") or {}).get("status"),
                "is_relevant_biodiversity": (record.get("llm_variables") or {}).get("is_relevant_biodiversity"),
                "relevance_score": (record.get("llm_variables") or {}).get("relevance_score"),
                "sentiment_label": (record.get("llm_variables") or {}).get("sentiment_label"),
                "narrative_label": (record.get("llm_variables") or {}).get("narrative_label"),
            }
        )
    flat_df = pd.DataFrame(flat_rows)
    flat_df.to_parquet(flat_path, index=False)
    flat_df.to_csv(csv_path, index=False)
    return {
        "status": "success",
        "rows": len(records),
        "raw_json_parquet": str(raw_path.relative_to(ROOT)),
        "flat_parquet": str(flat_path.relative_to(ROOT)),
        "flat_csv": str(csv_path.relative_to(ROOT)),
    }


def write_mongo(config: dict[str, Any], mongo_uri: str, run_id: str, records: list[dict[str, Any]], run_record: dict[str, Any]) -> dict[str, Any]:
    client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    db = client[config["outputs"]["mongo_database"]]
    result_collection = db[config["outputs"]["mongo_results_collection"]]
    runs_collection = db[config["outputs"]["mongo_runs_collection"]]
    result_collection.delete_many({"run_id": run_id})
    if records:
        result_collection.insert_many(records, ordered=False)
    runs_collection.update_one({"run_id": run_id}, {"$set": run_record}, upsert=True)
    return {"status": "success", "rows": len(records)}


def ensure_postgres_tables(cur: Any, schema: str, results_table: str, runs_table: str) -> None:
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.{results_table} (
            result_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            document_id TEXT,
            source TEXT,
            country_key TEXT,
            language TEXT,
            created_at TEXT,
            title TEXT,
            etl_metrics JSONB,
            deterministic_variables JSONB,
            hf_variables JSONB,
            hf_metadata JSONB,
            llm_variables JSONB,
            llm_metadata JSONB,
            computed_at TIMESTAMPTZ
        )
        """
    )
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.{runs_table} (
            run_id TEXT PRIMARY KEY,
            run_record JSONB,
            updated_at TIMESTAMPTZ
        )
        """
    )


def write_postgres(config: dict[str, Any], postgres_uri: str, run_id: str, records: list[dict[str, Any]], run_record: dict[str, Any]) -> dict[str, Any]:
    schema = config["outputs"]["postgres_schema"]
    results_table = config["outputs"]["postgres_results_table"]
    runs_table = config["outputs"]["postgres_runs_table"]
    with psycopg.connect(postgres_uri, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            ensure_postgres_tables(cur, schema, results_table, runs_table)
            cur.execute(f"DELETE FROM {schema}.{results_table} WHERE run_id = %s", (run_id,))
            sql = f"""
                INSERT INTO {schema}.{results_table}
                (result_id, run_id, document_id, source, country_key, language, created_at, title,
                 etl_metrics, deterministic_variables, hf_variables, hf_metadata, llm_variables, llm_metadata, computed_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (result_id) DO UPDATE SET
                  etl_metrics = EXCLUDED.etl_metrics,
                  deterministic_variables = EXCLUDED.deterministic_variables,
                  hf_variables = EXCLUDED.hf_variables,
                  hf_metadata = EXCLUDED.hf_metadata,
                  llm_variables = EXCLUDED.llm_variables,
                  llm_metadata = EXCLUDED.llm_metadata,
                  computed_at = EXCLUDED.computed_at
                """
            batch = []
            for record in records:
                batch.append(
                    (
                            record.get("result_id"),
                            record.get("run_id"),
                            record.get("document_id"),
                            record.get("source"),
                            record.get("country_key"),
                            record.get("language"),
                            str(record.get("created_at")),
                            record.get("title"),
                            Jsonb(json_sanitize(record.get("etl_metrics", {}))),
                            Jsonb(json_sanitize(record.get("deterministic_variables", {}))),
                            Jsonb(json_sanitize(record.get("hf_variables", {}))),
                            Jsonb(json_sanitize(record.get("hf_metadata", {}))),
                            Jsonb(json_sanitize(record.get("llm_variables", {}))),
                            Jsonb(json_sanitize(record.get("llm_metadata", {}))),
                            record.get("computed_at"),
                    )
                )
                if len(batch) >= 1000:
                    cur.executemany(sql, batch)
                    batch.clear()
            if batch:
                cur.executemany(sql, batch)
            cur.execute(
                f"""
                INSERT INTO {schema}.{runs_table} (run_id, run_record, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (run_id) DO UPDATE SET run_record = EXCLUDED.run_record, updated_at = EXCLUDED.updated_at
                """,
                (run_id, Jsonb(json_sanitize(run_record)), utcnow()),
            )
        conn.commit()
    return {"status": "success", "rows": len(records)}


def selected_run_dirs(base_dir: Path, patterns: list[str]) -> list[Path]:
    seen: set[Path] = set()
    selected: list[Path] = []
    for pattern in patterns:
        for path in sorted(base_dir.glob(pattern)):
            if not path.is_dir() or path.name == "_prepared_shards" or path in seen:
                continue
            seen.add(path)
            selected.append(path)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync partial/incremental DRAGONS outputs to parquet, Mongo and Postgres.")
    parser.add_argument("--config", default="config/pipeline_config.yml")
    parser.add_argument("--run-glob", action="append", default=None, help="Run directory glob; can be repeated.")
    parser.add_argument("--mongo-uri", default=os.environ.get("MONGODB_URI"))
    parser.add_argument("--postgres-uri", default=os.environ.get("POSTGRES_URI"))
    parser.add_argument("--no-parquet", action="store_true")
    parser.add_argument("--no-mongo", action="store_true")
    parser.add_argument("--no-postgres", action="store_true")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    config = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8"))
    base_dir = ROOT / config["outputs"]["parquet_dir"]
    mongo_uri = args.mongo_uri or "mongodb://root:dragons_dev_password@localhost:50030/?authSource=admin"
    postgres_uri = args.postgres_uri or "postgresql://dragons:dragons_dev_password@localhost:50020/dragons"

    summary: list[dict[str, Any]] = []
    run_globs = args.run_glob or ["full*"]
    for run_dir in selected_run_dirs(base_dir, run_globs):
        records = [json_sanitize(record) for record in load_run_results(run_dir)]
        if not records:
            continue
        run_id = run_dir.name
        run_record = run_record_for(run_dir, records)
        item: dict[str, Any] = {"run_id": run_id, "rows": len(records)}
        if not args.no_parquet:
            item["parquet"] = ensure_parquet_outputs(run_dir, records)
        if not args.no_mongo:
            item["mongo"] = write_mongo(config, mongo_uri, run_id, records, run_record)
        if not args.no_postgres:
            item["postgres"] = write_postgres(config, postgres_uri, run_id, records, run_record)
        summary.append(item)
        print(json.dumps(item, ensure_ascii=False, default=str))

    total_rows = sum(int(item["rows"]) for item in summary)
    print(json.dumps({"status": "complete", "runs": len(summary), "rows": total_rows}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

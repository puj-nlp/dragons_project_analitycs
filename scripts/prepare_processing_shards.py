from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VENDOR_DIR = Path(__file__).resolve().parents[1] / ".vendor" / "python"
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))
VENDOR_DIR_ALT = Path(__file__).resolve().parents[1] / "vendor_python"
if VENDOR_DIR_ALT.exists():
    sys.path.insert(0, str(VENDOR_DIR_ALT))

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_BASE = ROOT / "data" / "processed" / "pilot_variables" / "_prepared_shards"
COLUMNS = [
    "document_id", "mongo_id", "collection_name", "source", "strategy",
    "source_type", "country_key", "language", "created_at", "url", "title",
    "text", "metadata", "raw_metadata", "char_count", "word_count",
    "sentence_count", "paragraph_count", "lexical_density_proxy", "top_terms",
]


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: Any) -> str:
    return "" if value is None else " ".join(str(value).split())


def shard_value(value: Any, shard_count: int) -> int:
    digest = hashlib.sha256(str(value).encode("utf-8", errors="ignore")).hexdigest()
    return int(digest[:16], 16) % shard_count


def read_jsonl(path: Path):
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


def load_existing_document_ids(patterns: list[str]) -> set[str]:
    ids: set[str] = set()
    runs_dir = ROOT / "data" / "processed" / "pilot_variables"
    for pattern in patterns:
        for run_dir in runs_dir.glob(pattern):
            path = run_dir / "results_incremental.jsonl" if run_dir.is_dir() else run_dir
            for record in read_jsonl(path) or []:
                document_id = record.get("document_id")
                if document_id:
                    ids.add(str(document_id))
    return ids


def normalize_sources(values: list[str]) -> list[str]:
    sources: list[str] = []
    for value in values:
        for item in value.split(","):
            item = item.strip()
            if item and item not in sources:
                sources.append(item)
    return sources


def worker_plan(sources: list[str], max_workers: int) -> list[dict[str, Any]]:
    worker_count = max(1, max_workers)
    base = worker_count // len(sources)
    extra = worker_count % len(sources)
    plan: list[dict[str, Any]] = []
    for source_index, source in enumerate(sources):
        shard_count = max(1, base)
        if source_index < extra:
            shard_count += 1
        for shard_index in range(shard_count):
            plan.append(
                {
                    "source": source,
                    "shard_index": shard_index,
                    "shard_count": shard_count,
                }
            )
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare small parquet shards for DRAGONS processing workers.")
    parser.add_argument("--config", default="config/pipeline_config.yml")
    parser.add_argument("--run-prefix", required=True)
    parser.add_argument("--sources", nargs="+", required=True)
    parser.add_argument("--max-workers", type=int, required=True)
    parser.add_argument("--skip-existing-run-glob", action="append", default=[])
    args = parser.parse_args()

    config = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8"))
    sources = normalize_sources(args.sources)
    configured_sources = set(config["run"].get("sources") or [])
    unknown = sorted(set(sources) - configured_sources)
    if unknown:
        raise ValueError(f"Unknown source(s) for this config: {unknown}")

    output_dir = OUTPUT_BASE / args.run_prefix
    output_dir.mkdir(parents=True, exist_ok=True)
    existing_ids = load_existing_document_ids(args.skip_existing_run_glob)

    source_path = Path(config["analytics_parquet"])
    df = pd.read_parquet(source_path, columns=COLUMNS)
    df["text_clean"] = df["text"].map(clean_text)
    min_chars = int(config["run"].get("min_text_chars", 40))
    df = df[df["source"].isin(sources)]
    df = df[df["text_clean"].str.len() >= min_chars]
    if existing_ids:
        df = df[~df["document_id"].astype(str).isin(existing_ids)]
    df = df.sort_values(["source", "created_at", "document_id"], na_position="last").reset_index(drop=True)

    manifest = {
        "run_prefix": args.run_prefix,
        "generated_at": utcnow(),
        "analytics_parquet": str(source_path),
        "sources": sources,
        "max_workers": args.max_workers,
        "skip_existing_run_glob": args.skip_existing_run_glob,
        "skipped_existing_documents": len(existing_ids),
        "remaining_documents": int(len(df)),
        "shards": [],
    }

    for item in worker_plan(sources, args.max_workers):
        source = item["source"]
        shard_index = item["shard_index"]
        shard_count = item["shard_count"]
        run_id = f"{args.run_prefix}_{source}_s{shard_index}of{shard_count}"
        shard_df = df[df["source"].eq(source)]
        shard_df = shard_df[
            shard_df["document_id"].map(lambda value: shard_value(value, shard_count) == shard_index)
        ].reset_index(drop=True)
        shard_path = output_dir / f"{run_id}.parquet"
        shard_df[COLUMNS].to_parquet(shard_path, index=False)
        manifest["shards"].append(
            {
                "run_id": run_id,
                "source": source,
                "shard_index": shard_index,
                "shard_count": shard_count,
                "rows": int(len(shard_df)),
                "path": str(shard_path.relative_to(ROOT)),
            }
        )

    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

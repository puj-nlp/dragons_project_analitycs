from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from sync_incremental_outputs import ROOT, iter_jsonl, json_sanitize, selected_run_dirs


PATTERNS = [
    "full_gliner25_multi_no_llm",
    "full_parallel_gliner25_multi_no_llm_*",
    "full_by_source_all_variables_llm_*",
    "full_parallel_all_variables_llm_*",
]


def encode(value: Any) -> str:
    return json.dumps(json_sanitize(value), ensure_ascii=False, sort_keys=True, allow_nan=False)


def text_hash(value: Any) -> str:
    clean = re.sub(r"\s+", " ", "" if value is None else str(value)).strip()
    return hashlib.sha256(clean.encode("utf-8", errors="ignore")).hexdigest()[:16]


def input_hash(record: dict[str, Any]) -> str | None:
    return (record.get("deterministic_variables") or {}).get("text_hash")


def priority(record: dict[str, Any], metadata: str) -> tuple[int, str, str]:
    status = (record.get(metadata) or {}).get("status")
    return (int(status == "success"), str(record.get("computed_at") or ""), str(record.get("result_id") or ""))


def has_empty_struct(data_type: pa.DataType) -> bool:
    if pa.types.is_struct(data_type):
        return not len(data_type) or any(has_empty_struct(field.type) for field in data_type)
    if pa.types.is_list(data_type) or pa.types.is_large_list(data_type):
        return has_empty_struct(data_type.value_type)
    return False


def equivalent(actual: Any, expected: Any) -> bool:
    if isinstance(actual, dict) and isinstance(expected, dict):
        return all(equivalent(actual.get(key), expected.get(key)) for key in actual.keys() | expected.keys())
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(equivalent(left, right) for left, right in zip(actual, expected))
    return actual == expected


def export_table(output: Path, name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    columns = sorted({key for row in rows for key in row})
    columns.remove("document_id")
    columns.insert(0, "document_id")
    arrays = []
    descriptions = {}
    for column in columns:
        values = [row.get(column) for row in rows]
        encoding = "native"
        try:
            array = pa.array(values)
            if has_empty_struct(array.type):
                raise ValueError("Parquet cannot store empty structs")
            if not all(equivalent(actual, expected) for actual, expected in zip(array.to_pylist(), values)):
                raise ValueError("Native conversion changed values")
        except (pa.ArrowException, ValueError, TypeError, OverflowError):
            array = pa.array([None if value is None else encode(value) for value in values], type=pa.string())
            encoding = "json"
        arrays.append(array)
        descriptions[column] = {"type": str(array.type), "encoding": encoding}
    table = pa.Table.from_arrays(arrays, names=columns)
    table = table.replace_schema_metadata({
        b"document_key": b"document_id",
        b"column_encodings": encode(descriptions).encode("utf-8"),
    })
    temporary = output / (name + ".tmp")
    destination = output / name
    pq.write_table(table, temporary, compression="zstd", row_group_size=10000)
    restored = pq.read_table(temporary)
    assert restored.num_rows == len(rows)
    for column in columns:
        actual_values = restored.column(column).to_pylist()
        if descriptions[column]["encoding"] == "json":
            actual_values = [None if value is None else json.loads(value) for value in actual_values]
        if not all(equivalent(actual, row.get(column)) for actual, row in zip(actual_values, rows)):
            raise ValueError(f"Round-trip mismatch: {name}/{column}")
    temporary.replace(destination)
    digest = hashlib.sha256()
    with destination.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            digest.update(chunk)
    return {"file": name, "rows": len(rows), "column_count": len(columns), "columns": descriptions,
            "bytes": destination.stat().st_size, "sha256": digest.hexdigest(), "round_trip_verified": True}


def variable_rows(ids: list[str], selected: dict[str, dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    group = "llm_variables" if kind == "llm" else "hf_variables"
    metadata = "llm_metadata" if kind == "llm" else "hf_metadata"
    result = []
    for document_id in ids:
        record = selected[document_id]
        values = record.get(group) or {}
        meta = record.get(metadata) or {}
        row = {"document_id": document_id, "source": record.get("source"), "run_id": record.get("run_id"),
               "result_id": record.get("result_id"), "computed_at": record.get("computed_at"),
               "status": meta.get("status"), "provider": meta.get("provider"), "model": meta.get("model"),
               "input_text_hash": input_hash(record), "metadata_json": encode(meta),
               "variables_json": encode(values)}
        row.update({kind + "__" + key: value for key, value in values.items()})
        result.append(row)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Export independent, document-level consolidated Parquets.")
    parser.add_argument("--config", default="config/pipeline_config.yml")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-documents", type=int, default=169248)
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output must be a new or empty directory: {output}")
    config = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8"))
    base = ROOT / config["outputs"]["parquet_dir"]
    selected = {"llm": {}, "gliner": {}}
    selected_hf_only = {}
    inventory = []
    started = datetime.now(timezone.utc).isoformat()
    for directory in selected_run_dirs(base, PATTERNS):
        path = directory / "results_incremental.jsonl"
        if not path.exists():
            continue
        count = 0
        for raw in iter_jsonl(path):
            record = json_sanitize(raw)
            document_id = record.get("document_id")
            if not document_id:
                raise ValueError(f"Missing document_id in {path}")
            count += 1
            for kind, metadata in (("llm", "llm_metadata"), ("gliner", "hf_metadata")):
                if (record.get(metadata) or {}).get("status") not in {"success", "failed"}:
                    continue
                current = selected[kind].get(document_id)
                if current is None or priority(record, metadata) > priority(current, metadata):
                    selected[kind][document_id] = record
            if directory.name == "full_gliner25_multi_no_llm" or directory.name.startswith("full_parallel_gliner25_multi_no_llm_"):
                current = selected_hf_only.get(document_id)
                if current is None or priority(record, "hf_metadata") > priority(current, "hf_metadata"):
                    selected_hf_only[document_id] = record
        if count:
            inventory.append({"run_id": directory.name, "records": count, "bytes": path.stat().st_size})
        print("READ", directory.name, count, flush=True)
    ids = sorted(selected["llm"])
    if len(ids) != args.expected_documents or set(ids) != set(selected["gliner"]):
        raise ValueError("The LLM and GLiNER document universes differ from the expected universe")
    universe = set(ids)
    desired = {document_id: {value for value in (input_hash(selected["llm"][document_id]), input_hash(selected["gliner"][document_id])) if value}
               for document_id in ids}
    primary = {document_id: input_hash(selected["llm"][document_id]) or input_hash(selected["gliner"][document_id]) for document_id in ids}
    documents = {}
    origins = {}
    versions = {}
    document_columns = set()
    source = Path(config["analytics_parquet"])
    source_rows = pq.ParquetFile(source).metadata.num_rows

    def ingest(path: Path) -> None:
        parquet = pq.ParquetFile(path)
        document_columns.update(parquet.schema_arrow.names)
        for batch in parquet.iter_batches(batch_size=2000):
            for raw in batch.to_pylist():
                row = json_sanitize(raw)
                document_id = row.get("document_id")
                if document_id not in universe:
                    continue
                fingerprint = text_hash(row.get("text"))
                if fingerprint in desired[document_id]:
                    versions[(document_id, fingerprint)] = row.get("text")
                existing = documents.get(document_id)
                if existing is None or (fingerprint == primary[document_id] and text_hash(existing.get("text")) != primary[document_id]):
                    documents[document_id] = row
                    origins[document_id] = str(path)

    ingest(source)
    missing_versions = {(document_id, fingerprint) for document_id in ids for fingerprint in desired[document_id]
                        if (document_id, fingerprint) not in versions}
    for path in sorted((base / "_prepared_shards").glob("*/*.parquet")):
        if not missing_versions:
            break
        candidates = set(pq.read_table(path, columns=["document_id"]).column("document_id").to_pylist())
        if not candidates.intersection(document_id for document_id, fingerprint in missing_versions):
            continue
        ingest(path)
        missing_versions = {(document_id, fingerprint) for document_id, fingerprint in missing_versions
                            if (document_id, fingerprint) not in versions}
    for document_id in ids:
        record = selected["llm"][document_id]
        embedded = (record.get("llm_variables") or {}).get("text")
        if embedded is not None and text_hash(embedded) in desired[document_id]:
            fingerprint = text_hash(embedded)
            versions.setdefault((document_id, fingerprint), embedded)
            if document_id not in documents or text_hash(documents[document_id].get("text")) != primary[document_id]:
                if fingerprint == primary[document_id]:
                    documents[document_id] = {key: value for key, value in record.items() if key in document_columns}
                    documents[document_id]["text"] = embedded
                    origins[document_id] = "llm_variables.text:" + str(record.get("result_id"))
    missing_versions = {(document_id, fingerprint) for document_id in ids for fingerprint in desired[document_id]
                        if (document_id, fingerprint) not in versions}
    if missing_versions or set(documents) != universe:
        raise ValueError(f"Cannot recover complete matching input texts: {len(missing_versions)} versions; {len(universe-set(documents))} documents")
    document_rows = []
    for document_id in ids:
        llm = selected["llm"][document_id]
        gliner = selected["gliner"][document_id]
        reference = max((llm, gliner), key=lambda record: (
            int((record.get("llm_metadata") or {}).get("status") == "success" or (record.get("hf_metadata") or {}).get("status") == "success"),
            str(record.get("computed_at") or ""),
        ))
        row = {key: documents[document_id].get(key) for key in document_columns}
        if primary[document_id] and text_hash(row.get("text")) != primary[document_id]:
            raise ValueError(f"Primary text hash mismatch: {document_id}")
        hf_hash = input_hash(gliner)
        row.update({"document_id": document_id, "documents_origin_path": origins[document_id],
                    "input_text_hash": text_hash(row.get("text")), "llm_input_text_hash": input_hash(llm),
                    "gliner_input_text_hash": hf_hash, "llm_status": (llm.get("llm_metadata") or {}).get("status"),
                    "gliner_status": (gliner.get("hf_metadata") or {}).get("status"),
                    "llm_run_id": llm.get("run_id"), "gliner_run_id": gliner.get("run_id"),
                    "gliner_input_text": versions[(document_id, hf_hash)] if hf_hash and hf_hash != primary[document_id] else None,
                    "etl_metrics_json": encode(reference.get("etl_metrics") or {}),
                    "deterministic_variables_json": encode(reference.get("deterministic_variables") or {})})
        for group, prefix in (("etl_metrics", "etl__"), ("deterministic_variables", "deterministic__")):
            row.update({prefix + key: value for key, value in (reference.get(group) or {}).items()})
        document_rows.append(row)
    output.mkdir(parents=True, exist_ok=True)
    files = {}
    for kind, name in (("llm", "variables_llm.parquet"), ("gliner", "variables_gliner.parquet")):
        rows = variable_rows(ids, selected[kind], kind)
        files[kind] = export_table(output, name, rows)
        print("EXPORTED", name, files[kind]["bytes"], flush=True)
    files["documents"] = export_table(output, "documentos_metadatos.parquet", document_rows)
    for item in files.values():
        actual = pq.read_table(output / item["file"], columns=["document_id"]).column("document_id").to_pylist()
        if actual != ids or len(set(actual)) != len(ids):
            raise ValueError("Duplicate, missing or misaligned document IDs in export")
    manifest = {"started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                "document_count": len(ids), "join_key": "document_id", "ids_unique_and_aligned": True,
                "source_analytics": str(source), "source_analytics_rows": source_rows,
                "selection": "success before failed; newest computed_at; result_id breaks ties. LLM and GLiNER selected independently across all productive runs; skipped/unknown excluded.",
                "source_runs": inventory, "files": files,
                "status_counts": {kind: dict(Counter((record.get("llm_metadata" if kind == "llm" else "hf_metadata") or {}).get("status") for record in selected[kind].values())) for kind in selected},
                "hf_only_baseline_status": dict(Counter((record.get("hf_metadata") or {}).get("status") for record in selected_hf_only.values())),
                "gliner_success_recovered_from_llm_runs": sum((selected_hf_only.get(document_id, {}).get("hf_metadata") or {}).get("status") != "success" and (selected["gliner"][document_id].get("hf_metadata") or {}).get("status") == "success" for document_id in ids),
                "different_llm_gliner_text_versions": sum(input_hash(selected["llm"][document_id]) != input_hash(selected["gliner"][document_id]) for document_id in ids),
                "matching_input_texts_verified": True,
                "document_origin_counts": dict(Counter(origins.values()))}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("COMPLETE", encode({"output": str(output), "documents": len(ids), "status_counts": manifest["status_counts"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

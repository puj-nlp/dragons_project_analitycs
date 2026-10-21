from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "data/processed/consolidated_predictions/2026-10-19"
TYPES = {"bool": pa.bool_(), "int": pa.int64(), "float": pa.float64(), "string": pa.string()}
BATCH_SIZE = 4096


def escape_key(value: str) -> str:
    return quote(value, safe="").replace(".", "%2E").replace("[", "%5B").replace("]", "%5D")


def scalar_kind(value: object) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    raise TypeError(f"Unsupported scalar type: {type(value)}")


def flatten(value: object, path: str, result: dict) -> None:
    if isinstance(value, str) and value.lstrip().startswith(("{", "[")):
        try:
            decoded = json.loads(value)
        except ValueError:
            decoded = None
        if isinstance(decoded, (dict, list)):
            value = decoded
    if isinstance(value, dict):
        result[path + "#object"] = True
        for key, child in value.items():
            flatten(child, path + "." + escape_key(key), result)
    elif isinstance(value, list):
        result[path + "#length"] = len(value)
        for index, child in enumerate(value, start=1):
            flatten(child, f"{path}[{index:04d}]", result)
    else:
        if value is not None:
            scalar_kind(value)
        result[path] = value


def flatten_row(row: dict, kind: str) -> dict:
    result = {}
    if kind == "documents":
        for name, value in row.items():
            flatten(value, name, result)
        return result
    for name, value in row.items():
        if name not in {"variables_json", "metadata_json"}:
            flatten(value, name, result)
    variables = json.loads(row["variables_json"])
    metadata = json.loads(row["metadata_json"])
    if not isinstance(variables, dict) or not isinstance(metadata, dict):
        raise ValueError("Expected objects in variables_json and metadata_json")
    for name, value in variables.items():
        flatten(value, kind + "__" + escape_key(name), result)
    flatten(metadata, "prediction_metadata", result)
    return result


def source_batches(source: Path, kind: str):
    with pq.ParquetFile(source) as parquet:
        columns = [name for name in parquet.schema_arrow.names if kind == "documents" or not name.startswith(("llm__", "gliner__"))]
        for batch in parquet.iter_batches(batch_size=BATCH_SIZE, columns=columns):
            yield batch.to_pylist()


def hash_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def make_table(records: list[dict], schema: pa.Schema, routing: dict) -> pa.Table:
    values_by_column = {}
    for index, record in enumerate(records):
        for path, value in record.items():
            if value is None:
                continue
            column = routing[path][scalar_kind(value)]
            if column not in values_by_column:
                values_by_column[column] = [None] * len(records)
            values_by_column[column][index] = value
    arrays = [
        pa.array(values_by_column[field.name], type=field.type)
        if field.name in values_by_column else pa.nulls(len(records), type=field.type)
        for field in schema
    ]
    return pa.Table.from_arrays(arrays, schema=schema)


def export(source: Path, output: Path, kind: str, resume: bool = False) -> dict:
    manifest_path = output.with_suffix(".manifest.json")
    partial = output.with_suffix(".parquet.partial")
    for path in (output, manifest_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
    if partial.exists() and not resume:
        raise FileExistsError(f"Use --resume to validate an existing partial: {partial}")
    print(f"SCAN {kind}", flush=True)
    observed = defaultdict(set)
    ids = set()
    row_count = 0
    list_maxima = Counter()
    for rows in source_batches(source, kind):
        for row in rows:
            document_id = row["document_id"]
            if not document_id or document_id in ids:
                raise ValueError(f"Missing or duplicate document_id: {document_id}")
            ids.add(document_id)
            for path, value in flatten_row(row, kind).items():
                observed[path]
                if value is not None:
                    observed[path].add(scalar_kind(value))
                if path.endswith("#length"):
                    list_maxima[path[:-7]] = max(list_maxima[path[:-7]], value)
            row_count += 1
    fields = []
    routing = {}
    dictionary = []
    paths = ["document_id"] + sorted(path for path in observed if path != "document_id")
    for path in paths:
        kinds = sorted(observed[path])
        routing[path] = {}
        for scalar_type in kinds or ["string"]:
            name = path if len(kinds) < 2 else path + "#as_" + scalar_type
            fields.append(pa.field(name, TYPES[scalar_type]))
            routing[path][scalar_type] = name
            dictionary.append({"column": name, "source_path": path, "type": scalar_type, "all_null": not kinds})
    if len({field.name for field in fields}) != len(fields):
        raise ValueError("Flattened column name collision")
    schema = pa.schema(fields, metadata={b"document_key": b"document_id", b"layout": b"flat scalar columns; list positions are one-based"})
    output.parent.mkdir(parents=True, exist_ok=True)
    if not partial.exists():
        print(f"WRITE {kind} rows={row_count} columns={len(fields)}", flush=True)
        with pq.ParquetWriter(partial, schema, compression="zstd") as writer:
            for rows in source_batches(source, kind):
                writer.write_table(make_table([flatten_row(row, kind) for row in rows], schema, routing))
    print(f"VERIFY {kind}", flush=True)
    exported = pq.ParquetFile(partial)
    if exported.metadata.num_rows != row_count or any(pa.types.is_nested(field.type) for field in exported.schema_arrow):
        raise ValueError("Output must preserve rows and contain only scalar types")
    verified = 0
    for rows, actual in zip(source_batches(source, kind), exported.iter_batches(batch_size=BATCH_SIZE), strict=True):
        expected = make_table([flatten_row(row, kind) for row in rows], schema, routing)
        if not expected.equals(pa.Table.from_batches([actual]), check_metadata=False):
            raise ValueError("Full readback comparison failed")
        verified += actual.num_rows
    if verified != row_count:
        raise ValueError("Readback row count mismatch")
    exported.close()
    partial.rename(output)
    manifest = {
        "source": str(source.relative_to(ROOT)),
        "output": str(output.relative_to(ROOT)),
        "source_sha256": hash_file(source),
        "output_sha256": hash_file(output),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": row_count,
        "columns": len(schema),
        "bytes": output.stat().st_size,
        "max_list_lengths": dict(list_maxima),
        "column_dictionary": dictionary,
        "validation": {"full_readback_compared": True, "scalar_columns_only": True, "unique_ids_and_original_order": True, "no_list_truncation": True},
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"COMPLETE {kind} rows={row_count} columns={len(schema)} bytes={output.stat().st_size}", flush=True)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Expand predictions or document metadata into scalar-only document tables")
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--kind", choices=["llm", "gliner", "both", "documents"], default="both")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    base = args.base.resolve()
    output_dir = (args.output_dir or base / "tabular").resolve()
    manifests = []
    for kind in (["gliner", "llm"] if args.kind == "both" else [args.kind]):
        name = "documentos_metadatos" if kind == "documents" else f"variables_{kind}"
        manifests.append(export(base / f"{name}.parquet", output_dir / f"{name}_tabular.parquet", kind, args.resume))
    document_ids = None
    for manifest in manifests:
        current = pq.read_table(ROOT / manifest["output"], columns=["document_id"])["document_id"]
        if document_ids is not None and not current.equals(document_ids):
            raise ValueError("Document IDs differ between the two outputs")
        document_ids = current


if __name__ == "__main__":
    main()

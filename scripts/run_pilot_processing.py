from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VENDOR_DIR = Path(__file__).resolve().parents[1] / ".vendor" / "python"
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))
VENDOR_DIR_ALT = Path(__file__).resolve().parents[1] / "vendor_python"
if VENDOR_DIR_ALT.exists():
    sys.path.insert(0, str(VENDOR_DIR_ALT))

ROOT = Path(__file__).resolve().parents[1]

import networkx as nx
import pandas as pd
import requests
import yaml

try:
    import pymongo
    if not hasattr(pymongo, "MongoClient"):
        pymongo = None
except Exception:  # pragma: no cover - optional dependency in some environments
    pymongo = None

try:
    import psycopg
    from psycopg.types.json import Jsonb
    if not hasattr(psycopg, "connect"):
        psycopg = None
        Jsonb = None
except Exception:  # pragma: no cover - optional dependency in some environments
    psycopg = None
    Jsonb = None


ALLOWED_SENTIMENT = {"positive", "neutral", "negative", "mixed", "unclear"}
ALLOWED_EMOTIONS = {"concern", "fear", "anger", "sadness", "hope", "trust", "pride", "none", "unclear"}
ALLOWED_FRAME_FAMILIES = [
    "ecological_crisis",
    "conservation_solution",
    "policy_governance",
    "justice_rights",
    "economic_development",
    "science_evidence",
    "conflict_tradeoff",
    "animal_welfare",
    "indigenous_local_knowledge",
    "risk_security",
    "public_participation",
    "unclear",
]
ALLOWED_FRAME_FUNCTIONS = [
    "diagnostic",
    "prognostic",
    "motivational",
    "moral_evaluation",
    "mixed",
    "unclear",
]
ALLOWED_FRAME_SCALES = ["local", "national", "regional", "global", "mixed", "unclear"]
DEFAULT_GLINER_LABELS = [
    "person",
    "organization",
    "government institution",
    "media outlet",
    "civil society organization",
    "indigenous or local community",
    "scientific institution",
    "company",
    "location",
    "country",
    "biodiversity concept",
    "species",
    "ecosystem",
    "protected area",
    "policy or law",
    "event",
    "date",
    "funding or money",
    "risk or threat",
    "proposed action",
]

BIODIVERSITY_TERMS = {
    "biodiversity", "biodiversidad", "biodiverzitas", "biodiverzitás",
    "species", "especies", "faj", "nature", "naturaleza", "termeszet", "természet",
    "ecosystem", "ecosistema", "ökoszisztéma", "conservation", "conservacion",
    "conservación", "restoration", "restauracion", "restauración", "habitat",
    "forest", "bosque", "erdő", "wildlife", "fauna", "flora", "extinction",
    "extincion", "extinción", "climate", "clima", "water", "agua", "víz",
}

PROJECT_CODING_STANDARD = {
    "project": "DRAGONS Task 1.1 biodiversity discourse analysis",
    "scope": (
        "Code public discourse from news and social media texts using only the supplied document text, "
        "metadata, deterministic signals and GLiNER entities. Treat LLM outputs as analytical estimates "
        "for validation, not as ground truth."
    ),
    "research_questions": [
        "How biodiversity loss is represented in relation to condition, causes, impacts and urgency.",
        "Which actors are associated with responsibility, agency, proposed action, blame, affectedness or expertise.",
        "Which sentiment, emotion-related signals, narratives and dominant frames are observable in the text.",
        "Which engagement, participation or action pathways are described in the text.",
        "How observable discourse patterns vary by source type, outlet/platform, language, time and country metadata.",
    ],
    "hard_limits": [
        "Do not classify truth or falsity.",
        "Do not label content as disinformation, misinformation or misleading.",
        "Do not infer algorithmic amplification, recommendation mechanisms, echo chambers or filter bubbles.",
        "Do not infer personal identity attributes, residence, nationality, ideology or group membership unless explicit in the text.",
        "Do not use external knowledge to add facts not present in the supplied document.",
        "Use null, false, empty lists or 'unclear' when evidence is insufficient.",
    ],
    "evidence_rules": [
        "Prefer short evidence spans copied or tightly paraphrased from the supplied text.",
        "If a field asks for an actor, policy, species, ecosystem, place or claim, use names present in text or GLiNER entities.",
        "If the text is too short, noisy, duplicated, off-topic or metadata-only, mark quality_flags accordingly.",
        "Sentiment must be interpreted with target and frame: negative sentiment may mean concern about biodiversity loss, not opposition to biodiversity policy.",
        "A topic cluster is not a narrative. A narrative needs a relation among actors, problems, causes, values, responsibilities and desired futures.",
    ],
    "source_rules": {
        "media_cloud": "Usually news/media. Code outlet discourse and quoted actors; distinguish journalist framing from quoted actor claims when possible.",
        "gdelt": "Usually event-linked news. Treat event context as metadata only; code only what the article text supports.",
        "bluesky": "Social post. Code the post text and visible thread metadata only; do not infer audience response beyond supplied engagement counts.",
    },
}

OPERATIONAL_DEFINITIONS = {
    "is_relevant_biodiversity": "true only when biodiversity, conservation, ecosystem, species, habitat, restoration, nature governance or biodiversity policy is substantively present.",
    "relevance_score": "0 means no relevance; 1 means biodiversity is central. Use intermediate values for partial or indirect relevance.",
    "primary_topic": "main substantive issue in the document, not simply the source or country.",
    "sentiment_label": "overall evaluative tone toward the central biodiversity-related issue, actor or policy; use mixed when targets differ.",
    "emotion_labels": "emotion signals expressed in the text, not emotions inferred for the audience.",
    "narrative_label": "short candidate narrative tying actors, problem, cause/value and direction of action.",
    "dominant_frame": "the main interpretive frame: how the problem is defined, what causes it, what consequences matter and what response is implied.",
    "actors": "actors explicitly mentioned or strongly supported by GLiNER entities; roles require textual evidence.",
    "claim_typology": "classify the main claim form and evidence presence; do not verify whether the claim is true.",
    "solution_orientation": "whether the document only describes a problem, proposes a solution, evaluates a solution or calls for action.",
    "justice_equity_signal": "explicit signal of rights, equity, participation, affected communities or unequal costs/benefits.",
    "uncertainty_signal": "explicit uncertainty, lack of evidence, technical controversy or need for more data.",
    "conflict_polarization_signal": "explicit conflict between actors, values or interests; do not infer polarization from disagreement alone.",
    "marginalised_frame_candidate": "possible underrepresented frame only when the text itself presents a distinct less-dominant perspective.",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_key_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:16]


def clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_jsonish(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def parse_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        return None


def choose_first(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", "None", "nan"):
            return value
    return None


def scalar_text(value: Any) -> str | None:
    if value in (None, "", "None", "nan"):
        return None
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return str(value)


def actor_identifier(value: Any) -> str | None:
    if value in (None, "", "None", "nan"):
        return None
    if isinstance(value, dict):
        return scalar_text(
            choose_first(
                value.get("did"),
                value.get("handle"),
                value.get("display_name"),
                value.get("displayName"),
            )
        )
    return scalar_text(value)


@dataclass
class RunPaths:
    run_id: str
    log_dir: Path
    parquet_dir: Path
    document_log_path: Path
    variable_log_path: Path
    error_log_path: Path
    incremental_results_path: Path
    checkpoint_path: Path


def setup_run(config: dict[str, Any], run_id: str | None) -> RunPaths:
    actual_run_id = run_id or datetime.now(timezone.utc).strftime("pilot_%Y%m%dT%H%M%SZ")
    log_dir = Path(config["outputs"]["log_dir"]) / actual_run_id
    parquet_dir = Path(config["outputs"]["parquet_dir"]) / actual_run_id
    log_dir.mkdir(parents=True, exist_ok=True)
    parquet_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "run.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return RunPaths(
        run_id=actual_run_id,
        log_dir=log_dir,
        parquet_dir=parquet_dir,
        document_log_path=log_dir / "documents.jsonl",
        variable_log_path=log_dir / "variables.jsonl",
        error_log_path=log_dir / "errors.jsonl",
        incremental_results_path=parquet_dir / "results_incremental.jsonl",
        checkpoint_path=parquet_dir / "checkpoint.json",
    )


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    needs_separator = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8") as handle:
        if needs_separator:
            with path.open("rb") as read_handle:
                read_handle.seek(-1, os.SEEK_END)
                if read_handle.read(1) != b"\n":
                    handle.write("\n")
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                loaded = json.loads(line)
                if isinstance(loaded, dict):
                    records.append(loaded)
            except Exception:
                logging.warning("Skipping malformed JSONL line %s in %s", line_number, path)
    return records


def load_incremental_results(path: Path) -> list[dict[str, Any]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    for record in read_jsonl(path):
        document_id = record.get("document_id")
        if document_id:
            records_by_id[str(document_id)] = record
    return list(records_by_id.values())


def load_existing_document_ids_from_run_globs(patterns: list[str] | None) -> set[str]:
    document_ids: set[str] = set()
    if not patterns:
        return document_ids
    base_dir = Path("data/processed/pilot_variables")
    for pattern in patterns:
        for run_dir in base_dir.glob(pattern):
            path = run_dir / "results_incremental.jsonl" if run_dir.is_dir() else run_dir
            if not path.exists():
                continue
            for record in read_jsonl(path):
                document_id = record.get("document_id")
                if document_id:
                    document_ids.add(str(document_id))
    return document_ids


def write_checkpoint(paths: RunPaths, record: dict[str, Any]) -> None:
    tmp_path = paths.checkpoint_path.with_suffix(paths.checkpoint_path.suffix + ".tmp")
    payload = json.dumps(record, ensure_ascii=False, indent=2, default=str)
    last_error: Exception | None = None
    for attempt in range(1, 6):
        try:
            tmp_path.write_text(payload, encoding="utf-8")
            os.replace(tmp_path, paths.checkpoint_path)
            return
        except PermissionError as exc:
            last_error = exc
            logging.warning("Checkpoint write attempt %s failed for %s: %s", attempt, paths.checkpoint_path, exc)
            time.sleep(0.5 * attempt)
    fallback_path = paths.checkpoint_path.with_name(
        f"{paths.checkpoint_path.stem}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.json"
    )
    fallback_path.write_text(payload, encoding="utf-8")
    logging.error("Checkpoint locked after retries; wrote fallback checkpoint to %s", fallback_path)
    if last_error is not None:
        logging.debug("Last checkpoint error", exc_info=last_error)


def shard_value(value: Any, shard_count: int) -> int:
    digest = hashlib.sha256(str(value).encode("utf-8", errors="ignore")).hexdigest()
    return int(digest[:16], 16) % shard_count


def apply_shard(df: pd.DataFrame, shard_index: int | None, shard_count: int | None) -> pd.DataFrame:
    if shard_index is None and shard_count is None:
        return df
    if shard_index is None or shard_count is None:
        raise ValueError("--shard-index and --shard-count must be provided together")
    if shard_count <= 0:
        raise ValueError("--shard-count must be greater than zero")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("--shard-index must be between 0 and shard-count - 1")
    mask = df["document_id"].map(lambda value: shard_value(value, shard_count) == shard_index)
    result = df[mask].reset_index(drop=True)
    logging.info("Shard selected: index=%s count=%s rows=%s", shard_index, shard_count, len(result))
    return result


def load_sample(
    config: dict[str, Any],
    limit_per_source: int,
    all_documents: bool = False,
    max_documents: int | None = None,
    shard_index: int | None = None,
    shard_count: int | None = None,
    input_parquet: str | None = None,
) -> pd.DataFrame:
    path = Path(input_parquet) if input_parquet else Path(config["analytics_parquet"])
    columns = [
        "document_id", "mongo_id", "collection_name", "source", "strategy",
        "source_type", "country_key", "language", "created_at", "url", "title",
        "text", "metadata", "raw_metadata", "char_count", "word_count",
        "sentence_count", "paragraph_count", "lexical_density_proxy", "top_terms",
    ]
    logging.info("Reading analytics parquet: %s", path)
    df = pd.read_parquet(path, columns=columns)
    df["text_clean"] = df["text"].map(clean_text)
    min_chars = int(config["run"].get("min_text_chars", 40))
    sources = set(config["run"].get("sources") or [])
    df = df[df["source"].isin(sources)]
    df = df[df["text_clean"].str.len() >= min_chars]
    if all_documents:
        result = df.sort_values(["source", "created_at", "document_id"], na_position="last").reset_index(drop=True)
        result = apply_shard(result, shard_index, shard_count)
        if max_documents is not None:
            result = result.head(max_documents).reset_index(drop=True)
        logging.info("Full dataset loaded: %s rows by source: %s", len(result), result["source"].value_counts().to_dict())
        return result
    sampled = []
    for source in config["run"]["sources"]:
        part = df[df["source"] == source].sort_values(["created_at", "document_id"], na_position="last")
        sampled.append(part.head(limit_per_source))
    result = pd.concat(sampled, ignore_index=True) if sampled else pd.DataFrame(columns=df.columns)
    result = apply_shard(result, shard_index, shard_count)
    if max_documents is not None:
        result = result.head(max_documents).reset_index(drop=True)
    logging.info("Sample loaded: %s rows by source: %s", len(result), result["source"].value_counts().to_dict())
    return result


def deterministic_variables(row: pd.Series) -> dict[str, Any]:
    text = clean_text(row.get("text"))
    title = clean_text(row.get("title"))
    haystack = f"{title} {text}".casefold()
    matched_terms = sorted(term for term in BIODIVERSITY_TERMS if term.casefold() in haystack)
    raw = parse_jsonish(row.get("raw_metadata"))
    metadata = parse_jsonish(row.get("metadata"))

    like_count = choose_first(raw.get("engagement_like_count"), raw.get("raw_likecount"))
    reply_count = choose_first(raw.get("engagement_reply_count"), raw.get("raw_replycount"))
    repost_count = choose_first(raw.get("engagement_repost_count"), raw.get("raw_repostcount"))
    quote_count = choose_first(raw.get("engagement_quote_count"), raw.get("raw_quotecount"))
    nums = [parse_number(v) or 0 for v in (like_count, reply_count, repost_count, quote_count)]

    return {
        "deterministic_computed_at": utcnow(),
        "text_hash": short_hash(text),
        "title_hash": short_hash(title),
        "text_char_count_runtime": len(text),
        "text_word_count_runtime": len(re.findall(r"\w+", text, flags=re.UNICODE)),
        "has_title": bool(title),
        "keyword_matches": matched_terms,
        "keyword_match_count": len(matched_terms),
        "keyword_relevance_proxy": min(1.0, len(matched_terms) / 3),
        "source_type_normalized": row.get("source_type") or ("social_post" if row.get("source") == "bluesky" else "news"),
        "platform_or_outlet": scalar_text(choose_first(
            raw.get("metadata_media_name"),
            raw.get("media_name"),
            raw.get("source_common_name"),
            raw.get("author_handle"),
            raw.get("author_display_name"),
            row.get("source"),
        )),
        "author_id": actor_identifier(choose_first(raw.get("author_did"), raw.get("author_handle"), raw.get("author"))),
        "author_handle": actor_identifier(choose_first(raw.get("author_handle"), raw.get("author_display_name"))),
        "uri": scalar_text(choose_first(raw.get("uri"), raw.get("raw_uri"), row.get("url"))),
        "reply_parent_uri": scalar_text(choose_first(raw.get("raw_record_reply_parent_uri"), raw.get("reply_parent_uri"))),
        "reply_root_uri": scalar_text(choose_first(raw.get("raw_record_reply_root_uri"), raw.get("reply_root_uri"))),
        "engagement_like_count": parse_number(like_count),
        "engagement_reply_count": parse_number(reply_count),
        "engagement_repost_count": parse_number(repost_count),
        "engagement_quote_count": parse_number(quote_count),
        "engagement_total": sum(nums),
        "metadata_keys": sorted(list(metadata.keys()))[:50],
    }


class HFModelClient:
    def __init__(self, config: dict[str, Any], paths: RunPaths | None = None):
        self.config = config
        self.paths = paths
        self._gliner_model = None
        self._gliner_import_error: str | None = None

    def _gliner_settings(self) -> dict[str, Any]:
        return ((self.config.get("hf_models") or {}).get("gliner") or {})

    def _gliner_library(self) -> str:
        settings = self._gliner_settings()
        model_name = settings.get("model", "fastino/gliner2.5-multi-v1")
        library = settings.get("library")
        if library:
            return str(library)
        if "gliner2.5" in str(model_name).casefold() or str(model_name).casefold().startswith("fastino/gliner2"):
            return "gliner2"
        return "gliner"

    def _load_gliner(self):
        if self._gliner_model is not None:
            return self._gliner_model
        settings = self._gliner_settings()
        model_name = settings.get("model", "fastino/gliner2.5-multi-v1")
        try:
            if self._gliner_library() == "gliner2":
                from gliner2 import AutoExtractor

                self._gliner_model = AutoExtractor.from_pretrained(model_name)
            else:
                from gliner import GLiNER

                self._gliner_model = GLiNER.from_pretrained(model_name)
            return self._gliner_model
        except Exception as exc:
            self._gliner_import_error = f"{type(exc).__name__}: {str(exc)[:500]}"
            raise

    @staticmethod
    def _chunk_text(text: str, max_chars: int, overlap_chars: int, max_chunks: int) -> list[tuple[int, str]]:
        if len(text) <= max_chars:
            return [(0, text)]
        chunks: list[tuple[int, str]] = []
        start = 0
        step = max(1, max_chars - max(0, overlap_chars))
        while start < len(text) and len(chunks) < max_chunks:
            end = min(len(text), start + max_chars)
            chunks.append((start, text[start:end]))
            if end >= len(text):
                break
            start += step
        return chunks

    def annotate(self, row: pd.Series) -> tuple[dict[str, Any], dict[str, Any]]:
        hf_config = self.config.get("hf_models") or {}
        settings = self._gliner_settings()
        if not hf_config.get("enabled", False) or not settings.get("enabled", False):
            return {}, {"status": "skipped", "reason": "hf_disabled"}

        text = clean_text(row.get("text"))
        title = clean_text(row.get("title"))
        candidate_text = clean_text(f"{title}. {text}")
        max_chars = int(settings.get("max_text_chars", 3500))
        overlap_chars = int(settings.get("chunk_overlap_chars", 300))
        max_chunks = int(settings.get("max_chunks", 8))
        labels = settings.get("labels") or DEFAULT_GLINER_LABELS
        threshold = float(settings.get("threshold", 0.35))
        model_name = settings.get("model", "fastino/gliner2.5-multi-v1")
        library = self._gliner_library()
        started = time.time()
        try:
            model = self._load_gliner()
            entities_raw = []
            for offset, chunk in self._chunk_text(candidate_text, max_chars, overlap_chars, max_chunks):
                if library == "gliner2":
                    chunk_result = model.extract_entities(
                        chunk,
                        labels,
                        include_confidence=True,
                        include_spans=True,
                    )
                    label_map = chunk_result.get("entities", {}) if isinstance(chunk_result, dict) else {}
                    for label, items in label_map.items():
                        for item in items or []:
                            if not isinstance(item, dict):
                                continue
                            adjusted = {
                                "text": item.get("text"),
                                "label": label,
                                "score": item.get("confidence", item.get("score")),
                                "start": item.get("start"),
                                "end": item.get("end"),
                            }
                            if isinstance(adjusted.get("start"), int):
                                adjusted["start"] += offset
                            if isinstance(adjusted.get("end"), int):
                                adjusted["end"] += offset
                            if adjusted.get("score") is None or float(adjusted["score"]) >= threshold:
                                entities_raw.append(adjusted)
                else:
                    for item in model.predict_entities(chunk, labels, threshold=threshold):
                        if isinstance(item, dict):
                            adjusted = dict(item)
                            if isinstance(adjusted.get("start"), int):
                                adjusted["start"] += offset
                            if isinstance(adjusted.get("end"), int):
                                adjusted["end"] += offset
                            entities_raw.append(adjusted)
            entities = []
            seen: set[tuple[str | None, str | None, Any, Any]] = set()
            for item in entities_raw:
                if not isinstance(item, dict):
                    continue
                marker = (item.get("text"), item.get("label"), item.get("start"), item.get("end"))
                if marker in seen:
                    continue
                seen.add(marker)
                entities.append({
                    "text": item.get("text"),
                    "label": item.get("label"),
                    "score": round(float(item.get("score", 0.0)), 4) if item.get("score") is not None else None,
                    "start": item.get("start"),
                    "end": item.get("end"),
                })
            counts = pd.Series([entity["label"] for entity in entities if entity.get("label")]).value_counts().to_dict()
            data = {
                "gliner_named_entities": entities,
                "gliner_entity_counts_by_label": counts,
                "gliner_top_entity_labels": list(counts.keys())[:10],
            }
            meta = {
                "status": "success",
                "provider": "huggingface",
                "library": library,
                "model": model_name,
                "threshold": threshold,
                "labels": labels,
                "chunks_processed": len(self._chunk_text(candidate_text, max_chars, overlap_chars, max_chunks)),
                "elapsed_seconds": round(time.time() - started, 3),
            }
            return data, meta
        except Exception as exc:
            error = {
                "status": "failed",
                "provider": "huggingface",
                "library": library,
                "model": model_name,
                "document_id": row.get("document_id"),
                "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
            }
            if self.paths is not None:
                append_jsonl(self.paths.error_log_path, {**error, "logged_at": utcnow()})
            return {}, error


def llm_prompt(
    row: pd.Series,
    deterministic: dict[str, Any],
    max_chars: int,
    hf_data: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    text = clean_text(row.get("text"))[:max_chars]
    title = clean_text(row.get("title"))
    language = row.get("language") or "unknown"
    source = row.get("source") or "unknown"
    system = (
        "You are an expert analytical coder for DRAGONS Task 1.1 biodiversity discourse analysis. "
        "Return only one valid JSON object matching the requested schema. "
        "Use only the supplied title, text, metadata, deterministic signals and GLiNER entities. "
        "Do not classify truth/falsity, disinformation or misinformation. "
        "Do not infer algorithmic amplification or hidden platform mechanisms. "
        "If evidence is insufficient, use unclear, null, false or empty lists as appropriate."
    )
    user = {
        "task": "Annotate one document for discourse variables.",
        "project_coding_standard": PROJECT_CODING_STANDARD,
        "operational_definitions": OPERATIONAL_DEFINITIONS,
        "coding_instructions": [
            "Code the document as one analytical unit.",
            "Ground every interpretive field in the supplied text; use evidence_span fields when available.",
            "Use GLiNER entities as candidate evidence, but do not add entities or actors that are not supported by the text.",
            "Keep labels short and stable so they can be aggregated across documents.",
            "Prefer 'unclear' over speculative coding.",
            "For non-relevant or weakly relevant documents, still return the full schema with low relevance_score and conservative values.",
            "For multilingual text, code in the language of the document but use the fixed English enum values exactly.",
            "Do not expand the enum values. If no enum fits, use 'unclear' or the closest permitted value with lower confidence.",
        ],
        "allowed_values": {
            "sentiment_label": sorted(ALLOWED_SENTIMENT),
            "emotion_labels": sorted(ALLOWED_EMOTIONS),
            "claim_type": [
                "factual_claim", "opinion", "interpretation", "value_judgment",
                "prediction", "testimony", "mixed_claim", "unclear",
            ],
            "verifiability": [
                "directly_verifiable", "verifiable_with_external_evidence",
                "difficult_to_verify", "not_factually_verifiable",
                "insufficient_context", "unclear",
            ],
            "evidence_presence": [
                "explicit_evidence", "source_mentioned", "testimony_only",
                "no_evidence_presented", "not_applicable", "unclear",
            ],
            "evidence_type": [
                "data_or_statistics", "expert_source", "official_document",
                "eyewitness_or_testimony", "anecdotal", "no_evidence", "unclear",
            ],
            "solution_orientation": [
                "problem_only", "proposes_solution", "evaluates_solution",
                "calls_for_action", "unclear",
            ],
            "uncertainty_signal": [
                "high_uncertainty", "moderate_uncertainty", "low_uncertainty",
                "no_uncertainty_signal", "unclear",
            ],
            "frame_family": ALLOWED_FRAME_FAMILIES,
            "frame_function": ALLOWED_FRAME_FUNCTIONS,
            "frame_scale": ALLOWED_FRAME_SCALES,
        },
        "required_json_schema": {
            "is_relevant_biodiversity": "boolean",
            "relevance_score": "number 0..1",
            "primary_topic": "short string",
            "subtopic": "short string or null",
            "sentiment_label": "allowed value",
            "emotion_labels": "list of allowed values",
            "emotional_intensity": "number 0..1",
            "narrative_label": "short string",
            "narrative_summary": "one sentence",
            "dominant_frame": {
                "frame_label": "short string",
                "frame_family": "allowed value",
                "frame_function": "allowed value",
                "frame_scale": "allowed value",
                "problem_definition": "short string or null",
                "cause": "short string or null",
                "consequence": "short string or null",
                "solution": "short string or null",
                "moral_evaluation": "short string or null",
                "beneficiary_actor": "short string or null",
                "affected_actor": "short string or null",
                "evidence_span": "short string or null",
            },
            "framing_analysis": {
                "diagnostic_frame": "how the text defines the problem, or null",
                "causal_attribution": "actor/process blamed or identified as cause, or null",
                "prognostic_frame": "solution or intervention proposed, or null",
                "motivational_frame": "call to action, urgency or mobilizing argument, or null",
                "risk_frame": "risk/threat emphasized, or null",
                "opportunity_frame": "benefit/opportunity emphasized, or null",
                "knowledge_authority_frame": "whose knowledge or expertise is privileged, or null",
                "participation_frame": "how participation/inclusion/exclusion is framed, or null",
                "economic_frame": "cost, funding, livelihood or development frame, or null",
                "justice_rights_frame": "justice, rights, equity or affected community frame, or null",
                "evidence_span": "short string or null",
            },
            "counter_frame_candidate": {
                "is_present": "boolean",
                "frame_label": "short string or null",
                "contrasts_with": "short string or null",
                "evidence_span": "short string or null",
            },
            "discursive_pattern": "short string",
            "actors": [{"text": "string", "role": "responsibility|agency|blame|affected|expert|other"}],
            "stakeholder_presence": {
                "government_present": "boolean",
                "community_present": "boolean",
                "ngo_present": "boolean",
                "private_sector_present": "boolean",
                "science_present": "boolean",
                "media_present": "boolean",
                "evidence": "short string or null",
            },
            "biodiversity_object": {
                "species_mentions": "list of strings",
                "ecosystem_mentions": "list of strings",
                "protected_area_mentions": "list of strings",
                "biodiversity_concepts": "list of strings",
            },
            "responsibility_actor": "string or null",
            "agency_actor": "string or null",
            "blame_actor": "string or null",
            "proposed_action": "string or null",
            "governance_policy_mentions": {
                "policy_mentions": "list of strings",
                "institution_mentions": "list of strings",
                "regulation_or_commitment": "short string or null",
                "implementation_gap": "short string or null",
            },
            "claim_typology": {
                "main_claim": "short string or null",
                "claim_type": "allowed value",
                "verifiability": "allowed value",
                "evidence_presence": "allowed value",
                "evidence_type": "allowed value",
                "source_attribution": "string or null",
            },
            "solution_orientation": "allowed value",
            "justice_equity_signal": {
                "is_present": "boolean",
                "affected_group": "short string or null",
                "equity_dimension": "short string or null",
                "evidence_span": "short string or null",
            },
            "uncertainty_signal": "allowed value",
            "conflict_polarization_signal": {
                "is_conflict_present": "boolean",
                "conflict_axis": "short string or null",
                "actors_in_conflict": "list of strings",
                "evidence_span": "short string or null",
            },
            "marginalised_frame_candidate": {
                "is_candidate": "boolean",
                "frame_label": "short string or null",
                "reason": "short string or null",
                "evidence_span": "short string or null",
            },
            "confidence": "number 0..1",
            "quality_flags": "list of short strings",
        },
        "metadata": {
            "document_id": row.get("document_id"),
            "source": source,
            "language": language,
            "country_key": row.get("country_key"),
            "created_at": row.get("created_at"),
            "keyword_matches": deterministic.get("keyword_matches", []),
            "gliner_entities_sample": (hf_data or {}).get("gliner_named_entities", [])[:40],
            "gliner_entity_counts_by_label": (hf_data or {}).get("gliner_entity_counts_by_label", {}),
        },
        "title": title,
        "text": text,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def extract_json(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?", "", value.strip(), flags=re.IGNORECASE).strip()
        value = re.sub(r"```$", "", value).strip()
    try:
        data = json.loads(value)
    except Exception:
        match = re.search(r"\{.*\}", value, flags=re.S)
        if not match:
            raise
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("LLM response is not a JSON object")
    return data


class LLMClient:
    def __init__(self, config: dict[str, Any], paths: RunPaths):
        self.config = config
        self.paths = paths

    def write_trace(
        self,
        row: pd.Series,
        provider_name: str,
        provider: dict[str, Any],
        attempt: int,
        payload: dict[str, Any] | None,
        started: float,
        status: str,
        raw_response: dict[str, Any] | None = None,
        raw_content: str | None = None,
        parsed: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        trace = {
            "logged_at": utcnow(),
            "run_id": self.paths.run_id,
            "document_id": row.get("document_id"),
            "source": row.get("source"),
            "country_key": row.get("country_key"),
            "language": row.get("language"),
            "provider": provider_name,
            "model": provider.get("model"),
            "endpoint": provider.get("endpoint"),
            "attempt": attempt,
            "status": status,
            "elapsed_seconds": round(time.time() - started, 3),
            "request_payload": payload,
            "response_raw": raw_response,
            "response_content": raw_content,
            "parsed_json": parsed,
            "usage": (raw_response or {}).get("usage", {}),
            "error": error,
        }
        append_jsonl(self.paths.log_dir / "llm_traces.jsonl", trace)

    def annotate(
        self,
        row: pd.Series,
        deterministic: dict[str, Any],
        hf_data: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        if not self.config["run"].get("llm_enabled", True):
            return None, {"status": "skipped", "reason": "llm_disabled"}
        max_chars = int(self.config["run"].get("max_text_chars_for_llm", 4500))
        messages = llm_prompt(row, deterministic, max_chars, hf_data)
        errors = []
        for provider_name in self.config["run"].get("llm_provider_order", ["deepseek", "openai"]):
            provider = self.config["models"][provider_name]
            token = os.environ.get(provider["token_env"])
            if not token:
                started = time.time()
                error = {"provider": provider_name, "error": "missing_token"}
                errors.append(error)
                self.write_trace(row, provider_name, provider, 0, None, started, "skipped_missing_token", error=error)
                continue
            for attempt in range(1, int(self.config["run"].get("llm_max_retries", 2)) + 1):
                started = time.time()
                payload: dict[str, Any] | None = None
                try:
                    payload = {
                        "model": provider["model"],
                        "messages": messages,
                        "temperature": float(self.config["run"].get("llm_temperature", 0.0)),
                        "response_format": {"type": "json_object"},
                    }
                    response = requests.post(
                        provider["endpoint"],
                        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                        json=payload,
                        timeout=int(self.config["run"].get("llm_timeout_seconds", 90)),
                    )
                    response.raise_for_status()
                    raw = response.json()
                    content = raw["choices"][0]["message"]["content"]
                    parsed = extract_json(content)
                    meta = {
                        "status": "success",
                        "provider": provider_name,
                        "model": provider["model"],
                        "attempt": attempt,
                        "elapsed_seconds": round(time.time() - started, 3),
                        "usage": raw.get("usage", {}),
                    }
                    self.write_trace(
                        row,
                        provider_name,
                        provider,
                        attempt,
                        payload,
                        started,
                        "success",
                        raw_response=raw,
                        raw_content=content,
                        parsed=parsed,
                    )
                    return parsed, meta
                except Exception as exc:
                    raw_response = None
                    raw_content = None
                    if "response" in locals():
                        try:
                            raw_response = response.json()
                        except Exception:
                            try:
                                raw_content = response.text
                            except Exception:
                                raw_content = None
                    error = {
                        "status": "error",
                        "provider": provider_name,
                        "attempt": attempt,
                        "document_id": row.get("document_id"),
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:1000],
                    }
                    errors.append(error)
                    self.write_trace(
                        row,
                        provider_name,
                        provider,
                        attempt,
                        payload,
                        started,
                        "error",
                        raw_response=raw_response,
                        raw_content=raw_content,
                        error=error,
                    )
                    append_jsonl(self.paths.error_log_path, {**error, "logged_at": utcnow()})
                    time.sleep(min(2 * attempt, 5))
        return None, {"status": "failed", "errors": errors}


def normalize_llm_output(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    result = dict(data)
    sentiment = result.get("sentiment_label")
    if sentiment not in ALLOWED_SENTIMENT:
        result["sentiment_label"] = "unclear"
    emotions = result.get("emotion_labels")
    if not isinstance(emotions, list):
        emotions = ["unclear"]
    result["emotion_labels"] = [emotion if emotion in ALLOWED_EMOTIONS else "unclear" for emotion in emotions]
    for key in ("relevance_score", "emotional_intensity", "confidence"):
        try:
            value = float(result.get(key, 0))
            result[key] = max(0.0, min(1.0, value))
        except Exception:
            result[key] = 0.0
    return result


def build_result_record(
    row: pd.Series,
    deterministic: dict[str, Any],
    hf_data: dict[str, Any] | None,
    hf_meta: dict[str, Any],
    llm_data: dict[str, Any] | None,
    llm_meta: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    llm_norm = normalize_llm_output(llm_data)
    return {
        "run_id": run_id,
        "result_id": f"{run_id}:{row.get('document_id')}",
        "document_id": row.get("document_id"),
        "mongo_id": row.get("mongo_id"),
        "collection_name": row.get("collection_name"),
        "source": row.get("source"),
        "strategy": row.get("strategy"),
        "source_type": row.get("source_type"),
        "country_key": row.get("country_key"),
        "language": row.get("language"),
        "created_at": row.get("created_at"),
        "url": row.get("url"),
        "title": row.get("title"),
        "text_preview": clean_text(row.get("text"))[:500],
        "etl_metrics": {
            "char_count": row.get("char_count"),
            "word_count": row.get("word_count"),
            "sentence_count": row.get("sentence_count"),
            "paragraph_count": row.get("paragraph_count"),
            "lexical_density_proxy": row.get("lexical_density_proxy"),
            "top_terms": row.get("top_terms"),
        },
        "deterministic_variables": deterministic,
        "hf_variables": hf_data or {},
        "hf_metadata": hf_meta,
        "llm_variables": llm_norm,
        "llm_metadata": llm_meta,
        "computed_at": utcnow(),
    }


def log_variable_records(paths: RunPaths, result: dict[str, Any]) -> None:
    document_id = result["document_id"]
    variable_groups = {
        "etl_metrics": result.get("etl_metrics", {}),
        "deterministic_variables": result.get("deterministic_variables", {}),
        "hf_variables": result.get("hf_variables", {}),
        "llm_variables": result.get("llm_variables", {}),
    }
    append_jsonl(paths.document_log_path, {
        "run_id": paths.run_id,
        "document_id": document_id,
        "source": result.get("source"),
        "status": result.get("llm_metadata", {}).get("status"),
        "computed_at": result.get("computed_at"),
    })
    for group, values in variable_groups.items():
        if not isinstance(values, dict):
            continue
        for variable, value in values.items():
            append_jsonl(paths.variable_log_path, {
                "run_id": paths.run_id,
                "document_id": document_id,
                "source": result.get("source"),
                "group": group,
                "variable": variable,
                "status": "calculated",
                "value_type": type(value).__name__,
                "calculated_at": utcnow(),
            })


def create_sna_summary(results: list[dict[str, Any]], paths: RunPaths) -> dict[str, Any]:
    graph = nx.DiGraph()
    uri_to_author = {}
    for record in results:
        deterministic = record.get("deterministic_variables") or {}
        if record.get("source") != "bluesky":
            continue
        author = deterministic.get("author_id")
        uri = deterministic.get("uri")
        if author:
            graph.add_node(author, node_type="author")
        if uri and author:
            uri_to_author[uri] = author
    for record in results:
        deterministic = record.get("deterministic_variables") or {}
        if record.get("source") != "bluesky":
            continue
        author = deterministic.get("author_id")
        parent = deterministic.get("reply_parent_uri")
        parent_author = uri_to_author.get(parent)
        if author and parent_author and author != parent_author:
            graph.add_edge(author, parent_author, relation="reply")
    metrics = {}
    if graph.number_of_nodes():
        pagerank = nx.pagerank(graph) if graph.number_of_edges() else {node: 0 for node in graph.nodes}
        degree = dict(graph.degree())
        indegree = dict(graph.in_degree())
        outdegree = dict(graph.out_degree())
        metrics = {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "weakly_connected_components": nx.number_weakly_connected_components(graph) if graph.number_of_nodes() else 0,
            "top_pagerank": sorted(pagerank.items(), key=lambda item: item[1], reverse=True)[:20],
            "top_degree": sorted(degree.items(), key=lambda item: item[1], reverse=True)[:20],
            "top_indegree": sorted(indegree.items(), key=lambda item: item[1], reverse=True)[:20],
            "top_outdegree": sorted(outdegree.items(), key=lambda item: item[1], reverse=True)[:20],
        }
    (paths.parquet_dir / "sna_summary.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    append_jsonl(paths.variable_log_path, {
        "run_id": paths.run_id,
        "document_id": None,
        "source": "bluesky",
        "group": "sna_networkx",
        "variable": "bluesky_author_reply_network",
        "status": "calculated",
        "value_type": "graph_summary",
        "calculated_at": utcnow(),
    })
    return metrics


def mongo_uri_from_config(config: dict[str, Any]) -> str:
    if os.environ.get("MONGODB_URI"):
        return os.environ["MONGODB_URI"]
    nlp_repo = Path(config.get("nlp_repo", ""))
    mongo_env = load_key_values(nlp_repo / "docker" / "mongo" / ".env")
    user = mongo_env.get("MONGO_INITDB_ROOT_USERNAME", "root")
    password = mongo_env.get("MONGO_INITDB_ROOT_PASSWORD", "dragons_dev_password")
    return f"mongodb://{user}:{password}@localhost:50030/?authSource=admin"


def postgres_uri_from_config() -> str:
    return os.environ.get("POSTGRES_URI", "postgresql://dragons:dragons_dev_password@localhost:50020/dragons")


def json_sanitize(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {key: json_sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_sanitize(item) for item in value]
    return value


def write_mongo(config: dict[str, Any], paths: RunPaths, results: list[dict[str, Any]], run_record: dict[str, Any]) -> dict[str, Any]:
    if pymongo is None:
        return {"status": "skipped", "reason": "pymongo_not_available"}
    try:
        client = pymongo.MongoClient(mongo_uri_from_config(config), serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client[config["outputs"]["mongo_database"]]
        result_collection = db[config["outputs"]["mongo_results_collection"]]
        runs_collection = db[config["outputs"]["mongo_runs_collection"]]
        if results:
            result_collection.delete_many({"run_id": paths.run_id})
            result_collection.insert_many(results, ordered=False)
        runs_collection.update_one({"run_id": paths.run_id}, {"$set": run_record}, upsert=True)
        return {"status": "success", "rows": len(results)}
    except Exception as exc:
        append_jsonl(paths.error_log_path, {
            "logged_at": utcnow(),
            "stage": "mongo_write",
            "error_type": type(exc).__name__,
            "error": str(exc)[:1000],
        })
        return {"status": "failed", "error": str(exc)[:300]}


def write_postgres(config: dict[str, Any], paths: RunPaths, results: list[dict[str, Any]], run_record: dict[str, Any]) -> dict[str, Any]:
    if psycopg is None:
        return {"status": "skipped", "reason": "psycopg_not_available"}
    schema = config["outputs"]["postgres_schema"]
    results_table = config["outputs"]["postgres_results_table"]
    runs_table = config["outputs"]["postgres_runs_table"]
    try:
        with psycopg.connect(postgres_uri_from_config(), connect_timeout=5) as conn:
            with conn.cursor() as cur:
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
                cur.execute(f"ALTER TABLE {schema}.{results_table} ADD COLUMN IF NOT EXISTS hf_variables JSONB")
                cur.execute(f"ALTER TABLE {schema}.{results_table} ADD COLUMN IF NOT EXISTS hf_metadata JSONB")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {schema}.{runs_table} (
                        run_id TEXT PRIMARY KEY,
                        run_record JSONB,
                        updated_at TIMESTAMPTZ
                    )
                    """
                )
                cur.execute(f"DELETE FROM {schema}.{results_table} WHERE run_id = %s", (paths.run_id,))
                for record in results:
                    cur.execute(
                        f"""
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
                        """,
                        (
                            record["result_id"], record["run_id"], record["document_id"], record["source"],
                            record.get("country_key"), record.get("language"), str(record.get("created_at")),
                            record.get("title"), Jsonb(json_sanitize(record.get("etl_metrics", {}))),
                            Jsonb(json_sanitize(record.get("deterministic_variables", {}))),
                            Jsonb(json_sanitize(record.get("hf_variables", {}))),
                            Jsonb(json_sanitize(record.get("hf_metadata", {}))),
                            Jsonb(json_sanitize(record.get("llm_variables", {}))),
                            Jsonb(json_sanitize(record.get("llm_metadata", {}))),
                            record.get("computed_at"),
                        ),
                    )
                cur.execute(
                    f"""
                    INSERT INTO {schema}.{runs_table} (run_id, run_record, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (run_id) DO UPDATE SET run_record = EXCLUDED.run_record, updated_at = EXCLUDED.updated_at
                    """,
                    (paths.run_id, Jsonb(json_sanitize(run_record)), utcnow()),
                )
            conn.commit()
        return {"status": "success", "rows": len(results)}
    except Exception as exc:
        append_jsonl(paths.error_log_path, {
            "logged_at": utcnow(),
            "stage": "postgres_write",
            "error_type": type(exc).__name__,
            "error": str(exc)[:1000],
        })
        return {"status": "failed", "error": str(exc)[:300]}


def write_parquet_outputs(paths: RunPaths, results: list[dict[str, Any]], run_record: dict[str, Any]) -> dict[str, Any]:
    flat_rows = []
    for record in results:
        llm = record.get("llm_variables", {})
        det = record.get("deterministic_variables", {})
        flat_rows.append({
            "run_id": record["run_id"],
            "document_id": record["document_id"],
            "source": record["source"],
            "country_key": record.get("country_key"),
            "language": record.get("language"),
            "created_at": str(record.get("created_at")),
            "title": record.get("title"),
            "keyword_match_count": det.get("keyword_match_count"),
            "engagement_total": det.get("engagement_total"),
            "gliner_entity_count": len((record.get("hf_variables") or {}).get("gliner_named_entities", [])),
            "gliner_top_entity_labels": json.dumps((record.get("hf_variables") or {}).get("gliner_top_entity_labels", []), ensure_ascii=False),
            "is_relevant_biodiversity": llm.get("is_relevant_biodiversity"),
            "relevance_score": llm.get("relevance_score"),
            "primary_topic": llm.get("primary_topic"),
            "sentiment_label": llm.get("sentiment_label"),
            "emotion_labels": json.dumps(llm.get("emotion_labels", []), ensure_ascii=False),
            "narrative_label": llm.get("narrative_label"),
            "dominant_frame_label": (llm.get("dominant_frame") or {}).get("frame_label") if isinstance(llm.get("dominant_frame"), dict) else None,
            "confidence": llm.get("confidence"),
            "llm_status": record.get("llm_metadata", {}).get("status"),
            "computed_at": record.get("computed_at"),
        })
    pd.DataFrame(flat_rows).to_parquet(paths.parquet_dir / "analytics_variable_results_flat.parquet", index=False)
    pd.DataFrame(flat_rows).to_csv(paths.parquet_dir / "analytics_variable_results_flat.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    pd.DataFrame([{"record": json.dumps(record, ensure_ascii=False, default=str)} for record in results]).to_parquet(
        paths.parquet_dir / "analytics_variable_results_raw_json.parquet", index=False
    )
    (paths.parquet_dir / "run_record.json").write_text(json.dumps(run_record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {
        "status": "success",
        "flat_parquet": str(paths.parquet_dir / "analytics_variable_results_flat.parquet"),
        "flat_csv": str(paths.parquet_dir / "analytics_variable_results_flat.csv"),
        "raw_json_parquet": str(paths.parquet_dir / "analytics_variable_results_raw_json.parquet"),
        "incremental_jsonl": str(paths.incremental_results_path),
    }


def calculated_variables_manifest() -> dict[str, list[str]]:
    return {
        "etl_metrics": ["char_count", "word_count", "sentence_count", "paragraph_count", "lexical_density_proxy", "top_terms"],
        "deterministic_variables": [
            "keyword_matches", "keyword_relevance_proxy", "source_type_normalized",
            "platform_or_outlet", "author_id", "uri", "reply_parent_uri",
            "engagement_total", "text_hash",
        ],
        "hf_variables": [
            "gliner_named_entities", "gliner_entity_counts_by_label",
            "gliner_top_entity_labels",
        ],
            "llm_variables": [
                "is_relevant_biodiversity", "relevance_score", "primary_topic", "subtopic",
                "sentiment_label", "emotion_labels", "emotional_intensity", "narrative_label",
                "dominant_frame", "framing_analysis", "counter_frame_candidate",
                "discursive_pattern", "actors", "responsibility_actor",
            "agency_actor", "blame_actor", "proposed_action", "claim_typology",
            "stakeholder_presence", "biodiversity_object", "governance_policy_mentions",
            "solution_orientation", "justice_equity_signal", "uncertainty_signal",
            "conflict_polarization_signal",
                "marginalised_frame_candidate", "confidence", "quality_flags",
            ],
        "sna_networkx": ["bluesky_author_reply_network"],
    }


def build_run_record(
    paths: RunPaths,
    config: dict[str, Any],
    started_at: str,
    results: list[dict[str, Any]],
    sna_summary: dict[str, Any],
    all_documents: bool,
    resumed: bool,
    skipped_existing: int,
    status: str = "completed",
) -> dict[str, Any]:
    return {
        "run_id": paths.run_id,
        "status": status,
        "started_at": started_at,
        "finished_at": utcnow(),
        "all_documents": all_documents,
        "limit_per_source": None if all_documents else config["run"]["limit_per_source"],
        "sources": config["run"]["sources"],
        "rows_total": len(results),
        "rows_processed_this_invocation": max(0, len(results) - skipped_existing),
        "rows_skipped_existing": skipped_existing,
        "resumed": resumed,
        "rows_by_source": pd.Series([r["source"] for r in results]).value_counts().to_dict() if results else {},
        "llm_status_counts": pd.Series([r.get("llm_metadata", {}).get("status") for r in results]).value_counts().to_dict() if results else {},
        "hf_status_counts": pd.Series([r.get("hf_metadata", {}).get("status") for r in results]).value_counts().to_dict() if results else {},
        "variables_calculated": calculated_variables_manifest(),
        "sna_summary": sna_summary,
    }


def run_pipeline(args: argparse.Namespace) -> int:
    load_dotenv(ROOT / ".env")
    config = yaml.safe_load(resolve_repo_path(args.config).read_text(encoding="utf-8"))
    if args.limit_per_source is not None:
        config["run"]["limit_per_source"] = args.limit_per_source
    if args.no_llm:
        config["run"]["llm_enabled"] = False
    if args.no_hf:
        config.setdefault("hf_models", {})["enabled"] = False
    if args.hf_model:
        config.setdefault("hf_models", {}).setdefault("gliner", {})["model"] = args.hf_model
    if args.sources:
        configured_sources = set(config["run"].get("sources") or [])
        requested_sources = list(dict.fromkeys(args.sources))
        unknown_sources = sorted(set(requested_sources) - configured_sources)
        if unknown_sources:
            raise ValueError(f"Unknown source(s) for this config: {unknown_sources}")
        config["run"]["sources"] = requested_sources
    paths = setup_run(config, args.run_id)
    started_at = utcnow()
    logging.info("Run started: %s", paths.run_id)
    df = load_sample(
        config,
        int(config["run"]["limit_per_source"]),
        all_documents=args.all_documents,
        max_documents=args.max_documents,
        shard_index=args.shard_index,
        shard_count=args.shard_count,
        input_parquet=args.input_parquet,
    )
    hf_client = HFModelClient(config, paths)
    client = LLMClient(config, paths)
    existing_results = load_incremental_results(paths.incremental_results_path) if args.resume else []
    processed_ids = {str(record.get("document_id")) for record in existing_results if record.get("document_id")}
    external_processed_ids = load_existing_document_ids_from_run_globs(args.skip_existing_run_glob)
    if external_processed_ids:
        logging.info("Loaded %s externally processed document ids from %s", len(external_processed_ids), args.skip_existing_run_glob)
        processed_ids.update(external_processed_ids)
    if existing_results:
        logging.info("Resume enabled: loaded %s existing document results from %s", len(existing_results), paths.incremental_results_path)
    results: list[dict[str, Any]] = list(existing_results)
    processed_this_invocation = 0
    for idx, row in df.iterrows():
        doc_id = row.get("document_id")
        if args.resume and str(doc_id) in processed_ids:
            if (idx + 1) % 1000 == 0:
                logging.info("Skipping already processed document %s/%s", idx + 1, len(df))
            continue
        logging.info("Processing %s/%s %s", idx + 1, len(df), doc_id)
        deterministic = deterministic_variables(row)
        hf_data, hf_meta = hf_client.annotate(row)
        llm_data, llm_meta = client.annotate(row, deterministic, hf_data)
        result = build_result_record(row, deterministic, hf_data, hf_meta, llm_data, llm_meta, paths.run_id)
        results.append(result)
        append_jsonl(paths.incremental_results_path, result)
        log_variable_records(paths, result)
        processed_ids.add(str(doc_id))
        processed_this_invocation += 1
        write_checkpoint(paths, {
            "run_id": paths.run_id,
            "status": "running",
            "updated_at": utcnow(),
            "all_documents": args.all_documents,
            "target_rows": len(df),
            "shard_index": args.shard_index,
            "shard_count": args.shard_count,
            "rows_total_incremental": len(results),
            "rows_skipped_external_existing": len(external_processed_ids),
            "rows_processed_this_invocation": processed_this_invocation,
            "last_document_id": doc_id,
            "incremental_results_path": str(paths.incremental_results_path),
            "log_dir": str(paths.log_dir),
        })
        if args.stop_after is not None and processed_this_invocation >= args.stop_after:
            logging.info("Stopping early after %s new documents because --stop-after was set.", processed_this_invocation)
            partial_sna_summary = create_sna_summary(results, paths)
            partial_run_record = build_run_record(
                paths,
                config,
                started_at,
                results,
                partial_sna_summary,
                args.all_documents,
                bool(existing_results),
                len(existing_results),
                status="partial",
            )
            parquet_status = write_parquet_outputs(paths, results, partial_run_record)
            partial_run_record["outputs"] = {
                "parquet": parquet_status,
                "mongo": {"status": "skipped", "reason": "partial_stop"},
                "postgres": {"status": "skipped", "reason": "partial_stop"},
                "log_dir": str(paths.log_dir),
                "checkpoint": str(paths.checkpoint_path),
                "incremental_results": str(paths.incremental_results_path),
            }
            write_checkpoint(paths, {**partial_run_record, "updated_at": utcnow()})
            (paths.parquet_dir / "run_record.json").write_text(json.dumps(partial_run_record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            append_jsonl(paths.log_dir / "run_summary.jsonl", partial_run_record)
            print(json.dumps(partial_run_record, ensure_ascii=False, indent=2, default=str))
            return 0
    sna_summary = create_sna_summary(results, paths)
    run_record = build_run_record(
        paths,
        config,
        started_at,
        results,
        sna_summary,
        args.all_documents,
        bool(existing_results),
        len(existing_results),
    )
    parquet_status = write_parquet_outputs(paths, results, run_record)
    mongo_status = write_mongo(config, paths, results, run_record)
    postgres_status = write_postgres(config, paths, results, run_record)
    run_record["outputs"] = {
        "parquet": parquet_status,
        "mongo": mongo_status,
        "postgres": postgres_status,
        "log_dir": str(paths.log_dir),
        "checkpoint": str(paths.checkpoint_path),
        "incremental_results": str(paths.incremental_results_path),
    }
    write_checkpoint(paths, {**run_record, "updated_at": utcnow()})
    (paths.parquet_dir / "run_record.json").write_text(json.dumps(run_record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    append_jsonl(paths.log_dir / "run_summary.jsonl", run_record)
    logging.info("Run finished: %s", json.dumps(run_record["outputs"], ensure_ascii=False))
    print(json.dumps(run_record, ensure_ascii=False, indent=2, default=str))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DRAGONS pilot variable processing.")
    parser.add_argument("--config", default="config/pipeline_config.yml")
    parser.add_argument("--run-id")
    parser.add_argument("--limit-per-source", type=int)
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--no-hf", action="store_true")
    parser.add_argument("--hf-model")
    parser.add_argument("--all-documents", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-documents", type=int)
    parser.add_argument("--stop-after", type=int)
    parser.add_argument("--sources", nargs="+")
    parser.add_argument("--shard-index", type=int)
    parser.add_argument("--shard-count", type=int)
    parser.add_argument("--input-parquet")
    parser.add_argument("--skip-existing-run-glob", action="append")
    return run_pipeline(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())

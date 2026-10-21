from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/consolidated_predictions/2026-10-19"
DIRECT = {
    "document_id": "Identificador original y clave del documento padre; permite unir resultados y atribuir fragmentos.",
    "text": "Texto completo original, sin limpieza, resumen ni truncamiento. Contenido principal para segmentar e indexar.",
    "collection_name": "Colección de origen (bluesky_posts o url_crawls). Identifica procedencia, no tema semántico.",
    "title": "Título original cuando existe; útil para contexto, búsqueda y citas. No se inventa para publicaciones sin título.",
    "url": "URL original para atribución y apertura de la fuente.",
    "source": "Canal de adquisición: bluesky, media_cloud o gdelt. Diferencia plataforma y agregadores.",
    "source_type": "Tipo declarado en origen, como social_post o news_article; se conserva nulo si falta.",
    "language": "Etiqueta original del idioma; puede contener región y errores del origen.",
    "country_key": "País registrado por el proceso de recolección; no prueba que el texto trate de ese país.",
    "created_at": "Fecha original del documento según el ETL, como texto de precisión/formato variable; no se certifica como fecha editorial.",
    "synced_at": "Fecha de sincronización del ETL; sirve para trazabilidad, no como fecha de publicación.",
    "mongo_id": "Identificador MongoDB conservado para rastrear el registro de origen.",
    "strategy": "Estrategia de adquisición, como whitelist o event_query; permite examinar sesgos de recolección.",
}
DERIVED = {
    "url_domain": ("url", "Dominio de la URL original en minúsculas; útil para filtros, diversidad de fuentes y citas."),
    "final_url": ("raw_metadata.final_url", "URL final tras la descarga. Compararla con url ayuda a revisar redirecciones; no reemplaza la URL original."),
    "language_base": ("language", "Idioma en minúsculas antes de guion/guion bajo (es-CO → es); no se vuelve a detectar el idioma."),
    "publisher": ("metadata.media_name → metadata.source_common_name → raw_metadata.source_common_name → deterministic__platform_or_outlet", "Medio o plataforma disponible, siguiendo esa prioridad. Puede ser un agregador genérico; url_domain es un filtro complementario."),
    "author_id": ("deterministic__author_id", "Identificador/valor de autor calculado en origen. Mezcla DID de Bluesky y nombres de prensa; no es una clave global de persona."),
    "author_name": ("raw_metadata.author.display_name o raw_metadata.author (cadena) → metadata.author (cadena)", "Nombre declarado del autor; útil para atribución y filtros, sin resolución de identidades."),
    "author_handle": ("raw_metadata.author.handle", "Handle de Bluesky recuperado del JSON, aunque la columna determinística de handle está vacía."),
    "uri": ("deterministic__uri", "URI original, incluidos identificadores at:// de Bluesky; útil para trazabilidad."),
    "section": ("metadata.section", "Sección editorial declarada cuando existe; filtro opcional de baja cobertura."),
    "event_id": ("metadata.event_id", "Evento de la consulta de adquisición de GDELT. No implica que el documento mencione realmente el evento."),
    "event_context": ("metadata.event", "Descripción del evento usado al recolectar; contexto auxiliar, no resumen ni tema validado del documento."),
    "keyword_family": ("metadata.keyword_family → raw_metadata.keyword_metadata.keyword_family", "Familia de palabras clave de la estrategia de adquisición; códigos del origen, no categorías inferidas."),
    "collection_keyword": ("raw_metadata.keyword_metadata.keyword", "Palabra clave usada para recolectar publicaciones; puede no aparecer en el texto final."),
    "collection_keyword_label": ("raw_metadata.keyword_metadata.keyword_label", "Descripción original de la palabra/familia de adquisición; no es una clasificación semántica validada."),
    "collection_query": ("raw_metadata.query", "Consulta original de recolección; útil para auditar el alcance y los sesgos de cobertura."),
    "keyword_matches": ("deterministic__keyword_matches", "Lista de coincidencias determinísticas del vocabulario del proyecto. Ayuda en filtros temáticos débiles; [] no significa documento inválido."),
    "top_terms": ("top_terms (JSON)", "Lista nativa de estructuras {term, count} del ETL. Apoyo léxico; puede incluir palabras vacías y no equivale a temas."),
    "word_count": ("text.split()", "Número de segmentos separados por espacios, recalculado sobre el texto exacto. Ayuda a planificar fragmentos; no cuenta tokens de un modelo."),
    "char_count": ("len(text)", "Longitud en caracteres Unicode, recalculada; útil para controlar documentos cortos o largos."),
    "text_sha256": ("SHA-256 de text codificado en UTF-8", "Huella completa del texto exacto para detectar duplicados y cambios. Se conservan documentos distintos con el mismo contenido."),
}


def present(value: object) -> bool:
    return value is not None and (bool(value.strip()) if isinstance(value, str) else bool(value))


def first_text(*values: object) -> str | None:
    return next((value for value in values if isinstance(value, str) and value.strip()), None)


def parse_object(value: str | None) -> dict:
    parsed = json.loads(value) if value else {}
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object in source metadata")
    return parsed


def domain(value: str | None) -> str | None:
    if not value:
        return None
    return urlsplit(value if "://" in value else "//" + value).hostname


def derive(row: dict) -> dict:
    metadata = parse_object(row["metadata"])
    raw = parse_object(row["raw_metadata"])
    author = raw.get("author")
    keyword = raw.get("keyword_metadata") or {}
    if not isinstance(keyword, dict):
        raise ValueError("Expected an object in keyword_metadata")
    terms = json.loads(row["top_terms"]) if row["top_terms"] else None
    if terms is not None and (
        not isinstance(terms, list)
        or any(
            not isinstance(term, dict)
            or set(term) != {"term", "count"}
            or not isinstance(term["term"], str)
            or type(term["count"]) is not int
            for term in terms
        )
    ):
        raise ValueError("Unexpected top_terms schema; refusing lossy conversion")
    text = row["text"]
    return {
        **{name: row[name] for name in DIRECT},
        "url_domain": domain(row["url"]),
        "final_url": first_text(raw.get("final_url")),
        "language_base": row["language"].strip().lower().replace("_", "-").split("-")[0] if present(row["language"]) else None,
        "publisher": first_text(metadata.get("media_name"), metadata.get("source_common_name"), raw.get("source_common_name"), row["deterministic__platform_or_outlet"]),
        "author_id": row["deterministic__author_id"],
        "author_name": first_text(author.get("display_name") if isinstance(author, dict) else author, metadata.get("author")),
        "author_handle": first_text(author.get("handle")) if isinstance(author, dict) else None,
        "uri": row["deterministic__uri"],
        "section": first_text(metadata.get("section")),
        "event_id": first_text(metadata.get("event_id")),
        "event_context": first_text(metadata.get("event")),
        "keyword_family": first_text(metadata.get("keyword_family"), keyword.get("keyword_family")),
        "collection_keyword": first_text(keyword.get("keyword")),
        "collection_keyword_label": first_text(keyword.get("keyword_label")),
        "collection_query": first_text(raw.get("query")),
        "keyword_matches": row["deterministic__keyword_matches"],
        "top_terms": terms,
        "word_count": len(text.split()),
        "char_count": len(text),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_report(path: Path, source: Path, output: Path, manifest: dict, schema: pa.Schema) -> None:
    lines = [
        "# Documentos preparados para RAG",
        "",
        f"Generado: {manifest['generated_at_utc']}.",
        f"Origen: `{source.relative_to(ROOT).as_posix()}`.",
        f"Resultado: `{output.relative_to(ROOT).as_posix()}`.",
        "",
        "## Alcance",
        "",
        f"Se conservaron **{manifest['rows']:,} documentos y {len(schema)} columnas**, una fila por documento padre, con el mismo orden e IDs del original. Texto completo sin modificar. No se eliminaron duplicados de contenido ni se filtró por resultados LLM/GLiNER.",
        "Este archivo prepara el corpus documental: no contiene embeddings, índice vectorial ni fragmentos. Las predicciones temáticas LLM y las entidades GLiNER están en otros Parquet y no se incorporaron porque este producto deriva exclusivamente de documentos_metadatos.parquet.",
        "",
        "## Diccionario de columnas",
        "",
        "Cobertura = filas con valor no nulo/no vacío. Para listas, [] cuenta como vacío. No evalúa exactitud semántica.",
        "",
        "| Columna | Tipo Parquet | Filas con valor | Procedencia | Uso y precauciones |",
        "|---|---|---:|---|---|",
    ]
    for field in schema:
        origin, description = (field.name, DIRECT[field.name]) if field.name in DIRECT else DERIVED[field.name]
        count = manifest["nonempty_counts"][field.name]
        lines.append(f"| `{field.name}` | `{field.type}` | {count:,} ({count / manifest['rows']:.1%}) | {origin} | {description} |")
    lines += ["", "## Distribución del corpus", "", "| Dimensión | Valor | Documentos |", "|---|---|---:|"]
    for name, counts in manifest["distributions"].items():
        for value, count in counts.items():
            lines.append(f"| {name} | {value} | {count:,} |")
    lines += [
        "", "## Integridad y duplicados", "",
        "- Relectura completa del Parquet y comparación de todas las columnas contra los valores exportados.",
        "- Comparación exacta de document_id, text y collection_name contra el origen; mismo orden y cantidad de filas.",
        "- IDs no vacíos y únicos; textos y colecciones no vacíos. Sin exclusiones silenciosas ni coerción de JSON inválido.",
        f"- Textos exactos distintos: {manifest['unique_texts']:,}; filas adicionales con texto repetido: {manifest['duplicate_text_rows']:,}. Las repeticiones se mantienen para conservar todas las procedencias.",
        f"- SHA-256 del resultado: `{manifest['output_sha256']}`.",
        "- El manifiesto contiguo registra hashes de origen y destino, tamaños, cobertura y validaciones.",
        "", "## Calidad y límites de interpretación", "",
        "La colección indica dónde se almacenó el documento; source indica cómo se adquirió. Ninguna de ellas es un tema. keyword_matches y top_terms son señales léxicas; keyword_family, collection_keyword y event_context describen la selección del corpus, no garantizan relevancia temática del contenido.",
        "Los idiomas y países se conservan del origen. Se observó una publicación en portugués marcada como en y registros donde country_key responde al país de la consulta. No se corrigieron ni se usaron para excluir documentos. Verificar antes de aplicar filtros estrictos.",
        "También se observó un registro de GDELT cuya URL final apunta a la portada y cuyo título no corresponde al evento de recolección. Esto demuestra que procedencia y respuesta HTTP exitosa no certifican relevancia ni calidad. Comparar texto, título y URL final al evaluar el RAG.",
        "created_at mezcla fechas sin hora y fechas con zona horaria. Se preserva como cadena para no inventar precisión ni zona; normalizar explícitamente antes de filtros cronológicos. synced_at es sincronización, no publicación.",
        "Los campos de autor son declarativos; author_id no resuelve identidades entre fuentes. publisher puede contener media_cloud o bluesky y no necesariamente un medio específico.",
        "", "## Columnas del origen omitidas", "",
        "Se revisaron las 78 columnas originales. Se conservaron directamente las del primer grupo del diccionario y se extrajeron los campos útiles indicados. Se omiten los JSON completos de metadata/raw_metadata para reducir tamaño y evitar repetir rutas internas y datos operativos. El original queda disponible para auditoría.",
        "Se omiten estados, corridas y hashes de entrada de LLM/GLiNER: describen inferencias, no la aptitud del documento para recuperación. Un fallo LLM no elimina el documento. También se omiten métricas de legibilidad, ratios, conteos repetidos, rutas internas y JSON determinísticos/ETL; word_count, char_count, top_terms y text_sha256 cubren las necesidades básicas sin duplicar el esquema.",
        "Las columnas nulas de engagement, respuesta y handle determinístico no aportan filtros en este corte. author_handle se recupera del JSON de origen. No se usa engagement_total como indicador de confiabilidad o relevancia.",
        "",
        "Columnas originales no copiadas literalmente (algunas tienen extracción o sustitución descrita arriba):",
        "",
        ", ".join(f"`{name}`" for name in manifest["source_columns_not_copied_verbatim"]) + ".",
        "", "## Uso para indexación", "",
        "1. Segmentar text según el tokenizer y el límite del modelo elegido. Conservar document_id como parent_document_id y crear chunk_id único con posición/versión. Los offsets deben referirse al text original.",
        "2. Usar el texto del fragmento y, cuando ayude, title para embeddings. Mantener colección, fuente, URLs, idioma, país, autor, fechas y señales de adquisición como metadatos; evitar añadirlos indiscriminadamente al texto vectorizado.",
        "3. Devolver document_id, collection_name, title, url y fragmento como evidencia. Heredar metadatos del padre en cada fragmento; usar las mismas restricciones al recuperar y al generar la respuesta.",
        "4. Agrupar text_sha256 repetidos al preparar el índice si se busca reducir redundancia, conservando la lista completa de IDs y procedencias. El Parquet no hace esa deduplicación por ti.",
        "5. Revisar relevancia, idioma y redirecciones sobre una muestra antes de evaluar recuperación. No tomar las etiquetas de recolección como verdad temática.",
        "", "## Reproducción", "", "```powershell", ".\\.venv\\Scripts\\python.exe scripts/export_rag_documents.py", "```", "",
        "El exportador rechaza destinos existentes. Para otro corte, indicar --source, --output y --report con rutas nuevas. El documento original no se modifica.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a document-level RAG corpus without changing source texts")
    parser.add_argument("--source", type=Path, default=BASE / "documentos_metadatos.parquet")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/rag/2026-10-19/documentos_rag.parquet")
    parser.add_argument("--report", type=Path, default=ROOT / "docs/DOCUMENTOS_RAG_2026-10-19.md")
    args = parser.parse_args()
    source, output, report = args.source.resolve(), args.output.resolve(), args.report.resolve()
    manifest_path = output.with_suffix(".manifest.json")
    for path in (output, report, manifest_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
    parquet = pq.ParquetFile(source)
    names = list(DIRECT) + ["metadata", "raw_metadata", "top_terms", "deterministic__platform_or_outlet", "deterministic__author_id", "deterministic__uri", "deterministic__keyword_matches"]
    fields = [pa.field(name, pa.string()) for name in DIRECT]
    for name in DERIVED:
        data_type = pa.string()
        if name in {"word_count", "char_count"}:
            data_type = pa.int64()
        elif name == "keyword_matches":
            data_type = pa.list_(pa.string())
        elif name == "top_terms":
            data_type = pa.list_(pa.struct([pa.field("term", pa.string()), pa.field("count", pa.int64())]))
        fields.append(pa.field(name, data_type))
    schema = pa.schema(fields, metadata={b"document_key": b"document_id", b"granularity": b"document", b"text_policy": b"original text preserved exactly; no chunking or embeddings"})
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".parquet.partial")
    if temporary.exists():
        raise FileExistsError(temporary)
    ids = set()
    text_hashes = Counter()
    nonempty = Counter()
    distributions = {name: Counter() for name in ("collection_name", "source")}
    rows = 0
    with pq.ParquetWriter(temporary, schema, compression="zstd") as writer:
        for batch in parquet.iter_batches(batch_size=2048, columns=names):
            records = []
            for row in batch.to_pylist():
                if any(not present(row[name]) for name in ("document_id", "text", "collection_name")):
                    raise ValueError("Missing required ID, text or collection")
                if row["document_id"] in ids:
                    raise ValueError(f"Duplicate document_id: {row['document_id']}")
                ids.add(row["document_id"])
                record = derive(row)
                records.append(record)
                nonempty.update(name for name, value in record.items() if present(value))
                text_hashes[record["text_sha256"]] += 1
                for name, counts in distributions.items():
                    counts[str(record[name])] += 1
            writer.write_table(pa.Table.from_pylist(records, schema=schema))
            rows += len(records)
    if rows != parquet.metadata.num_rows or rows == 0:
        raise ValueError("Unexpected output row count")
    validation_rows = 0
    source_batches = parquet.iter_batches(batch_size=2048, columns=names)
    output_batches = pq.ParquetFile(temporary).iter_batches(batch_size=2048)
    for original, actual in zip(source_batches, output_batches, strict=True):
        expected = pa.Table.from_pylist([derive(row) for row in original.to_pylist()], schema=schema)
        if not expected.equals(pa.Table.from_batches([actual]), check_metadata=False):
            raise ValueError("Parquet round-trip verification failed")
        validation_rows += actual.num_rows
    if validation_rows != rows:
        raise ValueError("Readback row count mismatch")
    temporary.rename(output)
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source.relative_to(ROOT).as_posix(),
        "source_sha256": file_hash(source),
        "output": output.relative_to(ROOT).as_posix(),
        "output_sha256": file_hash(output),
        "output_bytes": output.stat().st_size,
        "rows": rows,
        "columns": len(schema),
        "nonempty_counts": {name: nonempty[name] for name in schema.names},
        "distributions": distributions,
        "unique_texts": len(text_hashes),
        "duplicate_text_rows": rows - len(text_hashes),
        "source_columns_not_copied_verbatim": [name for name in parquet.schema_arrow.names if name not in DIRECT],
        "validation": {"all_columns_round_trip": True, "ids_unique": True, "required_fields_nonempty": True, "text_ids_collection_order_preserved": True},
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(report, source, output, manifest, schema)
    print(json.dumps({"output": str(output), "report": str(report), "rows": rows, "columns": len(schema), "bytes": output.stat().st_size, "validation": manifest["validation"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()

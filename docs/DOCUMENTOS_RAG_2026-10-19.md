# Documentos preparados para RAG

Generado: 2026-10-21T05:04:44.480181+00:00.
Origen: `data/processed/consolidated_predictions/2026-10-19/documentos_metadatos.parquet`.
Resultado: `data/processed/rag/2026-10-19/documentos_rag.parquet`.

## Alcance

Se conservaron **169,248 documentos y 33 columnas**, una fila por documento padre, con el mismo orden e IDs del original. Texto completo sin modificar. No se eliminaron duplicados de contenido ni se filtró por resultados LLM/GLiNER.
Este archivo prepara el corpus documental: no contiene embeddings, índice vectorial ni fragmentos. Las predicciones temáticas LLM y las entidades GLiNER están en otros Parquet y no se incorporaron porque este producto deriva exclusivamente de documentos_metadatos.parquet.

## Diccionario de columnas

Cobertura = filas con valor no nulo/no vacío. Para listas, [] cuenta como vacío. No evalúa exactitud semántica.

| Columna | Tipo Parquet | Filas con valor | Procedencia | Uso y precauciones |
|---|---|---:|---|---|
| `document_id` | `string` | 169,248 (100.0%) | document_id | Identificador original y clave del documento padre; permite unir resultados y atribuir fragmentos. |
| `text` | `string` | 169,248 (100.0%) | text | Texto completo original, sin limpieza, resumen ni truncamiento. Contenido principal para segmentar e indexar. |
| `collection_name` | `string` | 169,248 (100.0%) | collection_name | Colección de origen (bluesky_posts o url_crawls). Identifica procedencia, no tema semántico. |
| `title` | `string` | 104,574 (61.8%) | title | Título original cuando existe; útil para contexto, búsqueda y citas. No se inventa para publicaciones sin título. |
| `url` | `string` | 169,248 (100.0%) | url | URL original para atribución y apertura de la fuente. |
| `source` | `string` | 169,248 (100.0%) | source | Canal de adquisición: bluesky, media_cloud o gdelt. Diferencia plataforma y agregadores. |
| `source_type` | `string` | 69,922 (41.3%) | source_type | Tipo declarado en origen, como social_post o news_article; se conserva nulo si falta. |
| `language` | `string` | 156,111 (92.2%) | language | Etiqueta original del idioma; puede contener región y errores del origen. |
| `country_key` | `string` | 69,922 (41.3%) | country_key | País registrado por el proceso de recolección; no prueba que el texto trate de ese país. |
| `created_at` | `string` | 169,225 (100.0%) | created_at | Fecha original del documento según el ETL, como texto de precisión/formato variable; no se certifica como fecha editorial. |
| `synced_at` | `string` | 169,248 (100.0%) | synced_at | Fecha de sincronización del ETL; sirve para trazabilidad, no como fecha de publicación. |
| `mongo_id` | `string` | 169,248 (100.0%) | mongo_id | Identificador MongoDB conservado para rastrear el registro de origen. |
| `strategy` | `string` | 104,578 (61.8%) | strategy | Estrategia de adquisición, como whitelist o event_query; permite examinar sesgos de recolección. |
| `url_domain` | `string` | 169,248 (100.0%) | url | Dominio de la URL original en minúsculas; útil para filtros, diversidad de fuentes y citas. |
| `final_url` | `string` | 104,578 (61.8%) | raw_metadata.final_url | URL final tras la descarga. Compararla con url ayuda a revisar redirecciones; no reemplaza la URL original. |
| `language_base` | `string` | 156,111 (92.2%) | language | Idioma en minúsculas antes de guion/guion bajo (es-CO → es); no se vuelve a detectar el idioma. |
| `publisher` | `string` | 169,248 (100.0%) | metadata.media_name → metadata.source_common_name → raw_metadata.source_common_name → deterministic__platform_or_outlet | Medio o plataforma disponible, siguiendo esa prioridad. Puede ser un agregador genérico; url_domain es un filtro complementario. |
| `author_id` | `string` | 163,468 (96.6%) | deterministic__author_id | Identificador/valor de autor calculado en origen. Mezcla DID de Bluesky y nombres de prensa; no es una clave global de persona. |
| `author_name` | `string` | 155,908 (92.1%) | raw_metadata.author.display_name o raw_metadata.author (cadena) → metadata.author (cadena) | Nombre declarado del autor; útil para atribución y filtros, sin resolución de identidades. |
| `author_handle` | `string` | 64,670 (38.2%) | raw_metadata.author.handle | Handle de Bluesky recuperado del JSON, aunque la columna determinística de handle está vacía. |
| `uri` | `string` | 169,248 (100.0%) | deterministic__uri | URI original, incluidos identificadores at:// de Bluesky; útil para trazabilidad. |
| `section` | `string` | 5,252 (3.1%) | metadata.section | Sección editorial declarada cuando existe; filtro opcional de baja cobertura. |
| `event_id` | `string` | 1,198 (0.7%) | metadata.event_id | Evento de la consulta de adquisición de GDELT. No implica que el documento mencione realmente el evento. |
| `event_context` | `string` | 1,188 (0.7%) | metadata.event | Descripción del evento usado al recolectar; contexto auxiliar, no resumen ni tema validado del documento. |
| `keyword_family` | `string` | 168,040 (99.3%) | metadata.keyword_family → raw_metadata.keyword_metadata.keyword_family | Familia de palabras clave de la estrategia de adquisición; códigos del origen, no categorías inferidas. |
| `collection_keyword` | `string` | 64,660 (38.2%) | raw_metadata.keyword_metadata.keyword | Palabra clave usada para recolectar publicaciones; puede no aparecer en el texto final. |
| `collection_keyword_label` | `string` | 64,660 (38.2%) | raw_metadata.keyword_metadata.keyword_label | Descripción original de la palabra/familia de adquisición; no es una clasificación semántica validada. |
| `collection_query` | `string` | 64,670 (38.2%) | raw_metadata.query | Consulta original de recolección; útil para auditar el alcance y los sesgos de cobertura. |
| `keyword_matches` | `list<item: string>` | 107,159 (63.3%) | deterministic__keyword_matches | Lista de coincidencias determinísticas del vocabulario del proyecto. Ayuda en filtros temáticos débiles; [] no significa documento inválido. |
| `top_terms` | `list<item: struct<term: string, count: int64>>` | 169,240 (100.0%) | top_terms (JSON) | Lista nativa de estructuras {term, count} del ETL. Apoyo léxico; puede incluir palabras vacías y no equivale a temas. |
| `word_count` | `int64` | 169,248 (100.0%) | text.split() | Número de segmentos separados por espacios, recalculado sobre el texto exacto. Ayuda a planificar fragmentos; no cuenta tokens de un modelo. |
| `char_count` | `int64` | 169,248 (100.0%) | len(text) | Longitud en caracteres Unicode, recalculada; útil para controlar documentos cortos o largos. |
| `text_sha256` | `string` | 169,248 (100.0%) | SHA-256 de text codificado en UTF-8 | Huella completa del texto exacto para detectar duplicados y cambios. Se conservan documentos distintos con el mismo contenido. |

## Distribución del corpus

| Dimensión | Valor | Documentos |
|---|---|---:|
| collection_name | bluesky_posts | 64,670 |
| collection_name | url_crawls | 104,578 |
| source | bluesky | 64,670 |
| source | media_cloud | 103,380 |
| source | gdelt | 1,198 |

## Integridad y duplicados

- Relectura completa del Parquet y comparación de todas las columnas contra los valores exportados.
- Comparación exacta de document_id, text y collection_name contra el origen; mismo orden y cantidad de filas.
- IDs no vacíos y únicos; textos y colecciones no vacíos. Sin exclusiones silenciosas ni coerción de JSON inválido.
- Textos exactos distintos: 154,477; filas adicionales con texto repetido: 14,771. Las repeticiones se mantienen para conservar todas las procedencias.
- SHA-256 del resultado: `f4a669f17eaedd357f72b70c2192e685b6d534a94f6ffaeadbced7290b181728`.
- El manifiesto contiguo registra hashes de origen y destino, tamaños, cobertura y validaciones.

## Calidad y límites de interpretación

La colección indica dónde se almacenó el documento; source indica cómo se adquirió. Ninguna de ellas es un tema. keyword_matches y top_terms son señales léxicas; keyword_family, collection_keyword y event_context describen la selección del corpus, no garantizan relevancia temática del contenido.
Los idiomas y países se conservan del origen. Se observó una publicación en portugués marcada como en y registros donde country_key responde al país de la consulta. No se corrigieron ni se usaron para excluir documentos. Verificar antes de aplicar filtros estrictos.
También se observó un registro de GDELT cuya URL final apunta a la portada y cuyo título no corresponde al evento de recolección. Esto demuestra que procedencia y respuesta HTTP exitosa no certifican relevancia ni calidad. Comparar texto, título y URL final al evaluar el RAG.
created_at mezcla fechas sin hora y fechas con zona horaria. Se preserva como cadena para no inventar precisión ni zona; normalizar explícitamente antes de filtros cronológicos. synced_at es sincronización, no publicación.
Los campos de autor son declarativos; author_id no resuelve identidades entre fuentes. publisher puede contener media_cloud o bluesky y no necesariamente un medio específico.

## Columnas del origen omitidas

Se revisaron las 78 columnas originales. Se conservaron directamente las del primer grupo del diccionario y se extrajeron los campos útiles indicados. Se omiten los JSON completos de metadata/raw_metadata para reducir tamaño y evitar repetir rutas internas y datos operativos. El original queda disponible para auditoría.
Se omiten estados, corridas y hashes de entrada de LLM/GLiNER: describen inferencias, no la aptitud del documento para recuperación. Un fallo LLM no elimina el documento. También se omiten métricas de legibilidad, ratios, conteos repetidos, rutas internas y JSON determinísticos/ETL; word_count, char_count, top_terms y text_sha256 cubren las necesidades básicas sin duplicar el esquema.
Las columnas nulas de engagement, respuesta y handle determinístico no aportan filtros en este corte. author_handle se recupera del JSON de origen. No se usa engagement_total como indicador de confiabilidad o relevancia.

Columnas originales no copiadas literalmente (algunas tienen extracción o sustitución descrita arriba):

`avg_sentence_words`, `avg_word_length`, `char_count`, `char_count_no_spaces`, `deterministic__author_handle`, `deterministic__author_id`, `deterministic__deterministic_computed_at`, `deterministic__engagement_like_count`, `deterministic__engagement_quote_count`, `deterministic__engagement_reply_count`, `deterministic__engagement_repost_count`, `deterministic__engagement_total`, `deterministic__has_title`, `deterministic__keyword_match_count`, `deterministic__keyword_matches`, `deterministic__keyword_relevance_proxy`, `deterministic__metadata_keys`, `deterministic__platform_or_outlet`, `deterministic__reply_parent_uri`, `deterministic__reply_root_uri`, `deterministic__source_type_normalized`, `deterministic__text_char_count_runtime`, `deterministic__text_hash`, `deterministic__text_word_count_runtime`, `deterministic__title_hash`, `deterministic__uri`, `deterministic_variables_json`, `digit_count`, `documents_origin_path`, `etl__char_count`, `etl__lexical_density_proxy`, `etl__paragraph_count`, `etl__sentence_count`, `etl__top_terms`, `etl__word_count`, `etl_metrics_json`, `gliner_input_text`, `gliner_input_text_hash`, `gliner_run_id`, `gliner_status`, `hapax_count`, `hapax_ratio`, `input_text_hash`, `lexical_density_proxy`, `llm_input_text_hash`, `llm_run_id`, `llm_status`, `long_word_count`, `long_word_ratio`, `metadata`, `paragraph_count`, `punctuation_count`, `raw_metadata`, `readability_flesch_proxy`, `sentence_count`, `stopword_count`, `stopword_ratio`, `suffix_counts`, `syllable_estimate`, `titlecase_word_count`, `top_terms`, `type_token_ratio`, `unique_word_count`, `uppercase_word_count`, `word_count`.

## Uso para indexación

1. Segmentar text según el tokenizer y el límite del modelo elegido. Conservar document_id como parent_document_id y crear chunk_id único con posición/versión. Los offsets deben referirse al text original.
2. Usar el texto del fragmento y, cuando ayude, title para embeddings. Mantener colección, fuente, URLs, idioma, país, autor, fechas y señales de adquisición como metadatos; evitar añadirlos indiscriminadamente al texto vectorizado.
3. Devolver document_id, collection_name, title, url y fragmento como evidencia. Heredar metadatos del padre en cada fragmento; usar las mismas restricciones al recuperar y al generar la respuesta.
4. Agrupar text_sha256 repetidos al preparar el índice si se busca reducir redundancia, conservando la lista completa de IDs y procedencias. El Parquet no hace esa deduplicación por ti.
5. Revisar relevancia, idioma y redirecciones sobre una muestra antes de evaluar recuperación. No tomar las etiquetas de recolección como verdad temática.

## Reproducción

```powershell
.\.venv\Scripts\python.exe scripts/export_rag_documents.py
```

El exportador rechaza destinos existentes. Para otro corte, indicar --source, --output y --report con rutas nuevas. El documento original no se modifica.

# Resultado piloto 100 por fuente

Run id: `pilot_100_deepseek_full`  
Fecha de ejecucion: 2026-10-02  
Modelo LLM usado: `deepseek-chat` via DeepSeek API  

## Alcance ejecutado

Se procesaron 300 documentos:

| Fuente | Documentos |
|---|---:|
| `media_cloud` | 100 |
| `gdelt` | 100 |
| `bluesky` | 100 |

Estado LLM:

| Estado | Documentos |
|---|---:|
| `success` | 300 |

## Variables calculadas

### ETL existentes

- `char_count`
- `word_count`
- `sentence_count`
- `paragraph_count`
- `lexical_density_proxy`
- `top_terms`

### Deterministicas

- `text_hash`
- `title_hash`
- `text_char_count_runtime`
- `text_word_count_runtime`
- `keyword_matches`
- `keyword_match_count`
- `keyword_relevance_proxy`
- `source_type_normalized`
- `platform_or_outlet`
- `author_id`
- `author_handle`
- `uri`
- `reply_parent_uri`
- `reply_root_uri`
- `engagement_like_count`
- `engagement_reply_count`
- `engagement_repost_count`
- `engagement_quote_count`
- `engagement_total`

### LLM

- `is_relevant_biodiversity`
- `relevance_score`
- `primary_topic`
- `subtopic`
- `sentiment_label`
- `emotion_labels`
- `emotional_intensity`
- `narrative_label`
- `narrative_summary`
- `dominant_frame`
- `discursive_pattern`
- `actors`
- `responsibility_actor`
- `agency_actor`
- `blame_actor`
- `proposed_action`
- `claim_typology`
- `marginalised_frame_candidate`
- `confidence`
- `quality_flags`

### SNA

- `bluesky_author_reply_network`
- nodos, aristas, componentes, PageRank, degree, in-degree, out-degree.

En esta muestra el grafo de respuestas Bluesky tuvo `53` nodos y `0` aristas, porque no hubo relaciones reply dentro de la muestra de 100 posts seleccionada.

## Resultados rapidos

| Indicador | Valor |
|---|---:|
| Filas Parquet | 300 |
| Filas MongoDB | 300 |
| Filas PostgreSQL | 300 |
| Runs MongoDB | 1 |
| Runs PostgreSQL | 1 |

Distribucion de sentimiento:

| Sentiment | Documentos |
|---|---:|
| `neutral` | 110 |
| `negative` | 66 |
| `positive` | 62 |
| `mixed` | 38 |
| `unclear` | 24 |

Relevancia biodiversidad:

| Valor | Documentos |
|---|---:|
| `True` | 167 |
| `False` | 133 |

## Salidas generadas

Locales:

```text
data/processed/pilot_variables/pilot_100_deepseek_full/
  analytics_variable_results_flat.parquet
  analytics_variable_results_flat.csv
  analytics_variable_results_raw_json.parquet
  run_record.json
  sna_summary.json
```

Logs:

```text
logs/variable_processing/pilot_100_deepseek_full/
  run.log
  documents.jsonl
  variables.jsonl
  errors.jsonl
  run_summary.jsonl
```

MongoDB:

```text
database: dragons
collection results: analytics_variable_results_pilot
collection runs: analytics_variable_runs
run_id: pilot_100_deepseek_full
```

PostgreSQL:

```text
schema: public
table results: analytics_variable_results_pilot
table runs: analytics_variable_runs
run_id: pilot_100_deepseek_full
```

## Nota operativa

MongoDB ya estaba activo en `localhost:50030`. PostgreSQL no estaba activo inicialmente en `localhost:50020`; se levanto desde el stack `dragons_project_nlp` con WSL/Docker y despues se sincronizo el run existente sin recalcular LLM.

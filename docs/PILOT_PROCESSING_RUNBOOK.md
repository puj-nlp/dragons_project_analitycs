# Runbook del piloto de procesamiento

## Objetivo

Calcular variables analiticas sobre una muestra controlada de 100 documentos por fuente (`media_cloud`, `gdelt`, `bluesky`) y generar salidas verificables en:

- Parquet/CSV local.
- MongoDB, coleccion `analytics_variable_results_pilot`.
- PostgreSQL, tabla `public.analytics_variable_results_pilot`, si el servicio esta disponible.
- Logs JSONL por documento, variable y error.

## Comando

```powershell
C:\ProgramData\anaconda3\python.exe scripts\run_pilot_processing.py --limit-per-source 100
```

Para probar sin LLM:

```powershell
C:\ProgramData\anaconda3\python.exe scripts\run_pilot_processing.py --limit-per-source 5 --no-llm
```

## Variables calculadas

### ETL existentes

- `char_count`
- `word_count`
- `sentence_count`
- `paragraph_count`
- `lexical_density_proxy`
- `top_terms`

### Deterministicas del piloto

- `text_hash`
- `keyword_matches`
- `keyword_match_count`
- `keyword_relevance_proxy`
- `source_type_normalized`
- `platform_or_outlet`
- `author_id`
- `uri`
- `reply_parent_uri`
- `reply_root_uri`
- `engagement_like_count`
- `engagement_reply_count`
- `engagement_repost_count`
- `engagement_quote_count`
- `engagement_total`

### LLM con DeepSeek y fallback OpenAI

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

### SNA con networkx

- `bluesky_author_reply_network`
- nodos, aristas, componentes, PageRank, degree, in-degree, out-degree.

## Logs

Cada corrida crea:

```text
logs/variable_processing/<run_id>/
  run.log
  documents.jsonl
  variables.jsonl
  errors.jsonl
  run_summary.jsonl
```

## Salidas locales

```text
data/processed/pilot_variables/<run_id>/
  analytics_variable_results_flat.parquet
  analytics_variable_results_flat.csv
  analytics_variable_results_raw_json.parquet
  run_record.json
  sna_summary.json
```

## Notas de interpretacion

El campo de amplificacion se limita a proxies observables de engagement y red. No se debe afirmar causalidad algoritmica ni mecanismos internos de recomendacion.

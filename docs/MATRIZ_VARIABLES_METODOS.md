# Matriz de variables y metodos

## Lectura rapida

| Grupo | Variable | Metodo recomendado | Herramienta | Nivel | Observacion |
|---|---|---|---|---|---|
| Corpus | cobertura por fuente/pais/idioma/tiempo | deterministico | pandas | 1 | Antes de cualquier inferencia |
| Corpus | duplicados y texto vacio | deterministico | pandas/hash | 1 | Control de calidad |
| Texto | word_count, lexical_density, top_terms | existente ETL | `src/text_metrics.py` ETL | 1 | No usar LLM |
| Texto | keywords y n-grams | libreria | sklearn/pandas | 1 | Multilingue con normalizacion |
| Texto | embeddings | modelo local/HF | sentence-transformers | 1/2 | Para clustering y similitud |
| Texto | topic clusters | libreria + modelo | BERTopic/HDBSCAN o sklearn | 1/2 | LLM puede titular clusters |
| Relevancia | biodiversidad relevante | LLM o clasificador entrenado | prompt JSON / HF | 1 | Validar por muestra |
| Narrativa | narrative label | LLM + clustering | prompt JSON | 1 | Taxonomia inductiva o mixta |
| Framing | dominant framing | LLM + validacion humana | prompt JSON | 1 | Compromiso base |
| Framing | marginalised/counter framing | LLM + validacion humana | prompt JSON | 2 | Solo si corpus diverso |
| Sentiment | positivo/neutral/negativo | LLM o HF | prompt/HF | 1 | Validar por idioma |
| Emociones | miedo/ira/tristeza/esperanza/confianza/preocupacion | LLM o HF | prompt/HF | 2 | Taxonomia corta |
| Actores | entidades nombradas | modelo local/HF | spaCy/Stanza/HF | 1 | LLM solo para corregir/rol |
| Actores | responsabilidad/agencia/blame | LLM | prompt JSON | 1 | Juicio semantico |
| Claims | claim extraction | LLM | prompt JSON | 2 | Mejor por afirmacion, no solo documento |
| Claims | claim_type/verifiability/evidence | LLM | prompt JSON | 2 | No es fact-checking |
| Temporal | volumen y cambios | deterministico | pandas/statsmodels | 1/2 | Requiere cobertura homologada |
| Geografico | pais/fuente/idioma | metadatos | pandas | 1/2 | No inferir residencia personal |
| SNA | red autor-respuesta/quote | red | networkx | 2 | Bluesky tiene URIs y reply roots |
| SNA | centralidad de actores | red | networkx | 2 | Interpretar como visibilidad observable |
| SNA | red documento-documento por similitud | embeddings + red | sentence-transformers/networkx | 2 | Umbral documentado |
| Amplificacion | engagement relativo | deterministico | pandas/networkx | 3 | Proxy, no algoritmo |
| Desinformacion | verdadero/falso/desinformacion | fact-checking externo | no MVP | 3 | No comprometer |
| Algoritmico | ranking/recomendacion causal | datos internos | no viable | 4 | Documentar limitacion |

## Variables de Nivel 1 para compromiso base

1. `is_relevant_biodiversity`
2. `primary_topic`
3. `keyword_family`
4. `sentiment_label`
5. `narrative_label`
6. `dominant_frame`
7. `discursive_pattern`
8. `actor_mentions`
9. `responsibility_actor`
10. `agency_actor`
11. `proposed_action`
12. `source_country_language_time` comparables

## Variables de Nivel 2 para priorizar

1. `emotion_labels`
2. `emotional_intensity`
3. `marginalised_frame_candidate`
4. `counter_narrative_candidate`
5. `claim_type`
6. `verifiability`
7. `evidence_presence`
8. `engagement_proxy`
9. `network_centrality`
10. `event_window_change`

## Variables fuera de compromiso actual

1. `is_disinformation`
2. `is_misinformation`
3. `algorithmic_amplification_causal`
4. `echo_chamber_membership`
5. `filter_bubble_exposure`
6. `user_identity_group_inferred`

## Modelo de validacion

Cada variable interpretativa debe tener:

- Definicion operacional.
- Valores permitidos.
- Ejemplos positivos y negativos.
- Fuente de calculo.
- Riesgos por idioma.
- Muestra validada.
- Metrica de calidad.
- Decision de escalamiento.

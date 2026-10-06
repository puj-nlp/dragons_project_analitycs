# LLM Document Annotation v1

Este es el prompt usado por `scripts/run_pilot_processing.py` para calcular las variables LLM del piloto `pilot_100_deepseek_full`.

En la corrida piloto, el prompt se construyo dentro de la funcion:

```text
scripts/run_pilot_processing.py
function: llm_prompt(row, deterministic, max_chars)
```

## System Message

```text
You are an analytical coding assistant for the DRAGONS biodiversity discourse project. Return only valid JSON. Do not classify truth/falsity or disinformation. If evidence is insufficient, use unclear or null.
```

## User Message Template

El mensaje de usuario se envia como JSON con esta estructura:

```json
{
  "task": "Annotate one document for discourse variables.",
  "allowed_values": {
    "sentiment_label": [
      "mixed",
      "negative",
      "neutral",
      "positive",
      "unclear"
    ],
    "emotion_labels": [
      "anger",
      "concern",
      "fear",
      "hope",
      "none",
      "pride",
      "sadness",
      "trust",
      "unclear"
    ],
    "claim_type": [
      "factual_claim",
      "opinion",
      "interpretation",
      "value_judgment",
      "prediction",
      "testimony",
      "mixed_claim",
      "unclear"
    ],
    "verifiability": [
      "directly_verifiable",
      "verifiable_with_external_evidence",
      "difficult_to_verify",
      "not_factually_verifiable",
      "insufficient_context",
      "unclear"
    ],
    "evidence_presence": [
      "explicit_evidence",
      "source_mentioned",
      "testimony_only",
      "no_evidence_presented",
      "not_applicable",
      "unclear"
    ],
    "evidence_type": [
      "data_or_statistics",
      "expert_source",
      "official_document",
      "eyewitness_or_testimony",
      "anecdotal",
      "no_evidence",
      "unclear"
    ],
    "solution_orientation": [
      "problem_only",
      "proposes_solution",
      "evaluates_solution",
      "calls_for_action",
      "unclear"
    ],
    "uncertainty_signal": [
      "high_uncertainty",
      "moderate_uncertainty",
      "low_uncertainty",
      "no_uncertainty_signal",
      "unclear"
    ]
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
      "problem_definition": "short string or null",
      "cause": "short string or null",
      "consequence": "short string or null",
      "solution": "short string or null"
    },
    "discursive_pattern": "short string",
    "actors": [
      {
        "text": "string",
        "role": "responsibility|agency|blame|affected|expert|other"
      }
    ],
    "stakeholder_presence": {
      "government_present": "boolean",
      "community_present": "boolean",
      "ngo_present": "boolean",
      "private_sector_present": "boolean",
      "science_present": "boolean",
      "media_present": "boolean",
      "evidence": "short string or null"
    },
    "biodiversity_object": {
      "species_mentions": "list of strings",
      "ecosystem_mentions": "list of strings",
      "protected_area_mentions": "list of strings",
      "biodiversity_concepts": "list of strings"
    },
    "responsibility_actor": "string or null",
    "agency_actor": "string or null",
    "blame_actor": "string or null",
    "proposed_action": "string or null",
    "governance_policy_mentions": {
      "policy_mentions": "list of strings",
      "institution_mentions": "list of strings",
      "regulation_or_commitment": "short string or null",
      "implementation_gap": "short string or null"
    },
    "claim_typology": {
      "main_claim": "short string or null",
      "claim_type": "allowed value",
      "verifiability": "allowed value",
      "evidence_presence": "allowed value",
      "evidence_type": "allowed value",
      "source_attribution": "string or null"
    },
    "solution_orientation": "allowed value",
    "justice_equity_signal": {
      "is_present": "boolean",
      "affected_group": "short string or null",
      "equity_dimension": "short string or null",
      "evidence_span": "short string or null"
    },
    "uncertainty_signal": "allowed value",
    "conflict_polarization_signal": {
      "is_conflict_present": "boolean",
      "conflict_axis": "short string or null",
      "actors_in_conflict": "list of strings",
      "evidence_span": "short string or null"
    },
    "marginalised_frame_candidate": {
      "is_candidate": "boolean",
      "reason": "short string or null"
    },
    "confidence": "number 0..1",
    "quality_flags": "list of short strings"
  },
  "metadata": {
    "document_id": "<document_id>",
    "source": "<source>",
    "language": "<language>",
    "country_key": "<country_key>",
    "created_at": "<created_at>",
    "keyword_matches": []
  },
  "title": "<title>",
  "text": "<text truncated to max_text_chars_for_llm>"
}
```

## Modelo Usado En El Piloto

```yaml
provider: deepseek
endpoint: https://api.deepseek.com/chat/completions
model: deepseek-chat
temperature: 0.0
response_format:
  type: json_object
max_text_chars_for_llm: 4500
fallback_provider: openai
fallback_model: gpt-4o-mini
```

## Variables Calculadas Con Este Prompt

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
- `stakeholder_presence`
- `biodiversity_object`
- `responsibility_actor`
- `agency_actor`
- `blame_actor`
- `proposed_action`
- `governance_policy_mentions`
- `claim_typology`
- `solution_orientation`
- `justice_equity_signal`
- `uncertainty_signal`
- `conflict_polarization_signal`
- `marginalised_frame_candidate`
- `confidence`
- `quality_flags`

## Variables HF/GLiNER Agregadas

Antes o en paralelo al prompt LLM, el pipeline puede ejecutar GLiNER desde Hugging Face para extraer entidades abiertas:

```yaml
library: gliner2
default_model: fastino/gliner2.5-multi-v1
smoke_test_model: fastino/gliner2.5-small-v1
fallback_legacy_model: urchade/gliner_multi-v2.1
labels:
  - person
  - organization
  - government institution
  - media outlet
  - civil society organization
  - indigenous or local community
  - scientific institution
  - company
  - location
  - country
  - biodiversity concept
  - species
  - ecosystem
  - protected area
  - policy or law
  - event
  - date
  - funding or money
  - risk or threat
  - proposed action
outputs:
  - gliner_named_entities
  - gliner_entity_counts_by_label
  - gliner_top_entity_labels
```

## Importante

Este prompt no clasifica verdad/falsedad ni desinformacion. Para claims solo calcula tipo de afirmacion, verificabilidad y presencia de evidencia textual.

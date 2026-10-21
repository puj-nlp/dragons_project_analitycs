# LLM Document Annotation v2

Prompt operativo para variables interpretativas de DRAGONS Task 1.1.

## Proposito

Anotar documentos de medios y redes sociales sobre discurso de biodiversidad. El modelo debe producir solo JSON valido y debe tratar sus salidas como estimaciones analiticas sujetas a validacion humana.

## Contexto Metodologico

- Unidad de analisis: un documento.
- Fuentes: `media_cloud`, `gdelt`, `bluesky`.
- Insumos: titulo, texto, metadatos, variables deterministicas y entidades GLiNER.
- No usar conocimiento externo.
- No clasificar verdad/falsedad.
- No clasificar desinformacion, misinformation o misleading.
- No inferir amplificacion algoritmica, ranking, recomendacion, echo chambers o filter bubbles.
- No inferir atributos personales sensibles ni identidad de actores si no aparece explicitamente.
- Usar `unclear`, `null`, `false` o listas vacias cuando no haya evidencia suficiente.

## Reglas Por Fuente

- `media_cloud`: normalmente noticias. Distinguir framing periodistico de citas de actores cuando sea posible.
- `gdelt`: noticias asociadas a eventos. El evento es contexto de metadatos; codificar solo lo que el texto soporte.
- `bluesky`: publicacion social. Codificar texto visible y metadatos suministrados; no inferir respuesta de audiencia salvo conteos observables.

## Definiciones Operacionales

- `is_relevant_biodiversity`: verdadero solo si biodiversidad, conservacion, ecosistemas, especies, habitat, restauracion, gobernanza de naturaleza o politica de biodiversidad son sustantivos.
- `relevance_score`: 0 sin relevancia; 1 si biodiversidad es central.
- `sentiment_label`: tono evaluativo hacia el tema, actor o politica central. Negativo puede significar preocupacion por perdida de biodiversidad, no oposicion a una politica.
- `emotion_labels`: senales emocionales expresadas en el texto, no emociones inferidas de la audiencia.
- `narrative_label`: narrativa candidata que relaciona actores, problema, causa/valor y futuro deseado.
- `dominant_frame`: marco interpretativo central: problema, causa, consecuencia, solucion o juicio moral.
- `actors`: actores explicitamente mencionados o soportados por entidades GLiNER; el rol requiere evidencia textual.
- `claim_typology`: clasificar forma y evidencia del claim principal, sin verificar verdad.
- `solution_orientation`: problema solo, propone solucion, evalua solucion o llamado a la accion.
- `justice_equity_signal`: derechos, equidad, participacion, comunidades afectadas o distribucion desigual de costos/beneficios.
- `uncertainty_signal`: incertidumbre explicita, falta de evidencia, controversia tecnica o necesidad de mas datos.
- `conflict_polarization_signal`: conflicto explicito entre actores, valores o intereses; no inferir polarizacion por simple desacuerdo.
- `marginalised_frame_candidate`: perspectiva menos dominante solo si el texto la presenta.

## Variables De Salida

El JSON debe incluir el esquema usado por `scripts/run_pilot_processing.py`: relevancia, tema, sentimiento, emociones, narrativa, `dominant_frame`, `framing_analysis`, actores, stakeholders, objeto biodiverso, gobernanza, claims, solucion, justicia/equidad, incertidumbre, conflicto, frame marginalizado, confianza y `quality_flags`.

## Control De Calidad

Agregar `quality_flags` cuando aplique:

- `short_text`
- `low_biodiversity_relevance`
- `metadata_only`
- `unclear_language`
- `noisy_text`
- `insufficient_context`
- `possible_duplicate`
- `entity_evidence_weak`

## Implementacion

La version activa esta embebida en:

```text
scripts/run_pilot_processing.py
llm_prompt(row, deterministic, max_chars, hf_data)
```


# Reporte de variables, modelos, indicadores y entidades DRAGONS

Fecha: 2026-10-06  
Estado: propuesta operativa para validacion con `Cooreo_1_pabla.pdf` y muestra piloto de 300 documentos.

## 1. Decision metodologica

El pipeline final debe separar cuatro tipos de calculo:

1. **Variables deterministicas / ETL:** se calculan con reglas, metadatos, pandas y metricas textuales existentes. No requieren LLM.
2. **Variables Hugging Face / GLiNER:** se calculan con modelos locales o descargados de Hugging Face, principalmente para entidades nombradas y conceptos abiertos.
3. **Variables LLM:** se calculan con prompt JSON cuando se requiere juicio semantico, interpretacion discursiva o clasificacion contextual.
4. **Variables SNA:** se calculan con `networkx` sobre relaciones observables, especialmente en Bluesky.

Regla central: **no usar LLM para conteos, fechas, hashes, cobertura, textometria o redes**. El LLM se reserva para tareas interpretativas donde una regla o un modelo NER no capturan el sentido discursivo.

## Variables analiticas finales compuestas

La unidad final de analisis no es "una variable = una herramienta". El resultado final sera una **bateria de variables compuestas**, donde cada variable integra varias senales: metadatos, textometria, entidades GLiNER2.5, clasificacion LLM, reglas y redes.

| Variable final compuesta | Pregunta que responde | Componentes que combina | Metodo final |
|---|---|---|---|
| `corpus_profile` | Que cobertura real tiene el corpus? | fuente, pais, idioma, fecha, longitud, texto vacio, duplicados, metadatos | ETL + pandas + reglas |
| `document_quality_profile` | El documento sirve para analisis discursivo? | longitud, idioma, texto limpio, OCR si aplica, flags de calidad, campos faltantes | ETL + reglas + LLM solo para flags semanticos |
| `biodiversity_relevance_profile` | El documento realmente trata biodiversidad? | keywords, entidades biodiversas, tema LLM, relevancia LLM, evidencia textual | reglas + GLiNER2.5 + LLM |
| `biodiversity_object_profile` | Sobre que objeto biodiverso habla? | especies, ecosistemas, areas protegidas, conceptos, tema/subtema | GLiNER2.5 + LLM |
| `actor_stakeholder_profile` | Que actores aparecen y que tipo de actor son? | personas, organizaciones, gobierno, ciencia, comunidad, empresa, medios | GLiNER2.5 + reglas + LLM |
| `actor_role_profile` | Que papel discursivo tiene cada actor? | entidades actorales, responsabilidad, agencia, culpa, afectacion, experticia | GLiNER2.5 + LLM |
| `governance_policy_profile` | Que instituciones, politicas o compromisos aparecen? | instituciones, leyes, politicas, compromisos, brechas de implementacion | GLiNER2.5 + LLM |
| `narrative_frame_profile` | Que narrativa y frame domina? | tema, narrativa, definicion del problema, causa, consecuencia, solucion | LLM + clustering posterior |
| `emotion_sentiment_profile` | Que tono emocional expresa el texto? | sentimiento, emociones, intensidad, polaridad contextual | LLM o modelo HF + validacion humana |
| `claim_evidence_profile` | Que tipo de afirmacion y evidencia presenta? | claim principal, tipo de claim, verificabilidad, presencia/tipo de evidencia, atribucion | LLM; no fact-checking |
| `solution_action_profile` | El texto propone acciones o solo describe problemas? | acciones propuestas, orientacion a solucion, llamado a la accion, actores de agencia | GLiNER2.5 + LLM |
| `justice_equity_profile` | Aparecen justicia, derechos, participacion o afectaciones desiguales? | comunidades, grupos afectados, dimension de equidad, evidencia textual | GLiNER2.5 + LLM |
| `uncertainty_risk_profile` | El texto expresa riesgo, amenaza o incertidumbre? | riesgos GLiNER2.5, incertidumbre LLM, falta de datos, necesidades de monitoreo | GLiNER2.5 + LLM |
| `conflict_profile` | Hay conflicto entre actores, valores o intereses? | actores, eje de conflicto, evidencia, emociones, frame dominante | GLiNER2.5 + LLM |
| `engagement_visibility_profile` | Que visibilidad/interaccion observable tiene? | likes, replies, reposts, quotes, fuente, fecha, frame, emociones, entidades | metadatos + pandas; no causalidad algoritmica |
| `network_position_profile` | Que posicion ocupan actores/documentos en redes observables? | autores, replies, quotes, entidades co-ocurrentes, frames, centralidad | networkx + GLiNER2.5 + LLM |
| `comparative_country_source_profile` | Como cambian temas, actores y frames por pais/fuente/idioma? | pais, fuente, idioma, relevancia, frames, entidades, emociones, engagement | pandas + GLiNER2.5 + LLM |
| `temporal_event_profile` | Como cambian temas/frames alrededor de eventos? | fecha, evento, volumen, entidades, narrativas, frames, engagement | pandas + GLiNER2.5 + LLM |

Estas variables compuestas son las que deben aparecer en reportes y tableros. Las salidas individuales (`gliner_named_entities`, `dominant_frame`, `engagement_total`, etc.) son **componentes intermedios trazables** para construirlas, auditarlas y validarlas.

## 2. Prueba obligatoria antes de escalar

Cada cambio relevante del pipeline debe probarse con:

- **Correo 1 de Pabla:** `temp/resource_index_page/Cooreo_1_pabla.pdf`
  - Objetivo: validar OCR, extraccion de texto, entidades, personas, instituciones y menciones metodologicas.
  - Script: `py scripts\analyze_variables.py --hf-model fastino/gliner2.5-small-v1`
  - Criterio minimo: OCR produce texto no vacio y GLiNER devuelve entidades con `hf_metadata.status = success`.

- **Muestra piloto de 300 documentos:** 100 Media Cloud, 100 GDELT, 100 Bluesky.
  - Script rapido sin LLM: `py scripts\run_pilot_processing.py --run-id pilot_300_gliner25_small_no_llm --limit-per-source 100 --no-llm --hf-model fastino/gliner2.5-small-v1`
  - Criterio minimo: 300 filas, `hf_metadata.status = success` en todos o casi todos los documentos, salidas parquet/CSV generadas.

- **Muestra LLM acotada:** 3 a 15 documentos antes de correr 300 con LLM.
  - Objetivo: validar costo, formato JSON, campos nuevos y categorias fuera de taxonomia.
  - Criterio minimo: JSON valido, sin clasificar verdad/falsedad ni desinformacion.

## 3. Modelos Hugging Face priorizados

### Modelo principal para entidades

- **Modelo:** `fastino/gliner2.5-multi-v1`
- **Uso:** NER abierto multilingue para espanol, ingles y hungaro.
- **Ventaja:** GLiNER2.5 usa arquitectura boundary, soporta entidades, clasificacion, records, relaciones y atributos de span en una misma familia de modelos.
- **Carga local:** `from gliner2 import AutoExtractor`; `AutoExtractor.from_pretrained("fastino/gliner2.5-multi-v1")`.
- **Uso recomendado:** modelo principal para la corrida multilingue final.
- **Fallback:** `urchade/gliner_multi-v2.1` queda como modelo legacy si GLiNER2.5 no descarga o no corre en el ambiente.

### Modelo de prueba rapida

- **Modelo:** `fastino/gliner2.5-small-v1`
- **Uso:** smoke tests, validacion de pipeline, pruebas cortas y PDF de Pabla cuando se quiera ahorrar tiempo.
- **Limitacion:** modelo pequeno orientado a rapidez; para resultados finales multilingues usar `fastino/gliner2.5-multi-v1`.

### Candidato emergente

- **Modelo/familia:** variantes especializadas de GLiNER2.5, por ejemplo long-context, span attributes o classification.
- **Uso potencial:** extraccion multilingue y esquemas mas amplios.
- **Estado:** candidato de investigacion, no integrado todavia al pipeline operativo.

## 4. Variables deterministicas y ETL

| Variable / indicador | Unidad | Metodo | Salida final | Validacion |
|---|---:|---|---|---|
| `document_id`, `source`, `collection_name` | documento | metadatos | identificadores trazables | unicidad y no nulos |
| `country_key`, `language`, `created_at` | documento | metadatos | pais/idioma/fecha | cobertura y formatos |
| `source_type_normalized` | documento | regla | `news`, `social_post`, `email`, etc. | revision de categorias |
| `platform_or_outlet` | documento | metadatos + regla | medio/plataforma/autor observable | spot check |
| `text_hash`, `title_hash` | documento | SHA-256 corto | hashes reproducibles | duplicados |
| `text_char_count_runtime` | documento | regla | caracteres | comparacion con ETL |
| `text_word_count_runtime` | documento | regla | palabras | comparacion con ETL |
| `char_count`, `word_count`, `sentence_count`, `paragraph_count` | documento | ETL existente | textometria base | spot check |
| `lexical_density_proxy` | documento | ETL existente | proxy numerico | spot check |
| `top_terms` | documento | ETL existente | terminos frecuentes | revision por idioma |
| `keyword_matches` | documento | diccionario biodiversidad | lista de terminos | revision de falsos positivos |
| `keyword_match_count` | documento | conteo | numero | consistencia |
| `keyword_relevance_proxy` | documento | regla | 0..1 | comparacion con relevancia LLM |
| `engagement_like_count`, `reply`, `repost`, `quote` | documento social | metadatos | conteos | faltantes por plataforma |
| `engagement_total` | documento social | suma | total observable | consistencia |
| `metadata_keys` | documento | parseo JSON | campos presentes | auditoria de cobertura |

Indicadores agregados derivados:

- Conteo de documentos por fuente, pais, idioma y ventana temporal.
- Porcentaje de documentos con texto vacio o insuficiente.
- Distribucion de longitud textual por fuente.
- Tasa de documentos con keywords de biodiversidad.
- Duplicados exactos o casi exactos por hash.
- Cobertura de engagement por fuente social.
- Ranking de medios/plataformas por volumen documental.

## 5. Variables Hugging Face / GLiNER

GLiNER se usa para extraer entidades y conceptos desde el texto, en segmentos con solapamiento para documentos largos.

### Variables de salida

| Variable | Unidad | Metodo | Salida |
|---|---:|---|---|
| `gliner_named_entities` | documento | GLiNER | lista de entidades con texto, etiqueta, score, start, end |
| `gliner_entity_counts_by_label` | documento | GLiNER + conteo | conteo por etiqueta |
| `gliner_top_entity_labels` | documento | GLiNER + ranking | etiquetas dominantes |
| `gliner_entity_count` | documento | conteo | numero total de entidades |
| `entity_density` | documento | derivado | entidades por 1.000 palabras |
| `actor_entity_count` | documento | derivado | personas + organizaciones + instituciones |
| `biodiversity_entity_count` | documento | derivado | especies + ecosistemas + areas protegidas + conceptos |
| `policy_entity_count` | documento | derivado | politicas, leyes, instituciones, compromisos |
| `geo_entity_count` | documento | derivado | paises + lugares |

### Etiquetas de entidades propuestas

| Etiqueta GLiNER | Uso analitico |
|---|---|
| `person` | personas citadas, remitentes, voceros, expertos |
| `organization` | organizaciones generales |
| `government institution` | ministerios, agencias, alcaldias, autoridades |
| `media outlet` | medios tradicionales, plataformas o canales informativos |
| `civil society organization` | ONG, colectivos, asociaciones |
| `indigenous or local community` | comunidades locales o indigenas mencionadas explicitamente |
| `scientific institution` | universidades, centros de investigacion, grupos academicos |
| `company` | empresas y actores privados |
| `location` | ciudades, regiones, zonas especificas |
| `country` | paises |
| `biodiversity concept` | biodiversidad, conservacion, restauracion, naturaleza |
| `species` | especies animales/vegetales o grupos taxonomicos |
| `ecosystem` | bosques, humedales, rios, paramos, habitats |
| `protected area` | parques, reservas, areas protegidas |
| `policy or law` | politicas, leyes, acuerdos, regulaciones |
| `event` | COP, cumbres, incendios, protestas, hitos |
| `date` | fechas explicitas |
| `funding or money` | presupuestos, financiacion, grant, costos |
| `risk or threat` | amenazas, riesgos, presiones, perdida |
| `proposed action` | medidas, acciones, recomendaciones |

### Indicadores agregados de entidades

- Top 20 personas mencionadas.
- Top 20 instituciones publicas.
- Top 20 organizaciones civiles.
- Top 20 instituciones cientificas.
- Top 20 empresas.
- Top paises y lugares por fuente.
- Especies mas mencionadas.
- Ecosistemas mas mencionados.
- Politicas o leyes mas mencionadas.
- Eventos mas mencionados.
- Co-ocurrencia actor-tema.
- Co-ocurrencia actor-especie/ecosistema.
- Co-ocurrencia pais-frame.
- Diversidad de entidades por fuente.
- Proporcion de documentos con actores comunitarios.
- Proporcion de documentos con instituciones cientificas.
- Proporcion de documentos con instituciones gubernamentales.
- Proporcion de documentos con especies o ecosistemas especificos.

## 6. Variables LLM

El LLM se usa para clasificaciones interpretativas y debe devolver JSON valido. No debe clasificar verdad/falsedad ni desinformacion.

| Variable | Unidad | Metodo | Salida | Motivo para LLM |
|---|---:|---|---|---|
| `is_relevant_biodiversity` | documento | LLM | booleano | requiere contexto semantico |
| `relevance_score` | documento | LLM | 0..1 | graduar relevancia |
| `primary_topic` | documento | LLM | tema corto | resumen semantico |
| `subtopic` | documento | LLM | subtema corto | granularidad |
| `sentiment_label` | documento | LLM o HF | positivo, neutral, negativo, mixto, unclear | multilingue y contextual |
| `emotion_labels` | documento | LLM | concern, fear, anger, sadness, hope, trust, pride, none, unclear | emocion expresada en texto |
| `emotional_intensity` | documento | LLM | 0..1 | intensidad discursiva |
| `narrative_label` | documento | LLM + clustering | etiqueta corta | narrativa inductiva |
| `narrative_summary` | documento | LLM | una frase | interpretacion compacta |
| `dominant_frame` | documento | LLM | problema, causa, consecuencia, solucion | framing requiere juicio |
| `discursive_pattern` | documento | LLM | patron corto | clasificacion discursiva |
| `actors` | documento | GLiNER + LLM | actor + rol | NER extrae, LLM asigna rol |
| `responsibility_actor` | documento | LLM | actor o null | atribucion semantica |
| `agency_actor` | documento | LLM | actor o null | capacidad de accion |
| `blame_actor` | documento | LLM | actor o null | culpa/responsabilidad negativa |
| `proposed_action` | documento | LLM | accion o null | interpretacion de propuesta |
| `stakeholder_presence` | documento | GLiNER + LLM | booleanos por grupo | presencia contextual |
| `biodiversity_object` | documento | GLiNER + LLM | especies/ecosistemas/areas/conceptos | depuracion semantica |
| `governance_policy_mentions` | documento | GLiNER + LLM | politicas, instituciones, brechas | gobernanza contextual |
| `claim_typology` | claim/documento | LLM | tipo, verificabilidad, evidencia | no es fact-checking |
| `evidence_type` | claim/documento | LLM | dato, experto, documento, testimonio, etc. | clasificacion contextual |
| `solution_orientation` | documento | LLM | problem_only, proposes_solution, evaluates_solution, calls_for_action, unclear | lectura argumentativa |
| `justice_equity_signal` | documento | LLM | presencia, grupo, dimension, evidencia | requiere interpretacion |
| `uncertainty_signal` | documento | LLM | alta/media/baja/sin senal/unclear | senal discursiva |
| `conflict_polarization_signal` | documento | LLM | conflicto, eje, actores, evidencia | lectura relacional |
| `marginalised_frame_candidate` | documento/cluster | LLM + distribucion | booleano + razon | requiere comparacion y validacion |
| `confidence` | documento | LLM | 0..1 | autoconfianza operacional |
| `quality_flags` | documento | LLM | lista | problemas de entrada/salida |

### Indicadores derivados LLM

- Porcentaje de documentos relevantes a biodiversidad.
- Relevancia promedio por fuente/pais/idioma.
- Distribucion de temas y subtemas.
- Distribucion de sentimiento por fuente/pais/idioma.
- Frecuencia de emociones por fuente/pais/idioma.
- Intensidad emocional promedio por fuente.
- Top narrativas por fuente y pais.
- Top frames dominantes.
- Proporcion de frames orientados a problema, causa, consecuencia o solucion.
- Actores mas asociados a responsabilidad.
- Actores mas asociados a agencia.
- Actores mas asociados a culpa.
- Acciones propuestas mas frecuentes.
- Tipologia de claims por fuente.
- Distribucion de verificabilidad.
- Distribucion de presencia y tipo de evidencia.
- Proporcion de textos con orientacion a solucion.
- Proporcion de textos con senales de justicia/equidad.
- Proporcion de textos con incertidumbre explicita.
- Ejes de conflicto mas frecuentes.
- Documentos candidatos a framing marginalizado.

## 7. Variables SNA y redes

SNA solo se interpreta como red observable, no como causalidad algoritmica.

| Variable / indicador | Unidad | Metodo | Salida |
|---|---:|---|---|
| `bluesky_author_reply_network` | red | `networkx` | nodos, edges, componentes |
| `degree` | autor | `networkx` | centralidad total |
| `in_degree` | autor | `networkx` | respuestas/entradas observables |
| `out_degree` | autor | `networkx` | respuestas/salidas observables |
| `pagerank` | autor | `networkx` | centralidad estructural |
| `betweenness` | autor | `networkx` | puente entre componentes |
| `weakly_connected_components` | red | `networkx` | componentes debilmente conectados |
| `actor_entity_cooccurrence_network` | red | GLiNER + `networkx` | actor-entidad |
| `document_similarity_network` | red | embeddings + coseno | documento-documento |
| `frame_actor_network` | red | LLM + GLiNER | frame-actor |

Indicadores agregados SNA:

- Numero de nodos y aristas.
- Densidad de red.
- Componentes conectados.
- Top actores por PageRank.
- Top actores por grado.
- Puentes entre comunidades.
- Concentracion de frames por actores centrales.
- Co-ocurrencia de actores y conceptos de biodiversidad.

## 8. Bateria final de indicadores

### Cobertura y calidad del corpus

- Total de documentos.
- Documentos por fuente.
- Documentos por pais.
- Documentos por idioma.
- Documentos por fecha/semana/mes.
- Porcentaje de texto vacio o corto.
- Longitud promedio y mediana.
- Duplicados por hash.
- Cobertura de metadatos clave.
- Cobertura de engagement.

### Biodiversidad y temas

- Porcentaje de documentos relevantes.
- Score promedio de relevancia.
- Top keywords de biodiversidad.
- Top conceptos de biodiversidad extraidos por GLiNER.
- Top especies.
- Top ecosistemas.
- Top areas protegidas.
- Tema y subtema dominante.
- Diversidad tematica por fuente.

### Actores y gobernanza

- Top personas.
- Top organizaciones.
- Top instituciones publicas.
- Top instituciones cientificas.
- Top ONG/sociedad civil.
- Top empresas.
- Presencia de comunidades locales/indigenas.
- Presencia de politicas o leyes.
- Menciones de brechas de implementacion.
- Actores asociados a responsabilidad.
- Actores asociados a agencia.
- Actores asociados a culpa.

### Narrativas, frames y discurso

- Top narrativas.
- Top frames dominantes.
- Problemas definidos con mayor frecuencia.
- Causas atribuidas.
- Consecuencias mencionadas.
- Soluciones propuestas.
- Patrones discursivos.
- Frames marginalizados candidatos.
- Counter-frames candidatos, si se aprueba Nivel 2.

### Sentimiento y emociones

- Distribucion de sentimiento.
- Sentimiento por fuente/pais/idioma.
- Emociones predominantes.
- Intensidad emocional promedio.
- Emociones por frame.
- Emociones por actor mencionado.

### Claims y evidencia

- Numero de claims principales extraidos.
- Tipo de claim.
- Verificabilidad.
- Presencia de evidencia.
- Tipo de evidencia.
- Atribucion de fuente.
- Proporcion de claims con evidencia explicita.
- Proporcion de claims con testimonio solamente.

### Soluciones, justicia e incertidumbre

- Proporcion de textos orientados a solucion.
- Acciones propuestas mas frecuentes.
- Proporcion de textos con llamado a la accion.
- Proporcion de textos con justicia/equidad.
- Grupos afectados mencionados.
- Dimensiones de equidad mencionadas.
- Proporcion de textos con incertidumbre alta/media/baja.
- Senales de falta de datos o necesidad de monitoreo.

### Conflicto y polarizacion

- Proporcion de textos con conflicto explicito.
- Ejes de conflicto mas frecuentes.
- Actores en conflicto.
- Co-ocurrencia conflicto-frame.
- Co-ocurrencia conflicto-emocion.

### Engagement y visibilidad observable

- Engagement total por documento.
- Engagement promedio/mediana por fuente.
- Top documentos por engagement.
- Engagement por frame.
- Engagement por emocion.
- Engagement por actor o entidad mencionada.

Importante: estos indicadores permiten hablar de **visibilidad observable o interaccion**, no de amplificacion algoritmica causal.

## 9. Salidas esperadas del pipeline

Por cada corrida:

- `analytics_variable_results_flat.parquet`
- `analytics_variable_results_flat.csv`
- `analytics_variable_results_raw_json.parquet`
- `run_record.json`
- `sna_summary.json`
- `logs/variable_processing/<run_id>/documents.jsonl`
- `logs/variable_processing/<run_id>/variables.jsonl`
- `logs/variable_processing/<run_id>/errors.jsonl`

Por cada documento:

- Metadatos base.
- Textometria ETL.
- Variables deterministicas.
- Variables HF/GLiNER.
- Variables LLM, cuando este habilitado.
- Metadatos de modelo: proveedor, modelo, estado, tiempo y errores.

## 10. Validacion

Cada variable interpretativa debe tener validacion humana por muestra estratificada.

Validaciones minimas:

- 30 documentos por fuente para revision cualitativa inicial.
- Muestra multilingue: espanol, ingles, hungaro si hay cobertura.
- Revision de entidades: precision aproximada por etiqueta.
- Revision de LLM: JSON valido, categorias permitidas, evidencia textual.
- Revision de sesgos: errores por idioma, fuente, longitud y tipo de documento.
- Registro de costo y tiempo por 1.000 documentos.

Metricas de calidad:

- Porcentaje de documentos procesados exitosamente.
- Tasa de JSON invalido.
- Tasa de categorias fuera de taxonomia.
- Precision manual de entidades por etiqueta.
- Acuerdo humano para variables interpretativas.
- Campos nulos por variable.
- Tiempo promedio por documento.

## 11. Alcance que no se debe prometer

No se debe comprometer como resultado automatico:

- Verdad/falsedad de claims.
- Desinformacion validada.
- Misinformation.
- Amplificacion algoritmica causal.
- Echo chambers.
- Filter bubbles.
- Identidad personal sensible inferida.
- Nacionalidad/residencia inferida del autor si no aparece explicitamente.

Estas dimensiones requieren datos externos, protocolos especificos o acceso a informacion que el corpus actual no contiene.

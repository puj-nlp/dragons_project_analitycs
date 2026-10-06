# Plan de implementacion analitica DRAGONS Task 1.1

Fecha de organizacion: 2026-10-02

## 1. Objetivo operativo

Construir un flujo reproducible para calcular variables analiticas sobre el corpus DRAGONS de medios y redes sociales. El flujo debe distinguir que variables se calculan con reglas/librerias, cuales requieren modelos de Hugging Face u otros modelos locales, cuales requieren LLM/prompt engineering y cuales pueden abordarse con SNA usando `networkx`.

La decision central es no prometer mas de lo que los datos permiten. Cada variable debe quedar clasificada como:

- **Compromiso base:** alta viabilidad con corpus actual.
- **Cobertura selectiva:** viable solo si hay datos suficientes y validacion humana.
- **No comprometer ahora:** metodologicamente costoso o dependiente de datos externos.
- **Limitacion documentada:** no inferible con datos publicos actuales.

## 2. Evidencia revisada

### 2.1 Repositorio ETL

El ETL ya tiene:

- Media Cloud: 639.997 documentos fuente; 115.201 URLs unicas procesadas.
- GDELT eventos: 1.613 URLs encontradas; 1.196 descargadas; 417 fallidas.
- Bluesky: 71.344 posts completos para llaves definidas en Colombia, Reino Unido y Hungria.
- Threads: pendiente por falta de `THREADS_ACCESS_TOKEN`.
- Parquet analitico: `data/parquet/analytics/analytics_text_documents.parquet` con 170.791 documentos textuales.

La vista `analytics_text_documents` ya incluye textometria basica: conteos de caracteres, palabras, frases, parrafos, riqueza lexica, stopwords, proxies de legibilidad, puntuacion, digitos, palabras en mayuscula, terminos frecuentes y sufijos.

### 2.2 Documentos de alcance

El archivo `DRAGONS_Task_1_1_Alcance_y_Restricciones_v2` define cuatro niveles:

- **Nivel 1:** keywords, sentiment, narratives, dominant framings, patrones discursivos, medios tradicionales y procesamiento multilingue sujeto a datos. Comprometer.
- **Nivel 2:** marginalised framings, algunas emociones, comparaciones, temporalidad y hungaro con validacion. Priorizar selectivamente.
- **Nivel 3:** desinformacion validada, misinformation, difusion avanzada y amplificacion con multiples indicadores. No comprometer en el cronograma actual.
- **Nivel 4:** mecanismos de recomendacion/ranking, causalidad algoritmica, echo chambers, filter bubbles e inferencia directa sobre algoritmos propietarios. Documentar como limitacion.

El protocolo tecnico define siete preguntas de investigacion alrededor de representaciones de biodiversidad, responsabilidad/accion/blame, emociones, engagement, variacion por fuente/idioma/tiempo/contexto, comparacion geografica e hitos temporales.

## 3. Principios de diseno

1. **Corpus primero:** antes de analizar, medir cobertura, duplicados, campos faltantes, distribucion temporal, fuente, pais, idioma y longitud textual.
2. **LLM solo donde aporte juicio semantico:** no usar prompting para conteos, fechas, top terms, redes o metricas que una libreria calcula mejor.
3. **Validacion humana obligatoria para etiquetas interpretativas:** framing, narrativa, emocion, claim type, factualidad y marginalidad requieren muestreo y acuerdo.
4. **Separar texto de audiencia:** emocion expresada en un texto no es lo mismo que resonancia emocional de la audiencia.
5. **No inferir atributos personales sensibles:** grupos sociales, identidad, residencia o nacionalidad solo si aparecen como metadatos explicitos o evidencia textual defendible.
6. **No afirmar causalidad algoritmica:** engagement alto permite hablar de visibilidad o amplificacion observable, no del algoritmo interno de una plataforma.
7. **Reproducibilidad:** cada corrida debe registrar version de datos, prompt/modelo, parametros, fecha, costo aproximado, muestra validada y errores.

## 4. Arquitectura propuesta del repositorio

```text
dragons_project_analitycs/
  config/
    variables_catalog.yml          # catalogo versionable de variables y metodos
  data/
    samples/                       # datos de prueba pequenos, versionables
  docs/
    PLAN_IMPLEMENTACION_ANALITICA.md
    MATRIZ_VARIABLES_METODOS.md
  notebooks/                       # exploracion y reportes reproducibles
  prompts/                         # plantillas de prompt por tarea
  src/dragons_analytics/
    features/                      # calculos deterministicos y HF/local models
    llm/                           # clientes, prompts, parseo JSON, validacion
    sna/                           # redes con networkx
    validation/                    # muestreo, gold sets, metricas de acuerdo
  tests/
```

## 5. Fases de trabajo

### Fase 0 - Cierre de alcance

**Resultado:** matriz aprobada de variables.

Actividades:

- Confirmar que Nivel 1 queda como compromiso base.
- Escoger cuales variables de Nivel 2 entran al MVP.
- Marcar Nivel 3 y 4 como limitaciones salvo ampliacion formal.
- Definir el universo inicial: medios tradicionales, Bluesky, GDELT y Media Cloud; Threads solo si aparece token.
- Definir ventana temporal inicial: evento-basada o ventanas mensuales comparables.

### Fase 1 - Perfilamiento de corpus

**Resultado:** reporte de cobertura y calidad.

Calculos sin LLM:

- Conteos por fuente, pais, idioma, medio, fecha, evento y keyword family.
- Longitud, duplicados, texto vacio, idioma faltante, fecha faltante.
- Cobertura temporal y huecos.
- Tasa de crawl exitoso/fallido.
- Distribucion de engagement en Bluesky.

Decision clave:

- Solo comparar paises/fuentes si existe cobertura minima equivalente.

### Fase 2 - Dataset analitico minimo

**Resultado:** tabla documento-nivel lista para enriquecimiento.

Campos minimos:

- `document_id`, `source`, `source_type`, `platform_or_outlet`, `country_key`, `language`, `created_at`, `event_id`, `keyword_family`, `title`, `text`, `url`.
- Textometria existente del ETL.
- Campos sociales disponibles: autor, reply/repost/quote/likes, uri, parent/root uri.

### Fase 3 - Variables deterministicas y de libreria

**Resultado:** features base sin LLM.

Metodos:

- `pandas`: agregaciones, ventanas temporales, comparaciones.
- `langdetect` o fastText: deteccion/normalizacion de idioma si falta.
- `scikit-learn`: TF-IDF, n-grams, clustering base, similitud coseno.
- `sentence-transformers`: embeddings multilingues si se aprueba dependencia.
- `spaCy/Stanza/HF`: NER inicial por idioma cuando sea viable.
- `networkx`: SNA de autores, respuestas, quotes, co-ocurrencias y similitud semantica.

### Fase 4 - Prompt engineering / LLM

**Resultado:** anotaciones semanticas con JSON estructurado.

Variables candidatas por LLM:

- Relevancia de biodiversidad.
- Tema principal y subtema.
- Narrativa candidata.
- Dominant framing.
- Marginalised/counter framing, solo si hay evidencia.
- Actores representados, agencia, responsabilidad, blame y accion propuesta.
- Sentiment y emociones seleccionadas.
- Claim extraction y claim type.
- Verificabilidad, presencia de evidencia, tipo de evidencia y atribucion de fuente.
- Barreras/facilitadores de participacion.

Controles:

- Salida JSON validada con esquema.
- Muestra piloto de 100-300 documentos antes de escalar.
- Reanotacion humana de muestra estratificada.
- Registro de costo por 1.000 documentos.

### Fase 5 - SNA con networkx

**Resultado:** redes y metricas de difusion observable, no causalidad algoritmica.

Redes posibles:

- Autor -> documento.
- Autor -> autor por respuesta o quote en Bluesky.
- Documento -> documento por similitud semantica.
- Medio -> tema/frame.
- Evento -> tema/frame.
- Keyword -> documento -> frame.

Metricas:

- Grado, in-degree, out-degree.
- Betweenness, closeness, eigenvector/PageRank.
- Componentes conectados.
- Comunidades con Louvain/greedy modularity si la red lo justifica.
- Densidad, modularidad, k-core.

Interpretacion permitida:

- Centralidad de actores o fuentes.
- Puentes entre narrativas.
- Concentracion o dispersion de frames.
- Amplificacion observable como engagement/centralidad alta.

Interpretacion no permitida:

- “El algoritmo recomendo/amplifico” sin datos internos de recomendacion.

### Fase 6 - Validacion y reporte

**Resultado:** tablero metodologico y reporte reproducible.

Validaciones:

- Cobertura por pais/fuente/idioma.
- Precision/recall/F1 si hay gold set.
- Acuerdo humano: Cohen/Fleiss Kappa segun numero de anotadores.
- Auditoria de prompts: estabilidad, campos vacios, categorias fuera de taxonomia.
- Analisis de errores por idioma, fuente y longitud.

## 6. MVP sugerido

MVP 1:

- Perfilamiento de corpus.
- Variables textometricas existentes.
- Keywords, top terms y n-grams.
- Relevancia biodiversidad.
- Tema/subtema.
- Sentiment triclase.
- 5-7 emociones maximo.
- Narrativa candidata.
- Dominant framing.
- Actores/responsabilidad/accion/blame.
- Claim type y verificabilidad, sin fact-checking.
- Red de autores y replies/quotes en Bluesky.

MVP 2, si hay tiempo:

- Marginalised/counter framing.
- Comparacion temporal por eventos.
- Comparacion pais/fuente solo donde la cobertura sea defendible.
- Embeddings y clustering para descubrir narrativas.

Fuera del MVP:

- Desinformacion validada.
- Causalidad algoritmica.
- Echo chambers/filter bubbles.
- Inferencia de identidad o nacionalidad de autores.

## 7. Orden recomendado antes de procesar datos reales

1. Revisar y aprobar [MATRIZ_VARIABLES_METODOS.md](MATRIZ_VARIABLES_METODOS.md).
2. Ajustar [config/variables_catalog.yml](../config/variables_catalog.yml).
3. Crear prompts JSON en `prompts/`.
4. Probar con [data/samples/test_documents.csv](../data/samples/test_documents.csv).
5. Crear gold set pequeno con validacion humana.
6. Ejecutar piloto sobre muestra estratificada real.
7. Revisar costo, calidad y sesgos.
8. Escalar por lotes.

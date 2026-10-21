# Informe final de predicciones DRAGONS — cierre al 2026-10-18

Estado: **procesamiento masivo y sincronización final terminados, con incidencias históricas documentadas**.  
Servidor: `puj-nlp` (`192.168.194.86:722`).  
Repositorio remoto: `/home/support/project/puj/respos/dragons_project_analitycs`.  
Validación de datos terminada: 2026-10-18 23:41:16 America/Bogota.  
Comprobación final de procesos: 2026-10-18 23:41:43 America/Bogota.  
Corte UTC de validación: 2026-10-19T04:41:16.942469+00:00.  
Informe anterior: [2026-10-17](INFORME_ESTADO_PREDICCIONES_2026-10-17.md).  
Evidencia detallada: [datos del cierre](INFORME_ESTADO_PREDICCIONES_2026-10-18.datos.json).

## Dictamen de cierre

**El procesamiento masivo del proyecto terminó y sus resultados calculados quedaron actualizados y verificados en PostgreSQL, MongoDB y Parquet.** Al corte final no hay trabajadores de predicción, sincronizadores del proyecto ni procesos de inferencia de los motores inspeccionados. Ollama local responde con cero modelos cargados; sus servicios en espera no se detuvieron.

Se sincronizaron **84 corridas productivas e históricas, con 420,320 registros de resultados**. Se comprobó directamente que los registros de PostgreSQL, MongoDB y Parquet corresponden al contenido de los JSONL originales, aplicando la normalización de valores vacíos descrita en este informe.

Las 11 corridas finales de `media_cloud` están en `completed`, con tantos resultados persistidos como objetivos: 6 HF/GLiNER repair y 5 LLM remoto v3. Las corridas históricas incluidas en la sincronización conservan sus estados originales; sincronizar sus resultados parciales no las reclasifica como completadas.

El cierre operativo conserva **5 documentos sin éxito HF/GLiNER y 1 sin éxito LLM**. Se registran como incidencias residuales: no son procesos aún ejecutándose ni resultados pendientes de publicación. No se cambiaron a `success` ni se lanzaron nuevas inferencias para ocultar esos estados.

## Estado final del servidor

| Comprobación | Resultado |
|---|---|
| Trabajadores de predicción del proyecto | 0 |
| Sincronizadores del proyecto | 0 |
| Procesos de inferencia detectados de Ollama runner, vLLM, SGLang y llama-server | 0 |
| Modelos cargados en Ollama local | 0 |
| Último cierre HF/GLiNER repair | 2026-10-16 13:25:56 America/Bogota |
| Último cierre LLM remoto v3 media_cloud | 2026-10-17 18:40:38 America/Bogota |
| Estado de las 11 corridas finales | `completed` |

La comprobación de procesos identifica los argumentos reales de ejecución para distinguir trabajadores de inferencia, sincronizadores y servicios que permanecen en espera.

## Actualización de PostgreSQL, MongoDB y Parquet

| Destino | Objeto actualizado | Resultado final verificado |
|---|---|---:|
| PostgreSQL | `public.analytics_variable_results_pilot` | 420,320 registros |
| PostgreSQL | `public.analytics_variable_runs` | Metadatos de las 84 corridas sincronizadas y verificados |
| MongoDB, base `dragons` | `analytics_variable_results_pilot` | 420,320 documentos |
| MongoDB, base `dragons` | `analytics_variable_runs` | Metadatos de las 84 corridas sincronizadas y verificados |
| Parquet de JSON completo | 84 archivos `analytics_variable_results_raw_json.parquet` | 420,320 registros en conjunto |
| Parquet plano | 84 archivos `analytics_variable_results_flat.parquet` | 420,320 registros en conjunto |

Los Parquet se actualizaron en el servidor, dentro de:

```text
data/processed/pilot_variables/<run_id>/analytics_variable_results_raw_json.parquet
data/processed/pilot_variables/<run_id>/analytics_variable_results_flat.parquet
```

También se regeneraron los CSV planos auxiliares de las corridas. Los JSONL originales se conservaron como fuente de los resultados calculados.

### Distribución de los registros publicados

| Flujo | Corridas con resultados sincronizados | Registros brutos |
|---|---:|---:|
| HF/GLiNER sin LLM | 27 | 251,072 |
| LLM | 57 | 169,248 |
| **Total** | **84** | **420,320** |

Los 420,320 registros incluyen versiones y reprocesos. No representan 420,320 documentos distintos. Cada flujo conserva un universo de 169,248 documentos únicos; la cobertura exitosa se calcula mediante deduplicación.

### Corrección de valores vacíos

Se ajustó `scripts/sync_incremental_outputs.py:282` para normalizar cada resultado antes de exportarlo a los tres destinos. Los números no finitos (`NaN`, infinito positivo y negativo) se convierten en `null`; los textos literales se conservan.

Esto evita que un valor vacío como `country_key` se almacene como el texto `NaN` en PostgreSQL mientras los otros destinos lo tratan como un valor ausente. Se volvió a ejecutar la sincronización completa con esta corrección.

La comprobación de sintaxis y la prueba de normalización de valores anidados pasaron en el entorno virtual del servidor. La evidencia incluye el SHA-256 del script desplegado.

## Validación directa de los destinos

**Resultado: 84 de 84 corridas verificadas; cero discrepancias.** La sincronización terminó con código 0 y la revisión completa terminó con código 0, sin incidencias de consistencia.

Para cada corrida se verificó:

1. Coincidencia de los registros de PostgreSQL con los resultados originales mediante hashes de los 15 campos persistidos.
2. Coincidencia del mismo contenido en MongoDB, además del conteo físico de documentos.
3. Coincidencia del contenido completo persistido en el Parquet de JSON, además del conteo de filas.
4. Coincidencia de identidad, fuente y estados HF/LLM en el Parquet plano, además del conteo de filas.
5. Correspondencia de `rows_synced` en los metadatos de corrida de MongoDB.
6. Correspondencia de `rows_synced` en los metadatos de corrida de PostgreSQL.

Los campos de PostgreSQL comparados fueron:

```text
result_id, run_id, document_id, source, country_key, language, created_at, title,
etl_metrics, deterministic_variables, hf_variables, hf_metadata,
llm_variables, llm_metadata, computed_at
```

La comparación normaliza los valores no finitos y las fechas para verificar el contenido equivalente entre formatos. Incluye los bloques completos de variables calculadas y metadatos; no se limita a comprobar que existen archivos o que coinciden sus cantidades.

El Parquet plano se verificó en las columnas `result_id`, `run_id`, `document_id`, `source`, `hf_status` y `llm_status`. El Parquet de JSON completo conserva y valida los bloques de variables.

Se excluyó una línea JSON inválida preexistente del flujo HF/GLiNER. No se encontraron líneas inválidas LLM. Esa exclusión está contabilizada en la evidencia.

## Cobertura final de resultados exitosos

| Flujo | Objetivo único | Intentados únicos | Con estado exitoso | Fallidos sin éxito disponible | Cobertura exitosa |
|---|---:|---:|---:|---:|---:|
| HF/GLiNER sin LLM | 169,248 | 169,248 | 169,243 | 5 | 99.99705% |
| LLM | 169,248 | 169,248 | 169,247 | 1 | 99.99941% |

“Exitoso” indica `hf_metadata.status = success` o `llm_metadata.status = success`. No certifica exactitud semántica de las predicciones. Se muestran cinco decimales para no ocultar los fallos residuales mediante el redondeo a 100.00%.

### Por fuente

| Fuente | Objetivo | HF/GLiNER exitosos | Fallos HF/GLiNER | LLM exitosos | Fallos LLM |
|---|---:|---:|---:|---:|---:|
| `bluesky` | 64,670 | 64,670 | 0 | 64,669 | 1 |
| `gdelt` | 1,198 | 1,198 | 0 | 1,198 | 0 |
| `media_cloud` | 103,380 | 103,375 | 5 | 103,380 | 0 |
| **Total** | **169,248** | **169,243** | **5** | **169,247** | **1** |

Proveedores LLM de resultados exitosos: `deepseek`, 169,139; `openai`, 108.

## Evolución hasta el cierre

| Indicador | 2026-10-09 | 2026-10-13 | 2026-10-15 | 2026-10-17 | 2026-10-18 |
|---|---:|---:|---:|---:|---:|
| HF/GLiNER exitosos únicos | 92,163 | 138,086 | 153,808 | 169,243 | 169,243 |
| Cobertura HF/GLiNER | 54.45% | 81.59% | 90.88% | 99.99705% | 99.99705% |
| LLM exitosos únicos | 23,734 | 93,382 | 108,871 | 169,247 | 169,247 |
| Cobertura LLM | 14.02% | 55.17% | 64.33% | 99.99941% | 99.99941% |
| Trabajadores de predicción activos | 16 | 11 | 11 | 0 | 0 |

El 18 de octubre no se calcularon nuevas predicciones durante esta intervención. El cambio de este cierre consiste en publicar de nuevo todos los resultados disponibles, corregir la representación de valores ausentes y comprobar directamente la consistencia de los tres destinos.

## Cierre de las 11 corridas finales

Fechas en America/Bogota. Los conteos se contrastaron con los resultados originales y los destinos actualizados.

| Grupo media_cloud | Shard | Resultados / objetivo | Estado | Finalización local |
|---|---|---:|---|---|
| HF/GLiNER repair | `s0of6` | 13,558 / 13,558 | `completed` | 2026-10-16 11:44:00 |
| HF/GLiNER repair | `s1of6` | 13,781 / 13,781 | `completed` | 2026-10-16 13:25:56 |
| HF/GLiNER repair | `s2of6` | 13,569 / 13,569 | `completed` | 2026-10-16 12:54:25 |
| HF/GLiNER repair | `s3of6` | 13,565 / 13,565 | `completed` | 2026-10-16 13:04:49 |
| HF/GLiNER repair | `s4of6` | 13,717 / 13,717 | `completed` | 2026-10-16 13:23:23 |
| HF/GLiNER repair | `s5of6` | 13,634 / 13,634 | `completed` | 2026-10-16 13:12:19 |
| LLM remoto v3 | `s0of5` | 19,829 / 19,829 | `completed` | 2026-10-17 18:40:38 |
| LLM remoto v3 | `s1of5` | 19,620 / 19,620 | `completed` | 2026-10-17 17:34:01 |
| LLM remoto v3 | `s2of5` | 19,880 / 19,880 | `completed` | 2026-10-17 18:20:58 |
| LLM remoto v3 | `s3of5` | 19,825 / 19,825 | `completed` | 2026-10-17 18:28:16 |
| LLM remoto v3 | `s4of5` | 19,585 / 19,585 | `completed` | 2026-10-17 17:59:52 |

Los cinco shards LLM remoto v3 de `bluesky`, completados el 13 de octubre, están incluidos en la sincronización y en la cobertura global.

## Incidencias residuales conservadas

| Flujo | Fuente | document_id | Estado |
|---|---|---|---|
| HF/GLiNER | `media_cloud` | `url_crawls:crawl_uq_eeb9008b5f1410c2d74c0245_media_cloud_whitelist` | `failed` |
| HF/GLiNER | `media_cloud` | `url_crawls:crawl_uq_71195563eedd34a8d035c442_media_cloud_whitelist` | `failed` |
| HF/GLiNER | `media_cloud` | `url_crawls:crawl_uq_284129fc3bccc01d1c786d6f_media_cloud_whitelist` | `failed` |
| HF/GLiNER | `media_cloud` | `url_crawls:crawl_uq_0d14f24787f83b7e6cb3e092_media_cloud_whitelist` | `failed` |
| HF/GLiNER | `media_cloud` | `url_crawls:crawl_uq_4a579e98b02902edf0c8697b_media_cloud_whitelist` | `failed` |
| LLM | `bluesky` | `bluesky_posts:bluesky_3knv2v7fabs2s` | `failed` |

Los estados fallidos también quedaron publicados y verificados. Se cierra el procesamiento masivo con estas incidencias documentadas; conseguir una cobertura exitosa estrictamente del 100% requeriría una intervención dirigida sobre esos seis documentos.

No se ejecutaron nuevos cálculos LLM o GLiNER durante la sincronización de cierre.

## Infraestructura al corte final

| Recurso | Valor |
|---|---|
| Procesadores lógicos | 24 |
| Carga promedio 1 / 5 / 15 min | 1.64 / 1.90 / 1.77 |
| RAM total aproximada | 251 GiB |
| RAM disponible | 219.5 GiB |
| Swap usada | 0 GiB |
| Disco libre | 1,063.7 GiB |
| Consulta GPU | Persiste `Driver/library version mismatch`, NVML 595.99 |

El desajuste NVIDIA queda como incidencia de infraestructura conocida; no se modificó el controlador ni se atribuye a este corte una validación correcta de la GPU.

## Evidencias y alcance del cierre

Archivos de auditoría en el servidor:

```text
logs/sync/final_sync_2026-10-18.log
logs/sync/final_verification_2026-10-18.log
logs/sync/final_verification_2026-10-18.json
```

El JSON adjunto a este informe conserva el manifiesto de las 84 corridas, los conteos en cada destino, el resultado de las seis comprobaciones por corrida, la cobertura deduplicada, los documentos residuales y la comprobación final de procesos.

Se conservaron los nombres de tablas y colecciones y la organización de Parquet por corrida. No se presenta una suma de registros históricos como si fueran documentos únicos. Para el cálculo de cobertura se prioriza `success` por `document_id` y, en empate de estado, el registro más reciente por `computed_at`, manteniendo separados los flujos HF sin LLM y LLM.

**Cierre final:** procesamiento masivo terminado, resultados calculados sincronizados y consistencia verificada en PostgreSQL, MongoDB y Parquet; cero trabajos activos del proyecto al corte y seis estados fallidos históricos conservados de forma explícita.


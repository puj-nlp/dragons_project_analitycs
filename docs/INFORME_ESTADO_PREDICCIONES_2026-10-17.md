# Informe de estado de predicciones DRAGONS — cierre de corridas al 2026-10-17

Fecha de corte de resultados: 2026-10-17 22:25:07 America/Bogota  
Fecha de corte UTC: 2026-10-18T03:25:07.212062Z  
Fin de auditoría de resultados: 2026-10-17 22:25:41 America/Bogota  
Comprobación final de procesos y archivos: 2026-10-17 22:26:13 America/Bogota  
Servidor verificado por SSH: `puj-nlp` (`192.168.194.86:722`)  
Repositorio remoto: `/home/support/project/puj/respos/dragons_project_analitycs`  
Informe anterior: [2026-10-15](INFORME_ESTADO_PREDICCIONES_2026-10-15.md)  
Evidencia: [datos de auditoría](INFORME_ESTADO_PREDICCIONES_2026-10-17.datos.json)

## Resumen ejecutivo

**Sí: las 11 corridas que estaban activas terminaron.** No se encontraron procesos de `run_pilot_processing.py` en ejecución. Los checkpoints de los 6 shards HF/GLiNER repair y los 5 shards LLM remoto v3 de `media_cloud` indican `completed`, y cada corrida tiene tantos resultados únicos persistidos como documentos objetivo.

- **HF/GLiNER repair terminó el 2026-10-16 a las 13:25:56 de Bogotá**, al finalizar el último shard.
- **LLM remoto v3 de media_cloud terminó el 2026-10-17 a las 18:40:38 de Bogotá**, al finalizar el último shard.
- La cobertura global conserva **5 documentos HF/GLiNER sin éxito** en `media_cloud` y **1 documento LLM sin éxito** en `bluesky`. Finalizar las corridas no equivale a haber corregido esos fallos residuales.

| Métrica deduplicada | 2026-10-15 | 2026-10-17 | Cambio |
|---|---:|---:|---:|
| Universo objetivo | 169,248 | 169,248 | 0 |
| HF/GLiNER con estado exitoso | 153,808 | 169,243 | +15,435 |
| Cobertura HF/GLiNER | 90.88% | 99.99705% | +9.12 pp |
| Pendiente HF/GLiNER | 15,440 | 5 | -15,435 |
| LLM con estado exitoso | 108,871 | 169,247 | +60,376 |
| Cobertura LLM | 64.33% | 99.99941% | +35.67 pp |
| Pendiente LLM | 60,377 | 1 | -60,376 |
| Procesos de predicción activos | 11 | 0 | -11 |

Se muestran cinco decimales en las coberturas actuales para que el redondeo a 100.00% no oculte los pendientes. “Exitoso” significa `hf_metadata.status = success` o `llm_metadata.status = success`; no es una medida de exactitud semántica.

## Evolución desde el 9 de octubre

| Indicador | 2026-10-09 | 2026-10-13 | 2026-10-15 | 2026-10-17 |
|---|---:|---:|---:|---:|
| HF/GLiNER exitoso único | 92,163 | 138,086 | 153,808 | 169,243 |
| Cobertura HF/GLiNER | 54.45% | 81.59% | 90.88% | 99.99705% |
| Pendiente HF/GLiNER | 77,085 | 31,162 | 15,440 | 5 |
| LLM exitoso único | 23,734 | 93,382 | 108,871 | 169,247 |
| Cobertura LLM | 14.02% | 55.17% | 64.33% | 99.99941% |
| Pendiente LLM | 145,514 | 75,866 | 60,377 | 1 |
| Procesos LLM activos | 10 | 5 | 5 | 0 |
| Procesos repair HF/GLiNER activos | 6 | 6 | 6 | 0 |

Las cifras históricas se conservan como fueron publicadas. Al reconstruir el corte del 15 de octubre mediante `computed_at`, se obtienen exactamente los mismos éxitos de ese informe: 153,808 HF/GLiNER y 108,871 LLM.

## Cobertura real por fuente

### HF/GLiNER sin LLM

| Fuente | Objetivo | Exitosos 2026-10-15 | Exitosos actuales | Aumento | Fallidos sin éxito | Cobertura actual |
|---|---:|---:|---:|---:|---:|---:|
| `bluesky` | 64,670 | 64,670 | 64,670 | 0 | 0 | 100% |
| `gdelt` | 1,198 | 1,198 | 1,198 | 0 | 0 | 100% |
| `media_cloud` | 103,380 | 87,940 | 103,375 | +15,435 | 5 | 99.99516% |
| **Total** | **169,248** | **153,808** | **169,243** | **+15,435** | **5** | **99.99705%** |

### LLM

| Fuente | Objetivo | Exitosos 2026-10-15 | Exitosos actuales | Aumento | Fallidos sin éxito | Cobertura actual |
|---|---:|---:|---:|---:|---:|---:|
| `bluesky` | 64,670 | 64,669 | 64,669 | 0 | 1 | 99.99845% |
| `gdelt` | 1,198 | 1,198 | 1,198 | 0 | 0 | 100% |
| `media_cloud` | 103,380 | 43,004 | 103,380 | +60,376 | 0 | 100% |
| **Total** | **169,248** | **108,871** | **169,247** | **+60,376** | **1** | **99.99941%** |

Ambos flujos tienen intentos registrados para los 169,248 documentos. Los pendientes actuales son fallos sin éxito disponible, no documentos aún esperando a que continúen las corridas.

### Proveedores LLM de resultados exitosos

| Proveedor | 2026-10-15 | 2026-10-17 | Aumento |
|---|---:|---:|---:|
| `deepseek` | 108,788 | 169,139 | +60,351 |
| `openai` | 83 | 108 | +25 |
| **Total** | **108,871** | **169,247** | **+60,376** |

## Finalización de las corridas

| Grupo media_cloud | Estado | Resultados únicos / objetivo | Avance de corrida | Errores operativos acumulados | Variables registradas |
|---|---|---:|---:|---:|---:|
| HF/GLiNER repair PEFT v1, 6 shards | `completed` | 81,824 / 81,824 | 100% | 0 | 2,536,550 |
| LLM remoto v3, 5 shards | `completed` | 98,739 / 98,739 | 100% | 515 | 6,010,743 |

Todos los resultados del grupo repair tienen estado HF exitoso y todos los resultados del grupo LLM tienen estado LLM exitoso. Los 515 eventos de `errors.jsonl` del grupo LLM no equivalen a 515 documentos fallidos: son eventos operativos y los resultados finales del grupo son exitosos. Su causa individual no se auditó en este corte.

### Detalle HF/GLiNER repair

Prefijo: `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_`. Fechas de finalización en America/Bogota.

| Shard | Resultados únicos | Objetivo | Estado | Errores | Variables | Finalización local |
|---|---:|---:|---|---:|---:|---|
| `s0of6` | 13,558 | 13,558 | `completed` | 0 | 420,299 | 2026-10-16 11:44:00 |
| `s1of6` | 13,781 | 13,781 | `completed` | 0 | 427,212 | 2026-10-16 13:25:56 |
| `s2of6` | 13,569 | 13,569 | `completed` | 0 | 420,640 | 2026-10-16 12:54:25 |
| `s3of6` | 13,565 | 13,565 | `completed` | 0 | 420,516 | 2026-10-16 13:04:49 |
| `s4of6` | 13,717 | 13,717 | `completed` | 0 | 425,228 | 2026-10-16 13:23:23 |
| `s5of6` | 13,634 | 13,634 | `completed` | 0 | 422,655 | 2026-10-16 13:12:19 |

### Detalle LLM remoto v3 media_cloud

Prefijo: `full_parallel_all_variables_llm_remote_v3_media_cloud_`. Fechas de finalización en America/Bogota.

| Shard | Resultados únicos | Objetivo | Estado | Errores | Variables | Finalización local |
|---|---:|---:|---|---:|---:|---|
| `s0of5` | 19,829 | 19,829 | `completed` | 111 | 1,207,029 | 2026-10-17 18:40:38 |
| `s1of5` | 19,620 | 19,620 | `completed` | 95 | 1,194,397 | 2026-10-17 17:34:01 |
| `s2of5` | 19,880 | 19,880 | `completed` | 92 | 1,210,142 | 2026-10-17 18:20:58 |
| `s3of5` | 19,825 | 19,825 | `completed` | 108 | 1,206,840 | 2026-10-17 18:28:16 |
| `s4of5` | 19,585 | 19,585 | `completed` | 109 | 1,192,335 | 2026-10-17 17:59:52 |

Los cinco shards LLM remoto v3 de `bluesky`, completados desde el 13 de octubre, mantienen 54,533 resultados exitosos y están incluidos en el total deduplicado global.

### Salidas generadas

Para las 11 corridas de `media_cloud` se confirmó la existencia de las cuatro salidas indicadas en sus checkpoints: Parquet plano, CSV plano, Parquet de JSON bruto y JSONL incremental (**44 archivos existentes**).

Los checkpoints registran `success` para exportación Parquet, MongoDB y PostgreSQL en las 11 corridas. Se verificó la existencia de archivos; no se consultaron directamente las bases de datos ni se validó fila por fila su contenido.

## Pendientes residuales identificados

### HF/GLiNER: 5 documentos de media_cloud

| document_id | Estado deduplicado | Fecha del registro conservado, Bogotá |
|---|---|---|
| `url_crawls:crawl_uq_eeb9008b5f1410c2d74c0245_media_cloud_whitelist` | `failed` | 2026-10-08 20:00:22 |
| `url_crawls:crawl_uq_71195563eedd34a8d035c442_media_cloud_whitelist` | `failed` | 2026-10-08 20:00:22 |
| `url_crawls:crawl_uq_284129fc3bccc01d1c786d6f_media_cloud_whitelist` | `failed` | 2026-10-08 20:00:22 |
| `url_crawls:crawl_uq_0d14f24787f83b7e6cb3e092_media_cloud_whitelist` | `failed` | 2026-10-08 20:00:22 |
| `url_crawls:crawl_uq_4a579e98b02902edf0c8697b_media_cloud_whitelist` | `failed` | 2026-10-08 20:00:22 |

Los cinco permanecen con estado `failed` después de combinar las corridas HF sin LLM. La diferencia de 5 documentos señalada en el informe del 15 de octubre continúa al cierre: completar los 81,824 objetivos del grupo repair no eliminó ese pendiente global. Para cerrar la cobertura será necesario reprocesarlos o documentar una exclusión justificada; no se ejecutó ese reproceso.

### LLM: 1 documento de bluesky

- `document_id`: `bluesky_posts:bluesky_3knv2v7fabs2s`.
- Estado deduplicado: `failed`.
- Fecha del registro conservado: 2026-10-06 20:22:17 America/Bogota (2026-10-07T01:22:17.537545Z).

Este fallo ya existía en los informes previos. `media_cloud` sí alcanzó cobertura LLM completa.

## Registros brutos y deduplicación

| Indicador actual | HF/GLiNER sin LLM | LLM |
|---|---:|---:|
| Registros JSON válidos con document_id | 251,072 | 169,248 |
| Documentos únicos intentados | 169,248 | 169,248 |
| Registros adicionales por reproceso/duplicación | 81,824 | 0 |
| Documentos únicos exitosos | 169,243 | 169,247 |
| Documentos fallidos sin éxito disponible | 5 | 1 |
| Líneas JSON inválidas observadas | 1 | 0 |
| Colas incompletas excluidas | 0 | 0 |

El volumen bruto HF/GLiNER equivale al 148.35% del universo porque incluye reprocesos. La cobertura oficial se calcula con documentos exitosos únicos y es 99.99705%.

## Infraestructura al cierre

| Recurso | 2026-10-15 | 2026-10-17 |
|---|---|---|
| Procesadores lógicos | 24 | 24 |
| Carga promedio 1 / 5 / 15 min | 92.39 / 91.53 / 88.55 | 0.72 / 0.94 / 0.91 |
| RAM total / usada / disponible | 250 / 69 / 181 GiB | 250 / 31 / 219 GiB |
| Swap usada | 0 | 0 |
| Disco usado | 696 GiB; 40% | 705 GiB; 40% |
| Disco libre | 1.1 TiB | 1.1 TiB |
| Procesos de predicción activos | 11 | 0 |
| GPU vía nvidia-smi | Error NVML | Persiste error NVML |

La carga del servidor bajó considerablemente frente al corte con procesamiento activo. Persiste `Driver/library version mismatch`: biblioteca NVML 595.99 frente al módulo NVIDIA cargado 595.84. El problema sigue impidiendo consultar la GPU con `nvidia-smi`; no impidió que las corridas registraran su finalización.

## Metodología y alcance

1. Consulta SSH de solo lectura: procesos del sistema, checkpoints, resultados incrementales, logs y existencia de archivos de salida.
2. Universo conservado: 169,248 documentos (64,670 bluesky, 1,198 gdelt y 103,380 media_cloud).
3. Selección HF sin LLM: `full_gliner25_multi_no_llm` y `full_parallel_gliner25_multi_no_llm_*`. Selección LLM: `full_by_source_all_variables_llm_*` y `full_parallel_all_variables_llm_*`. La lista exacta se conserva en la evidencia JSON.
4. Se excluyeron smoke y directorios fuera de esos patrones. No se mezclaron los resultados HF de corridas LLM con la serie HF sin LLM.
5. Deduplicación por `document_id`, priorizando `success` y, en empate, el registro más reciente por `computed_at`.
6. Cobertura = documentos únicos con estado exitoso / 169,248. Se mantuvo la distinción entre éxito de ejecución, exactitud semántica y validación de exportaciones.
7. Se fijó el tamaño de cada JSONL al inicio de la lectura y se procesaron solo líneas completas dentro de ese límite.
8. La finalización se comprobó con ausencia de procesos, estado `completed`, fecha `finished_at` y coincidencia entre resultados persistidos y objetivo en los 11 shards que estaban activos.
9. No se iniciaron, reiniciaron ni modificaron procesos; tampoco se reprocesaron los pendientes ni se cambió la infraestructura.

## Acciones de cierre recomendadas

1. Reprocesar de forma dirigida los 5 documentos HF/GLiNER y el documento LLM identificados, conservando sus IDs para verificar el resultado deduplicado.
2. Verificar directamente MongoDB y PostgreSQL antes de considerar cerrada la validación de persistencia en bases de datos.
3. Conservar este corte y sus evidencias como cierre de las corridas masivas; no hace falta estimar tiempo restante de esas corridas, pues ya terminaron.
4. Revisar el desajuste NVIDIA antes de futuras ejecuciones que requieran GPU.

## Cifra para reportar

> **Corridas masivas terminadas:** 6 shards HF/GLiNER repair y 5 shards LLM de media_cloud, todos completados; 0 procesos de predicción activos.
>
> **HF/GLiNER sin LLM:** 169,243 documentos únicos exitosos de 169,248 (**99.99705%**). Quedan 5 fallos de media_cloud.
>
> **LLM:** 169,247 documentos únicos exitosos de 169,248 (**99.99941%**). Queda 1 fallo de bluesky; media_cloud está al 100% en LLM.


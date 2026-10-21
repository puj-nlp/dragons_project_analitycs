# Informe de estado de predicciones DRAGONS — evolución al 2026-10-15

Fecha de corte de resultados: 2026-10-15 00:26:54 America/Bogota  
Fecha de corte UTC: 2026-10-15T05:26:54.989671Z  
Fin de lectura de auditoría: 2026-10-15 00:27:27 America/Bogota  
Servidor verificado por SSH: `puj-nlp` (`192.168.194.86:722`)  
Repositorio remoto: `/home/support/project/puj/respos/dragons_project_analitycs`  
Informe base: [2026-10-13](INFORME_ESTADO_PREDICCIONES_2026-10-13.md)  
Evidencia de este corte: [datos de auditoría](INFORME_ESTADO_PREDICCIONES_2026-10-15.datos.json)

## Resumen ejecutivo

El procesamiento sigue avanzando. Permanecen activos los 11 procesos observados el 13 de octubre: 5 LLM remoto v3 y 6 HF/GLiNER sin LLM de reparación PEFT v1, todos para `media_cloud`. Sus resultados persistidos muestran actividad reciente.

Desde el corte publicado del 2026-10-13 15:19:24 hasta este corte transcurrieron aproximadamente 33 horas y 7 minutos:

| Métrica real deduplicada | 2026-10-13 | 2026-10-15 | Cambio |
|---|---:|---:|---:|
| Documentos objetivo | 169,248 | 169,248 | 0 |
| HF/GLiNER con estado `success` | 138,086 | 153,808 | +15,722 |
| Cobertura HF/GLiNER | 81.59% | 90.88% | +9.29 pp |
| Pendiente HF/GLiNER | 31,162 | 15,440 | -15,722 |
| LLM con estado `success` | 93,382 | 108,871 | +15,489 |
| Cobertura LLM | 55.17% | 64.33% | +9.15 pp |
| Pendiente LLM | 75,866 | 60,377 | -15,489 |

Todo el aumento de cobertura corresponde a `media_cloud`. HF/GLiNER ya supera el 90% del universo y redujo su pendiente un 50.45% respecto al informe anterior. LLM redujo su pendiente un 20.42%.

En este informe, “correcto” significa que la ejecución registró `metadata.status = success`, siguiendo la definición del informe base. No constituye una evaluación de exactitud semántica de las predicciones.

## Evolución de los tres cortes

| Indicador | 2026-10-09 | 2026-10-13 | 2026-10-15 |
|---|---:|---:|---:|
| HF/GLiNER correcto único | 92,163 | 138,086 | 153,808 |
| Cobertura HF/GLiNER | 54.45% | 81.59% | 90.88% |
| Pendiente HF/GLiNER | 77,085 | 31,162 | 15,440 |
| LLM correcto único | 23,734 | 93,382 | 108,871 |
| Cobertura LLM | 14.02% | 55.17% | 64.33% |
| Pendiente LLM | 145,514 | 75,866 | 60,377 |
| Procesos LLM activos | 10 | 5 | 5 |
| Procesos HF/GLiNER repair activos | 6 | 6 | 6 |

Los valores históricos son los publicados en sus respectivos informes. Desde el 9 de octubre se acumula una mejora neta de 61,645 documentos HF/GLiNER y 85,137 documentos LLM con estado exitoso.

## Cobertura real por fuente

### HF/GLiNER sin LLM

| Fuente | Objetivo | Correctos 2026-10-13 | Correctos 2026-10-15 | Aumento | Pendientes actuales | Cobertura actual |
|---|---:|---:|---:|---:|---:|---:|
| `bluesky` | 64,670 | 64,670 | 64,670 | 0 | 0 | 100.00% |
| `gdelt` | 1,198 | 1,198 | 1,198 | 0 | 0 | 100.00% |
| `media_cloud` | 103,380 | 72,218 | 87,940 | +15,722 | 15,440 | 85.06% |
| **Total** | **169,248** | **138,086** | **153,808** | **+15,722** | **15,440** | **90.88%** |

Todos los documentos objetivo tienen al menos un intento HF/GLiNER. Los 15,440 pendientes corresponden a documentos con fallo y sin un resultado exitoso posterior en las corridas seleccionadas.

### LLM

| Fuente | Objetivo | Correctos 2026-10-13 | Correctos 2026-10-15 | Aumento | Pendientes actuales | Cobertura actual |
|---|---:|---:|---:|---:|---:|---:|
| `bluesky` | 64,670 | 64,669 | 64,669 | 0 | 1 | 99.99845% |
| `gdelt` | 1,198 | 1,198 | 1,198 | 0 | 0 | 100.00% |
| `media_cloud` | 103,380 | 27,515 | 43,004 | +15,489 | 60,376 | 41.60% |
| **Total** | **169,248** | **93,382** | **108,871** | **+15,489** | **60,377** | **64.33%** |

Hay 108,872 documentos únicos intentados: 108,871 exitosos y 1 fallido sin corrección. Los 60,377 pendientes se descomponen en 60,376 documentos sin intento LLM registrado y el fallo de `bluesky`. Mostrar `bluesky` con más decimales evita interpretar el redondeo a 100.00% como cobertura completa.

### Proveedores LLM de resultados exitosos

| Proveedor | 2026-10-13 | 2026-10-15 | Aumento |
|---|---:|---:|---:|
| `deepseek` | 93,341 | 108,788 | +15,447 |
| `openai` | 41 | 83 | +42 |
| **Total** | **93,382** | **108,871** | **+15,489** |

## Registros brutos, duplicados y fallos

| Indicador | HF/GLiNER 2026-10-13 | HF/GLiNER 2026-10-15 | LLM 2026-10-13 | LLM 2026-10-15 |
|---|---:|---:|---:|---:|
| Registros válidos con `document_id` | 219,916 | 235,637 | 93,383 | 108,872 |
| Documentos únicos intentados | 169,248 | 169,248 | 93,383 | 108,872 |
| Registros adicionales por reproceso/duplicación | 50,668 | 66,389 | 0 | 0 |
| Documentos únicos exitosos | 138,086 | 153,808 | 93,382 | 108,871 |
| Documentos con fallo sin éxito disponible | 31,162 | 15,440 | 1 | 1 |
| Líneas JSON inválidas observadas | 1 | 1 | No informado | 0 |

En el corte actual no se excluyeron colas incompletas de JSONL. La línea inválida HF/GLiNER se excluye del conteo de registros válidos.

La suma bruta HF/GLiNER equivale al 139.23% del objetivo porque incluye reprocesos. La cobertura real es 90.88%; solo se cuenta una vez cada documento con resultado exitoso.

## Estado operativo de las corridas

| Grupo `media_cloud` | Procesos activos 13 → 15 | Procesados 2026-10-13 | Procesados 2026-10-15 | Aumento | Objetivo grupo | Avance actual |
|---|---:|---:|---:|---:|---:|---:|
| LLM remoto v3 | 5 → 5 | 22,871 | 38,363 | +15,492 | 98,739 | 38.85% |
| HF/GLiNER repair PEFT v1 | 6 → 6 | 50,666 | 66,389 | +15,723 | 81,824 | 81.14% |

| Indicador operativo | LLM 2026-10-13 | LLM 2026-10-15 | HF/GLiNER 2026-10-13 | HF/GLiNER 2026-10-15 |
|---|---:|---:|---:|---:|
| Errores en `errors.jsonl` | 60 | 206 | 0 | 0 |
| Variables en `variables.jsonl` | 1,394,970 | 2,340,066 | 1,570,646 | 2,058,090 |

Los 206 eventos de error operativo LLM no equivalen a 206 documentos fallidos: los 38,363 resultados persistidos de las cinco corridas activas tienen `llm_metadata.status = success`. No se auditó aquí la causa individual de esos eventos.

Los cinco shards LLM remoto v3 de `bluesky` continúan completados, sin procesos activos, con 54,533 resultados exitosos en conjunto. Esos resultados están incluidos en la cobertura deduplicada global.

El avance del grupo mide resultados de esas corridas; la cobertura global combina el mejor resultado de todas las corridas productivas seleccionadas. Por eso sus aumentos no tienen que coincidir exactamente.

### Detalle LLM activo

Prefijo de corrida: `full_parallel_all_variables_llm_remote_v3_media_cloud_`.

| Shard | PID | Procesados únicos | Objetivo | Avance | Errores | Variables | Último resultado UTC |
|---|---:|---:|---:|---:|---:|---:|---|
| `s0of5` | 2458644 | 7,614 | 19,829 | 38.40% | 47 | 464,395 | 2026-10-15T05:26:29Z |
| `s1of5` | 2458646 | 7,729 | 19,620 | 39.39% | 38 | 471,470 | 2026-10-15T05:26:39Z |
| `s2of5` | 2458648 | 7,713 | 19,880 | 38.80% | 32 | 470,462 | 2026-10-15T05:26:22Z |
| `s3of5` | 2458650 | 7,664 | 19,825 | 38.66% | 45 | 467,512 | 2026-10-15T05:26:23Z |
| `s4of5` | 2458652 | 7,643 | 19,585 | 39.02% | 44 | 466,227 | 2026-10-15T05:26:20Z |

### Detalle HF/GLiNER repair activo

Prefijo de corrida: `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_`.

| Shard | PID | Procesados únicos | Objetivo | Avance | Errores | Variables | Último resultado UTC |
|---|---:|---:|---:|---:|---:|---:|---|
| `s0of6` | 2462500 | 11,124 | 13,558 | 82.05% | 0 | 344,844 | 2026-10-15T05:26:32Z |
| `s1of6` | 2462502 | 11,022 | 13,781 | 79.98% | 0 | 341,713 | 2026-10-15T05:26:44Z |
| `s2of6` | 2462504 | 11,067 | 13,569 | 81.56% | 0 | 343,077 | 2026-10-15T05:24:50Z |
| `s3of6` | 2462506 | 11,036 | 13,565 | 81.36% | 0 | 342,116 | 2026-10-15T05:26:28Z |
| `s4of6` | 2462508 | 11,081 | 13,717 | 80.78% | 0 | 343,511 | 2026-10-15T05:26:32Z |
| `s5of6` | 2462510 | 11,059 | 13,634 | 81.11% | 0 | 342,829 | 2026-10-15T05:26:42Z |

Quedan 15,435 resultados para alcanzar los objetivos de los seis shards repair, frente a 15,440 documentos pendientes globales HF/GLiNER. Antes de declarar cobertura completa será necesario reconciliar por `document_id` esa diferencia de 5 documentos y verificar que todos los pendientes estén cubiertos por las corridas.

## Infraestructura y evolución

| Recurso | 2026-10-13 | 2026-10-15 |
|---|---|---|
| Procesadores lógicos | 24 | 24 |
| Carga promedio 1 / 5 / 15 min | 91.79 / 90.17 / 90.21 | 92.39 / 91.53 / 88.55 |
| RAM total / usada / disponible | 250 / 66 / 183 GiB | 250 / 69 / 181 GiB |
| Swap usada | No informada | 0 |
| Disco usado | 690 GiB; 39% | 696 GiB; 40% |
| Disco libre | 1.1 TiB | 1.1 TiB |
| GPU vía `nvidia-smi` | Error NVML | Persiste error NVML |
| Procesos de predicción activos | 11 | 11 |

La muestra `vmstat` del 15 de octubre muestra 0–1% de CPU ociosa y 88–96 tareas ejecutables en las dos muestras de intervalo. La CPU está saturada; la memoria y el disco mantienen margen.

Persiste `Driver/library version mismatch`: biblioteca NVML 595.99 y módulo NVIDIA cargado 595.84. Esto impide consultar la GPU con `nvidia-smi`; por sí solo no demuestra si cada proceso utiliza CUDA.

Ollama local responde y reporta cero modelos cargados. El procesamiento LLM registra resultados de `deepseek` y `openai`; el estado de Ollama local no verifica la disponibilidad de esos proveedores remotos.

## Ritmo del periodo y estimación orientativa

Se utiliza el aumento neto deduplicado entre el informe publicado del 13 de octubre y este corte, sobre 33.1253 horas. Es un promedio del periodo, distinto de la ventana de 60 segundos utilizada en el informe anterior.

| Flujo | Aumento neto | Promedio docs/h | Promedio docs/min | Pendiente real | Tiempo orientativo restante |
|---|---:|---:|---:|---:|---|
| HF/GLiNER | 15,722 | 474.6 | 7.91 | 15,440 | ~32.5 horas |
| LLM | 15,489 | 467.6 | 7.79 | 60,377 | ~129.1 horas (~5.4 días) |

Fórmula: `tiempo_restante = pendiente_real / (aumento_neto / horas_transcurridas)`.

Estas estimaciones suponen el mismo rendimiento y disponibilidad. La terminación de shards puede cambiar la contención de CPU y la velocidad. El fallo residual LLM de `bluesky` y la diferencia HF/GLiNER de 5 documentos requieren verificación específica; el cálculo no garantiza que las corridas activas cierren todos los pendientes.

## Metodología y límites del corte

1. Se consultó el servidor por SSH y se leyeron resultados, checkpoints, logs y estado de procesos. No se reinició ni modificó el procesamiento remoto.
2. Se mantuvo el universo de los informes anteriores: 169,248 documentos, distribuidos en 64,670 de `bluesky`, 1,198 de `gdelt` y 103,380 de `media_cloud`.
3. Se incluyeron los archivos `results_incremental.jsonl` de:
   - HF/GLiNER: `full_gliner25_multi_no_llm` y `full_parallel_gliner25_multi_no_llm_*`.
   - LLM: `full_by_source_all_variables_llm_*` y `full_parallel_all_variables_llm_*`.
4. Se excluyeron corridas smoke y otros directorios fuera de esos nombres. La lista exacta de corridas incluidas está en el JSON adjunto.
5. Se deduplicó por `document_id`, priorizando `success` sobre cualquier otro estado y, en empate, el registro más reciente por `computed_at`.
6. Se calculó cada cobertura usando el estado de su propio flujo: `hf_metadata.status` o `llm_metadata.status`. No se mezclaron resultados HF de las corridas LLM con la serie HF sin LLM.
7. Al inicio de la auditoría se fijó el tamaño de cada archivo de resultados. Solo se leyeron líneas completas dentro de ese límite; los procesos siguieron escribiendo durante la revisión.
8. Los checkpoints, eventos de error y conteos de variables se leyeron durante la ventana de auditoría y pueden estar unos segundos por delante del corte de resultados.
9. La evidencia conserva conteos, tamaños de resultados de las corridas detalladas, procesos activos, estados, proveedores y una reconstrucción histórica por `computed_at`.

### Conciliación con el informe anterior

El informe del 13 de octubre publicó 138,086 éxitos HF/GLiNER y 93,382 LLM. Una reconstrucción sobre los registros actuales, filtrando `computed_at <= 2026-10-13T20:19:24Z`, obtiene 138,085 HF/GLiNER y 93,380 LLM.

La diferencia es de 1 y 2 documentos, respectivamente. Es compatible con diferencias entre los momentos de lectura de archivos activos, aunque no se verificó su causa exacta. Para mantener continuidad, las tablas de evolución conservan las cifras publicadas, sin reemplazarlas silenciosamente por la reconstrucción. Los valores actuales se calcularon directamente sobre los resultados persistidos.

## Recomendaciones de seguimiento

1. Mantener el seguimiento de los 6 shards repair y los 5 shards LLM de `media_cloud`, verificando incremento de resultados persistidos y estado exitoso.
2. Conciliar los 5 documentos de diferencia entre el pendiente HF global y el restante de los shards antes de declarar cierre.
3. Identificar el documento LLM fallido de `bluesky` para su reproceso específico.
4. Revisar los 206 eventos de `errors.jsonl` del grupo LLM sin confundirlos con fallos finales deduplicados.
5. Programar una revisión del desajuste NVIDIA y de la concurrencia de CPU; no se aplicaron cambios de infraestructura en esta revisión.
6. Mantener como cifras oficiales los documentos exitosos únicos, separados de los registros brutos y del avance por corrida.

## Cifra para reportar

> **HF/GLiNER sin LLM:** 153,808 documentos únicos con estado exitoso sobre 169,248 objetivo (**90.88%**). Aumento de **15,722** respecto al 13 de octubre. Pendientes: **15,440**, todos de `media_cloud`.
>
> **LLM:** 108,871 documentos únicos con estado exitoso sobre 169,248 objetivo (**64.33%**). Aumento de **15,489** respecto al 13 de octubre. Pendientes: **60,377**: 60,376 de `media_cloud` y 1 de `bluesky`.


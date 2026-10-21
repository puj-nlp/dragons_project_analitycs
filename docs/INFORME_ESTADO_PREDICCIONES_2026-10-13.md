# Informe de estado de predicciones DRAGONS

Fecha de corte remoto: 2026-10-13 15:19:24 America/Bogota  
Fecha de corte UTC: 2026-10-13T20:19:24Z  
Servidor verificado: `puj-nlp`  
Repositorio remoto: `/home/support/project/puj/respos/dragons_project_analitycs`

## Resumen ejecutivo

El procesamiento remoto de predicciones sigue activo. En el corte revisado hay 11 procesos vivos: 5 procesos LLM para `media_cloud` y 6 procesos HF/GLiNER no-LLM de reparacion para `media_cloud`.

Desde el informe del 2026-10-09, el avance real deduplicado mejoro de forma importante:

| Metrica real deduplicada | 2026-10-09 | 2026-10-13 | Cambio |
|---|---:|---:|---:|
| HF/GLiNER correcto | 92,163 | 138,086 | +45,923 |
| Cobertura HF/GLiNER | 54.45% | 81.59% | +27.14 pp |
| LLM correcto | 23,734 | 93,382 | +69,648 |
| Cobertura LLM | 14.02% | 55.17% | +41.15 pp |

La metrica corregida para HF/GLiNER no-LLM, descontando reprocesos y errores, es:

| Indicador real HF/GLiNER no-LLM | Valor |
|---|---:|
| Documentos objetivo | 169,248 |
| Documentos unicos intentados | 169,248 |
| Documentos unicos con prediccion correcta | 138,086 |
| Documentos unicos con fallo y sin prediccion correcta | 31,162 |
| Cobertura real correcta | 81.59% |
| Pendiente real sin prediccion correcta | 18.41% |
| Registros brutos acumulados | 219,916 |
| Registros de reproceso o duplicacion | 50,668 |
| Lineas JSON invalidas observadas | 1 |

Conclusion principal: la cobertura HF/GLiNER no-LLM real subio a 81.59%. La brecha restante sigue concentrada en `media_cloud`. La metrica acumulada bruta de 129.94% no representa cobertura real porque suma corridas solapadas, reprocesos y reparaciones.

## Comparativa de avance procesado a hoy

Esta comparativa usa como linea base el informe del 2026-10-09 y como corte actual el estado remoto del 2026-10-13 15:19:24 America/Bogota. Los valores son deduplicados por `document_id`, por lo que representan avance real y no volumen bruto de reprocesos.

| Frente | 2026-10-09 | 2026-10-13 | Avance neto | Lectura |
|---|---:|---:|---:|---|
| HF/GLiNER correcto | 92,163 | 138,086 | +45,923 | La reparacion redujo la brecha real de `media_cloud`. |
| HF/GLiNER pendiente | 77,085 | 31,162 | -45,923 | Queda 18.41% del universo sin HF correcto. |
| Cobertura HF/GLiNER | 54.45% | 81.59% | +27.14 pp | `bluesky` y `gdelt` siguen completos; el cambio viene de `media_cloud`. |
| LLM correcto | 23,734 | 93,382 | +69,648 | LLM completo practicamente todo `bluesky` y avanzo en `media_cloud`. |
| LLM pendiente | 145,514 | 75,866 | -69,648 | Queda 44.83% del universo sin LLM correcto. |
| Cobertura LLM | 14.02% | 55.17% | +41.15 pp | El mayor salto del periodo viene del procesamiento LLM remoto v3. |

### Comparativa por fuente

| Fuente | HF correcto 2026-10-09 | HF correcto 2026-10-13 | Cambio HF | LLM correcto 2026-10-09 | LLM correcto 2026-10-13 | Cambio LLM |
|---|---:|---:|---:|---:|---:|---:|
| `bluesky` | 64,670 | 64,670 | 0 | 15,626 | 64,669 | +49,043 |
| `gdelt` | 1,198 | 1,198 | 0 | 1,198 | 1,198 | 0 |
| `media_cloud` | 26,295 | 72,218 | +45,923 | 6,910 | 27,515 | +20,605 |
| **Total** | **92,163** | **138,086** | **+45,923** | **23,734** | **93,382** | **+69,648** |

### Comparativa operativa de procesos activos

| Grupo | 2026-10-09 | 2026-10-13 | Cambio operativo |
|---|---:|---:|---|
| Procesos LLM activos | 10 | 5 | Los 5 shards LLM de `bluesky` completaron; siguen activos los 5 de `media_cloud`. |
| Procesos HF/GLiNER repair activos | 6 | 6 | La reparacion de `media_cloud` continua en los mismos 6 shards. |
| Procesos activos totales | 16 | 11 | La reduccion corresponde a la finalizacion de `bluesky` LLM. |
| Avance grupo LLM remoto v3 `media_cloud` | 2.25% aprox. | 23.16% | El grupo `media_cloud` LLM avanzo cerca de 20.9 pp. |
| Avance grupo repair PEFT v1 `media_cloud` | 5.72% | 61.92% | La reparacion HF/GLiNER avanzo 56.20 pp. |

## Metodologia de calculo real

Para mantener continuidad con el informe del 2026-10-09, el calculo real se hizo con estas reglas:

1. Se leyeron los archivos `results_incremental.jsonl` de las corridas HF/GLiNER no-LLM y LLM.
2. Se excluyeron corridas auxiliares, pruebas smoke y directorios no productivos.
3. Se deduplico por `document_id`.
4. Para cada documento se tomo el mejor estado disponible:
   - `success` tiene prioridad sobre `failed`.
   - Si hay varios registros con el mismo estado, se conserva el mas reciente por `computed_at`.
5. Solo se cuenta como prediccion correcta HF/GLiNER cuando `hf_metadata.status = success`.
6. Solo se cuenta como prediccion correcta LLM cuando `llm_metadata.status = success`.
7. Los documentos con solo `failed` se cuentan como pendientes reales, aunque existan registros brutos en los archivos.

Formula usada:

```text
cobertura_real = documentos_unicos_con_success / documentos_objetivo
```

Aplicada al corte HF/GLiNER:

```text
138,086 / 169,248 = 81.59%
```

Aplicada al corte LLM:

```text
93,382 / 169,248 = 55.17%
```

## Correccion de la estadistica acumulada

La estadistica acumulada generada por el reporte operativo fue:

| Metrica acumulada no corregida | Valor |
|---|---:|
| Registros procesados acumulados HF/GLiNER | 219,914 |
| Objetivo | 169,248 |
| Porcentaje acumulado | 129.94% |
| Procesos activos HF/GLiNER | 6 |

Esa lectura no debe usarse como cobertura real porque incluye:

- Corridas anteriores.
- Corridas fallidas.
- Reintentos.
- Reparaciones parciales.
- Registros duplicados por `document_id`.

La lectura corregida es:

| Metrica corregida | Valor |
|---|---:|
| Documentos unicos objetivo | 169,248 |
| Predicciones HF/GLiNER correctas unicas | 138,086 |
| Fallos unicos sin reparacion exitosa | 31,162 |
| Cobertura real correcta | 81.59% |

## Cobertura real HF/GLiNER por fuente

| Fuente | Total fuente | Correctos HF/GLiNER | Fallidos sin correccion | Cobertura real |
|---|---:|---:|---:|---:|
| `bluesky` | 64,670 | 64,670 | 0 | 100.00% |
| `gdelt` | 1,198 | 1,198 | 0 | 100.00% |
| `media_cloud` | 103,380 | 72,218 | 31,162 | 69.86% |
| **Total** | **169,248** | **138,086** | **31,162** | **81.59%** |

La brecha real sigue concentrada en `media_cloud`. Las fuentes `bluesky` y `gdelt` ya tienen cobertura HF/GLiNER correcta completa.

## Estado real LLM

La prediccion LLM tambien fue recalculada de forma deduplicada por `document_id`, contando solo `llm_metadata.status = success`.

| Indicador real LLM | Valor |
|---|---:|
| Documentos objetivo | 169,248 |
| Documentos unicos intentados | 93,383 |
| Documentos unicos con prediccion LLM correcta | 93,382 |
| Documentos unicos con fallo y sin prediccion correcta | 1 |
| Cobertura real LLM correcta | 55.17% |
| Pendiente real LLM | 75,866 |
| Registros brutos acumulados | 93,383 |
| Registros duplicados detectados | 0 |

### Cobertura LLM por fuente

| Fuente | Documentos con intento LLM | Correctos LLM | Fallidos sin correccion | Cobertura sobre fuente |
|---|---:|---:|---:|---:|
| `bluesky` | 64,670 | 64,669 | 1 | 100.00% |
| `gdelt` | 1,198 | 1,198 | 0 | 100.00% |
| `media_cloud` | 27,515 | 27,515 | 0 | 26.62% |
| **Total** | **93,383** | **93,382** | **1** | **55.17%** |

### Proveedores LLM exitosos

| Proveedor | Predicciones correctas |
|---|---:|
| `deepseek` | 93,341 |
| `openai` | 41 |

## Procesos activos al corte

| Grupo activo | Procesos | Procesados en grupo | Objetivo grupo | Avance grupo | Errores | Variables generadas |
|---|---:|---:|---:|---:|---:|---:|
| LLM remoto v3 `media_cloud` | 5 | 22,871 | 98,739 | 23.16% | 60 | 1,394,970 |
| Reparacion no-LLM PEFT v1 `media_cloud` | 6 | 50,666 | 81,824 | 61.92% | 0 | 1,570,646 |

El grupo LLM remoto v3 de `bluesky` ya aparece completado:

| Grupo completado | Procesos | Procesados | Objetivo | Avance | Errores | Variables generadas |
|---|---:|---:|---:|---:|---:|---:|
| LLM remoto v3 `bluesky` | 5 | 54,533 | 54,533 | 100.00% | 418 | 3,342,120 |

## Detalle de procesos LLM activos

| Run activo | Fuente | Procesados | Objetivo | Avance | Errores | Variables | Avance observado | Ultima actualizacion UTC |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `full_parallel_all_variables_llm_remote_v3_media_cloud_s0of5` | `media_cloud` | 4,558 | 19,829 | 22.99% | 11 | 278,007 | 2 docs/min | 2026-10-13T20:18:47Z |
| `full_parallel_all_variables_llm_remote_v3_media_cloud_s1of5` | `media_cloud` | 4,663 | 19,620 | 23.77% | 8 | 284,409 | 2 docs/min | 2026-10-13T20:18:46Z |
| `full_parallel_all_variables_llm_remote_v3_media_cloud_s2of5` | `media_cloud` | 4,580 | 19,880 | 23.04% | 9 | 279,337 | 1 docs/min | 2026-10-13T20:18:23Z |
| `full_parallel_all_variables_llm_remote_v3_media_cloud_s3of5` | `media_cloud` | 4,544 | 19,825 | 22.92% | 16 | 277,159 | 1 docs/min | 2026-10-13T20:18:49Z |
| `full_parallel_all_variables_llm_remote_v3_media_cloud_s4of5` | `media_cloud` | 4,526 | 19,585 | 23.11% | 16 | 276,058 | 2 docs/min | 2026-10-13T20:18:40Z |

## Detalle de procesos de reparacion HF/GLiNER activos

| Run activo | Fuente | Procesados | Objetivo | Avance | Errores | Variables | Avance observado | Ultima actualizacion UTC |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s0of6` | `media_cloud` | 8,507 | 13,558 | 62.75% | 0 | 263,717 | 1 docs/min | 2026-10-13T20:18:37Z |
| `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s1of6` | `media_cloud` | 8,399 | 13,781 | 60.95% | 0 | 260,369 | 2 docs/min | 2026-10-13T20:19:11Z |
| `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s2of6` | `media_cloud` | 8,433 | 13,569 | 62.15% | 0 | 261,423 | 1 docs/min | 2026-10-13T20:18:27Z |
| `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s3of6` | `media_cloud` | 8,415 | 13,565 | 62.03% | 0 | 260,865 | 1 docs/min | 2026-10-13T20:18:50Z |
| `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s4of6` | `media_cloud` | 8,479 | 13,717 | 61.81% | 0 | 262,849 | 1 docs/min | 2026-10-13T20:18:29Z |
| `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s5of6` | `media_cloud` | 8,433 | 13,634 | 61.85% | 0 | 261,423 | 1 docs/min | 2026-10-13T20:18:16Z |

## Errores observados

### HF/GLiNER no-LLM

| Estado final por documento | Conteo |
|---|---:|
| `success` | 138,086 |
| `failed` | 31,162 |

| Estado bruto de registros HF/GLiNER | Conteo |
|---|---:|
| Registros brutos acumulados | 219,916 |
| Documentos unicos intentados | 169,248 |
| Registros de reproceso o duplicacion | 50,668 |
| Lineas JSON invalidas | 1 |

Interpretacion: existen 50,668 registros adicionales por reproceso o duplicacion. Esos registros no deben sumarse a la cobertura real.

### LLM

| Estado final LLM por documento | Conteo |
|---|---:|
| `success` | 93,382 |
| `failed` | 1 |

El unico fallo final deduplicado LLM sigue siendo bajo frente al total intentado. Los procesos activos de `media_cloud` muestran algunos errores operativos, pero `llm_status` esta en `success` para los documentos ya procesados.

## Infraestructura remota

| Recurso | Estado |
|---|---|
| Procesadores logicos | 24 |
| Carga promedio | 91.79, 90.17, 90.21 |
| Memoria | 250 GiB total, 66 GiB usada, 183 GiB disponible |
| Disco del repo | 1.9 TiB total, 690 GiB usado, 1.1 TiB libre, 39% usado |
| GPU | No disponible por `Driver/library version mismatch` |
| Procesos activos de prediccion | 11 |

La carga de CPU esta muy alta frente a los 24 procesadores logicos. Ademas, `nvidia-smi` no pudo inicializar NVML por desajuste entre driver y libreria, por lo que este corte no permite validar uso real de GPU.

## Lectura operativa

1. HF/GLiNER real esta completo para `bluesky` y `gdelt`.
2. HF/GLiNER en `media_cloud` paso de 26,295 correctos a 72,218 correctos.
3. La reparacion `repair_peft_v1` sigue funcionando sin errores al corte.
4. LLM real ya cubre casi todo `bluesky`, todo `gdelt` y 26.62% de `media_cloud`.
5. Quedan 31,162 documentos sin prediccion HF/GLiNER correcta.
6. Quedan 75,866 documentos sin prediccion LLM correcta.
7. La velocidad observada en la ventana de 60 segundos fue baja: 7 docs/min HF/GLiNER acumulado y 8 docs/min LLM acumulado.

## Estimacion simple de finalizacion

Estas estimaciones usan la velocidad observada en una ventana corta de 60 segundos, por lo que deben leerse como orientativas:

| Flujo | Pendiente real | Velocidad observada | Tiempo estimado |
|---|---:|---:|---:|
| HF/GLiNER no-LLM | 31,162 docs | 7 docs/min | ~74.2 horas |
| LLM | 75,866 docs | 8 docs/min | ~158.1 horas |

## Recomendaciones

1. Mantener como cifra oficial la metrica deduplicada, no la metrica acumulada bruta.
2. Mantener la reparacion `repair_peft_v1` hasta cerrar los 31,162 documentos pendientes de `media_cloud`.
3. Mantener los 5 shards LLM de `media_cloud`; los shards de `bluesky` ya completaron.
4. Revisar el problema de GPU/NVML (`Driver/library version mismatch`) porque impide validar el estado de GPU con `nvidia-smi`.
5. Vigilar la carga del servidor: el load average cercano a 90 es alto para 24 CPUs logicas.
6. En futuros reportes, seguir separando:
   - registros brutos,
   - documentos unicos intentados,
   - documentos unicos exitosos,
   - documentos unicos fallidos,
   - reprocesos.

## Cifra oficial para reportar

La cifra recomendada para informe externo o de seguimiento es:

```text
HF/GLiNER no-LLM:
138,086 documentos con prediccion correcta unica sobre 169,248 documentos objetivo.
Cobertura real: 81.59%.
Pendiente real: 31,162 documentos, concentrados en media_cloud.

LLM:
93,382 documentos con prediccion correcta unica sobre 169,248 documentos objetivo.
Cobertura real: 55.17%.
Pendiente real: 75,866 documentos, concentrados en media_cloud.
```

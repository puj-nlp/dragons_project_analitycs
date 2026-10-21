# Informe de estado de predicciones DRAGONS

Fecha de corte remoto: 2026-10-09 09:01:40 America/Bogota  
Fecha de corte UTC: 2026-10-09T14:01:40Z  
Servidor verificado: `puj-nlp`  
Repositorio remoto: `/home/support/project/puj/respos/dragons_project_analitycs`

## Resumen ejecutivo

El procesamiento remoto de predicciones esta activo. En el corte revisado hay 16 procesos vivos: 10 procesos LLM para prediccion de todas las variables y 6 procesos HF/GLiNER no-LLM de reparacion para `media_cloud`.

La metrica corregida para HF/GLiNER no-LLM, descontando reprocesos y errores, es:

| Indicador real HF/GLiNER no-LLM | Valor |
|---|---:|
| Documentos objetivo | 169,248 |
| Documentos unicos intentados | 169,248 |
| Documentos unicos con prediccion correcta | 92,163 |
| Documentos unicos con fallo y sin prediccion correcta | 77,085 |
| Cobertura real correcta | 54.45% |
| Pendiente real sin prediccion correcta | 45.55% |
| Registros brutos acumulados | 173,992 |
| Registros de reproceso o duplicacion | 4,744 |

Conclusion principal: la cifra acumulada previa de 102.77% no representa cobertura real. Esa cifra suma corridas solapadas, reprocesos y reparaciones. La cobertura real correcta HF/GLiNER no-LLM es 54.45%.

## Metodologia de calculo real

Para evitar inflar los resultados, el calculo real se hizo con estas reglas:

1. Se leyeron los archivos `results_incremental.jsonl` de las corridas HF/GLiNER no-LLM.
2. Se excluyeron corridas LLM, pruebas smoke y directorios auxiliares.
3. Se deduplico por `document_id`.
4. Para cada documento se tomo el mejor estado disponible:
   - `success` tiene prioridad sobre `failed`.
   - Si hay varios registros con el mismo estado, se conserva el mas reciente por `computed_at`.
5. Solo se cuenta como prediccion correcta cuando `hf_metadata.status = success`.
6. Los documentos con solo `failed` se cuentan como pendientes reales, aunque existan registros brutos en los archivos.

Formula usada:

```text
cobertura_real = documentos_unicos_con_hf_success / documentos_objetivo
```

Aplicada al corte:

```text
92,163 / 169,248 = 54.45%
```

## Correccion de la estadistica acumulada

La estadistica acumulada generada por el reporte operativo fue:

| Metrica acumulada no corregida | Valor |
|---|---:|
| Registros procesados acumulados | 173,929 |
| Objetivo | 169,248 |
| Porcentaje acumulado | 102.77% |
| Procesos activos | 6 |

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
| Predicciones HF/GLiNER correctas unicas | 92,163 |
| Fallos unicos sin reparacion exitosa | 77,085 |
| Cobertura real correcta | 54.45% |

## Cobertura real HF/GLiNER por fuente

| Fuente | Total fuente | Correctos HF/GLiNER | Fallidos sin correccion | Cobertura real |
|---|---:|---:|---:|---:|
| `bluesky` | 64,670 | 64,670 | 0 | 100.00% |
| `gdelt` | 1,198 | 1,198 | 0 | 100.00% |
| `media_cloud` | 103,380 | 26,295 | 77,085 | 25.44% |
| **Total** | **169,248** | **92,163** | **77,085** | **54.45%** |

La brecha real esta concentrada en `media_cloud`. Las fuentes `bluesky` y `gdelt` ya tienen cobertura HF/GLiNER correcta completa en este corte.

## Estado real LLM

La prediccion LLM tambien fue recalculada de forma deduplicada por `document_id`, contando solo `llm_metadata.status = success`.

| Indicador real LLM | Valor |
|---|---:|
| Documentos objetivo | 169,248 |
| Documentos unicos intentados | 23,735 |
| Documentos unicos con prediccion LLM correcta | 23,734 |
| Documentos unicos con fallo y sin prediccion correcta | 1 |
| Cobertura real LLM correcta | 14.02% |
| Pendiente real LLM | 145,514 |
| Registros brutos acumulados | 23,735 |
| Registros duplicados detectados | 0 |

### Cobertura LLM por fuente

| Fuente | Documentos con intento LLM | Correctos LLM | Fallidos sin correccion |
|---|---:|---:|---:|
| `bluesky` | 15,627 | 15,626 | 1 |
| `gdelt` | 1,198 | 1,198 | 0 |
| `media_cloud` | 6,910 | 6,910 | 0 |
| **Total** | **23,735** | **23,734** | **1** |

### Proveedores LLM exitosos

| Proveedor | Predicciones correctas |
|---|---:|
| `deepseek` | 23,726 |
| `openai` | 8 |

## Procesos activos al corte

| Grupo activo | Procesos | Procesados en grupo | Objetivo grupo | Avance grupo | Errores | Variables generadas |
|---|---:|---:|---:|---:|---:|---:|
| LLM remoto v3 | 10 | 7,632 | 153,272 | 4.98% | 123 | 468,365 |
| Reparacion no-LLM PEFT v1 | 6 | 4,681 | 81,824 | 5.72% | 0 | 145,111 |

La reparacion no-LLM PEFT v1 esta corrigiendo fallos previos de `media_cloud`. Al corte, esa reparacion no registra errores.

## Detalle de procesos LLM activos

| Run activo | Fuente | Procesados | Objetivo | Avance | Errores | Variables | Ultima actualizacion UTC |
|---|---|---:|---:|---:|---:|---:|---|
| `full_parallel_all_variables_llm_remote_v3_bluesky_s0of5` | `bluesky` | 1,084 | 10,993 | 9.86% | 18 | 66,736 | 2026-10-09T14:01:16Z |
| `full_parallel_all_variables_llm_remote_v3_bluesky_s1of5` | `bluesky` | 1,081 | 10,918 | 9.90% | 15 | 66,500 | 2026-10-09T14:01:00Z |
| `full_parallel_all_variables_llm_remote_v3_bluesky_s2of5` | `bluesky` | 1,082 | 10,831 | 9.99% | 15 | 66,614 | 2026-10-09T14:01:07Z |
| `full_parallel_all_variables_llm_remote_v3_bluesky_s3of5` | `bluesky` | 1,075 | 10,950 | 9.82% | 21 | 66,158 | 2026-10-09T14:01:08Z |
| `full_parallel_all_variables_llm_remote_v3_bluesky_s4of5` | `bluesky` | 1,077 | 10,841 | 9.93% | 17 | 66,237 | 2026-10-09T14:01:32Z |
| `full_parallel_all_variables_llm_remote_v3_media_cloud_s0of5` | `media_cloud` | 450 | 19,829 | 2.27% | 8 | 27,427 | 2026-10-09T14:01:27Z |
| `full_parallel_all_variables_llm_remote_v3_media_cloud_s1of5` | `media_cloud` | 450 | 19,620 | 2.29% | 7 | 27,433 | 2026-10-09T14:01:29Z |
| `full_parallel_all_variables_llm_remote_v3_media_cloud_s2of5` | `media_cloud` | 440 | 19,880 | 2.21% | 7 | 26,821 | 2026-10-09T14:00:35Z |
| `full_parallel_all_variables_llm_remote_v3_media_cloud_s3of5` | `media_cloud` | 451 | 19,825 | 2.27% | 7 | 27,493 | 2026-10-09T14:01:20Z |
| `full_parallel_all_variables_llm_remote_v3_media_cloud_s4of5` | `media_cloud` | 442 | 19,585 | 2.26% | 8 | 26,946 | 2026-10-09T14:01:00Z |

## Detalle de procesos de reparacion HF/GLiNER activos

| Run activo | Fuente | Procesados | Objetivo | Avance | Errores | Variables | Ultima actualizacion UTC |
|---|---|---:|---:|---:|---:|---:|---|
| `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s0of6` | `media_cloud` | 795 | 13,558 | 5.86% | 0 | 24,645 | 2026-10-09T14:01:17Z |
| `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s1of6` | `media_cloud` | 786 | 13,781 | 5.70% | 0 | 24,366 | 2026-10-09T14:01:28Z |
| `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s2of6` | `media_cloud` | 777 | 13,569 | 5.73% | 0 | 24,087 | 2026-10-09T14:01:25Z |
| `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s3of6` | `media_cloud` | 762 | 13,565 | 5.62% | 0 | 23,622 | 2026-10-09T14:01:13Z |
| `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s4of6` | `media_cloud` | 787 | 13,717 | 5.74% | 0 | 24,397 | 2026-10-09T14:01:29Z |
| `full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s5of6` | `media_cloud` | 774 | 13,634 | 5.68% | 0 | 23,994 | 2026-10-09T14:01:27Z |

## Errores observados

### HF/GLiNER no-LLM

| Estado de registros HF/GLiNER | Conteo bruto |
|---|---:|
| `success` | 92,163 |
| `failed` | 81,829 |

Despues de deduplicar por documento:

| Estado final por documento | Conteo |
|---|---:|
| `success` | 92,163 |
| `failed` | 77,085 |

Interpretacion: existen 4,744 registros adicionales por reproceso o duplicacion. Esos registros no deben sumarse a la cobertura real.

### LLM

| Estado final LLM por documento | Conteo |
|---|---:|
| `success` | 23,734 |
| `failed` | 1 |

Los errores LLM activos observados son principalmente `JSONDecodeError` en respuestas de DeepSeek. Aun asi, el volumen de fallos finales deduplicados es bajo: 1 documento sin prediccion correcta en el conjunto LLM intentado.

## Infraestructura remota

| Recurso | Estado |
|---|---|
| Procesadores logicos | 24 |
| GPU | NVIDIA RTX 4500 Ada Generation |
| Memoria GPU total | 24,570 MiB |
| Memoria GPU libre al corte | 22,715 MiB |
| Utilizacion GPU | 0% |
| Procesos activos de prediccion | 16 |

La carga de trabajo actual parece estar limitada principalmente por CPU/concurrencia y no por GPU, porque la GPU estaba practicamente libre al corte.

## Lectura operativa

1. HF/GLiNER real esta completo para `bluesky` y `gdelt`.
2. HF/GLiNER tiene una brecha grande en `media_cloud`: 77,085 documentos siguen sin prediccion correcta.
3. La reparacion `repair_peft_v1` esta funcionando correctamente y sin errores al corte.
4. LLM real va en 14.02% de cobertura correcta total.
5. LLM avanza con 10 workers activos, repartidos entre `bluesky` y `media_cloud`.
6. La estadistica acumulada automatica es util para monitoreo bruto, pero no para reportar cobertura real.

## Recomendaciones

1. Usar la metrica deduplicada como fuente oficial de avance:
   - HF/GLiNER correcto real: 92,163 / 169,248 = 54.45%.
   - LLM correcto real: 23,734 / 169,248 = 14.02%.
2. Mantener la reparacion `repair_peft_v1` hasta reducir los 77,085 fallos de `media_cloud`.
3. En futuros reportes, separar siempre:
   - registros brutos,
   - documentos unicos intentados,
   - documentos unicos exitosos,
   - documentos unicos fallidos,
   - reprocesos.
4. No presentar porcentajes mayores a 100% como cobertura. Esos porcentajes deben etiquetarse como volumen acumulado bruto.
5. Revisar si conviene bajar o ajustar la concurrencia LLM si los `JSONDecodeError` aumentan, aunque por ahora el fallo final deduplicado LLM es bajo.

## Cifra oficial para reportar

La cifra recomendada para informe externo o de seguimiento es:

```text
HF/GLiNER no-LLM:
92,163 documentos con prediccion correcta unica sobre 169,248 documentos objetivo.
Cobertura real: 54.45%.
Pendiente real: 77,085 documentos, concentrados en media_cloud.

LLM:
23,734 documentos con prediccion correcta unica sobre 169,248 documentos objetivo.
Cobertura real: 14.02%.
Pendiente real: 145,514 documentos.
```

# Runbook de procesamiento resumible

Fecha: 2026-10-06

## Objetivo

Procesar toda la base analitica de DRAGONS sin perder avance si la maquina se suspende, se apaga o el proceso se interrumpe.

El pipeline escribe resultados por documento en:

```text
data/processed/pilot_variables/<run_id>/results_incremental.jsonl
```

Tambien mantiene checkpoint en:

```text
data/processed/pilot_variables/<run_id>/checkpoint.json
```

Al reactivar el mismo `run_id` con `--resume`, el proceso carga los documentos ya procesados y continua desde los pendientes.

## Comando recomendado para iniciar toda la base

Primer pase recomendado: GLiNER2.5 multilingue, sin LLM, para extraer entidades y variables deterministicas sin costo de API.

```powershell
.\scripts\run_full_resumable.ps1
```

Equivale a:

```powershell
py scripts\run_pilot_processing.py --run-id full_gliner25_multi_no_llm --all-documents --resume --no-llm --hf-model fastino/gliner2.5-multi-v1
```

## Reactivar despues de suspension o corte

Ejecutar el mismo comando:

```powershell
.\scripts\run_full_resumable.ps1
```

El pipeline detecta los `document_id` existentes en `results_incremental.jsonl` y continua con los pendientes.

## Prueba rapida antes de la corrida completa

```powershell
.\scripts\run_full_resumable.ps1 -RunId smoke_full_resume -Model fastino/gliner2.5-small-v1 -MaxDocuments 25
```

## Corrida con modelo pequeno

Si se necesita una corrida mas rapida para validar todo el flujo:

```powershell
.\scripts\run_full_resumable.ps1 -RunId full_gliner25_small_no_llm -Model fastino/gliner2.5-small-v1
```

## Corrida con LLM

No iniciar sobre toda la base sin aprobar costo, tiempo y cuota. Para una muestra:

```powershell
py scripts\run_pilot_processing.py --run-id llm_sample_15 --limit-per-source 5 --resume --hf-model fastino/gliner2.5-small-v1
```

Para toda la base con LLM, solo despues de aprobar presupuesto:

```powershell
.\scripts\run_full_resumable.ps1 -RunId full_gliner25_multi_llm -WithLlm
```

## Archivos de log

Por cada corrida:

```text
logs/variable_processing/<run_id>/run.log
logs/variable_processing/<run_id>/documents.jsonl
logs/variable_processing/<run_id>/variables.jsonl
logs/variable_processing/<run_id>/errors.jsonl
logs/variable_processing/<run_id>/run_summary.jsonl
```

Salidas analiticas:

```text
data/processed/pilot_variables/<run_id>/analytics_variable_results_flat.csv
data/processed/pilot_variables/<run_id>/analytics_variable_results_flat.parquet
data/processed/pilot_variables/<run_id>/analytics_variable_results_raw_json.parquet
data/processed/pilot_variables/<run_id>/results_incremental.jsonl
data/processed/pilot_variables/<run_id>/checkpoint.json
data/processed/pilot_variables/<run_id>/run_record.json
```

## Ver estado de avance

```powershell
Get-Content data\processed\pilot_variables\full_gliner25_multi_no_llm\checkpoint.json
```

Contar documentos ya persistidos:

```powershell
(Get-Content data\processed\pilot_variables\full_gliner25_multi_no_llm\results_incremental.jsonl).Count
```

Ver errores:

```powershell
Get-Content logs\variable_processing\full_gliner25_multi_no_llm\errors.jsonl -Tail 20
```

## Validacion de reanudacion ya probada

Se ejecuto una prueba con:

```powershell
py scripts\run_pilot_processing.py --run-id resume_smoke_checkpoint --limit-per-source 3 --max-documents 5 --no-llm --no-hf --stop-after 2
py scripts\run_pilot_processing.py --run-id resume_smoke_checkpoint --limit-per-source 3 --max-documents 5 --no-llm --no-hf --resume
```

Resultado:

- Primera ejecucion: 2 documentos procesados, estado `partial`.
- Segunda ejecucion: 2 documentos saltados como existentes, 3 documentos nuevos procesados, estado `completed`.
- Total final: 5 documentos.

## Nota operativa

Si se cambia el modelo, el prompt o la configuracion de variables, usar un `run_id` nuevo. Si se reutiliza el mismo `run_id`, `--resume` asumira que los documentos existentes ya son validos y no los recalculara.


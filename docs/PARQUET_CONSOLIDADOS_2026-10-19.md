# Parquet consolidados por documento — 2026-10-19

## Archivos nuevos

Se generaron tres Parquet independientes de los archivos históricos por corrida. Cada uno contiene **169,248 filas**, con `document_id` único y el mismo conjunto y orden de IDs.

Ubicación en el servidor `support@192.168.194.86`, puerto SSH `722`:

```text
/home/support/project/puj/respos/dragons_project_analitycs/data/processed/consolidated_predictions/2026-10-19/
```

| Archivo | Contenido | Filas | Columnas | Tamaño aproximado |
|---|---|---:|---:|---:|
| `variables_llm.parquet` | Todas las variables del resultado LLM seleccionado, estado, modelo y procedencia | 169,248 | 44 | 386.4 MiB |
| `variables_gliner.parquet` | Entidades, conteos por etiqueta y etiquetas principales GLiNER, estado y procedencia | 169,248 | 14 | 141.3 MiB |
| `documentos_metadatos.parquet` | Texto completo, título, URL, fuente, metadatos originales, métricas ETL y variables determinísticas | 169,248 | 78 | 403.7 MiB |

El directorio también contiene `manifest.json`, con esquemas, codificaciones, hashes SHA-256, corridas de origen y resultados de validación. Hay una [copia local del manifiesto](../data/processed/consolidated_predictions/2026-10-19/manifest.json).

Los tres Parquet completos están en el servidor. La descarga local se interrumpió por la baja velocidad del enlace; el fragmento local de documentos se dejó con extensión `.parquet.partial` y no es un Parquet utilizable. No se presenta esa descarga parcial como copia completa.

## Selección del mejor resultado

- Se recorrieron las 84 corridas productivas e históricas que forman el conjunto de resultados calculados.
- LLM y GLiNER se seleccionaron de forma independiente por `document_id`.
- Se priorizó `success` sobre `failed`; después, el `computed_at` más reciente y, en empate, `result_id`.
- Los estados `skipped` y desconocidos no se tomaron como intentos de predicción.
- Para GLiNER se consideraron también resultados HF calculados dentro de corridas LLM. Se recuperaron **5 éxitos ya existentes** que no estaban incluidos en la serie histórica de HF sin LLM.
- No se combinaron parcialmente campos de varias respuestas para inventar una predicción: cada fila de variables procede de un resultado seleccionado completo.

| Flujo consolidado | Éxitos | Fallos conservados |
|---|---:|---:|
| LLM | 169,247 | 1 |
| GLiNER | 169,248 | 0 |

La diferencia con los cinco fallos HF del informe de cierre anterior se debe al alcance de selección: aquel informe medía HF **sin LLM**; este nuevo Parquet utiliza todos los resultados GLiNER disponibles, incluidas las corridas LLM. No se recalcularon inferencias ni se alteraron los informes históricos o las bases de datos.

## Variables y tipos

### Variables LLM

Las columnas de variables comienzan por `llm__`. Incluyen relevancia, temas, sentimiento, emociones, narrativas, encuadres, actores, responsabilidad, gobernanza, justicia, incertidumbre, confianza y banderas de calidad, además de las demás claves presentes en los resultados seleccionados.

Se conservaron tanto las claves actuales como las variantes históricas presentes, por ejemplo `llm__stakeholder_presence` y `llm__stakeholder_present`.

También se incluyen:

- `status`, `provider`, `model`, `run_id`, `result_id`, `computed_at` e `input_text_hash`.
- `metadata_json`: metadatos completos del cálculo LLM.
- `variables_json`: diccionario completo de variables, sin pérdida de las estructuras originales, normalizando números no finitos a `null`.

### Variables GLiNER

- `gliner__gliner_named_entities`: entidades completas.
- `gliner__gliner_entity_counts_by_label`: conteos por etiqueta.
- `gliner__gliner_top_entity_labels`: etiquetas principales.
- Las mismas columnas de estado y procedencia, `metadata_json` y `variables_json`.

### Documentos y metadatos

Se conservaron todas las columnas del origen documental para los IDs procesados, incluyendo `text` completo, `title`, `url`, `source`, `collection_name`, `mongo_id`, `country_key`, `language`, `created_at`, `metadata` y `raw_metadata`.

Se añadieron las métricas calculadas `etl__*`, las variables `deterministic__*`, sus diccionarios completos en JSON y los IDs de corrida y hashes de entrada de ambos modelos. Las columnas originales de la fuente mantienen sus tipos de origen; las columnas calculadas prefijadas conservan sus valores calculados.

La fuente documental actual tiene 176,080 filas. Se seleccionó exclusivamente el universo de 169,248 IDs con resultados calculados, para que los tres Parquet se puedan unir uno a uno.

Todos los textos coincidieron con los hashes de entrada de los resultados seleccionados. No se encontraron diferencias de versión de texto entre LLM y GLiNER para estos IDs. No se usó `text_preview` como sustituto del documento completo.

### Estructuras anidadas y JSON

Se utilizan tipos Parquet nativos siempre que permiten conservar los valores: números, booleanos, cadenas, listas y estructuras anidadas.

`llm__biodiversity_object` tiene representaciones heterogéneas entre respuestas, por lo que se conserva como JSON para evitar pérdida de contenido o coerciones incorrectas. El manifiesto marca esta columna con `encoding: json`. Los campos terminados en `_json` también contienen JSON serializado por definición.

`metadata` y `raw_metadata` de documentos mantienen el formato de la fuente original, que en este corte es texto.

## Lectura y unión en Python

Ejecutar en el servidor, con un entorno que tenga `pandas` y `pyarrow`:

```python
from pathlib import Path
import pandas as pd

base = Path("/home/support/project/puj/respos/dragons_project_analitycs/data/processed/consolidated_predictions/2026-10-19")

documentos = pd.read_parquet(
    base / "documentos_metadatos.parquet",
    columns=["document_id", "source", "title", "text", "metadata", "llm_status", "gliner_status"],
)
llm = pd.read_parquet(
    base / "variables_llm.parquet",
    columns=["document_id", "llm__sentiment_label", "llm__primary_topic", "llm__confidence"],
)
gliner = pd.read_parquet(
    base / "variables_gliner.parquet",
    columns=["document_id", "gliner__gliner_named_entities", "gliner__gliner_entity_counts_by_label"],
)

completo = documentos.merge(llm, on="document_id", validate="one_to_one").merge(
    gliner, on="document_id", validate="one_to_one"
)
assert len(completo) == 169248
assert completo["document_id"].is_unique
```

Para recuperar el diccionario completo de una predicción:

```python
import json

llm_completo = pd.read_parquet(base / "variables_llm.parquet")
variables = json.loads(llm_completo.loc[0, "variables_json"])
```

Las filas fallidas se conservan con su estado explícito. Para análisis que requieren predicciones LLM exitosas, filtrar `status == "success"` en su Parquet o `llm_status == "success"` en documentos.

## Validación realizada

1. Escritura y relectura de los tres archivos con PyArrow.
2. Comparación de cada columna contra los valores elegidos antes de exportar.
3. Comprobación de estructuras anidadas y de la decodificación de columnas JSON.
4. Coincidencia exacta del conjunto y orden de los 169,248 IDs en los tres archivos, sin duplicados.
5. Verificación del texto completo por hash contra las entradas de los resultados seleccionados.
6. Generación de SHA-256 por archivo, registrados en el manifiesto.

## Regeneración

Desde el repositorio remoto, indicando otra carpeta nueva o vacía:

```bash
.venv/bin/python scripts/export_consolidated_parquets.py \
  --output-dir data/processed/consolidated_predictions/OTRO_CORTE
```

El exportador no reemplaza los Parquet de las corridas ni escribe en PostgreSQL o MongoDB. Rechaza directorios de salida que ya contienen archivos.

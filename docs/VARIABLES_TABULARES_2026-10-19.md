# Variables y documentos en tablas planas

Los archivos nuevos están en `data/processed/consolidated_predictions/2026-10-19/tabular/`:

- `variables_gliner_tabular.parquet`
- `variables_llm_tabular.parquet`

| Archivo | Filas | Columnas escalares |
|---|---:|---:|
| `variables_gliner_tabular.parquet` | 169.248 | 1.523 |
| `variables_llm_tabular.parquet` | 169.248 | 1.187 |

Cada tabla conserva una fila por documento, la columna `document_id`, el orden original y los campos de procedencia (`source`, `status`, `model`, `provider`, `run_id`, `result_id`, `computed_at`, `input_text_hash`). Los archivos originales se mantienen.

## Cómo se expanden las variables

Todas las celdas son escalares: texto, entero, decimal, booleano o nulo. No hay columnas de tipo lista, estructura, objeto ni diccionarios serializados como JSON. Las variables se toman de `variables_json`, que conserva el diccionario completo de las extracciones; las columnas originales `llm__*`/`gliner__*` son representaciones redundantes de esas mismas variables y no se duplican. `metadata_json` se expande bajo el prefijo `prediction_metadata`.

- Un objeto se expande por campo: `llm__dominant_frame.frame_label`, `llm__claim_typology.main_claim`, `llm__stakeholder_presence.government_present`.
- Una lista se expande por posición, empezando en 1: `llm__emotion_labels[0001]`, `llm__actors[0001].text`, `llm__actors[0001].role`.
- Cada entidad GLiNER tiene columnas de texto, etiqueta, puntuación y posiciones: `gliner__gliner_named_entities[0001].text`, `.label`, `.score`, `.start`, `.end`. La posición identifica el orden del resultado, no la identidad global de una entidad entre documentos.
- Los conteos se expanden por etiqueta, por ejemplo `gliner__gliner_entity_counts_by_label.country`. Se conservan los nulos originales; no se convierten automáticamente en ceros.
- Las entidades incluidas en variables LLM, como `llm__metadata.gliner_entities_sample`, también se expanden por posición y atributo. Lo mismo ocurre con actores, menciones de especies, ecosistemas, políticas, instituciones y cualquier otra lista encontrada.
- No se concatenan varias entidades en una celda ni se fija un máximo arbitrario de posiciones. El esquema incluye todas las posiciones observadas en el archivo completo.
- Una posición inexistente queda nula. No se multiplica el número de filas ni se crean productos cartesianos al expandir listas.

`llm__biodiversity_object`, que contenía JSON por tener representaciones heterogéneas, se decodifica y expande de la misma manera. Cualquier cadena que sea un objeto/lista JSON válido dentro de los valores se decodifica recursivamente; los textos ordinarios se mantienen.

## Nombres y columnas auxiliares

- `#length` indica la longitud original de una lista; 0 significa lista vacía y nulo indica que no había lista en esa ruta.
- `#object` vale `true` cuando existe un objeto en esa ruta, incluso si está vacío. Permite distinguirlo de un objeto ausente/nulo sin guardar el objeto en la celda.
- Cuando una misma ruta tiene escalares de diferentes tipos, se crean columnas `#as_string`, `#as_int`, `#as_float` o `#as_bool`, según corresponda. No se fuerza un número o booleano a convertirse en texto.
- Se escapan caracteres especiales de los nombres de claves con codificación porcentual. Por ejemplo, `policy or law` aparece como `policy%20or%20law` y una clave histórica `text ` permanece distinta de `text` mediante `text%20`.
- Las variables observadas solo con valor nulo se conservan como columnas de texto anulables.

Los manifiestos contiguos `*.manifest.json` contienen el diccionario de todas las columnas, tipos, rutas de origen, máximos de longitud de las listas y hashes SHA-256. Estos JSON son archivos de auditoría externos; los Parquet no almacenan columnas JSON.

## Validación

El exportador revisa IDs no vacíos y únicos, conserva la cantidad y el orden de documentos, vuelve a leer todas las columnas y compara todos sus valores con la expansión del origen. También comprueba que el esquema final solo contenga tipos escalares y que ambos archivos compartan exactamente los mismos IDs y orden. Los fallos de inferencia se mantienen con su estado, sin eliminar filas.

## Lectura

```python
import pandas as pd

base = "data/processed/consolidated_predictions/2026-10-19/tabular/"
gliner = pd.read_parquet(
    base + "variables_gliner_tabular.parquet",
    columns=[
        "document_id",
        "gliner__gliner_named_entities[0001].text",
        "gliner__gliner_named_entities[0001].label",
        "gliner__gliner_named_entities[0001].score",
    ],
)
llm = pd.read_parquet(
    base + "variables_llm_tabular.parquet",
    columns=["document_id", "llm__primary_topic", "llm__dominant_frame.frame_label"],
)
tabla = gliner.merge(llm, on="document_id", validate="one_to_one")
```

Para SQL, los nombres con puntos/corchetes deben citarse como identificadores completos según el motor utilizado. Leer solo las columnas necesarias evita materializar una tabla ancha completa en memoria.

## Reproducción

```powershell
.\.venv\Scripts\python.exe scripts/export_flat_predictions.py --output-dir data/processed/consolidated_predictions/2026-10-19/otro_tabular
```

El exportador rechaza destinos existentes y usa archivos `.partial` durante la escritura y validación. No modifica las predicciones originales ni recalcula inferencias.

Si quedó un `.partial` completo pendiente de validación, `--resume` permite reutilizarlo y compararlo completamente con el origen antes de publicarlo. No se admite un parcial truncado ni se omite la validación. Se puede seleccionar un único archivo con `--kind gliner` o `--kind llm`.

## Documentos y metadatos

Se revisó también `data/processed/consolidated_predictions/2026-10-19/documentos_metadatos.parquet`. Tiene 169.248 filas y 78 columnas, pero no es completamente plano:

- `deterministic__keyword_matches` y `deterministic__metadata_keys` son listas nativas.
- `deterministic_variables_json`, `etl__top_terms`, `etl_metrics_json`, `metadata`, `raw_metadata`, `suffix_counts` y `top_terms` contienen objetos o listas serializados como JSON.

La copia expandida es `data/processed/consolidated_predictions/2026-10-19/tabular/documentos_metadatos_tabular.parquet`, con **169.248 filas y 748 columnas escalares**. Se incluyen todas las columnas originales, expandiendo recursivamente listas y JSON, sin eliminar metadatos redundantes. Es una conversión completa, diferente del corpus RAG, que selecciona solo campos útiles para recuperación.

Se mantienen una fila por documento, el ID, el texto completo, la colección y el orden del origen. Las columnas simples conservan sus nombres y valores; las estructuras se expanden con las mismas convenciones de rutas, posiciones, tipos y marcadores descritas arriba. El manifiesto contiguo contiene el diccionario completo de columnas y la validación de relectura. El archivo original no se modifica.

```powershell
.\.venv\Scripts\python.exe scripts/export_flat_predictions.py --kind documents
```

# dragons_project_analitycs

Repositorio de planeacion e implementacion analitica para DRAGONS WP1 / Task 1.1.

Este repositorio consume los productos del ETL en `C:\project\javeriana\repos\dragons_project_etl` y organiza el trabajo de analisis: variables, prompts, modelos, pruebas, validacion humana y SNA.

## Punto de partida

- Plan maestro: [docs/PLAN_IMPLEMENTACION_ANALITICA.md](docs/PLAN_IMPLEMENTACION_ANALITICA.md)
- Matriz de variables y metodos: [docs/MATRIZ_VARIABLES_METODOS.md](docs/MATRIZ_VARIABLES_METODOS.md)
- Catalogo operativo: [config/variables_catalog.yml](config/variables_catalog.yml)
- Datos de prueba: [data/samples/test_documents.csv](data/samples/test_documents.csv)

## Regla de trabajo actual

Hasta aprobar el alcance, se trabaja solo con datos de prueba o muestras acotadas. Los datos reales se leen desde el ETL/Parquet, pero no se procesan masivamente desde este repositorio hasta cerrar el protocolo de variables, modelos, costos y validacion.

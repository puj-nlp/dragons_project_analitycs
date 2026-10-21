# Sincronización del repositorio remoto al local — 2026-10-19

## Estado

La sincronización completa está ejecutándose en segundo plano. Este documento no certifica que todos los datos ya estén descargados: el estado actualizado se consulta en [state.json](../logs/remote_sync/20261019_005137/state.json).

- Origen: `support@192.168.194.86:722`, `/home/support/project/puj/respos/dragons_project_analitycs`.
- Destino: `C:\project\javeriana\repos\dragons_project_analitycs`.
- Inventario inicial: **1,060 archivos y 19,334,739,225 bytes**, con SHA-256 calculado en el servidor.
- Se incluyen código, configuración, documentación, muestras, resultados históricos, los tres Parquet consolidados, shards y logs del proyecto.
- Se conservan los archivos que existen únicamente en el repositorio local; no se hace una eliminación en espejo.

El enlace es lento, por lo que los archivos grandes pueden tardar varias horas. Los tres Parquet consolidados tienen prioridad sobre los demás archivos grandes.

## Integridad y conservación de cambios locales

- Se omiten archivos cuyo tamaño y SHA-256 ya coinciden.
- Cada archivo descargado se guarda primero como parcial y sólo pasa a su ruta final después de comprobar tamaño y SHA-256.
- Los archivos locales reemplazados se respaldan dentro de [backups](../logs/remote_sync/20261019_005137/backups).
- Los cambios de código se integran usando la base Git común, sin modificar el índice Git ni crear commits.
- Los conflictos que no se pueden integrar automáticamente se conservan aparte en `logs/remote_sync/20261019_005137/conflicts`.
- Se conserva el ajuste local de `report_processing_status.py` que reconoce tanto `python.exe` como `py.exe` en Windows. La versión remota sólo reconocía `python.exe`; la decisión queda registrada en `resolutions.json`.
- Se conservan las rutas Windows de `etl_parquet_dir`, `analytics_parquet` y `nlp_repo`.

No se copian el `.git` remoto, archivos `.env`, entornos Python, paquetes instalados de Linux, cachés ni configuración de IDE. La configuración y credenciales locales se mantienen. La contraseña SSH no se guarda en archivos del proceso de sincronización.

## Seguimiento

Archivos de control:

```text
logs/remote_sync/20261019_005137/state.json
logs/remote_sync/20261019_005137/manifest.json
logs/remote_sync/20261019_005137/sync.log
logs/remote_sync/20261019_005137/resolutions.json
```

Consultar el progreso desde PowerShell, dentro del repositorio:

```powershell
$state = Get-Content logs\remote_sync\20261019_005137\state.json -Raw | ConvertFrom-Json
$state | Select-Object phase, completed_files, manifest_files, updated_at_utc, pid
$state.active | ConvertTo-Json -Depth 4
```

Interpretación de `phase`:

| Estado | Significado |
|---|---|
| `downloading` | Todavía hay archivos en descarga o validación. |
| `needs_retry` | Hay archivos que requieren reintento; el proceso en segundo plano vuelve a intentarlo. |
| `complete_with_code_conflicts` | Terminó la transferencia, pero hay diferencias de código conservadas para revisión. |
| `complete` | El inventario quedó procesado, sin errores de transferencia ni conflictos sin resolver. |

Los resultados individuales distinguen archivos idénticos, descargados, actualizados, integrados y cambios locales conservados deliberadamente. `complete` no significa que se hayan eliminado los cambios locales o los archivos adicionales locales.

## Reanudación

El proceso utiliza cuatro conexiones, compresión SSH y descarga reanudable. Puede seguir trabajando sin mantener abierta la terminal de lanzamiento. Necesita que este computador permanezca encendido y pueda conectarse al servidor.

Si se apaga el equipo o el proceso ya no existe, reanudar con:

```powershell
py -3.12 scripts\pull_remote_repository.py --resume logs\remote_sync\20261019_005137 --detach
```

El comando solicita la contraseña SSH y reutiliza los parciales y los archivos ya validados. No se debe lanzar una segunda instancia mientras el PID registrado en `state.json` siga activo.

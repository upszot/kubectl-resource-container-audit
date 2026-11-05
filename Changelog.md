# Changelog


## Version 5.1
- [X] Added:
  - **Versión centralizada**: nueva fuente única de verdad en el archivo
    [`VERSION`](./VERSION). El paquete Python (`krca.__version__`), el instalador,
    la verificación posterior y `krca --version` leen ese valor, evitando
    actualizar la versión en varios archivos.
  - **Instalador 7.1**: reescritura completa del instalador (incluye las mejoras
    7.0) con lectura de `VERSION`, copia del archivo a la instalación y
    comparación de la versión esperada contra la reportada por el comando.
  - **Instalación desde un solo archivo**: se descarga el archivo comprimido de
    la rama/tag en lugar de pedir cada archivo por separado. Esto incluye
    `krca/styles.css`, `krca/resize.css` y `krca/resize.js`, que el instalador
    anterior no descargaba y eran necesarios para exportar HTML/PDF.
  - **Entorno virtual aislado**: las dependencias Python se instalan en
    `$INSTALL_DIR/venv` y ya no se modifican los paquetes globales del sistema.
  - **Instalación local/offline** con `--source DIR` (desde un checkout).
  - **Opciones de instalación**: `--prefix`, `--bin-dir`, `--branch`,
    `--no-deps`, `--uninstall`, `--yes` y `--help`.
  - **Verificación real** al finalizar: importa el paquete y ejecuta
    `kubectl-krca --version`, comparando con la versión de `VERSION`.
  - Chequeos de Python, `venv`, `curl`, `tar`, `kubectl` y `wkhtmltopdf`, con
    mensajes claros cuando falta algo.
  - Instalación **idempotente** y preparada en un directorio temporal, para no
    romper una instalación existente si la descarga o las dependencias fallan.
- [X] FIX:
  - Corregida la versión reportada por el paquete: ahora `krca --version` muestra
    `5.1`, consistente con la rama actual, en lugar de `4.5`.
  - La rama por defecto del instalador ahora es `master` (antes apuntaba a
    `v4.4`, por lo que se instalaba código desactualizado).
  - `curl` ahora falla ante errores HTTP (`-f`) y reintenta la descarga.
  - Se usa `python3 -m pip` en lugar de `pip`, evitando ambigüedades con Python 2.
  - El wrapper resuelve symlinks, por lo que funciona con cualquier `--prefix`.
  - Se elimina la necesidad de configurar `PYTHONPATH` global y se limpian los
    restos de instalaciones anteriores (`/etc/profile.d/krca.sh` y líneas del
    `.bashrc`).
  - El desinstalador valida que los symlinks apunten a KRCA antes de borrarlos,
    y ya no elimina archivos ajenos.

## Version 4.5
- [X] Added:
  - **Análisis histórico con Prometheus**: nuevo modo `--history` que consulta el
    Prometheus (kube-prometheus-stack) del mismo cluster y agrega las columnas
    `CPU_AVG`, `CPU_P95`, `CPU_MAX`, `MEM_AVG`, `MEM_MAX` y `SAMPLES` a la vista `-o wide`.
  - **Descubrimiento automático** del servicio de Prometheus y consulta a través del
    proxy del API server de Kubernetes (sin port-forward ni credenciales extra).
    Se puede forzar con `--prometheus-namespace`, `--prometheus-service` y
    `--prometheus-timeout`.
  - **Ventana y paso configurables** con `--history-window` (default `24h`) y
    `--history-step` (automático, ~300 puntos por serie).
  - **Colores históricos**: mismas reglas que el modo live, evaluando CPU con el
    promedio y memoria con el pico (riesgo de OOMKill).
  - Soporte de las nuevas columnas en `-o custom-columns` y en la exportación a
    `.txt`, `.html` y `.pdf`.
  - Nuevos módulos `krca/prometheus.py` y `krca/history.py` (agregados al instalador).
- [X] FIX:
  - `-o custom-columns` ahora colorea cada dato según su columna real (antes usaba
    la posición del header personalizado).
  - `requests`/`limits` ausentes se marcan en amarillo también cuando el uso no
    está disponible (antes quedaban en blanco).
  - La infrautilización severa (`< underuse-pct` del request) ahora se marca en azul;
    antes la regla de púrpura la dejaba inalcanzable.
  - Conversión correcta de CPU (`1` = `1000m`) y memoria (`Ki`, bytes, etc.) para
    comparar uso contra requests/limits.
  - `kubectl top` se ejecuta una sola vez por auditoría (antes una vez por pod).

## Version 4.4
- [X] FIX:
  - Todas las mejoras son del instalador.
    - **Dependencias completas**: requirements.txt actualizado con todas las dependencias necesarias
    - **Instalación global**: Dependencias instaladas para todos los usuarios del sistema
    - **Configuración automática de PYTHONPATH**: Se crea `/etc/profile.d/krca.sh` para todos los usuarios
    - **Permisos corregidos**: Directorios y archivos con permisos 755 en lugar de 700
  
## Version 4.3
  - [X] FIX:
    - **Instalador mejorado**: Ahora funciona independientemente del directorio actual
    - Se agregó `krca-wrapper.sh` para configurar automáticamente el PYTHONPATH
    - Los symlinks ahora apuntan al wrapper en lugar del script Python directamente
  - [X] BUG:
    - **Resuelto**: El script ahora funciona correctamente desde cualquier path

## Version 4.2
  - [X] Added:
    - permite hacer resize de las columnas en el html

## Version 3.8
 - [x] Added:
    - Opción `--version` para mostrar la versión de la aplicación

## Version 3.7
 - [x] Added:
    - Soporte mejorado para exportación a HTML/PDF
    - Opción `--landscape` para orientación horizontal en PDF
    - Eliminación automática de códigos ANSI en headers para exportación
    - Opción `--force` para sobrescribir archivos existentes
 - [x] FIX:
    - Corrección de funciones faltantes que causaban errores
    - Mejora en el formato de tablas para exportación
    - Reemplazado `text=True` por `universal_newlines=True` en `subprocess.check_output()` para soportar Python 3.6.8 (Gracias **@miguel**)
 - [x] BUG:
    - Solucionado problema con códigos ANSI en headers de archivos exportados
    - Corregido error al verificar dependencias para PDF

## Version 3.4
 - [ ] Added:
    - output  custom-columns
 - [ ] FIX:
    - 
 - [ ] BUG:
    - la opcion de debug dejo de funcionar


## Version 3.0
 - [ ] Added:
   - set --color as default
 - [ ] FIX:
  - fix color on request_memory


## Version 2.0

### Added:
- Nuevo nombre oficial: **Kubernetes Resource Container Audit (KRCA)**.
- Alias soportado: `kubectl krca`.
- Soporte para colores según consumo y configuración:
  - 🔴 **Rojo**:
    - Uso > `danger-pct` (columnas CPU/MEMORY).
    - Uso > Limit (columnas LIM_CPU/LIM_MEM).
    - Estado `CrashLoopBackOff`.
  - 🟡 **Amarillo**:
    - `warning-pct` < Uso < `danger-pct` (columnas CPU/MEMORY).
    - `requests` no definidos (columnas REQ_CPU/REQ_MEM).
    - `limits` no definidos (columnas LIM_CPU/LIM_MEM).
    - Estado: `Terminated: Completed`.
  - 🟢 **Verde**:
    - Uso normal entre request y limit.
    - Estado: `Running`.
  - 🔵 **Azul**:
    - Otros estados (`Waiting`, `Terminated`, etc.).
    - Infrautilización severa (uso < `underuse-pct`).
  - 🟣 **Púrpura**:
    - Gran diferencia entre request y limit (LIM_CPU/LIM_MEM si `limit/request > diff-pct`).

### Changed:
- Vista principal muestra: NAMESPACE, POD, CONTAINER, CPU, REQ_CPU, LIM_CPU, MEMORY, REQ_MEM, LIM_MEM.
- Agregada opción `-o wide` para mostrar columnas adicionales: STATUS y RESTARTS.
- Mejora de formato para salida coloreada y legible.
- Argumentos CLI más robustos y descriptivos.

### CLI Options:
- `-A`, `--all-namespaces`: Mostrar recursos en todos los namespaces.
- `-n`, `--namespace`: Especificar un namespace.
- `--number`: Mostrar número de fila.
- `--debug`: Mostrar tablas de depuración.
- `--color`: Habilitar salida coloreada.
- `-o wide`: Salida extendida.
- `--warning-pct PCT`: Porcentaje para advertencia (default: 60).
- `--danger-pct PCT`: Porcentaje para peligro (default: 75).
- `--diff-pct PCT`: Porcentaje de diferencia entre request y limit para marcar en púrpura (default: 300).
- `--underuse-pct PCT`: Umbral de infrautilización para marcar en azul (default: 5).
- `--output-file FILE`: Guardar salida en archivo (soporta .txt, .html, .pdf).
- `--force`: Sobrescribir archivo existente.
- `--landscape`: Orientación horizontal para PDF.


### Description:
Este plugin de `kubectl` audita el uso de recursos de los contenedores en un cluster Kubernetes/OpenShift, resaltando en colores posibles problemas de consumo y configuración para facilitar su detección.

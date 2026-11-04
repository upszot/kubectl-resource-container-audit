#!/usr/bin/env python3
# krca/cli.py - Módulo para manejo de línea de comandos

import argparse
from . import __version__
from .utils import parse_duration

# Valores por defecto para los umbrales
DEFAULT_WARNING_PCT = 60
DEFAULT_DANGER_PCT = 75
DEFAULT_DIFF_PCT = 300
DEFAULT_UNDERUSE_PCT = 5

# Ventana histórica por defecto
DEFAULT_HISTORY_WINDOW = "24h"
DEFAULT_PROMETHEUS_TIMEOUT = 60

# Columnas históricas (requieren Prometheus)
HISTORICAL_COLUMNS = [
    'CPU_AVG', 'CPU_P95', 'CPU_MAX', 'MEM_AVG', 'MEM_MAX', 'SAMPLES'
]

# Columnas disponibles para custom-columns
AVAILABLE_COLUMNS = [
    'NAMESPACE', 'POD', 'CONTAINER', 'CPU', 'REQ_CPU', 'LIM_CPU',
    'MEMORY', 'REQ_MEM', 'LIM_MEM', 'STATUS', 'RESTARTS', 'NODE_IP', 'NODE'
] + HISTORICAL_COLUMNS

def create_parser():
    """Crea y configura el parser de argumentos"""
    parser = argparse.ArgumentParser(
        description=f"Kubernetes Resource Container Audit (KRCA) v{__version__}",
        add_help=False
    )
    
    # Grupo exclusivo para namespaces
    namespace_group = parser.add_mutually_exclusive_group()
    namespace_group.add_argument(
        "-A", "--all-namespaces",
        action="store_true",
        help="Mostrar recursos en todos los namespaces"
    )
    namespace_group.add_argument(
        "-n", "--namespace",
        help="Especificar un namespace particular"
    )
    
    # Opciones de visualización
    parser.add_argument(
        "--number",
        action="store_true",
        help="Mostrar números de fila"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mostrar tablas de depuración"
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Deshabilitar salida coloreada"
    )
    
    # Formato de salida
    parser.add_argument(
        "-o", "--output",
        help="Formato de salida (wide|custom-columns=<columnas>)"
    )
    
    # Exportación a archivo
    parser.add_argument(
        "--output-file",
        help="Guardar salida en archivo (soporta .txt, .html, .pdf)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescribir archivo existente"
    )
    parser.add_argument(
        "--landscape",
        action="store_true",
        help="Orientación horizontal para PDF"
    )
    
    # Opciones de ayuda y versión
    parser.add_argument(
        "-h", "--help",
        action="store_true",
        help="Mostrar mensaje de ayuda y salir"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Mostrar versión y salir"
    )
    
    # Umbrales configurables
    threshold_group = parser.add_argument_group('Umbrales configurables')
    threshold_group.add_argument(
        "--warning-pct",
        type=int,
        default=DEFAULT_WARNING_PCT,
        help=f"Porcentaje de warning (default: {DEFAULT_WARNING_PCT}%%)"
    )
    threshold_group.add_argument(
        "--danger-pct",
        type=int,
        default=DEFAULT_DANGER_PCT,
        help=f"Porcentaje de danger (default: {DEFAULT_DANGER_PCT}%%)"
    )
    threshold_group.add_argument(
        "--diff-pct",
        type=int,
        default=DEFAULT_DIFF_PCT,
        help=f"Porcentaje de diferencia para color púrpura (default: {DEFAULT_DIFF_PCT}%%)"
    )
    threshold_group.add_argument(
        "--underuse-pct",
        type=int,
        default=DEFAULT_UNDERUSE_PCT,
        help=f"Porcentaje para detectar infrautilización (default: {DEFAULT_UNDERUSE_PCT}%%)"
    )

    # Análisis histórico con Prometheus
    history_group = parser.add_argument_group('Análisis histórico (Prometheus)')
    history_group.add_argument(
        "--history",
        action="store_true",
        help="Agregar columnas históricas calculadas desde Prometheus (requiere -o wide)"
    )
    history_group.add_argument(
        "--history-window",
        default=DEFAULT_HISTORY_WINDOW,
        metavar="DUR",
        help=f"Ventana de análisis histórico (default: {DEFAULT_HISTORY_WINDOW}; ej: 90m, 12h, 7d)"
    )
    history_group.add_argument(
        "--history-step",
        default=None,
        metavar="DUR",
        help="Paso de muestreo histórico (default: automático según la ventana)"
    )
    history_group.add_argument(
        "--prometheus-namespace",
        metavar="NS",
        help="Namespace del servicio de Prometheus (default: autodetección)"
    )
    history_group.add_argument(
        "--prometheus-service",
        metavar="NAME",
        help="Nombre del servicio de Prometheus (default: autodetección; acepta ns/nombre)"
    )
    history_group.add_argument(
        "--prometheus-timeout",
        type=int,
        default=DEFAULT_PROMETHEUS_TIMEOUT,
        metavar="SEC",
        help=f"Timeout de consulta a Prometheus en segundos (default: {DEFAULT_PROMETHEUS_TIMEOUT})"
    )

    return parser

def parse_custom_columns(spec):
    """Valida y parsea las columnas personalizadas"""
    if not spec or not spec.startswith('custom-columns='):
        return None
    
    columns_spec = spec.split('=', 1)[1]
    columns = [col.strip() for col in columns_spec.split(',') if col.strip()]
    
    # Validar columnas
    valid_columns = []
    for col in columns:
        if col in AVAILABLE_COLUMNS:
            valid_columns.append(col)
        else:
            print(f"Advertencia: Columna '{col}' no reconocida. Columnas disponibles: {', '.join(AVAILABLE_COLUMNS)}")
    
    return valid_columns if valid_columns else None

def parse_args(argv=None):
    """Parse los argumentos de línea de comandos"""
    parser = create_parser()
    
    # Manejo especial para ejecución como plugin de kubectl
    if argv and len(argv) > 1 and not argv[1].startswith('-'):
        argv.insert(1, '--')
    
    args = parser.parse_args(argv)
    
    # Validación adicional de argumentos
    if args.output:
        if args.output.lower() == 'wide':
            args.wide_output = True
            args.custom_columns = None
        else:
            args.wide_output = False
            args.custom_columns = parse_custom_columns(args.output)
    else:
        args.wide_output = False
        args.custom_columns = None

    # Validar duraciones del modo histórico
    try:
        parse_duration(args.history_window)
    except ValueError as e:
        parser.error(str(e))

    if args.history_step:
        try:
            parse_duration(args.history_step)
        except ValueError as e:
            parser.error(str(e))

    # Si se piden columnas históricas por custom-columns, activar el modo
    if args.custom_columns and any(col in HISTORICAL_COLUMNS for col in args.custom_columns):
        args.history = True

    # El modo histórico solo tiene sentido con columnas extendidas
    if args.history and not (args.wide_output or args.custom_columns):
        parser.error("--history requiere -o wide (o -o custom-columns con columnas históricas)")

    return args

def show_help():
    """Muestra el mensaje de ayuda personalizado"""
    help_text = f"""
Kubernetes Resource Container Audit (KRCA) v{__version__}

Uso:
  kubectl resource-container-audit [OPCIONES]
  kubectl krca [OPCIONES]

Opciones:
  -h, --help            Muestra este mensaje de ayuda
  --version             Muestra la versión actual
  -A, --all-namespaces  Mostrar recursos en todos los namespaces
  -n, --namespace NAMESPACE
                        Especificar un namespace particular
  --number              Mostrar números de fila
  --debug               Mostrar tablas de depuración
  --no-color            Deshabilitar salida coloreada
  -o, --output FORMAT   Formato de salida (wide|custom-columns=<columnas>)
                        Ejemplo: -o custom-columns=NAMESPACE,POD,CPU,MEMORY
  --output-file FILE    Guardar salida en archivo (soporta .txt, .html, .pdf)
  --force               Sobrescribir archivo existente
  --landscape           Orientación horizontal para PDF

Umbrales configurables:
  --warning-pct PCT     Porcentaje de warning (default: {DEFAULT_WARNING_PCT}%)
  --danger-pct PCT      Porcentaje de danger (default: {DEFAULT_DANGER_PCT}%)
  --diff-pct PCT        Porcentaje de diferencia (default: {DEFAULT_DIFF_PCT}%)
  --underuse-pct PCT    Porcentaje de infrautilización (default: {DEFAULT_UNDERUSE_PCT}%)

Análisis histórico (Prometheus):
  --history             Agregar columnas históricas (requiere -o wide)
  --history-window DUR  Ventana de análisis (default: {DEFAULT_HISTORY_WINDOW}; ej: 90m, 12h, 7d)
  --history-step DUR    Paso de muestreo (default: automático)
  --prometheus-namespace NS
                        Namespace del servicio de Prometheus
  --prometheus-service NAME
                        Servicio de Prometheus (acepta ns/nombre)
  --prometheus-timeout SEC
                        Timeout de consulta (default: {DEFAULT_PROMETHEUS_TIMEOUT}s)

Columnas disponibles para custom-columns:
  {', '.join(AVAILABLE_COLUMNS)}
"""
    print(help_text)
    return 0

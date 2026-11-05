#!/usr/bin/env python3
# krca/__init__.py - Inicialización del paquete KRCA

from pathlib import Path


def _read_version():
    """Lee la versión desde el archivo VERSION del proyecto.

    Se buscan dos ubicaciones para cubrir tanto la ejecución desde el
    repositorio como la instalación realizada por install.sh:
      - <raíz del proyecto>/VERSION
      - <paquete krca>/VERSION
    """
    candidates = (
        Path(__file__).resolve().parent.parent / "VERSION",
        Path(__file__).resolve().parent / "VERSION",
    )

    for candidate in candidates:
        try:
            version = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if version:
            return version

    return "unknown"


# Fuente única de verdad: archivo VERSION en la raíz del proyecto.
__version__ = _read_version()

# Metadata del paquete
__author__ = "upszot"
__license__ = "GLP3.0"

# Importaciones públicas (API del paquete)
from .cli import parse_args, show_help
from .core import analyze_resources
from .colorizer import ResourceColorizer
from .kubectl import KubectlClient, KubectlError
from .prometheus import PrometheusClient, PrometheusError
from .history import HistoryAnalyzer
from .exporter import Exporter
from .utils import KRCAUtils
from .models import (
    ContainerResources,
    ContainerMetrics,
    PodStatus,
    PodData,
    ClusterStats,
    Thresholds,
    ExportConfig,
    ColumnDefinition,
    AnalysisResult
)

# Aliases para facilitar el acceso
KRCA = analyze_resources

# Lista de símbolos exportados
__all__ = [
    # Funciones principales
    'analyze_resources',
    'KRCA',
    
    # Clases de servicio
    'ResourceColorizer',
    'KubectlClient',
    'PrometheusClient',
    'HistoryAnalyzer',
    'Exporter',
    'KRCAUtils',
    
    # Modelos de datos
    'ContainerResources',
    'ContainerMetrics',
    'PodStatus',
    'PodData',
    'ClusterStats',
    'Thresholds',
    'ExportConfig',
    'ColumnDefinition',
    'AnalysisResult',
    
    # Utilidades
    'parse_args',
    'show_help',
    
    # Excepciones
    'KubectlError',
    'PrometheusError',
    
    # Metadata
    '__version__',
    '__author__',
    '__license__'
]

# Inicialización opcional del paquete
def _init_package():
    """Inicialización del paquete (opcional)"""
    # Podrías añadir verificaciones de configuración aquí
    pass

_init_package()

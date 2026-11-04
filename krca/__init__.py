#!/usr/bin/env python3
# krca/__init__.py - Inicialización del paquete KRCA

# Metadata del paquete
__version__ = "4.5"
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

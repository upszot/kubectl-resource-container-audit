#!/usr/bin/env python3
# krca/__init__.py - Inicialización del paquete KRCA

import os
from pathlib import Path


def _read_version_file():
    """Lee la versión desde el archivo VERSION de la instalación.

    Orden de búsqueda:
      1. Archivo indicado en la variable de entorno KRCA_VERSION_FILE.
      2. <raíz del proyecto>/VERSION (checkout o install.sh).
      3. <paquete krca>/VERSION (instalaciones que copian el archivo dentro).

    Devuelve None si no encuentra el archivo (por ejemplo en un wheel).
    """
    package_dir = Path(__file__).resolve().parent

    candidates = []
    override = os.environ.get("KRCA_VERSION_FILE")
    if override:
        candidates.append(Path(override).expanduser())
    candidates.append(package_dir.parent / "VERSION")
    candidates.append(package_dir / "VERSION")

    for candidate in candidates:
        try:
            version = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if version:
            return version

    return None


def _is_installed_package():
    """True si el paquete se está ejecutando desde site-packages/dist-packages."""
    package_path = str(Path(__file__).resolve())
    return "site-packages" in package_path or "dist-packages" in package_path


def _read_version():
    """Resuelve la versión del paquete.

    Orden de preferencia:
      1. Archivo VERSION (checkout del repo o instalación con install.sh).
      2. Metadatos del paquete instalado, sólo si el código se carga desde
         site-packages/dist-packages (wheel, pipx, Homebrew). Así una metadata
         vieja no se mezcla con el código de una instalación local.
      3. "unknown".
    """
    version = _read_version_file()
    if version:
        return version

    if not _is_installed_package():
        return "unknown"

    try:
        from importlib.metadata import PackageNotFoundError, version as dist_version

        try:
            return dist_version("krca")
        except PackageNotFoundError:
            return "unknown"
    except ImportError:  # pragma: no cover - Python < 3.8
        return "unknown"


# Fuente única de verdad en el repo: archivo VERSION.
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

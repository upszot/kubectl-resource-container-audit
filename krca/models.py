#!/usr/bin/env python3
# krca/models.py - Modelos de datos para KRCA

from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class ContainerResources:
    """Modelo para los recursos de un contenedor"""
    name: str
    request_cpu: str
    request_memory: str
    limit_cpu: str
    limit_memory: str

@dataclass
class ContainerMetrics:
    """Modelo para las métricas de uso de un contenedor"""
    cpu: str
    memory: str
    namespace: Optional[str] = None

@dataclass
class PodStatus:
    """Modelo para el estado de un pod"""
    status: str
    restarts: int
    node_ip: str
    node_name: str

@dataclass
class PodData:
    """Modelo completo para los datos de un pod"""
    name: str
    namespace: str
    containers: List[ContainerResources]
    metrics: Dict[str, ContainerMetrics]  # key: container name
    status: PodStatus

@dataclass
class ClusterStats:
    """Modelo para estadísticas agregadas del cluster"""
    total_pods: int
    running_pods: int
    warning_pods: int
    error_pods: int
    cpu_usage_percent: float
    memory_usage_percent: float
    underutilized_pods: int
    overutilized_pods: int

@dataclass
class Thresholds:
    """Modelo para los umbrales configurables"""
    warning: int
    danger: int
    diff: int
    underuse: int

@dataclass
class ExportConfig:
    """Modelo para configuración de exportación"""
    output_file: Optional[str] = None
    format: str = "text"  # text, html, pdf
    force: bool = False
    landscape: bool = False
    show_numbers: bool = False
    use_color: bool = True

@dataclass
class ColumnDefinition:
    """Modelo para definición de columnas personalizadas"""
    name: str
    visible: bool = True
    width: Optional[int] = None
    color: Optional[str] = None

@dataclass
class AnalysisResult:
    """Modelo para los resultados del análisis"""
    pod_data: List[PodData]
    cluster_stats: ClusterStats
    warnings: List[str]
    errors: List[str]

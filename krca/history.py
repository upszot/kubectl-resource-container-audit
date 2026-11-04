#!/usr/bin/env python3
# krca/history.py - Análisis histórico de recursos usando Prometheus

import math
import sys
import time
from typing import Dict, List, Optional, Tuple

from .prometheus import PrometheusClient, PrometheusError
from .utils import parse_duration, nice_step, format_duration

# Clave usada para unir series de Prometheus con los contenedores del cluster
ContainerKey = Tuple[str, str, str]


class HistoryAnalyzer:
    """
    Obtiene métricas históricas de CPU y memoria desde Prometheus y calcula
    estadísticos (promedio, p95, máximo y cantidad de muestras) por contenedor.
    """

    # Ventana de rate para CPU. 5m suaviza picos puntuales del scrape y es
    # suficiente para dimensionar requests/limits.
    CPU_RATE_WINDOW = '5m'

    def __init__(self, args):
        self.args = args
        self.window = parse_duration(getattr(args, 'history_window', '24h') or '24h')
        step_arg = getattr(args, 'history_step', None)
        self.step = int(parse_duration(step_arg)) if step_arg else nice_step(self.window)
        self.debug = bool(getattr(args, 'debug', False))

        self.client = PrometheusClient(
            namespace=getattr(args, 'prometheus_namespace', None),
            service=getattr(args, 'prometheus_service', None),
            timeout=getattr(args, 'prometheus_timeout', PrometheusClient.DEFAULT_TIMEOUT),
            debug=self.debug,
        )

        self.end_ts = time.time()
        self.start_ts = self.end_ts - self.window

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def _selector(self) -> str:
        parts = ['container!=""', 'container!="POD"']
        namespace = getattr(self.args, 'namespace', None)
        all_namespaces = getattr(self.args, 'all_namespaces', False)
        if namespace and not all_namespaces:
            parts.insert(0, f'namespace="{namespace}"')
        return ','.join(parts)

    def _cpu_expression(self) -> str:
        selector = self._selector()
        return (
            f'rate(container_cpu_usage_seconds_total{{{selector}}}'
            f'[{self.CPU_RATE_WINDOW}])'
        )

    def _memory_expression(self) -> str:
        return f'container_memory_working_set_bytes{{{self._selector()}}}'

    # ------------------------------------------------------------------
    # Procesamiento
    # ------------------------------------------------------------------
    def collect(self, pods: List[Dict]) -> Dict[ContainerKey, Dict[str, Dict]]:
        """
        Devuelve un diccionario:
            (namespace, pod, container) -> {'cpu': stats, 'mem': stats}
        donde stats = {'avg', 'p95', 'max', 'samples'}
        """
        expected = self._expected_containers(pods)
        if not expected:
            return {}

        if self.debug:
            print(
                f"[krca][history] ventana={self.window:.0f}s step={self.step}s "
                f"endpoint={self.client.endpoint}",
                file=sys.stderr,
            )

        cpu_series = self.client.query_range(
            self._cpu_expression(), self.start_ts, self.end_ts, self.step
        )
        memory_series = self.client.query_range(
            self._memory_expression(), self.start_ts, self.end_ts, self.step
        )

        stats: Dict[ContainerKey, Dict[str, Dict]] = {}

        # CPU: Prometheus devuelve cores (segundos de CPU / segundo) -> milicores
        self._accumulate(cpu_series, expected, stats, 'cpu', scale=1000.0)
        # Memoria: bytes -> MiB
        self._accumulate(memory_series, expected, stats, 'mem', scale=1.0 / (1024 * 1024))

        if not stats:
            raise PrometheusError(
                "Prometheus no devolvió métricas para los pods seleccionados en la "
                f"ventana de {self._window_label()}.\n"
                "Verifique que kube-state-metrics/cAdvisor estén activos y que la "
                "ventana no supere la retención de Prometheus "
                "(use --history-window con un valor menor)."
            )

        return stats

    def _accumulate(
        self,
        series: List[Dict],
        expected: set,
        stats: Dict[ContainerKey, Dict[str, Dict]],
        resource: str,
        scale: float,
    ) -> None:
        """Agrupa las series por contenedor y calcula los estadísticos."""
        grouped: Dict[ContainerKey, List[float]] = {}

        for item in series:
            metric = item.get('metric', {})
            namespace = metric.get('namespace')
            pod = metric.get('pod')
            container = metric.get('container')
            key = (namespace, pod, container)

            if key not in expected:
                continue

            values = grouped.setdefault(key, [])
            for point in item.get('values', []) or []:
                if len(point) < 2:
                    continue
                try:
                    value = float(point[1])
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(value):
                    continue
                values.append(value * scale)

        for key, values in grouped.items():
            if not values:
                continue
            stats.setdefault(key, {})[resource] = self._summarize(values)

    @staticmethod
    def _summarize(values: List[float]) -> Dict[str, float]:
        ordered = sorted(values)
        count = len(ordered)
        # Percentil 95 por rango más cercano
        index = max(0, min(count - 1, int(math.ceil(0.95 * count)) - 1))
        return {
            'avg': sum(ordered) / count,
            'p95': ordered[index],
            'max': ordered[-1],
            'samples': count,
        }

    @staticmethod
    def _expected_containers(pods: List[Dict]) -> set:
        expected = set()
        for pod in pods:
            metadata = pod.get('metadata', {})
            namespace = metadata.get('namespace')
            pod_name = metadata.get('name')
            spec = pod.get('spec', {})
            for container in spec.get('containers', []) or []:
                expected.add((namespace, pod_name, container.get('name')))
        return expected

    def _window_label(self) -> str:
        return format_duration(self.window)

    # ------------------------------------------------------------------
    # Formato para la tabla
    # ------------------------------------------------------------------
    @staticmethod
    def format_millicores(value: Optional[float]) -> str:
        if value is None:
            return '-'
        if value >= 10:
            return f"{value:.0f}m"
        return f"{value:.1f}m"

    @staticmethod
    def format_mib(value: Optional[float]) -> str:
        if value is None:
            return '-'
        if value >= 10:
            return f"{value:.0f}Mi"
        return f"{value:.1f}Mi"

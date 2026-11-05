#!/usr/bin/env python3
# krca/core.py - Módulo principal completo

from tabulate import tabulate
import sys
import traceback
from typing import Dict, Any, List

from .kubectl import KubectlClient
from .colorizer import ResourceColorizer
from .exporter import Exporter
from .history import HistoryAnalyzer
from .prometheus import PrometheusError


class KRCAnalyzer:
    """Clase principal para el análisis de recursos de Kubernetes"""

    # Orden fijo de todas las columnas que puede construir una fila.
    # La colorización se hace por nombre, de modo que -o custom-columns
    # siempre colorea el dato correcto.
    COLUMN_ORDER = [
        "NAMESPACE", "POD", "CONTAINER",
        "CPU", "REQ_CPU", "LIM_CPU",
        "MEMORY", "REQ_MEM", "LIM_MEM",
        "STATUS", "RESTARTS", "NODE_IP", "NODE",
        "CPU_AVG", "CPU_P95", "CPU_MAX", "MEM_AVG", "MEM_MAX", "SAMPLES",
    ]

    # Índices de columnas live/históricas dentro de COLUMN_ORDER
    HISTORY_START_INDEX = 13

    LIVE_RESOURCE_HEADERS = ('CPU', 'REQ_CPU', 'LIM_CPU', 'MEMORY', 'REQ_MEM', 'LIM_MEM')

    def __init__(self, args):
        self.args = args
        self.use_color = not args.no_color
        self.wide_output = bool(getattr(args, 'wide_output', False))
        self.custom_columns = getattr(args, 'custom_columns', None)
        self.history_requested = bool(getattr(args, 'history', False))
        # El histórico solo se calcula cuando sus columnas se van a mostrar
        self.include_history = self.history_requested and (
            self.wide_output or bool(self.custom_columns)
        )
        self.headers = self._determine_headers()
        # Con custom-columns, evitar consultar Prometheus si no se pidió
        # ninguna columna histórica.
        if self.custom_columns:
            self.include_history = self.history_requested and any(
                header in ResourceColorizer.HISTORICAL_COLUMNS
                for header in self.headers
            )

    def _determine_headers(self) -> List[str]:
        """Define las columnas a mostrar basadas en los argumentos"""
        # Columnas básicas por defecto
        base_headers = self.COLUMN_ORDER[:9]

        # Solo agregar columnas adicionales si se usa -o wide
        if self.wide_output:
            base_headers.extend(self.COLUMN_ORDER[9:13])
            if self.include_history:
                base_headers.extend(self.COLUMN_ORDER[self.HISTORY_START_INDEX:])

        # Permitir columnas personalizadas si se especifican
        if self.custom_columns:
            return self.custom_columns

        return base_headers

    def _get_column_index(self, column_name: str) -> int:
        """Obtiene el índice de una columna por su nombre"""
        try:
            return self.COLUMN_ORDER.index(column_name)
        except ValueError:
            return -1

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------
    def _history_values(self, stats: Dict[str, Dict]) -> List[str]:
        """Formatea los estadísticos históricos de un contenedor."""
        if not stats:
            return ['-', '-', '-', '-', '-', '-']

        cpu = stats.get('cpu') or {}
        mem = stats.get('mem') or {}
        samples = max(int(cpu.get('samples', 0)), int(mem.get('samples', 0)))

        return [
            HistoryAnalyzer.format_millicores(cpu.get('avg')),
            HistoryAnalyzer.format_millicores(cpu.get('p95')),
            HistoryAnalyzer.format_millicores(cpu.get('max')),
            HistoryAnalyzer.format_mib(mem.get('avg')),
            HistoryAnalyzer.format_mib(mem.get('max')),
            str(samples) if samples else '-',
        ]

    def _process_pod_data(self, pod: Dict[str, Any],
                          metrics: Dict[str, Any],
                          history_data: Dict[Any, Dict[str, Dict]]) -> List[List[str]]:
        """Procesa los datos de un pod y sus contenedores"""
        pod_data = []
        pod_name = pod["metadata"]["name"]
        namespace = pod["metadata"]["namespace"]

        status, restarts = KubectlClient.get_pod_status(pod)
        node_ip, node_name = KubectlClient.get_node_info(pod)
        containers = KubectlClient.get_container_resources(pod)
        pod_metrics = metrics.get(pod_name, {})

        for container in containers:
            container_name = container["name"]
            container_metrics = pod_metrics.get(container_name, {})

            # Obtener métricas con validación
            cpu_usage = container_metrics.get("cpu", "-")
            memory_usage = container_metrics.get("memory", "-")

            # Asegurar que memory tenga unidades válidas
            if memory_usage != "-" and not any(x in memory_usage for x in ['Ki', 'Mi', 'Gi']):
                if memory_usage.isdigit():
                    memory_usage = f"{memory_usage}Mi"
                else:
                    memory_usage = "-"

            row = [
                namespace,
                pod_name,
                container_name,
                cpu_usage,
                container["req_cpu"],
                container["lim_cpu"],
                memory_usage,
                container["req_mem"],
                container["lim_mem"],
                status,
                restarts,
                node_ip,
                node_name,
            ]

            if self.include_history:
                stats = history_data.get((namespace, pod_name, container_name))
                row.extend(self._history_values(stats))

            pod_data.append(row)

        return pod_data

    # ------------------------------------------------------------------
    # Colores
    # ------------------------------------------------------------------
    def _apply_colors(self, row: List) -> List[str]:
        """Aplica colores a los datos según su estado"""
        if not self.use_color:
            return [str(item) for item in row]

        warnings = self.args.warning_pct
        danger = self.args.danger_pct
        diff = self.args.diff_pct
        underuse = self.args.underuse_pct

        # CPU y memoria actuales
        cpu_colors = ResourceColorizer.colorize_usage(
            row[3], row[6],   # CPU y MEMORY
            row[4], row[7],   # REQ_CPU y REQ_MEM
            row[5], row[8],   # LIM_CPU y LIM_MEM
            warnings, danger, diff, underuse
        )
        color_map = {
            "CPU": cpu_colors[0],
            "REQ_CPU": cpu_colors[1],
            "LIM_CPU": cpu_colors[2],
            "MEMORY": cpu_colors[3],
            "REQ_MEM": cpu_colors[4],
            "LIM_MEM": cpu_colors[5],
        }

        # Columnas históricas (si están presentes en la fila)
        has_history = len(row) >= len(self.COLUMN_ORDER) and (
            row[13] != '-' or row[16] != '-'
        )

        if has_history:
            history_colors = ResourceColorizer.colorize_historical(
                row[13], row[14], row[15],  # CPU_AVG, CPU_P95, CPU_MAX
                row[16], row[17],           # MEM_AVG, MEM_MAX
                row[4], row[7],             # REQ_CPU, REQ_MEM
                row[5], row[8],             # LIM_CPU, LIM_MEM
                warnings, danger, diff, underuse
            )
            # Si hay datos históricos, REQ/LIM se evalúan con el uso histórico
            color_map.update(history_colors)

        colored_row = []
        for index, item in enumerate(row):
            if index >= len(self.COLUMN_ORDER):
                break

            header = self.COLUMN_ORDER[index]

            if header == "NAMESPACE":
                colored_row.append(f"{ResourceColorizer.colorize_namespace(item)}")
            elif header == "POD":
                colored_row.append(f"{ResourceColorizer.colorize_pod(item)}")
            elif header == "CONTAINER":
                colored_row.append(f"{ResourceColorizer.colorize_container(item)}")
            elif header in self.LIVE_RESOURCE_HEADERS or header in ResourceColorizer.HISTORICAL_COLUMNS:
                color = color_map.get(header, ResourceColorizer.WHITE)
                colored_row.append(f"{color}{item}{ResourceColorizer.RESET}")
            elif header == "STATUS":
                status_color, _ = ResourceColorizer.colorize_status(item, 0)
                colored_row.append(f"{status_color}{item}{ResourceColorizer.RESET}")
            elif header == "RESTARTS":
                try:
                    restarts_value = int(item)
                except (TypeError, ValueError):
                    restarts_value = 0
                _, restarts_color = ResourceColorizer.colorize_status("", restarts_value)
                colored_row.append(f"{restarts_color}{item}{ResourceColorizer.RESET}")
            elif header in ["NODE_IP", "NODE"]:
                colored_row.append(f"{ResourceColorizer.colorize_node(item)}")
            else:
                colored_row.append(str(item))

        return colored_row

    # ------------------------------------------------------------------
    # Histórico
    # ------------------------------------------------------------------
    def _collect_history(self, pods: List[Dict]) -> Dict[Any, Dict[str, Dict]]:
        """
        Obtiene las métricas históricas desde Prometheus. Si algo falla,
        se informa por stderr y se continúa con la tabla live.
        """
        try:
            return HistoryAnalyzer(self.args).collect(pods)
        except PrometheusError as e:
            message = f"Advertencia: no se pudo obtener el histórico de Prometheus: {e}"
            print(ResourceColorizer.yellow(message) if self.use_color else message,
                  file=sys.stderr)
            if getattr(self.args, 'debug', False):
                traceback.print_exc()
            return {}
        except Exception as e:  # Nunca romper la auditoría live
            message = f"Advertencia: error inesperado al consultar Prometheus: {e}"
            print(ResourceColorizer.yellow(message) if self.use_color else message,
                  file=sys.stderr)
            if getattr(self.args, 'debug', False):
                traceback.print_exc()
            return {}

    # ------------------------------------------------------------------
    # Ejecución
    # ------------------------------------------------------------------
    def analyze(self) -> int:
        """Ejecuta el análisis completo y muestra los resultados"""
        try:
            if self.history_requested and not (self.wide_output or self.custom_columns):
                error_msg = (
                    f"{ResourceColorizer.RED}Error:{ResourceColorizer.RESET} "
                    "--history requiere -o wide (o -o custom-columns con columnas históricas)."
                )
                print(error_msg)
                return 1

            pods = KubectlClient.get_pods(self.args.namespace, self.args.all_namespaces)
            metrics = KubectlClient.get_metrics(self.args.namespace, self.args.all_namespaces)

            history_data = {}
            if self.include_history:
                history_data = self._collect_history(pods["items"])

            all_data = []
            for pod in pods["items"]:
                all_data.extend(self._process_pod_data(pod, metrics, history_data))

            colored_data = [self._apply_colors(row) for row in all_data]

            # Filtrar solo las columnas que queremos mostrar
            column_indices = [self._get_column_index(col) for col in self.headers]
            colored_data = [
                [row[i] for i in column_indices if i != -1]
                for row in colored_data
            ]

            # Usar tablefmt="plain" para eliminar líneas de separación
            table_output = tabulate(
                colored_data,
                headers=[f"{ResourceColorizer.BOLD if self.use_color else ''}{h}{ResourceColorizer.RESET if self.use_color else ''}"
                        for h in self.headers],
                showindex=getattr(self.args, 'number', False),
                tablefmt="plain"  # Formato sin líneas de separación
            )

            if hasattr(self.args, 'output_file') and self.args.output_file:
                Exporter.export(
                    table_output,
                    self.args.output_file,
                    self.use_color,
                    getattr(self.args, 'force', False),
                    getattr(self.args, 'landscape', False)
                )
            else:
                print(table_output)

            return 0

        except Exception as e:
            error_msg = f"{ResourceColorizer.RED}Error:{ResourceColorizer.RESET} {str(e)}"
            if getattr(self.args, 'debug', False):
                error_msg += f"\n\n{ResourceColorizer.YELLOW}Debug info:{ResourceColorizer.RESET}\n{traceback.format_exc()}"
            print(error_msg)
            return 1


def analyze_resources(args) -> int:
    """Función principal para iniciar el análisis"""
    return KRCAnalyzer(args).analyze()

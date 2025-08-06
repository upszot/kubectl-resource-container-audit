#!/usr/bin/env python3
# krca/core.py - Módulo principal completo

from tabulate import tabulate
import traceback
from typing import List, Dict, Any
from .kubectl import KubectlClient
from .colorizer import ResourceColorizer, COLOR_RESET, COLOR_BOLD, COLOR_RED, COLOR_YELLOW
from .exporter import Exporter

class KRCAnalyzer:
    """Clase principal para el análisis de recursos de Kubernetes"""
    
    def __init__(self, args):
        self.args = args
        self.use_color = not args.no_color
        self.headers = self._determine_headers()

    def _determine_headers(self) -> List[str]:
        """Define las columnas a mostrar basadas en los argumentos"""
        # Columnas básicas por defecto
        base_headers = [
            "NAMESPACE", 
            "POD", 
            "CONTAINER", 
            "CPU", 
            "REQ_CPU", 
            "LIM_CPU", 
            "MEMORY", 
            "REQ_MEM", 
            "LIM_MEM"
        ]
        
        # Solo agregar columnas adicionales si se usa -o wide
        if getattr(self.args, 'wide_output', False):
            base_headers.extend([
                "STATUS", 
                "RESTARTS", 
                "NODE_IP", 
                "NODE"
            ])
        
        # Permitir columnas personalizadas si se especifican
        if hasattr(self.args, 'custom_columns') and self.args.custom_columns:
            return self.args.custom_columns
        
        return base_headers

    def _get_column_index(self, column_name: str) -> int:
        """Obtiene el índice de una columna por su nombre"""
        column_mapping = {
            'NAMESPACE': 0, 'POD': 1, 'CONTAINER': 2,
            'CPU': 3, 'REQ_CPU': 4, 'LIM_CPU': 5,
            'MEMORY': 6, 'REQ_MEM': 7, 'LIM_MEM': 8,
            'STATUS': 9, 'RESTARTS': 10,
            'NODE_IP': 11, 'NODE': 12
        }
        return column_mapping.get(column_name, -1)

    def _process_pod_data(self, pod: Dict[str, Any]) -> List[List[str]]:
        """Procesa los datos de un pod y sus contenedores"""
        pod_data = []
        pod_name = pod["metadata"]["name"]
        namespace = pod["metadata"]["namespace"]
        
        status, restarts = KubectlClient.get_pod_status(pod)
        node_ip, node_name = KubectlClient.get_node_info(pod)
        containers = KubectlClient.get_container_resources(pod)
        metrics = KubectlClient.get_metrics(self.args.namespace, self.args.all_namespaces)
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
                node_name
            ]
            pod_data.append(row)
        
        return pod_data

    def _apply_colors(self, row: List[str]) -> List[str]:
        """Aplica colores a los datos según su estado"""
        colored_row = []
        for i, item in enumerate(row):
            if i >= len(self.headers):
                continue
                
            header = self.headers[i]
            
            if not self.use_color:
                colored_row.append(item)
                continue
            
            # Colorización especial para cada tipo de campo
            if header == "NAMESPACE":
                colored_row.append(ResourceColorizer.colorize_namespace(item))
            elif header == "POD":
                colored_row.append(ResourceColorizer.colorize_pod(item))
            elif header == "CONTAINER":
                colored_row.append(ResourceColorizer.colorize_container(item))
            elif header in ["CPU", "REQ_CPU", "LIM_CPU", "MEMORY", "REQ_MEM", "LIM_MEM"]:
                cpu_colors = ResourceColorizer.colorize_usage(
                    row[3], row[6],  # CPU y MEMORY
                    row[4], row[7],  # REQ_CPU y REQ_MEM
                    row[5], row[8],  # LIM_CPU y LIM_MEM
                    self.args.warning_pct,
                    self.args.danger_pct,
                    self.args.diff_pct,
                    self.args.underuse_pct
                )
                color_map = {
                    "CPU": cpu_colors[0],
                    "REQ_CPU": cpu_colors[1],
                    "LIM_CPU": cpu_colors[2],
                    "MEMORY": cpu_colors[3],
                    "REQ_MEM": cpu_colors[4],
                    "LIM_MEM": cpu_colors[5]
                }
                colored_row.append(f"{color_map[header]}{item}{COLOR_RESET}")
            elif header == "STATUS":
                status_color, _ = ResourceColorizer.colorize_status(item, 0)
                colored_row.append(f"{status_color}{item}{COLOR_RESET}")
            elif header == "RESTARTS":
                _, restarts_color = ResourceColorizer.colorize_status("", int(item))
                colored_row.append(f"{restarts_color}{item}{COLOR_RESET}")
            elif header in ["NODE_IP", "NODE"]:
                colored_row.append(ResourceColorizer.colorize_node(item))
            else:
                colored_row.append(item)
        
        return colored_row

    def analyze(self) -> int:
        """Ejecuta el análisis completo y muestra los resultados"""
        try:
            pods = KubectlClient.get_pods(self.args.namespace, self.args.all_namespaces)
            all_data = []
            
            for pod in pods["items"]:
                all_data.extend(self._process_pod_data(pod))
            
            colored_data = [self._apply_colors(row) for row in all_data]
            
            # Filtrar solo las columnas que queremos mostrar
            if hasattr(self.args, 'custom_columns') and self.args.custom_columns:
                column_indices = [self._get_column_index(col) for col in self.args.custom_columns]
                colored_data = [
                    [row[i] for i in column_indices if i != -1]
                    for row in colored_data
                ]
            else:
                # Mostrar solo las columnas básicas si no se especifica otra cosa
                column_indices = [self._get_column_index(col) for col in self.headers]
                colored_data = [
                    [row[i] for i in column_indices if i != -1]
                    for row in colored_data
                ]
            
            table_output = tabulate(
                colored_data,
                headers=[f"{COLOR_BOLD if self.use_color else ''}{h}{COLOR_RESET if self.use_color else ''}" 
                        for h in self.headers],
                showindex=getattr(self.args, 'number', False),
                tablefmt="fancy_grid" if self.use_color else "plain"
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
            error_msg = f"{COLOR_RED}Error:{COLOR_RESET} {str(e)}"
            if getattr(self.args, 'debug', False):
                error_msg += f"\n\n{COLOR_YELLOW}Debug info:{COLOR_RESET}\n{traceback.format_exc()}"
            print(error_msg)
            return 1

def analyze_resources(args) -> int:
    """Función principal para iniciar el análisis"""
    return KRCAnalyzer(args).analyze()

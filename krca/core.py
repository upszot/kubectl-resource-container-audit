#!/usr/bin/env python3
# krca/core.py - Módulo principal de lógica de negocio

from tabulate import tabulate
from .kubectl import KubectlClient
from .colorizer import ResourceColorizer
from .exporter import Exporter
from .utils import calculate_percentage_diff

class KRCAnalyzer:
    """Clase principal que coordina el análisis de recursos"""
    
    def __init__(self, args):
        self.args = args
        self.use_color = not args.no_color
        self.headers = self._determine_headers()

    def _determine_headers(self):
        """Determina las cabeceras basadas en los argumentos"""
        base_headers = ["NAMESPACE", "POD", "CONTAINER", "CPU", "REQ_CPU", "LIM_CPU", 
                       "MEMORY", "REQ_MEM", "LIM_MEM"]
        
        if self.args.wide_output or self.args.output_file:
            base_headers.extend(["STATUS", "RESTARTS", "NODE_IP", "NODE"])
        
        if self.args.custom_columns:
            return self.args.custom_columns
        
        return base_headers

    def _get_column_index(self, column_name):
        """Obtiene el índice de una columna por su nombre"""
        column_mapping = {
            'NAMESPACE': 0, 'POD': 1, 'CONTAINER': 2,
            'CPU': 3, 'REQ_CPU': 4, 'LIM_CPU': 5,
            'MEMORY': 6, 'REQ_MEM': 7, 'LIM_MEM': 8,
            'STATUS': 9, 'RESTARTS': 10,
            'NODE_IP': 11, 'NODE': 12
        }
        return column_mapping.get(column_name, -1)

    def _process_pod_data(self, pod):
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
            
            row = [
                namespace,                    # NAMESPACE
                pod_name,                    # POD
                container_name,              # CONTAINER
                container_metrics.get("cpu", "-"),  # CPU
                container["req_cpu"],        # REQ_CPU
                container["lim_cpu"],        # LIM_CPU
                container_metrics.get("memory", "-"),  # MEMORY
                container["req_mem"],        # REQ_MEM
                container["lim_mem"],        # LIM_MEM
                status,                      # STATUS
                restarts,                    # RESTARTS
                node_ip,                     # NODE_IP
                node_name                    # NODE
            ]
            pod_data.append(row)
        
        return pod_data

    def _apply_colors(self, row):
        """Aplica colores a una fila de datos según su estado"""
        colored_row = []
        cpu_idx = self._get_column_index('CPU')
        req_cpu_idx = self._get_column_index('REQ_CPU')
        lim_cpu_idx = self._get_column_index('LIM_CPU')
        mem_idx = self._get_column_index('MEMORY')
        req_mem_idx = self._get_column_index('REQ_MEM')
        lim_mem_idx = self._get_column_index('LIM_MEM')
        status_idx = self._get_column_index('STATUS')
        restarts_idx = self._get_column_index('RESTARTS')

        # Obtener colores para recursos
        (cpu_color, req_cpu_color, lim_cpu_color,
         mem_color, req_mem_color, lim_mem_color) = ResourceColorizer.colorize_usage(
            row[cpu_idx], row[mem_idx],
            row[req_cpu_idx], row[req_mem_idx],
            row[lim_cpu_idx], row[lim_mem_idx],
            self.args.warning_pct,
            self.args.danger_pct,
            self.args.diff_pct,
            self.args.underuse_pct
        )

        # Aplicar colores a cada campo
        for i, item in enumerate(row):
            if i >= len(self.headers):
                continue
                
            header = self.headers[i]
            
            if not self.use_color:
                colored_row.append(item)
                continue
            
            if header == "NAMESPACE":
                colored_row.append(ResourceColorizer.colorize_namespace(item))
            elif header == "POD":
                colored_row.append(ResourceColorizer.colorize_pod(item))
            elif header == "CONTAINER":
                colored_row.append(ResourceColorizer.colorize_container(item))
            elif header == "CPU":
                colored_row.append(f"{cpu_color}{item}{COLOR_RESET}")
            elif header == "REQ_CPU":
                colored_row.append(f"{req_cpu_color}{item}{COLOR_RESET}")
            elif header == "LIM_CPU":
                colored_row.append(f"{lim_cpu_color}{item}{COLOR_RESET}")
            elif header == "MEMORY":
                colored_row.append(f"{mem_color}{item}{COLOR_RESET}")
            elif header == "REQ_MEM":
                colored_row.append(f"{req_mem_color}{item}{COLOR_RESET}")
            elif header == "LIM_MEM":
                colored_row.append(f"{lim_mem_color}{item}{COLOR_RESET}")
            elif header == "STATUS":
                status_color, _ = ResourceColorizer.colorize_status(item, 0)
                colored_row.append(f"{status_color}{item}{COLOR_RESET}")
            elif header == "RESTARTS":
                _, restarts_color = ResourceColorizer.colorize_status("", item)
                colored_row.append(f"{restarts_color}{item}{COLOR_RESET}")
            elif header in ["NODE_IP", "NODE"]:
                colored_row.append(ResourceColorizer.colorize_node(item))
            else:
                colored_row.append(item)
        
        return colored_row

    def _generate_table(self, data):
        """Genera la tabla final para mostrar"""
        if self.args.number:
            return tabulate(
                data,
                headers=[f"{COLOR_BOLD if self.use_color else ''}{h}{COLOR_RESET if self.use_color else ''}" 
                        for h in self.headers],
                showindex=True,
                tablefmt="fancy_grid" if self.use_color else "plain"
            )
        return tabulate(
            data,
            headers=[f"{COLOR_BOLD if self.use_color else ''}{h}{COLOR_RESET if self.use_color else ''}" 
                    for h in self.headers],
            tablefmt="fancy_grid" if self.use_color else "plain"
        )

    def analyze(self):
        """Método principal que ejecuta el análisis completo"""
        try:
            # Obtener datos de Kubernetes
            pods = KubectlClient.get_pods(self.args.namespace, self.args.all_namespaces)
            
            # Procesar todos los pods
            all_data = []
            for pod in pods["items"]:
                all_data.extend(self._process_pod_data(pod))
            
            # Aplicar formato y colores
            colored_data = [self._apply_colors(row) for row in all_data]
            
            # Filtrar columnas si es necesario
            if self.args.custom_columns:
                column_indices = [self._get_column_index(col) for col in self.args.custom_columns]
                filtered_data = []
                for row in colored_data:
                    filtered_row = [row[i] for i in column_indices if i != -1]
                    filtered_data.append(filtered_row)
                colored_data = filtered_data
            
            # Generar salida
            table_output = self._generate_table(colored_data)
            
            # Exportar o mostrar resultados
            if self.args.output_file:
                Exporter.export(
                    table_output,
                    self.args.output_file,
                    self.use_color,
                    self.args.force,
                    self.args.landscape
                )
            else:
                print(table_output)
            
            return 0
        
        except Exception as e:
            error_msg = f"{COLOR_RED}Error:{COLOR_RESET} {str(e)}"
            if self.args.debug:
                error_msg += f"\n\n{COLOR_YELLOW}Debug info:{COLOR_RESET}\n{traceback.format_exc()}"
            print(error_msg)
            return 1

def analyze_resources(args):
    """Función de entrada para el análisis de recursos"""
    analyzer = KRCAnalyzer(args)
    return analyzer.analyze()

#!/usr/bin/env python3
#-----------------------------------------------------------------------------------#
# kubectl-resource-container-audit (KRCA) - Kubernetes Resource Container Auditor
# by: upszot
# Version 3.7 (with improved PDF/HTML export)
#-----------------------------------------------------------------------------------#

import argparse
import subprocess
import json
from tabulate import tabulate
import sys
import os
import re

# Códigos de color ANSI
COLOR_RESET = "\033[0m"
COLOR_RED = "\033[31m"
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_PURPLE = "\033[35m"
COLOR_WHITE = "\033[37m"
COLOR_BOLD = "\033[1m"
COLOR_CYAN = "\033[36m"
COLOR_BLUE = "\033[34m"

# Valores por defecto para los umbrales
DEFAULT_WARNING_PCT = 60
DEFAULT_DANGER_PCT = 75
DEFAULT_DIFF_PCT = 300
DEFAULT_UNDERUSE_PCT = 5

# Mapeo de columnas disponibles
AVAILABLE_COLUMNS = {
    'NAMESPACE': 0,
    'POD': 1,
    'CONTAINER': 2,
    'CPU': 3,
    'REQ_CPU': 4,
    'LIM_CPU': 5,
    'MEMORY': 6,
    'REQ_MEM': 7,
    'LIM_MEM': 8,
    'STATUS': 9,
    'RESTARTS': 10,
    'NODE_IP': 11,
    'NODE': 12
}

def show_help():
    """Muestra el mensaje de ayuda personalizado"""
    help_text = f"""
{COLOR_CYAN}{COLOR_BOLD}Kubernetes Resource Container Audit (KRCA){COLOR_RESET}

{COLOR_BOLD}Uso:{COLOR_RESET}
  kubectl resource-container-audit [OPCIONES]
  kubectl krca [OPCIONES]

{COLOR_BOLD}Opciones:{COLOR_RESET}
  -h, --help            Muestra este mensaje de ayuda
  -A, --all-namespaces  Mostrar recursos en todos los namespaces
  -n, --namespace NAMESPACE
                        Especificar un namespace particular
  --number              Mostrar números de fila
  --debug               Mostrar tablas de depuración
  --no-color            Deshabilitar salida coloreada (color activado por defecto)
  -o, --output FORMAT   Formato de salida (wide|custom-columns=<spec>)
                        Ejemplo: -o custom-columns=NAMESPACE,POD,CPU,MEMORY
  --warning-pct PCT     Porcentaje de warning (default: {DEFAULT_WARNING_PCT}%)
  --danger-pct PCT      Porcentaje de danger (default: {DEFAULT_DANGER_PCT}%)
  --diff-pct PCT        Porcentaje de diferencia para color púrpura (default: {DEFAULT_DIFF_PCT}%)
  --underuse-pct PCT    Porcentaje para detectar infrautilización (default: {DEFAULT_UNDERUSE_PCT}%)
  --output-file FILE    Guardar salida en archivo (soporta .txt, .html, .pdf)
  --force               Sobrescribir archivo existente
  --landscape           Orientación horizontal para PDF

{COLOR_BOLD}Columnas disponibles para custom-columns:{COLOR_RESET}
  NAMESPACE, POD, CONTAINER, CPU, REQ_CPU, LIM_CPU, MEMORY, REQ_MEM, LIM_MEM,
  STATUS, RESTARTS, NODE_IP, NODE

{COLOR_BOLD}Sistema de colores (activado por defecto):{COLOR_RESET}
  🟢 Verde  - Uso normal/Running
  🟡 Amarillo - Advertencia/Completed
  🔴 Rojo    - Peligro/CrashLoop
  🟣 Púrpura - Gran diff requests/limits
  🔵 Azul    - Infrautilización/Otros estados
"""
    print(help_text)
    sys.exit(0)

def check_dependencies():
    """Verifica todas las dependencias necesarias"""
    missing = []
    
    # Verificar módulos Python
    try:
        import tabulate
    except ImportError:
        missing.append("El módulo 'tabulate' no está instalado (pip install tabulate)")
    
    # Verificar wkhtmltopdf (solo necesario para exportar PDF)
    if os.system("which wkhtmltopdf > /dev/null 2>&1") != 0:
        missing.append("wkhtmltopdf no está instalado (necesario para exportar PDF)")
    
    # Verificar versión de Python
    if sys.version_info < (3, 6):
        missing.append(f"Se requiere Python 3.6+ (tienes {sys.version.split()[0]})")
    
    if missing:
        error_msg = "Error: Dependencias faltantes:\n- " + "\n- ".join(missing)
        error_msg += "\n\nInstale las dependencias con:\n"
        error_msg += "  pip install -r requirements.txt\n"
        error_msg += "Y para wkhtmltopdf:\n"
        error_msg += "  # Debian/Ubuntu:\n  sudo apt-get install wkhtmltopdf\n"
        error_msg += "  # RHEL/CentOS:\n  sudo yum install wkhtmltopdf"
        return False, error_msg
    
    return True, ""


def clean_ansi_codes(text):
    """Elimina los códigos ANSI del texto"""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)

def print_output(text, output_file=None, use_color=True, force=False, landscape=False):
    """Imprime en pantalla o guarda en archivo según corresponda"""
    if not output_file:
        print(text)
        return
    
    # Verificar si el archivo existe
    if os.path.exists(output_file) and not force:
        if use_color:
            print(f"{COLOR_RED}Error: El archivo {output_file} ya existe. Use --force para sobrescribir.{COLOR_RESET}")
        else:
            print(f"Error: El archivo {output_file} ya existe. Use --force para sobrescribir.")
        return
    
    try:
        # Para archivos de texto plano (.txt)
        if output_file.endswith('.txt'):
            with open(output_file, 'w') as f:
                # Eliminar códigos ANSI si no se usa color
                if not use_color:
                    text = clean_ansi_codes(text)
                f.write(text)
        
        # Para archivos HTML/PDF
        elif output_file.endswith(('.html', '.pdf')):
            # Extraer datos y cabeceras del texto formateado
            lines = text.split('\n')
            headers = []
            data = []
            
            # Procesar encabezados (eliminando códigos ANSI)
            if lines and len(lines) > 0:
                clean_header = clean_ansi_codes(lines[0])
                headers = [h.strip() for h in clean_header.split('\t') if h.strip()]
            
            # Procesar datos
            for line in lines[1:]:
                if line.strip():
                    # Eliminar códigos ANSI y dividir
                    clean_line = clean_ansi_codes(line)
                    row = [cell.strip() for cell in clean_line.split('\t') if cell.strip()]
                    if row:
                        data.append(row)
            
            # Generar tabla HTML con estilo mejorado
            html_table = tabulate(data, headers=headers, tablefmt='html')
            
            # CSS para la tabla
            table_style = """
            <style>
                table {
                    border-collapse: collapse;
                    width: 100%;
                    font-family: Arial, sans-serif;
                    font-size: 12px;
                }
                th, td {
                    border: 1px solid #ddd;
                    padding: 6px;
                    text-align: left;
                    white-space: nowrap;
                }
                th {
                    background-color: #f2f2f2;
                    font-weight: bold;
                    position: sticky;
                    top: 0;
                }
                tr:nth-child(even) {
                    background-color: #f9f9f9;
                }
                tr:hover {
                    background-color: #f1f1f1;
                }
                .container {
                    overflow-x: auto;
                    margin: 10px;
                }
                @page {
                    size: A4 landscape;
                    margin: 10mm;
                }
            </style>
            """
            
            full_html = f"""
            <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Kubernetes Resource Audit</title>
                    {table_style}
                </head>
                <body>
                    <div class="container">
                        {html_table}
                    </div>
                </body>
            </html>
            """
            
            # Para HTML
            if output_file.endswith('.html'):
                with open(output_file, 'w') as f:
                    f.write(full_html)
            
            # Para PDF
            else:
                tmp_html = "/tmp/krca_output.html"
                with open(tmp_html, 'w') as f:
                    f.write(full_html)
                
                try:
                    # Opciones para wkhtmltopdf
                    options = "--quiet --enable-local-file-access"
                    if landscape:
                        options += " -O landscape"
                    
                    os.system(f"wkhtmltopdf {options} {tmp_html} {output_file}")
                    os.remove(tmp_html)
                    if use_color:
                        print(f"{COLOR_GREEN}PDF generado: {output_file}{COLOR_RESET}")
                    else:
                        print(f"PDF generado: {output_file}")
                except Exception as e:
                    if use_color:
                        print(f"{COLOR_RED}Error al generar PDF: {e}{COLOR_RESET}")
                    else:
                        print(f"Error al generar PDF: {e}")
        
        else:
            raise ValueError(f"Formato de archivo no soportado: {output_file}")
    
    except Exception as e:
        if use_color:
            print(f"{COLOR_RED}Error al guardar archivo: {e}{COLOR_RESET}")
        else:
            print(f"Error al guardar archivo: {e}")

def run_cmd(cmd):
    """Ejecuta un comando en el shell y retorna su salida"""
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"{COLOR_RED}Error ejecutando comando: {e.cmd}{COLOR_RESET}")
        print(f"Mensaje de error: {e.stderr}")
        sys.exit(1)

def get_current_namespace():
    """Obtiene el namespace actual del contexto de kubectl"""
    cmd = "kubectl config view --minify -o jsonpath='{..namespace}'"
    try:
        namespace = run_cmd(cmd).strip()
        return namespace if namespace else "default"
    except subprocess.CalledProcessError:
        return "default"

def get_pods(namespace=None, all_namespaces=False):
    """Obtiene la lista de pods en formato JSON"""
    cmd = "kubectl get pods"
    if all_namespaces:
        cmd += " -A"
    elif namespace:
        cmd += f" -n {namespace}"
    else:
        cmd += f" -n {get_current_namespace()}"
    cmd += " -o json"
    output = run_cmd(cmd)
    return json.loads(output)

def get_pod_status(pod):
    """Obtiene el estado y reinicios de un pod"""
    status = pod["status"]
    container_statuses = status.get("containerStatuses", [])
    
    if not container_statuses:
        return "Unknown", 0
    
    # Tomamos el estado del primer contenedor
    container_status = container_statuses[0]
    state = container_status["state"]
    
    if "running" in state:
        return "Running", container_status.get("restartCount", 0)
    elif "waiting" in state:
        return f"Waiting: {state['waiting']['reason']}", container_status.get("restartCount", 0)
    elif "terminated" in state:
        return f"Terminated: {state['terminated']['reason']}", container_status.get("restartCount", 0)
    else:
        return "Unknown", container_status.get("restartCount", 0)

def get_node_info(pod):
    """Obtiene la IP y nombre del nodo donde está alojado el pod"""
    try:
        node_ip = pod["status"]["hostIP"]
    except KeyError:
        node_ip = "<none>"
    
    try:
        node_name = pod["spec"]["nodeName"]
    except KeyError:
        node_name = "<none>"
    
    return node_ip, node_name

def get_container_resources(pod):
    """Extrae las configuraciones de recursos de los contenedores"""
    containers = []
    for container in pod["spec"]["containers"]:
        name = container["name"]
        resources = container.get("resources", {})
        limits = resources.get("limits", {})
        requests = resources.get("requests", {})
        containers.append({
            "name": name,
            "req_cpu": requests.get("cpu", "<none>"),
            "req_mem": requests.get("memory", "<none>"),
            "lim_cpu": limits.get("cpu", "<none>"),
            "lim_mem": limits.get("memory", "<none>"),
        })
    return containers

def get_metrics(namespace=None, all_namespaces=False):
    """Obtiene las métricas de uso de recursos"""
    try:
        cmd = "kubectl top pod --no-headers"
        if all_namespaces:
            cmd += " -A"
        elif namespace:
            cmd += f" -n {namespace}"
        else:
            cmd += f" -n {get_current_namespace()}"
        
        cmd += " --containers"
        output = run_cmd(cmd)
        metrics = {}
        for line in output.splitlines():
            parts = line.split()
            if all_namespaces and len(parts) >= 5:
                namespace, pod_name, container_name, cpu, memory = parts[0], parts[1], parts[2], parts[3], parts[4]
                if pod_name not in metrics:
                    metrics[pod_name] = {}
                metrics[pod_name][container_name] = {
                    "cpu": cpu,
                    "memory": memory,
                }
            elif not all_namespaces and len(parts) >= 4:
                pod_name, container_name, cpu, memory = parts[0], parts[1], parts[2], parts[3]
                if pod_name not in metrics:
                    metrics[pod_name] = {}
                metrics[pod_name][container_name] = {
                    "cpu": cpu,
                    "memory": memory,
                }
        return metrics
    except subprocess.CalledProcessError:
        return {}

def parse_resource_value(value):
    """Convierte valores de recursos a milicores/mebibytes numéricos"""
    if value == "<none>" or value == "-":
        return None
    
    try:
        if value.endswith('m'):
            return float(value[:-1])
        elif value.endswith('Mi'):
            return float(value[:-2])
        elif value.endswith('Gi'):
            return float(value[:-2]) * 1024
        else:
            return float(value) * 1000 if '.' in value else float(value)
    except ValueError:
        return None

def colorize_usage(cpu_usage, mem_usage, req_cpu, req_mem, lim_cpu, lim_mem, 
                  warning_pct, danger_pct, diff_pct, underuse_pct):
    """Determina el color según la lógica de colores con umbrales configurables"""
    # Valores no definidos
    if cpu_usage in ("-", "<none>") or mem_usage in ("-", "<none>"):
        return (COLOR_WHITE, COLOR_WHITE, COLOR_WHITE, 
                COLOR_WHITE, COLOR_WHITE, COLOR_WHITE)
    
    try:
        # Convertir todo a valores numéricos comparables
        cpu_num = parse_resource_value(cpu_usage)
        mem_num = parse_resource_value(mem_usage)
        req_cpu_num = parse_resource_value(req_cpu)
        req_mem_num = parse_resource_value(req_mem)
        lim_cpu_num = parse_resource_value(lim_cpu)
        lim_mem_num = parse_resource_value(lim_mem)
        
        # Inicializar colores para cada campo
        cpu_color = COLOR_WHITE
        req_cpu_color = COLOR_WHITE
        lim_cpu_color = COLOR_WHITE
        mem_color = COLOR_WHITE
        req_mem_color = COLOR_WHITE
        lim_mem_color = COLOR_WHITE
        
        # Caso especial: Request no definido (amarillo)
        no_request_cpu = req_cpu in ("<none>", "-") or req_cpu_num is None
        no_request_mem = req_mem in ("<none>", "-") or req_mem_num is None
        
        # Caso especial: Limit no definido (amarillo)
        no_limit_cpu = lim_cpu in ("<none>", "-") or lim_cpu_num is None
        no_limit_mem = lim_mem in ("<none>", "-") or lim_mem_num is None
        
        # Colorear requests no definidos
        if no_request_cpu:
            req_cpu_color = COLOR_YELLOW
        if no_request_mem:
            req_mem_color = COLOR_YELLOW
            
        # Colorear limits no definidos
        if no_limit_cpu:
            lim_cpu_color = COLOR_YELLOW
        if no_limit_mem:
            lim_mem_color = COLOR_YELLOW
        
        # Lógica para CPU
        if cpu_num is not None:
            # Uso > limit (rojo en limit)
            if lim_cpu_num and cpu_num > lim_cpu_num:
                lim_cpu_color = COLOR_RED
                cpu_color = COLOR_RED
            
            # Uso normal entre request y limit (verde en uso y request)
            elif req_cpu_num and lim_cpu_num and req_cpu_num <= cpu_num <= lim_cpu_num:
                cpu_color = COLOR_GREEN
                req_cpu_color = COLOR_GREEN
            
            # Uso > danger-pct (rojo en uso)
            elif lim_cpu_num and (cpu_num / lim_cpu_num * 100) > danger_pct:
                cpu_color = COLOR_RED
            
            # warning-pct < Uso < danger-pct (amarillo en uso)
            elif lim_cpu_num and (cpu_num / lim_cpu_num * 100) > warning_pct:
                cpu_color = COLOR_YELLOW
            
            # Uso por debajo del request (púrpura en request)
            elif req_cpu_num and cpu_num < req_cpu_num:
                req_cpu_color = COLOR_PURPLE
            
            # Infrautilización severa (azul en request)
            elif req_cpu_num and (cpu_num / req_cpu_num * 100) < underuse_pct:
                req_cpu_color = COLOR_BLUE
            
            # Gran diferencia entre request y limit (púrpura en limit)
            if (not no_request_cpu and not no_limit_cpu and 
                lim_cpu_num and req_cpu_num and 
                (lim_cpu_num / req_cpu_num * 100) > diff_pct):
                lim_cpu_color = COLOR_PURPLE
        
        # Lógica para Memory
        if mem_num is not None:
            # Uso > limit (rojo en limit)
            if lim_mem_num and mem_num > lim_mem_num:
                lim_mem_color = COLOR_RED
                mem_color = COLOR_RED
            
            # Uso normal entre request y limit (verde en uso y request)
            elif req_mem_num and lim_mem_num and req_mem_num <= mem_num <= lim_mem_num:
                mem_color = COLOR_GREEN
                req_mem_color = COLOR_GREEN
            
            # Uso > danger-pct (rojo en uso)
            elif lim_mem_num and (mem_num / lim_mem_num * 100) > danger_pct:
                mem_color = COLOR_RED
            
            # warning-pct < Uso < danger-pct (amarillo en uso)
            elif lim_mem_num and (mem_num / lim_mem_num * 100) > warning_pct:
                mem_color = COLOR_YELLOW
            
            # Uso por debajo del request (púrpura en request)
            elif req_mem_num and mem_num < req_mem_num:
                req_mem_color = COLOR_PURPLE
            
            # Infrautilización severa (azul en request)
            elif req_mem_num and (mem_num / req_mem_num * 100) < underuse_pct:
                req_mem_color = COLOR_BLUE
            
            # Gran diferencia entre request y limit (púrpura en limit)
            if (not no_request_mem and not no_limit_mem and 
                lim_mem_num and req_mem_num and 
                (lim_mem_num / req_mem_num * 100) > diff_pct):
                lim_mem_color = COLOR_PURPLE
        
        return (cpu_color, req_cpu_color, lim_cpu_color, 
                mem_color, req_mem_color, lim_mem_color)
        
    except (ValueError, TypeError, ZeroDivisionError):
        return (COLOR_WHITE, COLOR_WHITE, COLOR_WHITE, 
                COLOR_WHITE, COLOR_WHITE, COLOR_WHITE)

def colorize_status(status, restarts):
    """Determina el color para las columnas STATUS y RESTARTS"""
    status_color = COLOR_WHITE
    restarts_color = COLOR_WHITE
    
    if "Running" in status:
        status_color = COLOR_GREEN
    elif "Terminated: Completed" in status:
        status_color = COLOR_YELLOW
    elif "Waiting: CrashLoopBackOff" in status:
        status_color = COLOR_RED
    elif "Waiting" in status or "Terminated" in status:
        status_color = COLOR_BLUE
    else:
        status_color = COLOR_BLUE
    
    if restarts > 0:
        restarts_color = COLOR_YELLOW if restarts < 5 else COLOR_RED
    
    return status_color, restarts_color

def parse_custom_columns(spec):
    """Parsea la especificación de columnas personalizadas"""
    if not spec.startswith('custom-columns='):
        return None
    
    columns_spec = spec.split('=', 1)[1]
    columns = [col.strip() for col in columns_spec.split(',')]
    
    # Validar columnas
    valid_columns = []
    for col in columns:
        if col in AVAILABLE_COLUMNS:
            valid_columns.append(col)
        else:
            print(f"{COLOR_YELLOW}Advertencia: Columna '{col}' no reconocida. Columnas disponibles: {', '.join(AVAILABLE_COLUMNS.keys())}{COLOR_RESET}")
    
    return valid_columns if valid_columns else None

def main():
    # Verificar si se ejecuta como plugin de kubectl
    if os.path.basename(sys.argv[0]) in ['kubectl-resource-container-audit', 'kubectl-krca']:
        # Reordenar argumentos para que funcione como plugin
        if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
            sys.argv.insert(1, '--')

    parser = argparse.ArgumentParser(description="Kubernetes Resource Container Audit (KRCA)", add_help=False)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-A", "--all-namespaces", action="store_true", help="All namespaces")
    group.add_argument("-n", "--namespace", help="Kubernetes namespace")
    parser.add_argument("--number", action="store_true", help="Show row numbers")
    parser.add_argument("--debug", action="store_true", help="Show debug tables")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("-o", "--output", help="Output format (wide|custom-columns=<spec>)")
    parser.add_argument("--output-file", help="Save output to file (supports .txt, .html, .pdf)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output file")
    parser.add_argument("--landscape", action="store_true", help="Landscape orientation for PDF")
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message and exit")
    
    # Parámetros configurables para los umbrales
    parser.add_argument("--warning-pct", type=int, default=DEFAULT_WARNING_PCT,
                       help=f"Warning threshold percentage (default: {DEFAULT_WARNING_PCT}%%)")
    parser.add_argument("--danger-pct", type=int, default=DEFAULT_DANGER_PCT,
                       help=f"Danger threshold percentage (default: {DEFAULT_DANGER_PCT}%%)")
    parser.add_argument("--diff-pct", type=int, default=DEFAULT_DIFF_PCT,
                       help=f"Difference threshold for purple color (default: {DEFAULT_DIFF_PCT}%%)")
    parser.add_argument("--underuse-pct", type=int, default=DEFAULT_UNDERUSE_PCT,
                       help=f"Underuse threshold percentage (default: {DEFAULT_UNDERUSE_PCT}%%)")
    
    args = parser.parse_args()

    # Mostrar ayuda si se solicita
    if args.help:
        show_help()

    # Verificar dependencias si se va a exportar
    if args.output_file and args.output_file.endswith(('.html', '.pdf')):
        deps_ok, deps_msg = check_dependencies()
        if not deps_ok:
            print(f"{COLOR_RED}Error: {deps_msg}{COLOR_RESET}")
            sys.exit(1)

    # Determinar el formato de salida
    wide_output = args.output and args.output.lower() == "wide"
    custom_columns = args.output and parse_custom_columns(args.output)
    use_color = not args.no_color

    # Obtener datos
    pods = get_pods(args.namespace, args.all_namespaces)
    metrics = get_metrics(args.namespace, args.all_namespaces)

    # Preparar datos para las tablas
    final_data = []

    for pod in pods["items"]:
        pod_name = pod["metadata"]["name"]
        namespace = pod["metadata"]["namespace"]
        status, restarts = get_pod_status(pod)
        node_ip, node_name = get_node_info(pod)
        containers = get_container_resources(pod)
        
        for container in containers:
            container_name = container["name"]
            pod_metrics = metrics.get(pod_name, {})
            container_metrics = pod_metrics.get(container_name, {})
            
            # Tabla final con todas las columnas posibles
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
            final_data.append(row)

    # Determinar las columnas a mostrar
    if custom_columns:
        headers = custom_columns
        column_indices = [AVAILABLE_COLUMNS[col] for col in custom_columns]
        filtered_data = [[row[i] for i in column_indices] for row in final_data]
        
        colored_final_data = []
        for row in filtered_data:
            colored_row = []
            for i, item in enumerate(row):
                col_name = headers[i]
                if use_color:
                    if col_name == "NAMESPACE":
                        colored_row.append(f"{COLOR_CYAN}{item}{COLOR_RESET}")
                    elif col_name == "CONTAINER":
                        colored_row.append(f"{COLOR_CYAN}{item}{COLOR_RESET}")
                    elif col_name == "POD":
                        colored_row.append(f"{COLOR_WHITE}{item}{COLOR_RESET}")
                    elif col_name in ["NODE_IP", "NODE"]:
                        colored_row.append(f"{COLOR_WHITE}{item}{COLOR_RESET}")
                    elif col_name == "STATUS":
                        status_color, _ = colorize_status(item, 0)
                        colored_row.append(f"{status_color}{item}{COLOR_RESET}")
                    else:
                        colored_row.append(item)
                else:
                    colored_row.append(item)
            colored_final_data.append(colored_row)
            
    else:
        headers = ["NAMESPACE", "POD", "CONTAINER", "CPU", "REQ_CPU", "LIM_CPU", "MEMORY", "REQ_MEM", "LIM_MEM"]
        if wide_output:
            headers.extend(["STATUS", "RESTARTS", "NODE_IP", "NODE"])
        
        colored_final_data = []
        for row in final_data:
            colored_row = []
            (cpu_color, req_cpu_color, lim_cpu_color, 
             mem_color, req_mem_color, lim_mem_color) = colorize_usage(
                row[3], row[6], row[4], row[7], row[5], row[8],
                args.warning_pct, args.danger_pct, args.diff_pct, args.underuse_pct)
            
            status_color, restarts_color = colorize_status(row[9], row[10]) if len(row) > 9 else (COLOR_WHITE, COLOR_WHITE)
            
            for i, item in enumerate(row):
                if i >= len(headers):
                    continue
                    
                if use_color:
                    if headers[i] == "NAMESPACE":
                        colored_row.append(f"{COLOR_CYAN}{item}{COLOR_RESET}")
                    elif headers[i] == "CONTAINER":
                        colored_row.append(f"{COLOR_CYAN}{item}{COLOR_RESET}")
                    elif headers[i] == "POD":
                        colored_row.append(f"{COLOR_WHITE}{item}{COLOR_RESET}")
                    elif headers[i] == "CPU":
                        colored_row.append(f"{cpu_color}{item}{COLOR_RESET}")
                    elif headers[i] == "REQ_CPU":
                        colored_row.append(f"{req_cpu_color}{item}{COLOR_RESET}")
                    elif headers[i] == "LIM_CPU":
                        colored_row.append(f"{lim_cpu_color}{item}{COLOR_RESET}")
                    elif headers[i] == "MEMORY":
                        colored_row.append(f"{mem_color}{item}{COLOR_RESET}")
                    elif headers[i] == "REQ_MEM":
                        colored_row.append(f"{req_mem_color}{item}{COLOR_RESET}")
                    elif headers[i] == "LIM_MEM":
                        colored_row.append(f"{lim_mem_color}{item}{COLOR_RESET}")
                    elif headers[i] == "STATUS":
                        colored_row.append(f"{status_color}{item}{COLOR_RESET}")
                    elif headers[i] == "RESTARTS":
                        colored_row.append(f"{restarts_color}{item}{COLOR_RESET}")
                    elif headers[i] in ["NODE_IP", "NODE"]:
                        colored_row.append(f"{COLOR_WHITE}{item}{COLOR_RESET}")
                    else:
                        colored_row.append(item)
                else:
                    colored_row.append(item)
            colored_final_data.append(colored_row)
    
    # Generar salida en formato TSV para mejor parsing
    if args.number:
        table_output = tabulate(colored_final_data, 
                              headers=[f"{COLOR_BOLD if use_color else ''}{h}{COLOR_RESET if use_color else ''}" for h in headers], 
                              showindex=True, 
                              tablefmt="tsv")
    else:
        table_output = tabulate(colored_final_data, 
                              headers=[f"{COLOR_BOLD if use_color else ''}{h}{COLOR_RESET if use_color else ''}" for h in headers], 
                              tablefmt="tsv")
    
    # Imprimir o guardar en archivo
    print_output(table_output, args.output_file, use_color, args.force, args.landscape)

if __name__ == "__main__":
    main()

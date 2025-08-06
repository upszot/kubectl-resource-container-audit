#!/usr/bin/env python3
# krca/colorizer.py - Módulo para manejo de colores y estilos

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

class ResourceColorizer:
    """Clase para aplicar colores a los recursos según su estado y uso"""
    
    @staticmethod
    def colorize_usage(cpu_usage, mem_usage, req_cpu, req_mem, lim_cpu, lim_mem, 
                      warning_pct, danger_pct, diff_pct, underuse_pct):
        """
        Determina los colores para los valores de uso de recursos
        Retorna tuplas de colores para: (cpu, req_cpu, lim_cpu, mem, req_mem, lim_mem)
        """
        def get_cpu_colors():
            """Lógica específica para colores de CPU"""
            # Valores no definidos
            if cpu_usage in ("-", "<none>") or req_cpu in ("-", "<none>") or lim_cpu in ("-", "<none>"):
                return (COLOR_WHITE, COLOR_WHITE, COLOR_WHITE)
            
            cpu_num = ResourceColorizer.parse_resource_value(cpu_usage)
            req_cpu_num = ResourceColorizer.parse_resource_value(req_cpu)
            lim_cpu_num = ResourceColorizer.parse_resource_value(lim_cpu)
            
            cpu_color = COLOR_WHITE
            req_cpu_color = COLOR_WHITE
            lim_cpu_color = COLOR_WHITE
            
            # Caso especial: Request no definido
            if req_cpu in ("<none>", "-") or req_cpu_num is None:
                req_cpu_color = COLOR_YELLOW
            
            # Caso especial: Limit no definido
            if lim_cpu in ("<none>", "-") or lim_cpu_num is None:
                lim_cpu_color = COLOR_YELLOW
            
            if cpu_num is not None:
                # Uso > limit (rojo)
                if lim_cpu_num and cpu_num > lim_cpu_num:
                    lim_cpu_color = COLOR_RED
                    cpu_color = COLOR_RED
                
                # Uso normal entre request y limit (verde)
                elif req_cpu_num and lim_cpu_num and req_cpu_num <= cpu_num <= lim_cpu_num:
                    cpu_color = COLOR_GREEN
                    req_cpu_color = COLOR_GREEN
                
                # Uso > danger-pct (rojo)
                elif lim_cpu_num and (cpu_num / lim_cpu_num * 100) > danger_pct:
                    cpu_color = COLOR_RED
                
                # warning-pct < Uso < danger-pct (amarillo)
                elif lim_cpu_num and (cpu_num / lim_cpu_num * 100) > warning_pct:
                    cpu_color = COLOR_YELLOW
                
                # Uso por debajo del request (púrpura)
                elif req_cpu_num and cpu_num < req_cpu_num:
                    req_cpu_color = COLOR_PURPLE
                
                # Infrautilización severa (azul)
                elif req_cpu_num and (cpu_num / req_cpu_num * 100) < underuse_pct:
                    req_cpu_color = COLOR_BLUE
                
                # Gran diferencia entre request y limit (púrpura)
                if (req_cpu_num and lim_cpu_num and 
                    (lim_cpu_num / req_cpu_num * 100) > diff_pct):
                    lim_cpu_color = COLOR_PURPLE
            
            return (cpu_color, req_cpu_color, lim_cpu_color)
        
        def get_mem_colors():
            """Lógica específica para colores de memoria"""
            # Valores no definidos
            if mem_usage in ("-", "<none>") or req_mem in ("-", "<none>") or lim_mem in ("-", "<none>"):
                return (COLOR_WHITE, COLOR_WHITE, COLOR_WHITE)
            
            mem_num = ResourceColorizer.parse_resource_value(mem_usage)
            req_mem_num = ResourceColorizer.parse_resource_value(req_mem)
            lim_mem_num = ResourceColorizer.parse_resource_value(lim_mem)
            
            mem_color = COLOR_WHITE
            req_mem_color = COLOR_WHITE
            lim_mem_color = COLOR_WHITE
            
            # Caso especial: Request no definido
            if req_mem in ("<none>", "-") or req_mem_num is None:
                req_mem_color = COLOR_YELLOW
            
            # Caso especial: Limit no definido
            if lim_mem in ("<none>", "-") or lim_mem_num is None:
                lim_mem_color = COLOR_YELLOW
            
            if mem_num is not None:
                # Uso > limit (rojo)
                if lim_mem_num and mem_num > lim_mem_num:
                    lim_mem_color = COLOR_RED
                    mem_color = COLOR_RED
                
                # Uso normal entre request y limit (verde)
                elif req_mem_num and lim_mem_num and req_mem_num <= mem_num <= lim_mem_num:
                    mem_color = COLOR_GREEN
                    req_mem_color = COLOR_GREEN
                
                # Uso > danger-pct (rojo)
                elif lim_mem_num and (mem_num / lim_mem_num * 100) > danger_pct:
                    mem_color = COLOR_RED
                
                # warning-pct < Uso < danger-pct (amarillo)
                elif lim_mem_num and (mem_num / lim_mem_num * 100) > warning_pct:
                    mem_color = COLOR_YELLOW
                
                # Uso por debajo del request (púrpura)
                elif req_mem_num and mem_num < req_mem_num:
                    req_mem_color = COLOR_PURPLE
                
                # Infrautilización severa (azul)
                elif req_mem_num and (mem_num / req_mem_num * 100) < underuse_pct:
                    req_mem_color = COLOR_BLUE
                
                # Gran diferencia entre request y limit (púrpura)
                if (req_mem_num and lim_mem_num and 
                    (lim_mem_num / req_mem_num * 100) > diff_pct):
                    lim_mem_color = COLOR_PURPLE
            
            return (mem_color, req_mem_color, lim_mem_color)
        
        # Obtener colores para CPU y memoria
        cpu_colors = get_cpu_colors()
        mem_colors = get_mem_colors()
        
        return (
            cpu_colors[0], cpu_colors[1], cpu_colors[2],  # CPU, REQ_CPU, LIM_CPU
            mem_colors[0], mem_colors[1], mem_colors[2]   # MEM, REQ_MEM, LIM_MEM
        )

    @staticmethod
    def colorize_status(status, restarts):
        """
        Determina el color para las columnas STATUS y RESTARTS
        Retorna tupla: (status_color, restarts_color)
        """
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

    @staticmethod
    def colorize_namespace(name):
        """Color para nombres de namespace"""
        return f"{COLOR_CYAN}{name}{COLOR_RESET}"

    @staticmethod
    def colorize_pod(name):
        """Color para nombres de pod"""
        return f"{COLOR_WHITE}{name}{COLOR_RESET}"

    @staticmethod
    def colorize_container(name):
        """Color para nombres de contenedor"""
        return f"{COLOR_CYAN}{name}{COLOR_RESET}"

    @staticmethod
    def colorize_node(name):
        """Color para nombres de nodo"""
        return f"{COLOR_WHITE}{name}{COLOR_RESET}"

    @staticmethod
    def parse_resource_value(value):
        """
        Convierte valores de recursos a milicores/mebibytes numéricos
        Retorna None para valores inválidos
        """
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

    @staticmethod
    def strip_colors(text):
        """Elimina códigos ANSI del texto"""
        import re
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        return ansi_escape.sub('', text)

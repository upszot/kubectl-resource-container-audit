#!/usr/bin/env python3
# krca/colorizer.py - Módulo para manejo de colores y estilos

from .utils import KRCAUtils

class ResourceColorizer:
    """Clase para aplicar colores a los recursos según su estado y uso"""

    # Códigos de color ANSI como constantes de clase
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    PURPLE = "\033[35m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    BLUE = "\033[34m"

    # Columnas que usan la lógica de color histórica
    HISTORICAL_COLUMNS = ('CPU_AVG', 'CPU_P95', 'CPU_MAX', 'MEM_AVG', 'MEM_MAX')

    @classmethod
    def red(cls, text: str) -> str:
        """Aplica color rojo al texto"""
        return f"{cls.RED}{text}{cls.RESET}"

    @classmethod
    def green(cls, text: str) -> str:
        """Aplica color verde al texto"""
        return f"{cls.GREEN}{text}{cls.RESET}"

    @classmethod
    def yellow(cls, text: str) -> str:
        """Aplica color amarillo al texto"""
        return f"{cls.YELLOW}{text}{cls.RESET}"

    @classmethod
    def blue(cls, text: str) -> str:
        """Aplica color azul al texto"""
        return f"{cls.BLUE}{text}{cls.RESET}"

    @classmethod
    def cyan(cls, text: str) -> str:
        """Aplica color cyan al texto"""
        return f"{cls.CYAN}{text}{cls.RESET}"

    @classmethod
    def purple(cls, text: str) -> str:
        """Aplica color púrpura al texto"""
        return f"{cls.PURPLE}{text}{cls.RESET}"

    @classmethod
    def bold(cls, text: str) -> str:
        """Aplica negrita al texto"""
        return f"{cls.BOLD}{text}{cls.RESET}"

    # ------------------------------------------------------------------
    # Lógica compartida de colores (modo live y modo histórico)
    # ------------------------------------------------------------------
    @classmethod
    def _color_resource(cls, usage, request, limit, warning_pct, danger_pct,
                        diff_pct, underuse_pct, parser):
        """
        Calcula los colores de (uso, request, limit) aplicando las mismas
        reglas para CPU y memoria. `parser` normaliza las unidades.
        """
        usage_num = parser(usage)
        req_num = parser(request)
        lim_num = parser(limit)

        usage_color = cls.WHITE
        req_color = cls.WHITE
        lim_color = cls.WHITE

        # Valores de configuración ausentes -> amarillo
        if req_num is None:
            req_color = cls.YELLOW
        if lim_num is None:
            lim_color = cls.YELLOW

        if usage_num is not None:
            if lim_num and usage_num > lim_num:
                # Uso por encima del límite
                usage_color = cls.RED
                lim_color = cls.RED
            elif req_num and lim_num and req_num <= usage_num <= lim_num:
                # Uso normal entre request y limit
                usage_color = cls.GREEN
                req_color = cls.GREEN
            elif lim_num and (usage_num / lim_num * 100) > danger_pct:
                usage_color = cls.RED
            elif lim_num and (usage_num / lim_num * 100) > warning_pct:
                usage_color = cls.YELLOW
            elif req_num and (usage_num / req_num * 100) < underuse_pct:
                # Infrautilización severa (tiene prioridad sobre "bajo request")
                req_color = cls.BLUE
            elif req_num and usage_num < req_num:
                # Uso por debajo del request
                req_color = cls.PURPLE

            # Gran diferencia entre request y limit
            if req_num and lim_num and (lim_num / req_num * 100) > diff_pct:
                lim_color = cls.PURPLE

        return usage_color, req_color, lim_color

    @classmethod
    def _color_peak(cls, peak, request, limit, warning_pct, danger_pct,
                    underuse_pct, parser):
        """
        Colores para valores pico (p95/máximo) del análisis histórico.
        Un pico por encima del limit es siempre rojo.
        """
        value = parser(peak)
        req_num = parser(request)
        lim_num = parser(limit)

        if value is None:
            return cls.WHITE
        if lim_num and value > lim_num:
            return cls.RED
        if lim_num and (value / lim_num * 100) > danger_pct:
            return cls.RED
        if lim_num and (value / lim_num * 100) > warning_pct:
            return cls.YELLOW
        if req_num and lim_num and req_num <= value <= lim_num:
            return cls.GREEN
        if req_num and (value / req_num * 100) < underuse_pct:
            return cls.BLUE
        return cls.WHITE

    @classmethod
    def colorize_usage(cls, cpu_usage, mem_usage, req_cpu, req_mem, lim_cpu, lim_mem,
                       warning_pct, danger_pct, diff_pct, underuse_pct):
        """
        Determina los colores para los valores de uso de recursos
        Retorna tuplas de colores para: (cpu, req_cpu, lim_cpu, mem, req_mem, lim_mem)
        """
        cpu_colors = cls._color_resource(
            cpu_usage, req_cpu, lim_cpu,
            warning_pct, danger_pct, diff_pct, underuse_pct,
            KRCAUtils.parse_cpu_to_millicores
        )
        mem_colors = cls._color_resource(
            mem_usage, req_mem, lim_mem,
            warning_pct, danger_pct, diff_pct, underuse_pct,
            KRCAUtils.parse_memory_to_mib
        )

        return (
            cpu_colors[0], cpu_colors[1], cpu_colors[2],  # CPU, REQ_CPU, LIM_CPU
            mem_colors[0], mem_colors[1], mem_colors[2]   # MEM, REQ_MEM, LIM_MEM
        )

    @classmethod
    def colorize_historical(cls, cpu_avg, cpu_p95, cpu_max, mem_avg, mem_max,
                            req_cpu, req_mem, lim_cpu, lim_mem,
                            warning_pct, danger_pct, diff_pct, underuse_pct):
        """
        Determina los colores para las columnas históricas.

        - CPU se evalúa con el promedio (uso típico).
        - Memoria se evalúa con el promedio en MEM_AVG y con el pico en MEM_MAX,
          que es el valor que anticipa un OOMKill.

        Retorna un diccionario columna -> código ANSI.
        """
        cpu_avg_color, req_cpu_color, lim_cpu_color = cls._color_resource(
            cpu_avg, req_cpu, lim_cpu,
            warning_pct, danger_pct, diff_pct, underuse_pct,
            KRCAUtils.parse_cpu_to_millicores
        )
        mem_avg_color, req_mem_color, lim_mem_color = cls._color_resource(
            mem_avg, req_mem, lim_mem,
            warning_pct, danger_pct, diff_pct, underuse_pct,
            KRCAUtils.parse_memory_to_mib
        )

        return {
            'CPU_AVG': cpu_avg_color,
            'CPU_P95': cls._color_peak(
                cpu_p95, req_cpu, lim_cpu,
                warning_pct, danger_pct, underuse_pct,
                KRCAUtils.parse_cpu_to_millicores
            ),
            'CPU_MAX': cls._color_peak(
                cpu_max, req_cpu, lim_cpu,
                warning_pct, danger_pct, underuse_pct,
                KRCAUtils.parse_cpu_to_millicores
            ),
            'MEM_AVG': mem_avg_color,
            'MEM_MAX': cls._color_peak(
                mem_max, req_mem, lim_mem,
                warning_pct, danger_pct, underuse_pct,
                KRCAUtils.parse_memory_to_mib
            ),
            'REQ_CPU': req_cpu_color,
            'LIM_CPU': lim_cpu_color,
            'REQ_MEM': req_mem_color,
            'LIM_MEM': lim_mem_color,
        }

    @staticmethod
    def colorize_status(status, restarts):
        """
        Determina el color para las columnas STATUS y RESTARTS
        Retorna tupla: (status_color, restarts_color)
        """
        status_color = ResourceColorizer.WHITE
        restarts_color = ResourceColorizer.WHITE

        if "Running" in status:
            status_color = ResourceColorizer.GREEN
        elif "Terminated: Completed" in status:
            status_color = ResourceColorizer.YELLOW
        elif "Waiting: CrashLoopBackOff" in status:
            status_color = ResourceColorizer.RED
        elif "Waiting" in status or "Terminated" in status:
            status_color = ResourceColorizer.BLUE
        else:
            status_color = ResourceColorizer.BLUE

        if restarts > 0:
            restarts_color = ResourceColorizer.YELLOW if restarts < 5 else ResourceColorizer.RED

        return status_color, restarts_color

    @staticmethod
    def colorize_namespace(name):
        """Color para nombres de namespace"""
        return f"{ResourceColorizer.CYAN}{name}{ResourceColorizer.RESET}"

    @staticmethod
    def colorize_pod(name):
        """Color para nombres de pod"""
        return f"{ResourceColorizer.WHITE}{name}{ResourceColorizer.RESET}"

    @staticmethod
    def colorize_container(name):
        """Color para nombres de contenedor"""
        return f"{ResourceColorizer.CYAN}{name}{ResourceColorizer.RESET}"

    @staticmethod
    def colorize_node(name):
        """Color para nombres de nodo"""
        return f"{ResourceColorizer.WHITE}{name}{ResourceColorizer.RESET}"

    @staticmethod
    def parse_resource_value(value):
        """
        Convierte valores de recursos a milicores/mebibytes numéricos
        Retorna None para valores inválidos

        Se mantiene por compatibilidad. Para comparaciones exactas use
        KRCAUtils.parse_cpu_to_millicores / KRCAUtils.parse_memory_to_mib.
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

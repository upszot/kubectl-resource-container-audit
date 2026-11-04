#!/usr/bin/env python3
# krca/utils.py - Módulo utilitario completo (Compatible con v4.0)

import re
from typing import Optional, Union

# Unidades de tiempo aceptadas por --history-window / --history-step
_DURATION_UNITS = {
    's': 1,
    'm': 60,
    'h': 3600,
    'd': 86400,
    'w': 604800,
}

# Una duración es una secuencia de tokens "<número><unidad>", por ejemplo
# "90m", "12h", "7d", "1d12h" o "2w".
_DURATION_RE = re.compile(r'^(?:\d+(?:\.\d+)?[smhdw])+$')
_DURATION_TOKEN_RE = re.compile(r'(\d+(?:\.\d+)?)([smhdw])')

# Pasos de muestreo "redondos" que entiende Prometheus sin problemas
_STEP_CANDIDATES = [
    30, 60, 120, 300, 600, 900, 1800, 3600,
    7200, 10800, 21600, 43200, 86400, 172800, 604800,
]

# Mínimo de puntos por serie que se consideran suficientes para calcular
# promedio, p95 y máximo con una precisión razonable.
DEFAULT_HISTORY_POINTS = 300


def parse_duration(value: Union[str, int, float]) -> float:
    """
    Convierte una duración legible a segundos.

    Ejemplos: "90m" -> 5400, "7d" -> 604800, "1d12h" -> 129600
    Un número sin unidad se interpreta como segundos.

    Raises:
        ValueError: si el formato no es válido o la duración no es positiva.
    """
    if isinstance(value, bool):
        raise ValueError(f"Duración inválida: {value!r}")

    if isinstance(value, (int, float)):
        if value <= 0:
            raise ValueError(f"La duración debe ser positiva: {value!r}")
        return float(value)

    text = str(value).strip().lower()
    if not text:
        raise ValueError("La duración no puede estar vacía")

    # Número plano -> segundos
    if re.fullmatch(r'\d+(?:\.\d+)?', text):
        seconds = float(text)
        if seconds <= 0:
            raise ValueError(f"La duración debe ser positiva: {value!r}")
        return seconds

    if not _DURATION_RE.match(text):
        raise ValueError(
            f"Duración inválida: '{value}'. Use formatos como 30s, 90m, 12h, 7d o 2w"
        )

    total = 0.0
    for number, unit in _DURATION_TOKEN_RE.findall(text):
        total += float(number) * _DURATION_UNITS[unit]

    if total <= 0:
        raise ValueError(f"La duración debe ser positiva: {value!r}")
    return total


def format_duration(seconds: float) -> str:
    """Convierte segundos a una duración compacta (ej. 129600 -> '1d12h')."""
    seconds = int(round(seconds))
    if seconds <= 0:
        return "0s"

    parts = []
    for unit, factor in (('w', 604800), ('d', 86400), ('h', 3600), ('m', 60), ('s', 1)):
        if seconds >= factor:
            amount, seconds = divmod(seconds, factor)
            parts.append(f"{amount}{unit}")
    return ''.join(parts)


def nice_step(window_seconds: float, target_points: int = DEFAULT_HISTORY_POINTS) -> int:
    """
    Calcula un paso de muestreo que devuelva aproximadamente `target_points`
    puntos por serie. Evita pasos no alineados y valores por debajo del
    intervalo de scrape habitual (30s).
    """
    if target_points <= 0:
        target_points = DEFAULT_HISTORY_POINTS
    raw_step = max(float(window_seconds) / target_points, 30.0)
    for candidate in _STEP_CANDIDATES:
        if candidate >= raw_step:
            return candidate
    return _STEP_CANDIDATES[-1]


def parse_cpu_to_millicores(value) -> Optional[float]:
    """
    Convierte un valor de CPU de Kubernetes a milicores.

    Ejemplos: "500m" -> 500, "1" -> 1000, "0.5" -> 500, "250000n" -> 0.25
    """
    if value is None:
        return None
    text = str(value).strip()
    if text in ('', '-', '<none>', 'None'):
        return None

    try:
        if text.endswith('n'):
            return float(text[:-1]) / 1_000_000
        if text.endswith('u') or text.endswith('µ'):
            return float(text[:-1]) / 1_000
        if text.endswith('m'):
            return float(text[:-1])
        return float(text) * 1000
    except ValueError:
        return None


def parse_memory_to_mib(value) -> Optional[float]:
    """
    Convierte un valor de memoria de Kubernetes a mebibytes (MiB).

    Ejemplos: "128Mi" -> 128, "1Gi" -> 1024, "1024Ki" -> 1,
    "1048576" (bytes) -> 1
    """
    if value is None:
        return None
    text = str(value).strip()
    if text in ('', '-', '<none>', 'None'):
        return None

    suffixes = {
        'Ki': 1.0 / 1024,
        'Mi': 1.0,
        'Gi': 1024.0,
        'Ti': 1024.0 * 1024,
        'Pi': 1024.0 * 1024 * 1024,
        'K': 1000.0 / (1024 * 1024),
        'M': 1000000.0 / (1024 * 1024),
        'G': 1000000000.0 / (1024 * 1024),
        'T': 1000000000000.0 / (1024 * 1024),
        'P': 1000000000000000.0 / (1024 * 1024),
    }

    try:
        for suffix in ('Ki', 'Mi', 'Gi', 'Ti', 'Pi'):
            if text.endswith(suffix):
                return float(text[:-2]) * suffixes[suffix]
        if text[-1] in 'KMGTP':
            return float(text[:-1]) * suffixes[text[-1]]
        # Sin sufijo: bytes
        return float(text) / (1024 * 1024)
    except (ValueError, KeyError):
        return None


# Función independiente para compatibilidad
def calculate_percentage_diff(current: Union[float, int], reference: Union[float, int]) -> float:
    """Calcula diferencia porcentual entre valores (compatible con v4.0)"""
    if reference == 0:
        return 0.0
    return ((current - reference) / reference) * 100

class KRCAUtils:
    """Clase con todas las utilidades necesarias para KRCA"""
    
    @staticmethod
    def calculate_percentage_diff(current: Union[float, int], reference: Union[float, int]) -> float:
        """Versión de clase que usa la función independiente"""
        return calculate_percentage_diff(current, reference)

    @staticmethod
    def parse_resource_value(value: str) -> Optional[float]:
        """
        Convierte valores de recursos (CPU/memoria) a números.
        Ejemplos: "100m" -> 0.1, "1Gi" -> 1024.0
        """
        if value in ("<none>", "-", ""):
            return None
            
        try:
            if value.endswith('m'):
                return float(value[:-1])          # 500m -> 0.5
            elif value.endswith('Ki'):
                return float(value[:-2]) / 1024   # 1024Ki -> 1
            elif value.endswith('Mi'):
                return float(value[:-2])          # 512Mi -> 512
            elif value.endswith('Gi'):
                return float(value[:-2]) * 1024   # 2Gi -> 2048
            elif value.endswith('Ti'):
                return float(value[:-2]) * 1048576 # 1Ti -> 1048576
            else:
                return float(value)               # Valor directo
        except (ValueError, TypeError):
            return None

    @staticmethod
    def human_readable_size(size_bytes: float) -> str:
        """Convierte bytes a formato legible (ej. 2048 -> '2.00 KiB')"""
        for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PiB"

    @staticmethod
    def validate_thresholds(
        warning_pct: int,
        danger_pct: int,
        diff_pct: int,
        underuse_pct: int
    ) -> bool:
        """Valida que los umbrales sean lógicos"""
        return (
            0 <= underuse_pct < warning_pct < danger_pct <= 1000 and
            0 < diff_pct <= 1000
        )

    @staticmethod
    def get_resource_difference(
        request: Optional[float],
        limit: Optional[float]
    ) -> Optional[float]:
        """Calcula diferencia porcentual entre request y limit"""
        if request is None or limit is None or request == 0:
            return None
        return ((limit - request) / request) * 100

    # Helpers para el análisis histórico (Prometheus)
    parse_duration = staticmethod(parse_duration)
    format_duration = staticmethod(format_duration)
    nice_step = staticmethod(nice_step)
    parse_cpu_to_millicores = staticmethod(parse_cpu_to_millicores)
    parse_memory_to_mib = staticmethod(parse_memory_to_mib)

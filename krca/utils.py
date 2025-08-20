#!/usr/bin/env python3
# krca/utils.py - Módulo utilitario completo (Compatible con v4.0)

from typing import Optional, Union

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

#!/usr/bin/env python3
# krca/utils.py - Módulo con funciones utilitarias

from typing import Optional, Union

class KRCAUtils:
    """Clase con funciones utilitarias para KRCA"""

    @staticmethod
    def parse_resource_value(value: str) -> Optional[float]:
        """
        Convierte valores de recursos a milicores/mebibytes numéricos
        
        Args:
            value: Valor a convertir (ej. "100m", "1Gi")
            
        Returns:
            Valor numérico o None si no es válido
        """
        if value in ("<none>", "-", ""):
            return None
            
        try:
            if value.endswith('m'):
                return float(value[:-1])
            elif value.endswith('Ki'):
                return float(value[:-2]) / 1024
            elif value.endswith('Mi'):
                return float(value[:-2])
            elif value.endswith('Gi'):
                return float(value[:-2]) * 1024
            elif value.endswith('Ti'):
                return float(value[:-2]) * 1024 * 1024
            elif value.endswith('K'):
                return float(value[:-1]) / 1000
            elif value.endswith('M'):
                return float(value[:-1])
            elif value.endswith('G'):
                return float(value[:-1]) * 1000
            else:
                return float(value) * 1000 if '.' in value else float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def calculate_percentage_diff(current: Union[float, int], reference: Union[float, int]) -> float:
        """
        Calcula la diferencia porcentual entre dos valores
        
        Args:
            current: Valor actual
            reference: Valor de referencia
            
        Returns:
            Diferencia porcentual (100 = 100%)
        """
        if reference == 0:
            return 0.0
        return ((current - reference) / reference) * 100

    @staticmethod
    def human_readable_size(size_bytes: float) -> str:
        """
        Convierte bytes a un formato legible (KB, MB, GB, etc.)
        
        Args:
            size_bytes: Tamaño en bytes
            
        Returns:
            String formateado (ej. "1.5 MB")
        """
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
        """
        Valida que los umbrales sean lógicos
        
        Args:
            warning_pct: Porcentaje de warning
            danger_pct: Porcentaje de danger
            diff_pct: Porcentaje de diferencia
            underuse_pct: Porcentaje de infrautilización
            
        Returns:
            True si los umbrales son válidos
        """
        return (
            0 <= underuse_pct < warning_pct < danger_pct <= 1000 and
            0 < diff_pct <= 1000
        )

    @staticmethod
    def get_resource_difference(
        request: Optional[float],
        limit: Optional[float]
    ) -> Optional[float]:
        """
        Calcula la diferencia entre request y limit
        
        Args:
            request: Valor de request
            limit: Valor de limit
            
        Returns:
            Diferencia porcentual o None si no se puede calcular
        """
        if request is None or limit is None or request == 0:
            return None
        return ((limit - request) / request) * 100

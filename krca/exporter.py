#!/usr/bin/env python3
# krca/exporter.py - Módulo para exportación de resultados

import os
import tempfile
import subprocess
from tabulate import tabulate
from typing import List, Optional
from .colorizer import ResourceColorizer

class Exporter:
    """Clase para manejar la exportación de resultados a diferentes formatos"""

    @staticmethod
    def export(
        data: str,
        output_file: str,
        use_color: bool = True,
        force: bool = False,
        landscape: bool = False
    ) -> None:
        """
        Exporta los datos al formato especificado
        
        Args:
            data: Datos a exportar (en formato de tabla)
            output_file: Ruta del archivo de salida
            use_color: Si se deben mantener los colores
            force: Sobrescribir archivo existente
            landscape: Orientación horizontal para PDF
            
        Raises:
            ValueError: Si el formato no es soportado
            IOError: Si el archivo existe y force es False
        """
        if not force and os.path.exists(output_file):
            raise IOError(f"El archivo {output_file} ya existe. Use --force para sobrescribir.")

        if output_file.endswith('.txt'):
            Exporter._export_text(data, output_file, use_color)
        elif output_file.endswith('.html'):
            Exporter._export_html(data, output_file)
        elif output_file.endswith('.pdf'):
            Exporter._export_pdf(data, output_file, landscape)
        else:
            raise ValueError(f"Formato no soportado: {output_file}")

    @staticmethod
    def _export_text(data: str, output_file: str, use_color: bool) -> None:
        """Exporta a archivo de texto plano"""
        content = data
        if not use_color:
            content = ResourceColorizer.strip_colors(data)
        
        with open(output_file, 'w') as f:
            f.write(content)

    @staticmethod
    def _export_html(data: str, output_file: str) -> None:
        """Exporta a archivo HTML"""
        # Extraer datos y cabeceras
        lines = data.split('\n')
        headers = []
        table_data = []
        
        if lines:
            # Eliminar códigos ANSI de los headers
            clean_header = ResourceColorizer.strip_colors(lines[0])
            headers = [h.strip() for h in clean_header.split('\t') if h.strip()]
        
        for line in lines[1:]:
            if line.strip():
                # Eliminar códigos ANSI de cada línea
                clean_line = ResourceColorizer.strip_colors(line)
                row = [cell.strip() for cell in clean_line.split('\t') if cell.strip()]
                if row:
                    table_data.append(row)

        # Generar HTML
        html_content = Exporter._generate_html(table_data, headers)
        
        with open(output_file, 'w') as f:
            f.write(html_content)


@staticmethod
def _generate_html(table_data: List[List[str]], headers: List[str]]) -> str:
    """Genera el contenido HTML completo con estilo minimalista"""
    html_table = tabulate(table_data, headers=headers, tablefmt="html")
    
    # Estilo minimalista
    table_style = """
    <style>
        table {
            border-collapse: collapse;
            width: 100%;
            font-family: Arial, sans-serif;
            font-size: 12px;
            border: none;
        }
        th {
            padding: 6px;
            text-align: left;
            font-weight: bold;
            border-bottom: 1px solid #ddd;
        }
        td {
            padding: 6px;
            text-align: left;
            border: none;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
    </style>
    """
    
    return f"""
    <html>
        <head>
            <meta charset="UTF-8">
            <title>Kubernetes Resource Audit</title>
            {table_style}
        </head>
        <body>
            {html_table}
        </body>
    </html>
    """

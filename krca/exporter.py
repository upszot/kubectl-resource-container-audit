#!/usr/bin/env python3
# krca/exporter.py - Módulo para exportación de resultados

import os
import tempfile
import subprocess
from tabulate import tabulate
from .colorizer import ResourceColorizer

class Exporter:
    """Clase para manejar la exportación de resultados"""

    @staticmethod
    def export(
        data: str,
        output_file: str = None,
        use_color: bool = True,
        force: bool = False,
        landscape: bool = False
    ) -> None:
        """
        Exporta los datos al formato especificado o imprime en pantalla
        
        Args:
            data: Texto a exportar
            output_file: Ruta del archivo de salida (None para imprimir)
            use_color: Mantener códigos de color ANSI
            force: Sobrescribir archivo existente
            landscape: Orientación horizontal para PDF
        """
        if not output_file:
            print(data)
            return
        
        # Verificar si el archivo existe
        if os.path.exists(output_file) and not force:
            error_msg = f"Error: El archivo {output_file} ya existe. Use --force para sobrescribir."
            print(ResourceColorizer.red(error_msg) if use_color else error_msg)
            return
        
        try:
            if output_file.endswith('.txt'):
                Exporter._export_text(data, output_file, use_color)
            elif output_file.endswith('.html'):
                Exporter._export_html(data, output_file, landscape)
            elif output_file.endswith('.pdf'):
                Exporter._export_pdf(data, output_file, landscape)
            else:
                raise ValueError(f"Formato no soportado: {output_file}")
            
            # Mensaje de confirmación
            if output_file.endswith('.pdf'):
                success_msg = f"PDF generado: {output_file}"
                print(ResourceColorizer.green(success_msg) if use_color else success_msg)
                
        except Exception as e:
            error_msg = f"Error al guardar archivo: {e}"
            print(ResourceColorizer.red(error_msg) if use_color else error_msg)
            raise

    @staticmethod
    def _export_text(data: str, output_file: str, use_color: bool) -> None:
        """Exporta a archivo de texto plano"""
        content = ResourceColorizer.strip_colors(data) if not use_color else data
        with open(output_file, 'w') as f:
            f.write(content)

    @staticmethod
    def _export_html(data: str, output_file: str, landscape: bool, resizable_columns: bool = True) -> None:
        """Exporta a archivo HTML con estilo mejorado y columnas redimensionables
        Args:
            data: Texto tabular a exportar
            output_file: Ruta del archivo de salida
            landscape: Orientación horizontal
            resizable_columns: Habilita el redimensionamiento de columnas
        """
        # Procesamiento de datos
        lines = [line for line in ResourceColorizer.strip_colors(data).split('\n') if line.strip()]
        
        if not lines:
            raise ValueError("No hay datos para exportar")
        
        # Detectar separador (tabs o múltiples espacios)
        separator = '\t' if '\t' in lines[0] else '  '
        headers = [h.strip() for h in lines[0].split(separator) if h.strip()]
        
        # Procesar filas de datos
        table_data = []
        for line in lines[1:]:
            if line.strip():
                row = [cell.strip() for cell in line.split(separator) if cell.strip()]
                if len(row) < len(headers):
                    row.extend([''] * (len(headers) - len(row)))
                table_data.append(row)

        # Generar estructura de la tabla
        thead = "<thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead>"
        tbody = "<tbody>" + "".join(
            "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
            for row in table_data
        ) + "</tbody>"

        # Cargar estilos base
        css_path = os.path.join(os.path.dirname(__file__), 'styles.css')
        with open(css_path, 'r') as f:
            table_style = f.read()

        # Cargar estilos y JS para redimensionamiento si está habilitado
        resize_script = ""
        if resizable_columns:
            # CSS para redimensionamiento
            resize_css_path = os.path.join(os.path.dirname(__file__), 'resize.css')
            with open(resize_css_path, 'r') as f:
                table_style += f.read()
            
            # JavaScript para redimensionamiento
            js_path = os.path.join(os.path.dirname(__file__), 'resize.js')
            with open(js_path, 'r') as f:
                resize_script = f"<script>{f.read()}</script>"

        # HTML final
        full_html = f"""<!DOCTYPE html>
        <html>
            <head>
                <meta charset="UTF-8">
                <title>Kubernetes Resource Audit</title>
                <style>{table_style}</style>
            </head>
            <body>
                <div class="container">
                    <table class="{'resizable' if resizable_columns else ''}">
                        {thead}
                        {tbody}
                    </table>
                </div>
                {resize_script}
            </body>
        </html>"""
        
        # Escribir archivo de salida
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_html)


    @staticmethod
    def _export_pdf(data: str, output_file: str, landscape: bool) -> None:
        """Exporta a archivo PDF usando wkhtmltopdf"""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp_html:
            try:
                # Primero generamos el HTML temporal usando nuestro método mejorado
                Exporter._export_html(data, tmp_html.name, landscape)
                
                # Opciones para wkhtmltopdf
                options = [
                    "--quiet",
                    "--enable-local-file-access",
                    "--print-media-type",
                    "--margin-top", "10mm",
                    "--margin-right", "10mm",
                    "--margin-bottom", "10mm",
                    "--margin-left", "10mm",
                    "--encoding", "UTF-8",
                    "--disable-smart-shrinking"
                ]
                
                if landscape:
                    options.extend(["--orientation", "Landscape"])
                
                # Ejecutar wkhtmltopdf
                subprocess.run(
                    ["wkhtmltopdf"] + options + [tmp_html.name, output_file],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = (
                    "Error al generar PDF. Verifique que:\n"
                    "1. wkhtmltopdf esté instalado (sudo apt install wkhtmltopdf)\n"
                    "2. La versión sea compatible (pruebe con wkhtmltopdf 0.12.6)\n"
                    f"Error detallado: {e.stderr.decode('utf-8') if e.stderr else str(e)}"
                )
                raise RuntimeError(error_msg)
            except FileNotFoundError:
                raise RuntimeError(
                    "wkhtmltopdf no encontrado. Por favor instálelo:\n"
                    "Ubuntu/Debian: sudo apt install wkhtmltopdf\n"
                    "CentOS/RHEL: sudo yum install wkhtmltopdf"
                )
            finally:
                try:
                    os.unlink(tmp_html.name)
                except:
                    pass

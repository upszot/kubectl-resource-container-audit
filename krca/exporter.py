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
        """Exporta a archivo HTML conservando los colores ANSI"""
        # Procesar datos manteniendo códigos ANSI
        lines = data.split('\n')
        
        if not lines:
            raise ValueError("No hay datos para exportar")
        
        # Detectar separador y headers
        separator = '\t' if '\t' in lines[0] else '  '
        headers = [h.strip() for h in ResourceColorizer.strip_colors(lines[0]).split(separator) if h.strip()]
        
        # Mapeo completo de colores ANSI a CSS (incluyendo \033[37m)
        ansi_to_css = {
            '\033[30m': 'color: #000000;',  # Negro
            '\033[31m': 'color: #cc0000;',  # Rojo
            '\033[32m': 'color: #00cc00;',  # Verde
            '\033[33m': 'color: #cccc00;',  # Amarillo
            '\033[34m': 'color: #0000cc;',  # Azul
            '\033[35m': 'color: #cc00cc;',  # Magenta
            '\033[36m': 'color: #00cccc;',  # Cian
            '\033[37m': 'color: #000000;',  # Originalmente blanco, ahora negro para mejor contraste
            '\033[90m': 'color: #555555;',  # Gris oscuro
            '\033[0m': 'color: inherit;',   # Reset
        }

        # Procesar filas conservando colores
        def process_cell(cell, is_header=False):
            processed = cell
            # Primero manejar los códigos ANSI
            for code, style in ansi_to_css.items():
                processed = processed.replace(code, f'<span style="{style}">')
            
            # Manejar texto sin formato (negro por defecto)
            if '\033[' not in cell and '<span' not in processed:
                processed = f'<span style="color: black;">{processed}</span>'
            
            # Cerrar todos los spans abiertos
            processed = processed.replace('\033[0m', '</span>')
            
            return processed

        table_data = []
        for line in lines[1:]:
            if line.strip():
                raw_row = line.split(separator)
                row = [process_cell(cell.strip()) for cell in raw_row if cell.strip()]
                if len(row) < len(headers):
                    row.extend([''] * (len(headers) - len(row)))
                table_data.append(row)

        # Generar tabla
        thead = "<thead><tr>" + "".join(f"<th>{process_cell(h, True)}</th>" for h in headers) + "</tr></thead>"
        tbody = "<tbody>" + "".join(
            "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
            for row in table_data
        ) + "</tbody>"

        # Rest of the method remains the same...
        # Cargar estilos
        css_path = os.path.join(os.path.dirname(__file__), 'styles.css')
        with open(css_path, 'r') as f:
            table_style = f.read()

        # Añadir estilos para colores ANSI
        table_style += """
        .ansi-red { color: #cc0000; }
        .ansi-green { color: #00cc00; }
        .ansi-yellow { color: #cccc00; }
        .ansi-blue { color: #0000cc; }
        .ansi-magenta { color: #cc00cc; }
        .ansi-cyan { color: #00cccc; }
        """

        # Cargar estilos de redimensionamiento si está habilitado
        if resizable_columns:
            resize_css_path = os.path.join(os.path.dirname(__file__), 'resize.css')
            with open(resize_css_path, 'r') as f:
                table_style += f.read()

        # Cargar JavaScript si está habilitado
        resize_script = ""
        if resizable_columns:
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
        </html>
        """
        
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

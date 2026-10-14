"""
exportador_pdf.py
Módulo encargado de generar planillas en PDF a partir de los datos que se
están visualizando en la interfaz (catálogo de libros, listado de préstamos
o resultados de una búsqueda avanzada).

Utiliza la librería reportlab. Se mantiene separado de la lógica de negocio
y de persistencia: sólo recibe encabezados y filas de datos ya procesados
por la GUI.

Opcionalmente puede anteponer a cada fila la imagen pequeña de la tapa del
libro, cuando la GUI así lo solicita.
"""

import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
)
from reportlab.lib.styles import getSampleStyleSheet

# Alto máximo, en centímetros, de la miniatura de portada dentro de la tabla.
ALTO_MAXIMO_MINIATURA = 2.0 * cm
ANCHO_MAXIMO_MINIATURA = 1.5 * cm


class ExportadorPDF:
    """Genera reportes en PDF a partir de encabezados y filas de una tabla."""

    NOMBRE_INSTITUCION = "Biblioteca Escolar"

    @staticmethod
    def exportar(ruta_archivo, titulo_reporte, encabezados, filas,
                 imagenes=None, encabezado_imagen="Portada"):
        """
        Genera un PDF con una tabla.

        - ruta_archivo: ruta completa donde se guardará el PDF.
        - titulo_reporte: título que aparece en el encabezado del documento.
        - encabezados: lista de strings con los nombres de columna.
        - filas: lista de tuplas/listas con los datos de cada fila.
        - imagenes: lista opcional (del mismo largo que 'filas') con los bytes
          de la portada de cada registro, o None donde no haya imagen. Si se
          indica, se agrega una primera columna con las miniaturas.
        - encabezado_imagen: título de esa primera columna.
        """
        documento = SimpleDocTemplate(
            ruta_archivo, pagesize=landscape(A4),
            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
            leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        )
        estilos = getSampleStyleSheet()
        elementos = []

        elementos.append(Paragraph(ExportadorPDF.NOMBRE_INSTITUCION, estilos["Title"]))
        elementos.append(Paragraph(titulo_reporte, estilos["Heading2"]))
        fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M")
        elementos.append(Paragraph(f"Generado el: {fecha_generacion}", estilos["Normal"]))
        elementos.append(Spacer(1, 0.5 * cm))

        con_imagenes = imagenes is not None

        if con_imagenes:
            datos_tabla = [[encabezado_imagen] + list(encabezados)]
            for indice, fila in enumerate(filas):
                datos_imagen = imagenes[indice] if indice < len(imagenes) else None
                celda = ExportadorPDF._celda_imagen(datos_imagen)
                datos_tabla.append([celda] + list(fila))
        else:
            datos_tabla = [list(encabezados)] + [list(fila) for fila in filas]

        tabla = Table(datos_tabla, repeatRows=1)
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ]
        if con_imagenes:
            # La columna de portadas se centra y se le da algo de aire.
            estilo.append(("ALIGN", (0, 1), (0, -1), "CENTER"))
            estilo.append(("TOPPADDING", (0, 1), (0, -1), 3))
            estilo.append(("BOTTOMPADDING", (0, 1), (0, -1), 3))
        tabla.setStyle(TableStyle(estilo))
        elementos.append(tabla)

        elementos.append(Spacer(1, 0.5 * cm))
        elementos.append(Paragraph(f"Total de registros: {len(filas)}", estilos["Normal"]))

        documento.build(elementos)

    @staticmethod
    def _celda_imagen(datos_imagen):
        """
        Construye el contenido de la celda de portada: una imagen escalada
        dentro del recuadro máximo, o un guion si el libro no tiene tapa
        cargada (o si la imagen no se puede interpretar).
        """
        if not datos_imagen:
            return "-"
        try:
            buffer = io.BytesIO(bytes(datos_imagen))
            imagen = Image(buffer)
            ancho_original = float(imagen.imageWidth)
            alto_original = float(imagen.imageHeight)
            if ancho_original <= 0 or alto_original <= 0:
                return "-"
            escala = min(ANCHO_MAXIMO_MINIATURA / ancho_original,
                          ALTO_MAXIMO_MINIATURA / alto_original)
            imagen.drawWidth = ancho_original * escala
            imagen.drawHeight = alto_original * escala
            return imagen
        except Exception:
            # Una portada dañada nunca debe impedir que se genere el reporte.
            return "-"

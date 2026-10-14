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
from xml.sax.saxutils import escape
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

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
        if not encabezados:
            raise ValueError("Debe haber al menos una columna para exportar.")
        if any(len(fila) != len(encabezados) for fila in filas):
            raise ValueError("Las filas deben coincidir con las columnas del reporte.")
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

        # Anchos proporcionales: textos largos se envuelven en lugar de
        # empujar la tabla fuera de la página al añadir CDD y clasificación.
        pesos = {"ID": 0.45, "Título": 2.6, "Autor": 1.8, "Editorial": 1.5,
                 "ISBN": 1.4, "Género": 1.2, "Edad": 0.9, "Ciclo": 1.2,
                 "Stock": 0.55, "Disp.": 0.55, "Tapa": 0.55, "CDD": 1.15,
                 "Clasificación": 2.6, "Portada": 0.85}
        titulos = datos_tabla[0]
        factores = [pesos.get(str(titulo), 1.6) for titulo in titulos]
        preferidos = [documento.width * factor / sum(factores) for factor in factores]
        minimos = [max(22, stringWidth(str(t), "Helvetica-Bold", 7.5) + 12) for t in titulos]
        if sum(minimos) < documento.width:
            flexibles = [max(0, ancho - minimo) for ancho, minimo in zip(preferidos, minimos)]
            sobrante = documento.width - sum(minimos)
            total_flexible = sum(flexibles) or len(flexibles)
            anchos = [minimo + sobrante * (flex if sum(flexibles) else 1) / total_flexible
                      for minimo, flex in zip(minimos, flexibles)]
        else:
            anchos = preferidos
        celda_estilo = ParagraphStyle("Celda", fontName="Helvetica", fontSize=7.5,
                                      leading=10, splitLongWords=True)
        cabecera_estilo = ParagraphStyle("Cabecera", parent=celda_estilo,
                                         fontName="Helvetica-Bold", textColor=colors.white)
        def texto_seguro(valor, estilo):
            texto = "" if valor is None else str(valor)
            return Paragraph(escape(texto).replace("\n", "<br/>"), estilo)
        datos_tabla[0] = [texto_seguro(titulo, cabecera_estilo) for titulo in titulos]
        for indice in range(1, len(datos_tabla)):
            for col, celda in enumerate(datos_tabla[indice]):
                if isinstance(celda, Image) and celda.drawWidth > anchos[col] - 12:
                    escala = max(1, anchos[col] - 12) / celda.drawWidth
                    celda.drawWidth *= escala
                    celda.drawHeight *= escala
            datos_tabla[indice] = [
                celda if isinstance(celda, Image) else texto_seguro(celda, celda_estilo)
                for celda in datos_tabla[indice]
            ]
        tabla = Table(datos_tabla, colWidths=anchos, repeatRows=1, hAlign="LEFT")
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

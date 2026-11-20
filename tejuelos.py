"""Generación de tejuelos para la biblioteca escolar, sin modificar la base de datos.

Formato: 7 x 2 cm, varias etiquetas por hoja A4.
Signatura: notación CDD, tres letras del apellido del autor y, opcionalmente,
el ID de registro del catálogo (que NO equivale a un inventario por ejemplar).
"""

import re
import unicodedata

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def sigla_autor(autor):
    """Extrae tres letras del apellido de forma orientativa.

    Admite tanto 'Borges, Jorge Luis' como 'Jorge Luis Borges'. Para apellidos
    compuestos se recomienda el formato 'García Márquez, Gabriel', que evita
    ambigüedades y produce GAR en vez de MAR.
    """
    texto = " ".join(str(autor or "").split())
    if not texto:
        raise ValueError("El nombre del autor está vacío.")

    if "," in texto:
        palabras = texto.split(",", 1)[0].split()
        # En apellidos con partículas iniciales (de la Cruz), usar la primera
        # palabra significativa en vez de la partícula.
        palabras = [p for p in palabras if p.lower() not in {"de", "del", "la", "las", "los"}]
        apellido = palabras[0] if palabras else texto.split(",", 1)[0]
    else:
        apellido = texto.split()[-1]

    normalizado = unicodedata.normalize("NFD", apellido)
    letras = "".join(c for c in normalizado if unicodedata.category(c) != "Mn")
    letras = re.sub(r"[^a-zA-Z]", "", letras).upper()
    if not letras:
        raise ValueError(f"No se puede extraer el apellido de: {autor!r}")
    return letras[:3]


def generar_tejuelos_pdf(ruta_archivo, registros, incluir_registro=False,
                         repetir_por_stock=False):
    """Crea un PDF A4 con etiquetas horizontales de 7 x 2 cm.

    registros: iterable de dicts con cdd, autor, id_libro y stock.
    Omite los registros sin CDD; la interfaz debe avisar antes al usuario.
    Devuelve la cantidad de etiquetas impresas.
    """
    etiquetas = []
    for registro in registros:
        cdd = str(registro.get("cdd") or "").strip()
        if not cdd:
            continue
        sigla = sigla_autor(registro.get("autor"))
        cantidad = max(0, int(registro.get("stock", 0))) if repetir_por_stock else 1
        for _ in range(cantidad):
            etiquetas.append((cdd, sigla, registro.get("id_libro")))

    if not etiquetas:
        raise ValueError("No hay ejemplares con CDD para generar etiquetas.")

    ancho, alto = 7 * cm, 2 * cm
    espacio_x, espacio_y = 0.45 * cm, 0.25 * cm
    margen_y = 1.0 * cm
    columnas = 2
    filas = int((A4[1] - 2 * margen_y + espacio_y) // (alto + espacio_y))
    por_pagina = columnas * filas
    margen_x = (A4[0] - columnas * ancho - (columnas - 1) * espacio_x) / 2

    pdf = canvas.Canvas(ruta_archivo, pagesize=A4)
    pdf.setTitle("Tejuelos bibliotecarios")
    pdf.setAuthor("Biblioteca Escolar")

    for indice, (cdd, sigla, id_libro) in enumerate(etiquetas):
        if indice and indice % por_pagina == 0:
            pdf.showPage()

        pos = indice % por_pagina
        columna, fila = pos % columnas, pos // columnas
        x = margen_x + columna * (ancho + espacio_x)
        y = A4[1] - margen_y - alto - fila * (alto + espacio_y)
        cx = x + ancho / 2

        # Trazo fino para recortar; conserva el diseño apto para impresora B/N.
        pdf.setStrokeColor(colors.HexColor("#A9A9A9"))
        pdf.setLineWidth(0.35)
        pdf.rect(x, y, ancho, alto, fill=0, stroke=1)
        pdf.setFillColor(colors.black)
        tamano_cdd = 13 if len(cdd) <= 10 else 10 if len(cdd) <= 16 else 8
        pdf.setFont("Helvetica-Bold", tamano_cdd)
        pdf.drawCentredString(cx, y + alto * (0.64 if incluir_registro else 0.56), cdd)
        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawCentredString(cx, y + alto * (0.33 if incluir_registro else 0.22), sigla)
        if incluir_registro and id_libro is not None:
            pdf.setFont("Helvetica", 8)
            pdf.drawCentredString(cx, y + alto * 0.12, f"Reg. {id_libro}")

    pdf.save()
    return len(etiquetas)

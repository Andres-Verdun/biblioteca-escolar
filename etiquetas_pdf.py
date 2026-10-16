"""Etiquetas de 70 × 20 mm, con clasificación cromática y ubicación manual."""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
import organizacion as org

ANCHO = 70 * mm
ALTO = 20 * mm
COLUMNAS = 2
FILAS = 11
POR_PAGINA = COLUMNAS * FILAS
SEPARACION_X = 5 * mm
SEPARACION_Y = 3 * mm
MARGEN_SUPERIOR = 15 * mm


def _texto(c, texto, x, y, ancho, fuente='Helvetica', tamano=8):
    texto = ' '.join(str(texto or '').split())
    # Los datos completos siguen en la base; en una etiqueta física no debe
    # invadirse el recuadro vecino aunque un título o ubicación sea muy largo.
    if stringWidth(texto, fuente, tamano) > ancho:
        while texto and stringWidth(texto + '...', fuente, tamano) > ancho:
            texto = texto[:-1]
        texto = texto.rstrip() + '...'
    c.setFont(fuente, tamano)
    c.drawString(x,y,texto)


def generar(ruta, etiquetas):
    """Cada elemento es un dict con titulo, codigo, ubicacion, etiqueta y franjas."""
    if not etiquetas:
        raise ValueError('Agregue al menos una etiqueta para imprimir.')
    # Validar todo antes de crear el archivo.
    for item in etiquetas:
        org.validar(etiqueta=item.get('etiqueta',''), franjas=item.get('franjas',[]))
    c = canvas.Canvas(ruta, pagesize=A4)
    c.setTitle('Etiquetas de biblioteca - 7 x 2 cm')
    c.setAuthor('Biblioteca Escolar')
    margen_x = (A4[0] - COLUMNAS*ANCHO - SEPARACION_X) / 2
    for indice,item in enumerate(etiquetas):
        posicion = indice % POR_PAGINA
        if posicion == 0:
            if indice:
                c.showPage()
            c.setFillColor(HexColor('#444444'))
            c.setFont('Helvetica',7)
            c.drawCentredString(A4[0]/2, 7*mm, 'Etiquetas 7 x 2 cm | Imprimir al 100 % / Tamaño real, sin ajustar')
        fila,columna = divmod(posicion,COLUMNAS)
        x = margen_x + columna*(ANCHO+SEPARACION_X)
        y = A4[1] - MARGEN_SUPERIOR - ALTO - fila*(ALTO+SEPARACION_Y)
        c.setFillColor(HexColor('#FFFFFF'))
        c.rect(x,y,ANCHO,ALTO,fill=1,stroke=0)
        banda = 8*mm
        clave = item.get('etiqueta','')
        colores = org.paleta(clave,item.get('franjas',[])) or ['#FFFFFF']
        for n,color in enumerate(colores):
            c.setFillColor(HexColor(color))
            c.rect(x,y+n*ALTO/len(colores),banda,ALTO/len(colores),fill=1,stroke=0)
        letra = org.ETIQUETAS[clave][2] if clave else ''
        if letra:
            c.setFillColor(HexColor('#000000'))
            c.setFont('Helvetica-Bold',16)
            c.drawCentredString(x+banda/2,y+ALTO/2-5,letra)
        ubicacion = ' '.join(str(item.get('ubicacion') or '').split())
        if ubicacion:
            c.setFillColor(HexColor('#000000'))
            # El rótulo corto de ubicación queda al pie de la banda, como B1-E1.
            ancho_ubicacion = banda-1*mm
            tamano = 6
            while tamano > 5 and stringWidth(ubicacion,'Helvetica-Bold',tamano) > ancho_ubicacion:
                tamano -= .25
            _texto(c,ubicacion,x+.5*mm,y+2*mm,ancho_ubicacion,'Helvetica-Bold',tamano)
        c.setStrokeColor(HexColor('#888888'))
        c.setLineWidth(.3)
        c.rect(x,y,ANCHO,ALTO,fill=0,stroke=1)
        c.setFillColor(HexColor('#000000'))
        tx=x+banda+2*mm
        ancho=ANCHO-banda-4*mm
        categoria=org.ETIQUETAS[clave][0] if clave else 'Sin etiqueta de color'
        if item.get('libre'):
            _texto(c,categoria,tx,y+ALTO/2-3,ancho,'Helvetica-Bold',9)
            continue
        _texto(c,categoria,tx,y+ALTO-10,ancho,'Helvetica-Bold',7)
        _texto(c,item.get('titulo',''),tx,y+ALTO-22,ancho,'Helvetica',7.5)
        _texto(c,'CDD: '+(item.get('codigo') or '-'),tx,y+ALTO-34,ancho,'Helvetica-Bold',8)
        if not ubicacion:
            _texto(c,'Sin ubicación',tx,y+7,ancho,'Helvetica',7.5)
    c.save()

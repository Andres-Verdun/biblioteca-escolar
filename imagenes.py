"""
imagenes.py
Módulo encargado del tratamiento de las imágenes de tapa (portadas) de los libros.

Responsabilidad única: convertir un archivo de imagen elegido por el usuario
en un dato apto para guardar en la base (PNG redimensionado), generar
miniaturas y preparar la imagen para mostrarla en la interfaz Tkinter.

Ni la GUI ni el DAO manipulan imágenes por su cuenta: siempre lo hacen a
través de las funciones públicas de este módulo.

Utiliza Pillow (PIL). Si la librería no estuviera instalada, el sistema sigue
funcionando: se admiten únicamente portadas en formato PNG o GIF y se guardan
tal cual, sin redimensionar.
"""

import io
import os

try:
    from PIL import Image
    PILLOW_DISPONIBLE = True
except ImportError:          # pragma: no cover - depende del entorno
    Image = None
    PILLOW_DISPONIBLE = False

# ImageTk se importa por separado porque depende de Tkinter: si faltara, el
# tratamiento de imágenes (redimensionar, guardar, exportar al PDF) igual debe
# seguir funcionando.
try:
    from PIL import ImageTk
    IMAGETK_DISPONIBLE = PILLOW_DISPONIBLE
except ImportError:          # pragma: no cover - depende del entorno
    ImageTk = None
    IMAGETK_DISPONIBLE = False

# Lado máximo (en píxeles) con el que se guarda la portada dentro de la base
# de datos. Suficiente para verse nítida en pantalla y en el PDF, sin inflar
# el tamaño del archivo biblioteca.db.
LADO_MAXIMO_GUARDADO = 500

# Tamaño del recuadro de vista previa en la ventana principal.
ANCHO_VISTA_PREVIA = 130
ALTO_VISTA_PREVIA = 175

# Lado máximo de la miniatura que se inserta en el PDF.
LADO_MAXIMO_PDF = 90

# Calidad de compresión JPEG con la que se guardan las tapas (0-95).
CALIDAD_JPEG = 85

# Peso máximo admitido para el archivo de imagen original (5 MB).
TAMANIO_MAXIMO_ARCHIVO = 5 * 1024 * 1024


def formatos_admitidos():
    """
    Devuelve la lista de tipos de archivo para el cuadro de diálogo
    "Abrir archivo" de Tkinter, según haya o no Pillow instalado.
    """
    if PILLOW_DISPONIBLE:
        return [
            ("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
            ("Todos los archivos", "*.*"),
        ]
    return [("Imágenes PNG o GIF", "*.png *.gif")]


def preparar_portada(ruta_archivo, lado_maximo=LADO_MAXIMO_GUARDADO):
    """
    Lee un archivo de imagen del disco y lo devuelve en bytes, listo para
    guardarse en la base de datos.

    Con Pillow: la imagen se convierte a JPEG y se reduce de modo que su lado
    mayor no supere 'lado_maximo', conservando la proporción original.

    Lanza ValueError si el archivo no existe, pesa demasiado o no es una
    imagen válida.
    """
    if not ruta_archivo or not os.path.isfile(ruta_archivo):
        raise ValueError("No se encontró el archivo de imagen seleccionado.")

    if os.path.getsize(ruta_archivo) > TAMANIO_MAXIMO_ARCHIVO:
        raise ValueError(
            "La imagen es demasiado pesada (máximo 5 MB). "
            "Elija una foto de menor tamaño."
        )

    with open(ruta_archivo, "rb") as archivo:
        datos_originales = archivo.read()

    if not PILLOW_DISPONIBLE:
        extension = os.path.splitext(ruta_archivo)[1].lower()
        if extension not in (".png", ".gif"):
            raise ValueError(
                "Sin la librería Pillow instalada sólo se admiten portadas "
                "en formato PNG o GIF."
            )
        return datos_originales

    return redimensionar(datos_originales, lado_maximo)


def redimensionar(datos_imagen, lado_maximo, calidad=CALIDAD_JPEG):
    """
    Devuelve la imagen (en bytes) reducida a un cuadro de 'lado_maximo' x
    'lado_maximo' píxeles, conservando la proporción original.

    El resultado se guarda en JPEG: al tratarse de fotos de tapas, ocupa unas
    cinco veces menos que un PNG, lo que mantiene liviano el archivo
    biblioteca.db. Si no hay Pillow disponible, devuelve los datos sin modificar.
    """
    if not datos_imagen:
        return None
    if not PILLOW_DISPONIBLE:
        return bytes(datos_imagen)

    try:
        imagen = Image.open(io.BytesIO(bytes(datos_imagen)))
        imagen.load()
    except Exception:
        raise ValueError("El archivo seleccionado no es una imagen válida.")

    # Las imágenes con transparencia se apoyan sobre un fondo blanco, porque
    # el formato JPEG no admite canal alfa.
    if imagen.mode in ("RGBA", "LA", "P"):
        imagen = imagen.convert("RGBA")
        fondo = Image.new("RGB", imagen.size, (255, 255, 255))
        fondo.paste(imagen, mask=imagen.split()[-1])
        imagen = fondo
    elif imagen.mode != "RGB":
        imagen = imagen.convert("RGB")

    imagen.thumbnail((lado_maximo, lado_maximo), Image.LANCZOS)

    salida = io.BytesIO()
    imagen.save(salida, format="JPEG", quality=calidad, optimize=True)
    return salida.getvalue()


def miniatura_para_pdf(datos_imagen, lado_maximo=LADO_MAXIMO_PDF):
    """
    Genera la versión pequeña de la portada que se inserta en el PDF.
    Devuelve None si el libro no tiene portada o si la imagen está dañada.
    """
    if not datos_imagen:
        return None
    try:
        return redimensionar(datos_imagen, lado_maximo)
    except ValueError:
        return None


def dimensiones(datos_imagen):
    """
    Devuelve (ancho, alto) en píxeles de una imagen en bytes, o None si no se
    puede determinar (por ejemplo, sin Pillow instalado).
    """
    if not datos_imagen or not PILLOW_DISPONIBLE:
        return None
    try:
        with Image.open(io.BytesIO(bytes(datos_imagen))) as imagen:
            return imagen.size
    except Exception:
        return None


def a_imagen_tk(datos_imagen, ancho=ANCHO_VISTA_PREVIA, alto=ALTO_VISTA_PREVIA):
    """
    Convierte los bytes de una portada en un objeto de imagen que Tkinter
    puede mostrar en una etiqueta, ajustado al recuadro (ancho x alto).

    IMPORTANTE: quien llame a esta función debe conservar una referencia al
    objeto devuelto (por ejemplo en un atributo de la ventana); si no, el
    recolector de basura de Python la elimina y la imagen se ve en blanco.

    Devuelve None si no hay imagen o si no se pudo interpretar.
    """
    if not datos_imagen:
        return None

    if IMAGETK_DISPONIBLE:
        try:
            imagen = Image.open(io.BytesIO(bytes(datos_imagen)))
            imagen.load()
            imagen.thumbnail((ancho, alto), Image.LANCZOS)
            return ImageTk.PhotoImage(imagen)
        except Exception:
            return None

    # Alternativa sin Pillow: Tkinter sólo admite PNG y GIF, y únicamente
    # permite reducir la imagen en proporciones enteras (1/2, 1/3, ...).
    try:
        import base64
        import tkinter as tk

        imagen = tk.PhotoImage(data=base64.b64encode(bytes(datos_imagen)))
        factor = max(1, imagen.width() // ancho, imagen.height() // alto)
        if factor > 1:
            imagen = imagen.subsample(factor, factor)
        return imagen
    except Exception:
        return None

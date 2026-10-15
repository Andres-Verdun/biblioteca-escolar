"""Notaciones verificadas en BNM, fichas editoriales y catálogos bibliotecarios."""
import csv
import os
import re
import sys
from dataclasses import dataclass
from conexion import ConexionDB

FUENTE = "Manual de notaciones de CDD - BNM, https://bnm.educacion.gob.ar/digital/documentos/EL006553.pdf"
SECTORES = {
    "R": "Referencia", "RE": "Referencia: enciclopedias",
    "L": "Códigos de legislación", "S": "Enseñanza secundaria",
    "E": "EGB, tercer ciclo", "1-E": "EGB, primer ciclo",
    "2-E": "EGB, segundo ciclo", "3-E": "EGB, tercer ciclo",
    "PL": "Polimodal",
}
# Se conservan prefijos locales. Sólo una equivalencia documentada
# permite clasificarlos; A863 tiene su propia fuente complementaria.
PATRON = re.compile(
    r"(?:(?P<prefijo>[123]-E|[A-Z]{1,3})\s*)?"
    r"(?P<numero>\d{1,3}(?:\.\d+)*(?:[/\-]\d+(?:\.\d+)*)*"
    r"(?:\[\d+(?:[./]\d+)*\]|\(\d+(?:[./]\d+)*\))?(?:-\d+)?)"
)


def _ruta_recurso(nombre):
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), nombre)
    return os.path.join(os.path.dirname(__file__), nombre)


def normalizar(codigo):
    """Normaliza mayúsculas/espacios, conservando ceros y signos de la notación."""
    texto = re.sub(r"\s+", "", codigo.strip().upper())
    if not texto:
        return ""
    encontrado = PATRON.fullmatch(texto)
    if not encontrado:
        raise ValueError("Notación inválida. Ejemplos: 370, RE 030, R 806.0-3, 3-E 372.4.")
    prefijo, numero = encontrado.group("prefijo", "numero")
    return f"{prefijo} {numero}" if prefijo else numero


def codigo_valido(codigo):
    try:
        normalizar(codigo)
        return True
    except ValueError:
        return False


def inicializar():
    """Actualiza equivalencias y fuentes sin alterar las notaciones de los libros."""
    # Leer y validar antes de abrir la transacción: un CSV dañado no debe
    # dejar una importación parcial. Las páginas son las del PDF, desde 1.
    with open(_ruta_recurso("cdd_bnm.csv"), encoding="utf-8-sig", newline="") as archivo:
        filas = [(normalizar(f["codigo"]), f["descripcion"].strip(), f.get("pagina", ""), f.get("fuente", "").strip() or FUENTE)
                 for f in csv.DictReader(archivo)]
    if any(not codigo or not descripcion for codigo, descripcion, _, _ in filas):
        raise ValueError("El catálogo CDD contiene una entrada vacía.")
    con = ConexionDB.conectar()
    try:
        with con:
            con.execute("CREATE TABLE IF NOT EXISTS cdd_bnm (codigo TEXT PRIMARY KEY, descripcion TEXT NOT NULL, pagina TEXT, fuente TEXT NOT NULL)")
            con.execute("CREATE TABLE IF NOT EXISTS libro_cdd (id_libro INTEGER PRIMARY KEY REFERENCES libros(id_libro) ON DELETE CASCADE, codigo TEXT NOT NULL)")
            con.executemany("""INSERT INTO cdd_bnm (codigo,descripcion,pagina,fuente)
                VALUES (?,?,?,?) ON CONFLICT(codigo) DO UPDATE SET
                descripcion=excluded.descripcion,pagina=excluded.pagina,fuente=excluded.fuente""",
                filas)
    finally:
        ConexionDB.cerrar(con)


def _consultar_detalle(codigo):
    codigo = normalizar(codigo)
    if not codigo:
        return None
    if codigo.startswith("E "):
        codigo = "3-" + codigo
    con = ConexionDB.conectar()
    try:
        fila = con.execute("SELECT descripcion,pagina,fuente FROM cdd_bnm WHERE codigo=?", (codigo,)).fetchone()
        return tuple(fila) if fila else None
    finally:
        ConexionDB.cerrar(con)


def consultar(codigo):
    """Coincidencia exacta; E se admite como alias del tercer ciclo 3-E."""
    fila = _consultar_detalle(codigo)
    return fila[:2] if fila else None


@dataclass(frozen=True)
class Clasificacion:
    codigo: str
    sector: str
    descripcion: str
    estado: str  # exacta, general, pendiente, vacia
    pagina: str = ""
    codigo_base: str = ""
    fuente: str = ""

    def texto(self):
        if self.estado == "vacia":
            return "Ingrese una notación o elija una del catálogo."
        sector = f"{self.sector}. " if self.sector else ""
        if self.estado == "exacta":
            return f"{sector}{self.descripcion}"
        if self.estado == "general":
            return (f"Categoría general: {self.descripcion} ({self.codigo_base}). "
                    "La subclasificación exacta requiere revisión.")
        return f"{sector}Sin equivalencia exacta verificada; se guardará la notación para revisión."


def clasificar(codigo):
    codigo = normalizar(codigo)
    if not codigo:
        return Clasificacion("", "", "", "vacia")
    encontrado = PATRON.fullmatch(codigo)
    prefijo = encontrado.group("prefijo") or ""
    sector = SECTORES.get(prefijo, "")
    exacta = _consultar_detalle(codigo)
    if exacta:
        return Clasificacion(codigo, sector, exacta[0], "exacta", exacta[1], fuente=exacta[2])
    # Sólo CDD numérica simple admite aproximación jerárquica. Nunca
    # quitar un prefijo ni reutilizar una equivalencia de CDU como CDD.
    numero = encontrado.group("numero")
    if not prefijo and re.fullmatch(r"\d{3}(?:\.\d+)?", numero):
        candidatos = []
        if "." in numero:
            entero, decimales = numero.split(".")
            candidatos.extend(entero + "." + decimales[:n]
                              for n in range(len(decimales) - 1, 0, -1))
            candidatos.append(entero)
        candidatos.extend([numero[:2] + "0", numero[0] + "00"])
        for base in dict.fromkeys(candidatos):
            general = _consultar_detalle(base)
            if general:
                return Clasificacion(codigo, "", general[0], "general", general[1], base, general[2])
    return Clasificacion(codigo, sector, "", "pendiente")


def catalogo(texto=""):
    """Lista de códigos y descripciones para el selector de la bibliotecaria."""
    con = ConexionDB.conectar()
    try:
        filas = con.execute("SELECT codigo,descripcion,pagina FROM cdd_bnm ORDER BY codigo").fetchall()
        texto = texto.casefold().strip()
        return [tuple(f) for f in filas if not texto or texto in f["codigo"].casefold()
                or texto in f["descripcion"].casefold()]
    finally:
        ConexionDB.cerrar(con)


def guardar(id_libro, codigo, conexion=None):
    codigo = normalizar(codigo)
    propia = conexion is None
    con = ConexionDB.conectar() if propia else conexion
    try:
        if codigo:
            con.execute("""INSERT INTO libro_cdd(id_libro,codigo) VALUES (?,?)
                ON CONFLICT(id_libro) DO UPDATE SET codigo=excluded.codigo""", (id_libro, codigo))
        else:
            con.execute("DELETE FROM libro_cdd WHERE id_libro=?", (id_libro,))
        if propia:
            con.commit()
    finally:
        if propia:
            ConexionDB.cerrar(con)


def obtener(id_libro):
    con = ConexionDB.conectar()
    try:
        fila = con.execute("SELECT codigo FROM libro_cdd WHERE id_libro=?", (id_libro,)).fetchone()
        return fila["codigo"] if fila else ""
    finally:
        ConexionDB.cerrar(con)


def obtener_codigos():
    """Carga las notaciones en una consulta para armar listados sin N consultas."""
    con = ConexionDB.conectar()
    try:
        return dict(con.execute("SELECT id_libro,codigo FROM libro_cdd").fetchall())
    finally:
        ConexionDB.cerrar(con)

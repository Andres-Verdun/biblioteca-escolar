"""CDD local. Clasificaciones verificadas en manual BNM; no interpreta códigos desconocidos."""
import csv
import os
import sys
import re
from conexion import ConexionDB

FUENTE = "Manual de notaciones de CDD - BNM, https://bnm.educacion.gob.ar/digital/documentos/EL006553.pdf"

def _ruta_recurso(nombre):
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), nombre)
    return os.path.join(os.path.dirname(__file__), nombre)

def inicializar():
    con = ConexionDB.conectar()
    try:
        con.execute("CREATE TABLE IF NOT EXISTS cdd_bnm (codigo TEXT PRIMARY KEY, descripcion TEXT NOT NULL, pagina TEXT, fuente TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS libro_cdd (id_libro INTEGER PRIMARY KEY REFERENCES libros(id_libro) ON DELETE CASCADE, codigo TEXT NOT NULL)")
        with open(_ruta_recurso('cdd_bnm.csv'), encoding='utf-8-sig',newline='') as f:
            for fila in csv.DictReader(f):
                codigo=fila['codigo'].strip(); desc=fila['descripcion'].strip()
                if codigo and desc:
                    con.execute('INSERT OR IGNORE INTO cdd_bnm (codigo,descripcion,pagina,fuente) VALUES (?,?,?,?)',(codigo,desc,fila.get('pagina',''),FUENTE))
        con.commit()
    finally: ConexionDB.cerrar(con)

def codigo_valido(codigo):
    return not codigo or bool(re.fullmatch(r"(?:[A-Za-z]{1,3}\s*)?\d{1,3}(?:\.\d+)?",codigo.strip()))

def consultar(codigo):
    codigo=codigo.strip()
    if not codigo: return None
    con=ConexionDB.conectar()
    try:
        fila=con.execute('SELECT descripcion,pagina FROM cdd_bnm WHERE codigo=?',(codigo,)).fetchone()
        return (fila['descripcion'],fila['pagina']) if fila else None
    finally: ConexionDB.cerrar(con)

def guardar(id_libro,codigo):
    codigo=codigo.strip()
    if not codigo_valido(codigo): raise ValueError('Formato de código CDD inválido.')
    con=ConexionDB.conectar()
    try:
        if codigo: con.execute('INSERT INTO libro_cdd(id_libro,codigo) VALUES (?,?) ON CONFLICT(id_libro) DO UPDATE SET codigo=excluded.codigo',(id_libro,codigo))
        else: con.execute('DELETE FROM libro_cdd WHERE id_libro=?',(id_libro,))
        con.commit()
    finally: ConexionDB.cerrar(con)

def obtener(id_libro):
    con=ConexionDB.conectar()
    try:
        fila=con.execute('SELECT codigo FROM libro_cdd WHERE id_libro=?',(id_libro,)).fetchone()
        return fila['codigo'] if fila else ''
    finally: ConexionDB.cerrar(con)

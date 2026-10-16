"""Ubicaciones reutilizables y clasificación por colores asignada por la bibliotecaria."""
import json
import unicodedata
from conexion import ConexionDB

# Rótulos según Clasificación por colores, docentes bibliotecarias de Neuquén,
# abril de 2023, cuadro de la página 5. Colores digitales representativos.
COLORES = {
    'amarillo': ('Amarillo', '#FFF000'), 'naranja': ('Naranja', '#FF9F32'),
    'verde': ('Verde claro', '#A5D65C'), 'fucsia': ('Fucsia', '#F72C91'),
    'azul': ('Azul', '#2277BB'), 'rojo': ('Rojo', '#ED4444'),
    'celeste': ('Celeste', '#9BD7F0'), 'violeta': ('Violeta', '#9C70CD'),
    'blanco': ('Blanco', '#FFFFFF'),
}
ETIQUETAS = {
    'cuento': ('Cuento', 'amarillo', ''),
    'cuento_terror': ('Cuento de terror', 'amarillo', 'T'),
    'cuento_policial': ('Cuento policial', 'amarillo', 'P'),
    'novela': ('Novela', 'naranja', ''),
    'novela_terror': ('Novela de terror', 'naranja', 'T'),
    'novela_policial': ('Novela policial', 'naranja', 'P'),
    'poesia': ('Poesía y formas poéticas', 'verde', ''),
    'album': ('Libro álbum', 'fucsia', ''),
    'historieta': ('Historieta, manga y novela gráfica', 'azul', ''),
    'mitos': ('Mitos, leyendas y fábulas', 'rojo', ''),
    'teatro': ('Teatro y títeres', 'celeste', ''),
    'patagonica': ('Literatura patagónica', 'violeta', ''),
    'antologia': ('Antologías', '', ''),
    'produccion': ('Producciones de los usuarios', 'blanco', ''),
}


def nombre_etiqueta(clave):
    if not clave:
        return ''
    nombre, color, letra = ETIQUETAS[clave]
    return nombre + (f" - {COLORES[color][0]}" if color else ' - Franjas de colores') + (f" {letra}" if letra else '')


def paleta(clave, franjas=()):
    if not clave:
        return []
    if clave == 'antologia':
        return [COLORES[c][1] for c in franjas]
    return [COLORES[ETIQUETAS[clave][1]][1]]


def inicializar():
    con = ConexionDB.conectar()
    try:
        with con:
            con.execute('''CREATE TABLE IF NOT EXISTS ubicaciones (
                id_ubicacion INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL, nombre_clave TEXT NOT NULL UNIQUE)''')
            con.execute('''CREATE TABLE IF NOT EXISTS libro_organizacion (
                id_libro INTEGER PRIMARY KEY REFERENCES libros(id_libro) ON DELETE CASCADE,
                id_ubicacion INTEGER REFERENCES ubicaciones(id_ubicacion) ON DELETE RESTRICT,
                etiqueta TEXT NOT NULL DEFAULT '',
                franjas TEXT NOT NULL DEFAULT '[]')''')
            con.execute('CREATE INDEX IF NOT EXISTS idx_libro_ubicacion ON libro_organizacion(id_ubicacion)')
    finally:
        ConexionDB.cerrar(con)


def _nombre(nombre):
    nombre = ' '.join(str(nombre).split())
    if not nombre or len(nombre) > 100:
        raise ValueError('La ubicación debe tener un nombre de entre 1 y 100 caracteres.')
    clave = unicodedata.normalize('NFKC', nombre).casefold()
    if clave in ('todas', 'sin ubicación'):
        raise ValueError('Elija un nombre que identifique un lugar de la biblioteca.')
    return nombre, clave


def listar_ubicaciones():
    con = ConexionDB.conectar()
    try:
        return [dict(f) for f in con.execute('''SELECT u.id_ubicacion,u.nombre,
            COUNT(o.id_libro) AS libros FROM ubicaciones u LEFT JOIN libro_organizacion o
            ON o.id_ubicacion=u.id_ubicacion GROUP BY u.id_ubicacion
            ORDER BY u.nombre COLLATE NOCASE''').fetchall()]
    finally:
        ConexionDB.cerrar(con)


def crear_ubicacion(nombre):
    nombre, clave = _nombre(nombre)
    con = ConexionDB.conectar()
    try:
        with con:
            if con.execute('SELECT 1 FROM ubicaciones WHERE nombre_clave=?', (clave,)).fetchone():
                raise ValueError('Ya existe una ubicación con ese nombre.')
            return con.execute('INSERT INTO ubicaciones(nombre,nombre_clave) VALUES (?,?)', (nombre,clave)).lastrowid
    finally:
        ConexionDB.cerrar(con)


def renombrar_ubicacion(id_ubicacion, nombre):
    nombre, clave = _nombre(nombre)
    con = ConexionDB.conectar()
    try:
        with con:
            if con.execute('SELECT 1 FROM ubicaciones WHERE nombre_clave=? AND id_ubicacion<>?', (clave,id_ubicacion)).fetchone():
                raise ValueError('Ya existe una ubicación con ese nombre.')
            if not con.execute('UPDATE ubicaciones SET nombre=?,nombre_clave=? WHERE id_ubicacion=?', (nombre,clave,id_ubicacion)).rowcount:
                raise ValueError('La ubicación ya no existe.')
    finally:
        ConexionDB.cerrar(con)


def eliminar_ubicacion(id_ubicacion):
    con = ConexionDB.conectar()
    try:
        with con:
            if con.execute('SELECT 1 FROM libro_organizacion WHERE id_ubicacion=?', (id_ubicacion,)).fetchone():
                raise ValueError('Esta ubicación tiene libros asignados. Reubíquelos antes de eliminarla.')
            if not con.execute('DELETE FROM ubicaciones WHERE id_ubicacion=?', (id_ubicacion,)).rowcount:
                raise ValueError('La ubicación ya no existe.')
    finally:
        ConexionDB.cerrar(con)


def validar(id_ubicacion=None, etiqueta='', franjas=()):
    if etiqueta and etiqueta not in ETIQUETAS:
        raise ValueError('Seleccione una clasificación por color de la lista.')
    if not isinstance(franjas, (list, tuple)) or any(c not in COLORES for c in franjas):
        raise ValueError('Seleccione colores válidos para las franjas.')
    if etiqueta == 'antologia':
        if not franjas:
            raise ValueError('Seleccione al menos un color para las franjas de la antología.')
        franjas = list(dict.fromkeys(franjas))
    else:
        franjas = []
    if id_ubicacion is not None and (not isinstance(id_ubicacion,int) or id_ubicacion <= 0):
        raise ValueError('Seleccione una ubicación válida.')
    return dict(id_ubicacion=id_ubicacion, etiqueta=etiqueta, franjas=franjas)


def guardar(id_libro, id_ubicacion=None, etiqueta='', franjas=(), conexion=None):
    datos = validar(id_ubicacion, etiqueta, franjas)
    propia = conexion is None
    con = ConexionDB.conectar() if propia else conexion
    try:
        if id_ubicacion is not None and not con.execute('SELECT 1 FROM ubicaciones WHERE id_ubicacion=?', (id_ubicacion,)).fetchone():
            raise ValueError('La ubicación seleccionada ya no existe.')
        if id_ubicacion is None and not etiqueta:
            con.execute('DELETE FROM libro_organizacion WHERE id_libro=?', (id_libro,))
        else:
            con.execute('''INSERT INTO libro_organizacion(id_libro,id_ubicacion,etiqueta,franjas)
                VALUES (?,?,?,?) ON CONFLICT(id_libro) DO UPDATE SET
                id_ubicacion=excluded.id_ubicacion,etiqueta=excluded.etiqueta,franjas=excluded.franjas''',
                (id_libro,id_ubicacion,etiqueta,json.dumps(datos['franjas'])))
        if propia:
            con.commit()
    finally:
        if propia:
            ConexionDB.cerrar(con)


def obtener_todos():
    con = ConexionDB.conectar()
    try:
        filas = con.execute('''SELECT o.*, COALESCE(u.nombre,'') AS ubicacion
            FROM libro_organizacion o LEFT JOIN ubicaciones u ON u.id_ubicacion=o.id_ubicacion''').fetchall()
        return {f['id_libro']: dict(id_ubicacion=f['id_ubicacion'], ubicacion=f['ubicacion'],
                etiqueta=f['etiqueta'], franjas=json.loads(f['franjas'])) for f in filas}
    finally:
        ConexionDB.cerrar(con)


def obtener(id_libro):
    return obtener_todos().get(id_libro, dict(id_ubicacion=None,ubicacion='',etiqueta='',franjas=[]))

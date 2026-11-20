"""
dao.py
Capa de acceso a datos (DAO - Data Access Object).

Cada clase DAO es responsable EXCLUSIVAMENTE de la persistencia de una
entidad: aquí, y sólo aquí, se escribe SQL. La lógica de negocio y la
interfaz gráfica nunca acceden directamente a la base de datos: siempre
lo hacen a través de los métodos públicos que exponen estas clases,
protegiendo así el encapsulamiento del sistema.
"""

from conexion import ConexionDB
import cdd
import organizacion as org
from modelos import Libro, Estudiante, Docente, Prestamo


class LibroDAO:
    """DAO encargado del acceso a datos de la entidad Libro."""

    # Columnas usadas en los listados. Se excluye a propósito el BLOB de la
    # portada (puede pesar varios KB por libro) y en su lugar se consulta
    # solamente si existe una imagen cargada.
    COLUMNAS_LISTADO = """
        id_libro, titulo, autor, editorial, isbn, genero, edad_recomendada,
        ciclo, stock, disponibles, (portada IS NOT NULL) AS hay_portada
    """

    # Criterios de ordenamiento permitidos para la búsqueda avanzada.
    # Se usa un diccionario cerrado para no interpolar texto del usuario en el SQL.
    ORDENAMIENTOS = {
        "Título (A-Z)": "titulo COLLATE NOCASE ASC",
        "Título (Z-A)": "titulo COLLATE NOCASE DESC",
        "Autor (A-Z)": "autor COLLATE NOCASE ASC, titulo COLLATE NOCASE ASC",
        "Ciclo": "ciclo COLLATE NOCASE ASC, titulo COLLATE NOCASE ASC",
        "Género": "genero COLLATE NOCASE ASC, titulo COLLATE NOCASE ASC",
        "Edad recomendada": "edad_recomendada COLLATE NOCASE ASC, titulo COLLATE NOCASE ASC",
        "Stock (menor a mayor)": "stock ASC, titulo COLLATE NOCASE ASC",
        "Stock (mayor a menor)": "stock DESC, titulo COLLATE NOCASE ASC",
        "ID (menor a mayor)": "id_libro ASC",
        "ID (mayor a menor)": "id_libro DESC",
    }
    ORDEN_POR_DEFECTO = "Título (A-Z)"

    def insertar(self, libro: Libro, codigo_cdd=None, organizacion=None) -> int:
        conexion = ConexionDB.conectar()
        try:
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO libros
                    (titulo, autor, editorial, isbn, genero, edad_recomendada,
                     ciclo, stock, disponibles, portada)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (libro.titulo, libro.autor, libro.editorial, libro.isbn or None,
                  libro.genero, libro.edad_recomendada or None, libro.ciclo,
                  libro.stock, libro.disponibles, libro.portada))
            if codigo_cdd is not None:
                cdd.guardar(cursor.lastrowid, codigo_cdd, conexion=conexion)
            if organizacion is not None:
                org.guardar(cursor.lastrowid, conexion=conexion, **organizacion)
            conexion.commit()
            return cursor.lastrowid
        finally:
            ConexionDB.cerrar(conexion)

    def obtener_todos(self):
        conexion = ConexionDB.conectar()
        try:
            filas = conexion.execute(
                f"SELECT {self.COLUMNAS_LISTADO} FROM libros "
                f"ORDER BY titulo COLLATE NOCASE ASC"
            ).fetchall()
            return [self._fila_a_libro(f) for f in filas]
        finally:
            ConexionDB.cerrar(conexion)

    def obtener_por_id(self, id_libro):
        conexion = ConexionDB.conectar()
        try:
            fila = conexion.execute(
                "SELECT * FROM libros WHERE id_libro = ?", (id_libro,)
            ).fetchone()
            return self._fila_a_libro(fila) if fila else None
        finally:
            ConexionDB.cerrar(conexion)

    def actualizar(self, libro: Libro, codigo_cdd=None, organizacion=None):
        if not libro.id_libro:
            raise ValueError("No se puede actualizar un libro sin id.")
        conexion = ConexionDB.conectar()
        try:
            conexion.execute("""
                UPDATE libros SET
                    titulo = ?, autor = ?, editorial = ?, isbn = ?,
                    genero = ?, edad_recomendada = ?, ciclo = ?,
                    stock = ?, disponibles = ?, portada = ?
                WHERE id_libro = ?
            """, (libro.titulo, libro.autor, libro.editorial, libro.isbn or None,
                  libro.genero, libro.edad_recomendada or None, libro.ciclo,
                  libro.stock, libro.disponibles, libro.portada, libro.id_libro))
            if codigo_cdd is not None:
                cdd.guardar(libro.id_libro, codigo_cdd, conexion=conexion)
            if organizacion is not None:
                org.guardar(libro.id_libro, conexion=conexion, **organizacion)
            conexion.commit()
        finally:
            ConexionDB.cerrar(conexion)

    def obtener_portada(self, id_libro):
        """
        Devuelve únicamente la imagen de tapa de un libro (en bytes) o None.
        Se consulta por separado para no cargar todas las imágenes en memoria
        cada vez que se refresca una tabla.
        """
        conexion = ConexionDB.conectar()
        try:
            fila = conexion.execute(
                "SELECT portada FROM libros WHERE id_libro = ?", (id_libro,)
            ).fetchone()
            if not fila or fila["portada"] is None:
                return None
            return bytes(fila["portada"])
        finally:
            ConexionDB.cerrar(conexion)

    def actualizar_portada(self, id_libro, portada):
        """Guarda (o borra, si portada es None) la imagen de tapa de un libro."""
        conexion = ConexionDB.conectar()
        try:
            conexion.execute(
                "UPDATE libros SET portada = ? WHERE id_libro = ?",
                (portada, id_libro)
            )
            conexion.commit()
        finally:
            ConexionDB.cerrar(conexion)

    def eliminar(self, id_libro):
        conexion = ConexionDB.conectar()
        try:
            conexion.execute("DELETE FROM libros WHERE id_libro = ?", (id_libro,))
            conexion.commit()
        finally:
            ConexionDB.cerrar(conexion)

    def actualizar_disponibles(self, id_libro, delta):
        """Suma (o resta, si delta es negativo) unidades al stock disponible de un libro."""
        conexion = ConexionDB.conectar()
        try:
            conexion.execute(
                "UPDATE libros SET disponibles = disponibles + ? WHERE id_libro = ?",
                (delta, id_libro)
            )
            conexion.commit()
        finally:
            ConexionDB.cerrar(conexion)

    def busqueda_avanzada(self, titulo="", autor="", genero="Todos",
                           ciclo="Todos", edad="Todos", solo_disponibles=False,
                           orden=None, ubicacion_id=None, etiqueta=None):
        """
        Búsqueda combinable de libros por título, autor, género, ciclo,
        edad recomendada y disponibilidad de stock.

        El parámetro 'orden' indica cómo se ordenan los resultados y debe ser
        una de las claves de ORDENAMIENTOS (alfabético por título o autor,
        por ciclo, por género o por edad recomendada).
        """
        condiciones = []
        parametros = []

        if titulo:
            condiciones.append("titulo LIKE ?")
            parametros.append(f"%{titulo}%")
        if autor:
            condiciones.append("autor LIKE ?")
            parametros.append(f"%{autor}%")
        if genero and genero != "Todos":
            condiciones.append("genero = ?")
            parametros.append(genero)
        if ciclo and ciclo != "Todos":
            condiciones.append("ciclo = ?")
            parametros.append(ciclo)
        if edad and edad != "Todos":
            if edad == "Sin especificar":
                condiciones.append("(edad_recomendada IS NULL OR edad_recomendada = '')")
            else:
                condiciones.append("edad_recomendada = ?")
                parametros.append(edad)
        if solo_disponibles:
            condiciones.append("disponibles > 0")

        if ubicacion_id == 0:
            condiciones.append("NOT EXISTS (SELECT 1 FROM libro_organizacion o WHERE o.id_libro=libros.id_libro AND o.id_ubicacion IS NOT NULL)")
        elif ubicacion_id is not None:
            condiciones.append("EXISTS (SELECT 1 FROM libro_organizacion o WHERE o.id_libro=libros.id_libro AND o.id_ubicacion=?)")
            parametros.append(ubicacion_id)
        if etiqueta == "":
            condiciones.append("NOT EXISTS (SELECT 1 FROM libro_organizacion o WHERE o.id_libro=libros.id_libro AND o.etiqueta<>'')")
        elif etiqueta is not None:
            condiciones.append("EXISTS (SELECT 1 FROM libro_organizacion o WHERE o.id_libro=libros.id_libro AND o.etiqueta=?)")
            parametros.append(etiqueta)

        consulta = f"SELECT {self.COLUMNAS_LISTADO} FROM libros"
        if condiciones:
            consulta += " WHERE " + " AND ".join(condiciones)
        criterio = self.ORDENAMIENTOS.get(orden, self.ORDENAMIENTOS[self.ORDEN_POR_DEFECTO])
        consulta += f" ORDER BY {criterio}"

        conexion = ConexionDB.conectar()
        try:
            filas = conexion.execute(consulta, parametros).fetchall()
            return [self._fila_a_libro(f) for f in filas]
        finally:
            ConexionDB.cerrar(conexion)

    @staticmethod
    def _fila_a_libro(fila):
        claves = fila.keys()
        portada = fila["portada"] if "portada" in claves else None
        hay_portada = fila["hay_portada"] if "hay_portada" in claves else None
        return Libro(
            id_libro=fila["id_libro"],
            titulo=fila["titulo"],
            autor=fila["autor"],
            editorial=fila["editorial"],
            isbn=fila["isbn"],
            genero=fila["genero"],
            edad_recomendada=fila["edad_recomendada"],
            ciclo=fila["ciclo"],
            stock=fila["stock"],
            disponibles=fila["disponibles"],
            portada=bytes(portada) if portada is not None else None,
            hay_portada=hay_portada,
        )


class EstudianteDAO:
    """DAO encargado del acceso a datos de la entidad Estudiante."""

    def insertar(self, estudiante: Estudiante) -> int:
        conexion = ConexionDB.conectar()
        try:
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO estudiantes (nombre, apellido, grado, dni)
                VALUES (?, ?, ?, ?)
            """, (estudiante.nombre, estudiante.apellido, estudiante.grado, estudiante.dni))
            conexion.commit()
            return cursor.lastrowid
        finally:
            ConexionDB.cerrar(conexion)

    def obtener_todos(self):
        conexion = ConexionDB.conectar()
        try:
            filas = conexion.execute(
                "SELECT * FROM estudiantes ORDER BY apellido ASC"
            ).fetchall()
            return [self._fila_a_estudiante(f) for f in filas]
        finally:
            ConexionDB.cerrar(conexion)

    def obtener_por_id(self, id_estudiante):
        conexion = ConexionDB.conectar()
        try:
            fila = conexion.execute(
                "SELECT * FROM estudiantes WHERE id_estudiante = ?", (id_estudiante,)
            ).fetchone()
            return self._fila_a_estudiante(fila) if fila else None
        finally:
            ConexionDB.cerrar(conexion)

    def actualizar(self, estudiante: Estudiante):
        conexion = ConexionDB.conectar()
        try:
            conexion.execute("""
                UPDATE estudiantes SET nombre = ?, apellido = ?, grado = ?, dni = ?
                WHERE id_estudiante = ?
            """, (estudiante.nombre, estudiante.apellido, estudiante.grado,
                  estudiante.dni, estudiante.id_estudiante))
            conexion.commit()
        finally:
            ConexionDB.cerrar(conexion)

    def eliminar(self, id_estudiante):
        conexion = ConexionDB.conectar()
        try:
            conexion.execute("DELETE FROM estudiantes WHERE id_estudiante = ?", (id_estudiante,))
            conexion.commit()
        finally:
            ConexionDB.cerrar(conexion)

    @staticmethod
    def _fila_a_estudiante(fila):
        return Estudiante(
            id_estudiante=fila["id_estudiante"],
            nombre=fila["nombre"],
            apellido=fila["apellido"],
            grado=fila["grado"],
            dni=fila["dni"],
        )


class DocenteDAO:
    """DAO encargado del acceso a datos de la entidad Docente."""

    def insertar(self, docente: Docente) -> int:
        conexion = ConexionDB.conectar()
        try:
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO docentes (nombre, apellido, area, dni)
                VALUES (?, ?, ?, ?)
            """, (docente.nombre, docente.apellido, docente.area, docente.dni))
            conexion.commit()
            return cursor.lastrowid
        finally:
            ConexionDB.cerrar(conexion)

    def obtener_todos(self):
        conexion = ConexionDB.conectar()
        try:
            filas = conexion.execute(
                "SELECT * FROM docentes ORDER BY apellido ASC"
            ).fetchall()
            return [self._fila_a_docente(f) for f in filas]
        finally:
            ConexionDB.cerrar(conexion)

    def obtener_por_id(self, id_docente):
        conexion = ConexionDB.conectar()
        try:
            fila = conexion.execute(
                "SELECT * FROM docentes WHERE id_docente = ?", (id_docente,)
            ).fetchone()
            return self._fila_a_docente(fila) if fila else None
        finally:
            ConexionDB.cerrar(conexion)

    def actualizar(self, docente: Docente):
        conexion = ConexionDB.conectar()
        try:
            conexion.execute("""
                UPDATE docentes SET nombre = ?, apellido = ?, area = ?, dni = ?
                WHERE id_docente = ?
            """, (docente.nombre, docente.apellido, docente.area,
                  docente.dni, docente.id_docente))
            conexion.commit()
        finally:
            ConexionDB.cerrar(conexion)

    def eliminar(self, id_docente):
        conexion = ConexionDB.conectar()
        try:
            conexion.execute("DELETE FROM docentes WHERE id_docente = ?", (id_docente,))
            conexion.commit()
        finally:
            ConexionDB.cerrar(conexion)

    @staticmethod
    def _fila_a_docente(fila):
        return Docente(
            id_docente=fila["id_docente"],
            nombre=fila["nombre"],
            apellido=fila["apellido"],
            area=fila["area"],
            dni=fila["dni"],
        )


class PrestamoDAO:
    """
    DAO encargado del acceso a datos de la entidad Prestamo.
    Implementa además consultas con JOIN para relacionar el préstamo
    con el libro y el solicitante (estudiante o docente) correspondiente.
    """

    def insertar(self, prestamo: Prestamo) -> int:
        conexion = ConexionDB.conectar()
        try:
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO prestamos
                    (id_libro, tipo_solicitante, id_solicitante, fecha_prestamo,
                     fecha_devolucion_estimada, fecha_devolucion_real, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (prestamo.id_libro, prestamo.tipo_solicitante, prestamo.id_solicitante,
                  prestamo.fecha_prestamo, prestamo.fecha_devolucion_estimada,
                  prestamo.fecha_devolucion_real, prestamo.estado))
            conexion.commit()
            return cursor.lastrowid
        finally:
            ConexionDB.cerrar(conexion)

    def actualizar(self, prestamo: Prestamo):
        conexion = ConexionDB.conectar()
        try:
            conexion.execute("""
                UPDATE prestamos SET
                    id_libro = ?, tipo_solicitante = ?, id_solicitante = ?,
                    fecha_prestamo = ?, fecha_devolucion_estimada = ?,
                    fecha_devolucion_real = ?, estado = ?
                WHERE id_prestamo = ?
            """, (prestamo.id_libro, prestamo.tipo_solicitante, prestamo.id_solicitante,
                  prestamo.fecha_prestamo, prestamo.fecha_devolucion_estimada,
                  prestamo.fecha_devolucion_real, prestamo.estado, prestamo.id_prestamo))
            conexion.commit()
        finally:
            ConexionDB.cerrar(conexion)

    def eliminar(self, id_prestamo):
        conexion = ConexionDB.conectar()
        try:
            conexion.execute("DELETE FROM prestamos WHERE id_prestamo = ?", (id_prestamo,))
            conexion.commit()
        finally:
            ConexionDB.cerrar(conexion)

    def registrar_devolucion(self, id_prestamo, fecha_devolucion_real):
        conexion = ConexionDB.conectar()
        try:
            conexion.execute("""
                UPDATE prestamos SET fecha_devolucion_real = ?, estado = 'Devuelto'
                WHERE id_prestamo = ?
            """, (fecha_devolucion_real, id_prestamo))
            conexion.commit()
        finally:
            ConexionDB.cerrar(conexion)

    def obtener_por_id(self, id_prestamo):
        conexion = ConexionDB.conectar()
        try:
            fila = conexion.execute(
                "SELECT * FROM prestamos WHERE id_prestamo = ?", (id_prestamo,)
            ).fetchone()
            if not fila:
                return None
            return Prestamo(
                id_prestamo=fila["id_prestamo"],
                id_libro=fila["id_libro"],
                tipo_solicitante=fila["tipo_solicitante"],
                id_solicitante=fila["id_solicitante"],
                fecha_prestamo=fila["fecha_prestamo"],
                fecha_devolucion_estimada=fila["fecha_devolucion_estimada"],
                fecha_devolucion_real=fila["fecha_devolucion_real"],
                estado=fila["estado"],
            )
        finally:
            ConexionDB.cerrar(conexion)

    def obtener_todos_detallado(self):
        """
        Consulta con JOIN: trae cada préstamo junto con el título del libro
        y el nombre completo del solicitante (estudiante o docente), resuelto
        dinámicamente según el campo tipo_solicitante.
        """
        consulta = """
            SELECT
                p.id_prestamo, p.id_libro, l.titulo AS titulo_libro,
                p.tipo_solicitante, p.id_solicitante,
                COALESCE(e.apellido || ', ' || e.nombre, d.apellido || ', ' || d.nombre) AS solicitante,
                p.fecha_prestamo, p.fecha_devolucion_estimada,
                p.fecha_devolucion_real, p.estado
            FROM prestamos p
            JOIN libros l ON l.id_libro = p.id_libro
            LEFT JOIN estudiantes e ON p.tipo_solicitante = 'Estudiante' AND e.id_estudiante = p.id_solicitante
            LEFT JOIN docentes d ON p.tipo_solicitante = 'Docente' AND d.id_docente = p.id_solicitante
            ORDER BY p.fecha_prestamo DESC
        """
        conexion = ConexionDB.conectar()
        try:
            filas = conexion.execute(consulta).fetchall()
            return [dict(f) for f in filas]
        finally:
            ConexionDB.cerrar(conexion)

    def buscar_detallado(self, estado="Todos", tipo_solicitante="Todos", texto=""):
        """Búsqueda combinable de préstamos por estado, tipo de solicitante y texto libre."""
        condiciones = []
        parametros = []

        if estado and estado != "Todos":
            condiciones.append("p.estado = ?")
            parametros.append(estado)
        if tipo_solicitante and tipo_solicitante != "Todos":
            condiciones.append("p.tipo_solicitante = ?")
            parametros.append(tipo_solicitante)
        if texto:
            condiciones.append("""
                (l.titulo LIKE ? OR
                 COALESCE(e.apellido || ' ' || e.nombre, d.apellido || ' ' || d.nombre) LIKE ?)
            """)
            parametros.extend([f"%{texto}%", f"%{texto}%"])

        consulta = """
            SELECT
                p.id_prestamo, p.id_libro, l.titulo AS titulo_libro,
                p.tipo_solicitante, p.id_solicitante,
                COALESCE(e.apellido || ', ' || e.nombre, d.apellido || ', ' || d.nombre) AS solicitante,
                p.fecha_prestamo, p.fecha_devolucion_estimada,
                p.fecha_devolucion_real, p.estado
            FROM prestamos p
            JOIN libros l ON l.id_libro = p.id_libro
            LEFT JOIN estudiantes e ON p.tipo_solicitante = 'Estudiante' AND e.id_estudiante = p.id_solicitante
            LEFT JOIN docentes d ON p.tipo_solicitante = 'Docente' AND d.id_docente = p.id_solicitante
        """
        if condiciones:
            consulta += " WHERE " + " AND ".join(condiciones)
        consulta += " ORDER BY p.fecha_prestamo DESC"

        conexion = ConexionDB.conectar()
        try:
            filas = conexion.execute(consulta, parametros).fetchall()
            return [dict(f) for f in filas]
        finally:
            ConexionDB.cerrar(conexion)

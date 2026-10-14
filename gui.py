"""
gui.py
Interfaz gráfica de usuario (Tkinter) del sistema de gestión de biblioteca escolar.

Esta capa NUNCA accede directamente a la base de datos: toda la persistencia
se resuelve a través de las clases DAO (dao.py). La GUI sólo se encarga de:
- Capturar datos de los formularios.
- Instanciar clases de dominio (modelos.py), que validan los datos.
- Invocar los métodos públicos de los DAO.
- Mostrar resultados en tablas (ttk.Treeview) y mensajes (tkinter.messagebox).
"""

import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime, timedelta

from modelos import (
    Libro, Estudiante, Docente, Prestamo,
    GENEROS, CICLOS, EDADES_RECOMENDADAS, TIPOS_SOLICITANTE, ORDENES_BUSQUEDA,
)
from dao import LibroDAO, EstudianteDAO, DocenteDAO, PrestamoDAO
from exportador_pdf import ExportadorPDF
from conexion import ConexionDB
import imagenes
import cdd

FORMATO_FECHA = "%d/%m/%Y"

# Clave que habilita el modo administrador. Es necesaria para eliminar o
# modificar libros, estudiantes, docentes y la cantidad (stock) de libros.
# Para cambiarla, edite este valor (y, si se distribuye como .exe, vuelva a
# generar el ejecutable con generar_ejecutable.bat).
CLAVE_ADMINISTRADOR = "escuela-360.2026"


def _validar_fecha(texto):
    try:
        datetime.strptime(texto.strip(), FORMATO_FECHA)
        return True
    except ValueError:
        return False


class AplicacionBiblioteca(tk.Tk):
    """Ventana principal del sistema de gestión de biblioteca escolar."""

    def __init__(self):
        super().__init__()
        self.title("Sistema de Gestión de Biblioteca Escolar")
        # La ventana es algo más ancha que antes para dejar lugar al panel
        # con la vista previa de la tapa del libro.
        self.geometry("1280x700")
        self.minsize(1100, 620)

        # Instancias únicas de los DAO utilizados en toda la aplicación.
        self.libro_dao = LibroDAO()
        self.estudiante_dao = EstudianteDAO()
        self.docente_dao = DocenteDAO()
        self.prestamo_dao = PrestamoDAO()

        # Modo administrador: controla si se permite eliminar o modificar
        # libros, estudiantes, docentes y la cantidad de libros.
        self.es_administrador = False

        cdd.inicializar()
        self._crear_menu()
        self._crear_barra_administrador()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_libros = ttk.Frame(self.notebook)
        self.tab_estudiantes = ttk.Frame(self.notebook)
        self.tab_docentes = ttk.Frame(self.notebook)
        self.tab_prestamos = ttk.Frame(self.notebook)
        self.tab_busqueda = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_libros, text="Libros")
        self.notebook.add(self.tab_estudiantes, text="Estudiantes")
        self.notebook.add(self.tab_docentes, text="Docentes")
        self.notebook.add(self.tab_prestamos, text="Préstamos")
        self.notebook.add(self.tab_busqueda, text="Búsqueda avanzada")

        self._construir_tab_libros()
        self._construir_tab_estudiantes()
        self._construir_tab_docentes()
        self._construir_tab_prestamos()
        self._construir_tab_busqueda()

        self._refrescar_libros()
        self._refrescar_estudiantes()
        self._refrescar_docentes()
        self._refrescar_prestamos()

    # ------------------------------------------------------------------
    # Menú superior: portabilidad de la base de datos
    # ------------------------------------------------------------------
    def _crear_menu(self):
        menu_barra = tk.Menu(self)

        menu_bd = tk.Menu(menu_barra, tearoff=0)
        menu_bd.add_command(label="Exportar copia de seguridad...", command=self._exportar_backup)
        menu_bd.add_command(label="Importar / Restaurar copia de seguridad...", command=self._importar_backup)
        menu_bd.add_separator()
        menu_bd.add_command(label="Salir", command=self.destroy)
        menu_barra.add_cascade(label="Base de datos", menu=menu_bd)

        self.config(menu=menu_barra)

    def _exportar_backup(self):
        """Copia el archivo biblioteca.db a la ubicación que elija el usuario (pendrive, etc.)."""
        destino = filedialog.asksaveasfilename(
            title="Guardar copia de seguridad",
            defaultextension=".db",
            initialfile="biblioteca_backup.db",
            filetypes=[("Base de datos SQLite", "*.db")],
        )
        if not destino:
            return
        try:
            shutil.copy(ConexionDB.obtener_ruta(), destino)
            messagebox.showinfo("Copia de seguridad", f"Copia guardada correctamente en:\n{destino}")
        except OSError as error:
            messagebox.showerror("Error", f"No se pudo generar la copia de seguridad.\n{error}")

    def _importar_backup(self):
        """Reemplaza la base de datos actual por un archivo .db elegido por el usuario."""
        origen = filedialog.askopenfilename(
            title="Seleccionar copia de seguridad",
            filetypes=[("Base de datos SQLite", "*.db")],
        )
        if not origen:
            return
        confirmar = messagebox.askyesno(
            "Confirmar restauración",
            "Esta acción reemplaza TODOS los datos actuales por los del archivo "
            "seleccionado. Esta operación no se puede deshacer.\n\n¿Desea continuar?",
        )
        if not confirmar:
            return
        try:
            shutil.copy(origen, ConexionDB.obtener_ruta())
            cdd.inicializar()
            messagebox.showinfo(
                "Restauración completa",
                "Los datos se restauraron correctamente.",
            )
            self._refrescar_libros()
            self._refrescar_estudiantes()
            self._refrescar_docentes()
            self._refrescar_prestamos()
            self._refrescar_combobox_libros_prestamo()
            self._refrescar_combobox_solicitantes()
        except OSError as error:
            messagebox.showerror("Error", f"No se pudo restaurar la copia de seguridad.\n{error}")

    # ------------------------------------------------------------------
    # Modo administrador
    # ------------------------------------------------------------------
    def _crear_barra_administrador(self):
        """Barra ubicada junto a las solapas, con el acceso al modo administrador."""
        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=8, pady=(8, 0))

        self.btn_admin = ttk.Button(
            barra, text="Ingresar como administrador", command=self._alternar_modo_administrador,
        )
        self.btn_admin.pack(side="right")

        self.lbl_modo_admin = ttk.Label(barra, text="Modo: invitado")
        self.lbl_modo_admin.pack(side="right", padx=(0, 8))

    def _alternar_modo_administrador(self):
        if self.es_administrador:
            confirmar = messagebox.askyesno(
                "Salir del modo administrador",
                "¿Desea salir del modo administrador?",
            )
            if not confirmar:
                return
            self.es_administrador = False
            self._actualizar_estado_administrador()
            return

        clave = simpledialog.askstring(
            "Ingresar como administrador",
            "Ingrese la clave de administrador:",
            show="*",
            parent=self,
        )
        if clave is None:
            return
        if clave == CLAVE_ADMINISTRADOR:
            self.es_administrador = True
            self._actualizar_estado_administrador()
            messagebox.showinfo("Modo administrador", "Modo administrador activado.")
        else:
            messagebox.showerror("Clave incorrecta", "La clave ingresada no es correcta.")

    def _actualizar_estado_administrador(self):
        if self.es_administrador:
            self.lbl_modo_admin.config(text="Modo: administrador")
            self.btn_admin.config(text="Salir del modo administrador")
        else:
            self.lbl_modo_admin.config(text="Modo: invitado")
            self.btn_admin.config(text="Ingresar como administrador")

    def _requiere_administrador(self):
        """Verifica el modo administrador; si no está activo, avisa y devuelve False."""
        if not self.es_administrador:
            messagebox.showwarning(
                "Acción restringida",
                "Esta acción requiere el modo administrador.\n"
                "Use el botón «Ingresar como administrador» e ingrese la clave.",
            )
            return False
        return True

    # ==================================================================
    # TAB LIBROS
    # ==================================================================
    def _construir_tab_libros(self):
        contenedor = self.tab_libros

        # La parte superior se divide en dos: a la izquierda el formulario de
        # datos y a la derecha la vista previa de la tapa del libro.
        fila_superior = ttk.Frame(contenedor)
        fila_superior.pack(fill="x", padx=8, pady=8)

        # El panel de la portada se ubica primero, contra el borde derecho:
        # así conserva siempre su ancho aunque el formulario sea más grande
        # que la ventana.
        panel_portada = ttk.LabelFrame(fila_superior, text="Portada del libro")
        panel_portada.pack(side="right", fill="y", padx=(8, 0))

        panel_form = ttk.LabelFrame(fila_superior, text="Datos del libro")
        panel_form.pack(side="left", fill="x", expand=True, anchor="n")

        self.var_libro_titulo = tk.StringVar()
        self.var_libro_autor = tk.StringVar()
        self.var_libro_editorial = tk.StringVar()
        self.var_libro_isbn = tk.StringVar()
        self.var_libro_genero = tk.StringVar()
        self.var_libro_edad = tk.StringVar()
        self.var_libro_ciclo = tk.StringVar()
        self.var_libro_stock = tk.StringVar()
        self._id_libro_seleccionado = None

        campos_texto = [
            ("Título*", self.var_libro_titulo), ("Autor*", self.var_libro_autor),
            ("Editorial", self.var_libro_editorial), ("ISBN", self.var_libro_isbn),
        ]
        for i, (texto, var) in enumerate(campos_texto):
            ttk.Label(panel_form, text=texto).grid(row=0, column=i * 2, sticky="w", padx=4, pady=4)
            ttk.Entry(panel_form, textvariable=var, width=17).grid(row=0, column=i * 2 + 1, padx=4, pady=4)

        ttk.Label(panel_form, text="Género*").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(panel_form, textvariable=self.var_libro_genero, values=GENEROS,
                     state="readonly", width=18).grid(row=1, column=1, padx=4, pady=4)

        ttk.Label(panel_form, text="Edad recomendada").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        ttk.Combobox(panel_form, textvariable=self.var_libro_edad, values=[""] + EDADES_RECOMENDADAS,
                     state="readonly", width=18).grid(row=1, column=3, padx=4, pady=4)

        ttk.Label(panel_form, text="Ciclo*").grid(row=1, column=4, sticky="w", padx=4, pady=4)
        ttk.Combobox(panel_form, textvariable=self.var_libro_ciclo, values=CICLOS,
                     state="readonly", width=18).grid(row=1, column=5, padx=4, pady=4)

        ttk.Label(panel_form, text="Stock*").grid(row=1, column=6, sticky="w", padx=4, pady=4)
        tk.Spinbox(panel_form, from_=0, to=9999, textvariable=self.var_libro_stock,
                   width=6).grid(row=1, column=7, sticky="w", padx=4, pady=4)

        # Clasificación Dewey según tabla local validada de BNM.
        ttk.Label(panel_form, text="Notación CDD/BNM").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.var_libro_cdd = tk.StringVar()
        entrada_cdd = ttk.Entry(panel_form, textvariable=self.var_libro_cdd, width=18)
        entrada_cdd.grid(row=2, column=1, padx=4, pady=4)
        ttk.Button(panel_form, text="Catálogo BNM…", command=self._elegir_cdd).grid(row=2,column=2,padx=4)
        self.var_cdd_descripcion = tk.StringVar(value="Ingrese el CDD impreso en el libro")
        ttk.Label(panel_form, textvariable=self.var_cdd_descripcion, wraplength=470).grid(row=2,column=3,columnspan=5,sticky="w",padx=4)
        self.var_libro_cdd.trace_add('write', lambda *_: self._consultar_cdd())

        # --- Vista previa de la portada -------------------------------------
        self._portada_libro_actual = None   # bytes de la tapa cargada en el formulario
        self._imagen_portada_libro = None   # referencia viva de la imagen mostrada

        self.lbl_portada_libro = self._crear_recuadro_portada(panel_portada)

        panel_portada_botones = ttk.Frame(panel_portada)
        panel_portada_botones.pack(fill="x", padx=6, pady=(0, 4))
        ttk.Button(panel_portada_botones, text="Cargar imagen...",
                   command=self._cargar_portada).pack(side="left", padx=2)
        ttk.Button(panel_portada_botones, text="Quitar",
                   command=self._quitar_portada).pack(side="left", padx=2)

        ttk.Label(panel_portada, text="Se guarda al presionar Agregar o Modificar.",
                  wraplength=imagenes.ANCHO_VISTA_PREVIA + 60, justify="center",
                  foreground="#666666").pack(padx=6, pady=(0, 6))

        panel_botones = ttk.Frame(contenedor)
        panel_botones.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(panel_botones, text="Agregar", command=self._agregar_libro).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Modificar", command=self._modificar_libro).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Eliminar", command=self._eliminar_libro).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Limpiar", command=self._limpiar_form_libro).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Exportar catálogo a PDF",
                   command=self._exportar_libros_pdf).pack(side="right", padx=4)
        self.var_pdf_portadas_libros = tk.BooleanVar(value=False)
        ttk.Checkbutton(panel_botones, text="Incluir portadas en el PDF",
                         variable=self.var_pdf_portadas_libros).pack(side="right", padx=4)

        columnas = ("id", "titulo", "autor", "editorial", "isbn", "genero", "edad",
                    "ciclo", "stock", "disponibles", "tapa")
        encabezados = ("ID", "Título", "Autor", "Editorial", "ISBN", "Género", "Edad",
                       "Ciclo", "Stock", "Disp.", "Tapa")
        self.tabla_libros = ttk.Treeview(contenedor, columns=columnas, show="headings", height=14)
        for col, enc in zip(columnas, encabezados):
            self.tabla_libros.heading(col, text=enc)
            self.tabla_libros.column(col, width=100, anchor="center")
        self.tabla_libros.column("titulo", width=180, anchor="w")
        self.tabla_libros.column("autor", width=140, anchor="w")
        self.tabla_libros.column("tapa", width=60, anchor="center")
        self.tabla_libros.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tabla_libros.bind("<<TreeviewSelect>>", self._seleccionar_libro)

    # ------------------------------------------------------------------
    # Portadas: recuadro de vista previa y carga de imágenes
    # ------------------------------------------------------------------
    def _crear_recuadro_portada(self, contenedor):
        """
        Crea el recuadro de tamaño fijo donde se muestra la tapa del libro y
        devuelve la etiqueta interna sobre la que se dibuja la imagen.
        """
        marco = tk.Frame(contenedor, width=imagenes.ANCHO_VISTA_PREVIA + 12,
                          height=imagenes.ALTO_VISTA_PREVIA + 12,
                          relief="groove", bd=1, bg="white")
        marco.pack(padx=6, pady=6)
        marco.pack_propagate(False)   # el marco no se achica ni se agranda con la imagen
        etiqueta = tk.Label(marco, text="Sin portada", bg="white", fg="#888888",
                             wraplength=imagenes.ANCHO_VISTA_PREVIA, justify="center")
        etiqueta.pack(fill="both", expand=True)
        return etiqueta

    def _mostrar_portada(self, etiqueta, datos, nombre_referencia):
        """
        Dibuja una portada en el recuadro indicado.

        La imagen se guarda además en un atributo de la ventana
        ('nombre_referencia'): Tkinter no conserva una referencia propia y, si
        Python la libera, el recuadro aparecería vacío.
        """
        imagen = imagenes.a_imagen_tk(datos) if datos else None
        if imagen is None:
            setattr(self, nombre_referencia, None)
            texto = "Sin portada" if not datos else "No se pudo mostrar la imagen"
            etiqueta.configure(image="", text=texto)
        else:
            setattr(self, nombre_referencia, imagen)
            etiqueta.configure(image=imagen, text="")

    def _cargar_portada(self):
        """Permite elegir un archivo de imagen y lo carga en el formulario del libro."""
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen de tapa",
            filetypes=imagenes.formatos_admitidos(),
        )
        if not ruta:
            return
        try:
            datos = imagenes.preparar_portada(ruta)
        except ValueError as error:
            messagebox.showerror("Imagen no válida", str(error))
            return
        except OSError as error:
            messagebox.showerror("Error", f"No se pudo leer la imagen.\n{error}")
            return
        self._portada_libro_actual = datos
        self._mostrar_portada(self.lbl_portada_libro, datos, "_imagen_portada_libro")

    def _quitar_portada(self):
        """Quita la tapa del formulario (se aplica al guardar el libro)."""
        self._portada_libro_actual = None
        self._mostrar_portada(self.lbl_portada_libro, None, "_imagen_portada_libro")

    def _consultar_cdd(self):
        try:
            resultado = cdd.clasificar(self.var_libro_cdd.get())
            self.var_cdd_descripcion.set(resultado.texto())
        except ValueError as error:
            self.var_cdd_descripcion.set(str(error))

    def _elegir_cdd(self):
        ventana = tk.Toplevel(self)
        ventana.title("Notaciones verificadas — Biblioteca Nacional de Maestros")
        ventana.geometry("790x480")
        ventana.transient(self)
        ventana.grab_set()
        ttk.Label(ventana, text="Buscar código o tema (ej.: narrativa, enciclopedias, matemáticas)").pack(padx=12, pady=8)
        filtro = tk.StringVar()
        entrada = ttk.Entry(ventana, textvariable=filtro)
        entrada.pack(fill="x", padx=12)
        marco = ttk.Frame(ventana)
        marco.pack(fill="both", expand=True, padx=12, pady=8)
        tabla = ttk.Treeview(marco, columns=("codigo", "descripcion", "pagina"), show="headings")
        for col, titulo, ancho in [("codigo", "Notación", 135), ("descripcion", "Clasificación", 500), ("pagina", "Pág. PDF", 75)]:
            tabla.heading(col, text=titulo)
            tabla.column(col, width=ancho, anchor="w")
        barra = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
        tabla.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        tabla.pack(fill="both", expand=True)

        def actualizar(*_):
            tabla.delete(*tabla.get_children())
            for fila in cdd.catalogo(filtro.get()):
                tabla.insert("", "end", values=fila)

        def elegir(*_):
            seleccion = tabla.selection()
            if seleccion:
                self.var_libro_cdd.set(tabla.item(seleccion[0], "values")[0])
                ventana.destroy()

        filtro.trace_add("write", actualizar)
        tabla.bind("<Double-1>", elegir)
        tabla.bind("<Return>", elegir)
        ttk.Label(ventana, text="Catálogo parcial. R/RE/L/S/E/PL corresponden a sectores especiales del manual.\nE se admite como 3-E; A y otros prefijos locales quedan pendientes de revisión.", wraplength=740).pack(padx=12)
        ttk.Button(ventana, text="Usar notación seleccionada", command=elegir).pack(pady=8)
        actualizar()
        entrada.focus_set()

    def _limpiar_form_libro(self):
        self._id_libro_seleccionado = None
        for var in (self.var_libro_titulo, self.var_libro_autor, self.var_libro_editorial,
                    self.var_libro_isbn, self.var_libro_genero, self.var_libro_edad,
                    self.var_libro_ciclo, self.var_libro_stock):
            var.set("")
        self.var_libro_cdd.set("")
        self._consultar_cdd()
        self._quitar_portada()
        self.tabla_libros.selection_remove(self.tabla_libros.selection())

    def _leer_form_libro(self, disponibles=None):
        return Libro(
            id_libro=self._id_libro_seleccionado,
            titulo=self.var_libro_titulo.get(),
            autor=self.var_libro_autor.get(),
            editorial=self.var_libro_editorial.get(),
            isbn=self.var_libro_isbn.get(),
            genero=self.var_libro_genero.get(),
            edad_recomendada=self.var_libro_edad.get(),
            ciclo=self.var_libro_ciclo.get(),
            stock=self.var_libro_stock.get() or 0,
            disponibles=disponibles,
            portada=self._portada_libro_actual,
        )

    def _agregar_libro(self):
        try:
            libro = self._leer_form_libro(disponibles=None)
        except ValueError as error:
            messagebox.showerror("Datos inválidos", str(error))
            return
        if not cdd.codigo_valido(self.var_libro_cdd.get()):
            messagebox.showerror("CDD", "El código CDD tiene un formato inválido.")
            return
        try:
            self.libro_dao.insertar(libro, codigo_cdd=self.var_libro_cdd.get())
        except Exception as error:
            messagebox.showerror("Error al guardar", f"No se pudo agregar el libro. "
                                                       f"Verifique que el ISBN no esté duplicado.\n{error}")
            return
        messagebox.showinfo("Éxito", "Libro agregado correctamente.")
        self._limpiar_form_libro()
        self._refrescar_libros()
        self._refrescar_combobox_libros_prestamo()

    def _modificar_libro(self):
        if not self._requiere_administrador():
            return
        if not self._id_libro_seleccionado:
            messagebox.showwarning("Atención", "Seleccione un libro de la lista para modificar.")
            return
        libro_actual = self.libro_dao.obtener_por_id(self._id_libro_seleccionado)
        if not libro_actual:
            messagebox.showerror("Error", "El libro seleccionado ya no existe.")
            return
        # Se conserva la cantidad de ejemplares actualmente prestados al recalcular
        # los disponibles según el nuevo stock ingresado.
        prestados = libro_actual.stock - libro_actual.disponibles
        try:
            nuevo_stock = int(self.var_libro_stock.get() or 0)
            libro = self._leer_form_libro(disponibles=max(0, nuevo_stock - prestados))
        except ValueError as error:
            messagebox.showerror("Datos inválidos", str(error))
            return
        if not cdd.codigo_valido(self.var_libro_cdd.get()):
            messagebox.showerror("CDD", "El código CDD tiene un formato inválido.")
            return
        try:
            self.libro_dao.actualizar(libro, codigo_cdd=self.var_libro_cdd.get())
        except Exception as error:
            messagebox.showerror("Error al guardar", f"No se pudo modificar el libro.\n{error}")
            return
        messagebox.showinfo("Éxito", "Libro modificado correctamente.")
        self._limpiar_form_libro()
        self._refrescar_libros()
        self._refrescar_combobox_libros_prestamo()

    def _eliminar_libro(self):
        if not self._requiere_administrador():
            return
        if not self._id_libro_seleccionado:
            messagebox.showwarning("Atención", "Seleccione un libro de la lista para eliminar.")
            return
        confirmar = messagebox.askyesno(
            "Confirmar eliminación",
            "¿Está seguro de eliminar este libro? Se eliminarán también sus registros de préstamo asociados.",
        )
        if not confirmar:
            return
        try:
            self.libro_dao.eliminar(self._id_libro_seleccionado)
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo eliminar el libro.\n{error}")
            return
        messagebox.showinfo("Éxito", "Libro eliminado correctamente.")
        self._limpiar_form_libro()
        self._refrescar_libros()
        self._refrescar_combobox_libros_prestamo()

    def _seleccionar_libro(self, evento):
        seleccion = self.tabla_libros.selection()
        if not seleccion:
            return
        valores = self.tabla_libros.item(seleccion[0], "values")
        self._id_libro_seleccionado = int(valores[0])
        self.var_libro_titulo.set(valores[1])
        self.var_libro_autor.set(valores[2])
        self.var_libro_editorial.set(valores[3])
        self.var_libro_isbn.set(valores[4])
        self.var_libro_genero.set(valores[5])
        self.var_libro_edad.set(valores[6])
        self.var_libro_ciclo.set(valores[7])
        self.var_libro_stock.set(valores[8])
        self.var_libro_cdd.set(cdd.obtener(self._id_libro_seleccionado))
        self._consultar_cdd()

        # La imagen se pide recién ahora (los listados no la traen, para no
        # cargar todas las tapas en memoria).
        self._portada_libro_actual = self.libro_dao.obtener_portada(self._id_libro_seleccionado)
        self._mostrar_portada(self.lbl_portada_libro, self._portada_libro_actual,
                               "_imagen_portada_libro")

    def _refrescar_libros(self):
        for fila in self.tabla_libros.get_children():
            self.tabla_libros.delete(fila)
        for libro in self.libro_dao.obtener_todos():
            self.tabla_libros.insert("", "end", values=(
                libro.id_libro, libro.titulo, libro.autor, libro.editorial, libro.isbn,
                libro.genero, libro.edad_recomendada, libro.ciclo, libro.stock, libro.disponibles,
                "Sí" if libro.tiene_portada() else "-",
            ))

    def _exportar_libros_pdf(self):
        self._exportar_treeview_pdf(self.tabla_libros, "Catálogo de libros",
                                     ("ID", "Título", "Autor", "Editorial", "ISBN",
                                      "Género", "Edad", "Ciclo", "Stock", "Disp.", "Tapa"),
                                     incluir_portadas=self.var_pdf_portadas_libros.get())

    # ==================================================================
    # TAB ESTUDIANTES
    # ==================================================================
    def _construir_tab_estudiantes(self):
        contenedor = self.tab_estudiantes
        panel_form = ttk.LabelFrame(contenedor, text="Datos del estudiante")
        panel_form.pack(fill="x", padx=8, pady=8)

        self.var_est_nombre = tk.StringVar()
        self.var_est_apellido = tk.StringVar()
        self.var_est_grado = tk.StringVar()
        self.var_est_dni = tk.StringVar()
        self._id_estudiante_seleccionado = None

        grados = [f"{n}° grado" for n in range(1, 8)]

        ttk.Label(panel_form, text="Nombre*").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(panel_form, textvariable=self.var_est_nombre, width=20).grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(panel_form, text="Apellido*").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(panel_form, textvariable=self.var_est_apellido, width=20).grid(row=0, column=3, padx=4, pady=4)

        ttk.Label(panel_form, text="Grado*").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        ttk.Combobox(panel_form, textvariable=self.var_est_grado, values=grados,
                     state="readonly", width=14).grid(row=0, column=5, padx=4, pady=4)

        ttk.Label(panel_form, text="DNI*").grid(row=0, column=6, sticky="w", padx=4, pady=4)
        ttk.Entry(panel_form, textvariable=self.var_est_dni, width=14).grid(row=0, column=7, padx=4, pady=4)

        panel_botones = ttk.Frame(contenedor)
        panel_botones.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(panel_botones, text="Agregar", command=self._agregar_estudiante).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Modificar", command=self._modificar_estudiante).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Eliminar", command=self._eliminar_estudiante).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Limpiar", command=self._limpiar_form_estudiante).pack(side="left", padx=4)

        columnas = ("id", "apellido", "nombre", "grado", "dni")
        encabezados = ("ID", "Apellido", "Nombre", "Grado", "DNI")
        self.tabla_estudiantes = ttk.Treeview(contenedor, columns=columnas, show="headings", height=14)
        for col, enc in zip(columnas, encabezados):
            self.tabla_estudiantes.heading(col, text=enc)
            self.tabla_estudiantes.column(col, width=130, anchor="center")
        self.tabla_estudiantes.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tabla_estudiantes.bind("<<TreeviewSelect>>", self._seleccionar_estudiante)

    def _limpiar_form_estudiante(self):
        self._id_estudiante_seleccionado = None
        for var in (self.var_est_nombre, self.var_est_apellido, self.var_est_grado, self.var_est_dni):
            var.set("")
        self.tabla_estudiantes.selection_remove(self.tabla_estudiantes.selection())

    def _agregar_estudiante(self):
        try:
            estudiante = Estudiante(nombre=self.var_est_nombre.get(), apellido=self.var_est_apellido.get(),
                                     grado=self.var_est_grado.get(), dni=self.var_est_dni.get())
            self.estudiante_dao.insertar(estudiante)
        except ValueError as error:
            messagebox.showerror("Datos inválidos", str(error))
            return
        except Exception as error:
            messagebox.showerror("Error al guardar", f"No se pudo agregar el estudiante. "
                                                       f"Verifique que el DNI no esté duplicado.\n{error}")
            return
        messagebox.showinfo("Éxito", "Estudiante agregado correctamente.")
        self._limpiar_form_estudiante()
        self._refrescar_estudiantes()
        self._refrescar_combobox_solicitantes()

    def _modificar_estudiante(self):
        if not self._requiere_administrador():
            return
        if not self._id_estudiante_seleccionado:
            messagebox.showwarning("Atención", "Seleccione un estudiante de la lista para modificar.")
            return
        try:
            estudiante = Estudiante(id_estudiante=self._id_estudiante_seleccionado,
                                     nombre=self.var_est_nombre.get(), apellido=self.var_est_apellido.get(),
                                     grado=self.var_est_grado.get(), dni=self.var_est_dni.get())
            self.estudiante_dao.actualizar(estudiante)
        except ValueError as error:
            messagebox.showerror("Datos inválidos", str(error))
            return
        except Exception as error:
            messagebox.showerror("Error al guardar", f"No se pudo modificar el estudiante.\n{error}")
            return
        messagebox.showinfo("Éxito", "Estudiante modificado correctamente.")
        self._limpiar_form_estudiante()
        self._refrescar_estudiantes()
        self._refrescar_combobox_solicitantes()

    def _eliminar_estudiante(self):
        if not self._requiere_administrador():
            return
        if not self._id_estudiante_seleccionado:
            messagebox.showwarning("Atención", "Seleccione un estudiante de la lista para eliminar.")
            return
        confirmar = messagebox.askyesno("Confirmar eliminación", "¿Está seguro de eliminar este estudiante?")
        if not confirmar:
            return
        try:
            self.estudiante_dao.eliminar(self._id_estudiante_seleccionado)
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo eliminar el estudiante.\n{error}")
            return
        messagebox.showinfo("Éxito", "Estudiante eliminado correctamente.")
        self._limpiar_form_estudiante()
        self._refrescar_estudiantes()
        self._refrescar_combobox_solicitantes()

    def _seleccionar_estudiante(self, evento):
        seleccion = self.tabla_estudiantes.selection()
        if not seleccion:
            return
        valores = self.tabla_estudiantes.item(seleccion[0], "values")
        self._id_estudiante_seleccionado = int(valores[0])
        self.var_est_apellido.set(valores[1])
        self.var_est_nombre.set(valores[2])
        self.var_est_grado.set(valores[3])
        self.var_est_dni.set(valores[4])

    def _refrescar_estudiantes(self):
        for fila in self.tabla_estudiantes.get_children():
            self.tabla_estudiantes.delete(fila)
        for estudiante in self.estudiante_dao.obtener_todos():
            self.tabla_estudiantes.insert("", "end", values=(
                estudiante.id_estudiante, estudiante.apellido, estudiante.nombre,
                estudiante.grado, estudiante.dni,
            ))

    # ==================================================================
    # TAB DOCENTES
    # ==================================================================
    def _construir_tab_docentes(self):
        contenedor = self.tab_docentes
        panel_form = ttk.LabelFrame(contenedor, text="Datos del docente")
        panel_form.pack(fill="x", padx=8, pady=8)

        self.var_doc_nombre = tk.StringVar()
        self.var_doc_apellido = tk.StringVar()
        self.var_doc_area = tk.StringVar()
        self.var_doc_dni = tk.StringVar()
        self._id_docente_seleccionado = None

        ttk.Label(panel_form, text="Nombre*").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(panel_form, textvariable=self.var_doc_nombre, width=20).grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(panel_form, text="Apellido*").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(panel_form, textvariable=self.var_doc_apellido, width=20).grid(row=0, column=3, padx=4, pady=4)

        ttk.Label(panel_form, text="Área").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        ttk.Entry(panel_form, textvariable=self.var_doc_area, width=18).grid(row=0, column=5, padx=4, pady=4)

        ttk.Label(panel_form, text="DNI*").grid(row=0, column=6, sticky="w", padx=4, pady=4)
        ttk.Entry(panel_form, textvariable=self.var_doc_dni, width=14).grid(row=0, column=7, padx=4, pady=4)

        panel_botones = ttk.Frame(contenedor)
        panel_botones.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(panel_botones, text="Agregar", command=self._agregar_docente).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Modificar", command=self._modificar_docente).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Eliminar", command=self._eliminar_docente).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Limpiar", command=self._limpiar_form_docente).pack(side="left", padx=4)

        columnas = ("id", "apellido", "nombre", "area", "dni")
        encabezados = ("ID", "Apellido", "Nombre", "Área", "DNI")
        self.tabla_docentes = ttk.Treeview(contenedor, columns=columnas, show="headings", height=14)
        for col, enc in zip(columnas, encabezados):
            self.tabla_docentes.heading(col, text=enc)
            self.tabla_docentes.column(col, width=130, anchor="center")
        self.tabla_docentes.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tabla_docentes.bind("<<TreeviewSelect>>", self._seleccionar_docente)

    def _limpiar_form_docente(self):
        self._id_docente_seleccionado = None
        for var in (self.var_doc_nombre, self.var_doc_apellido, self.var_doc_area, self.var_doc_dni):
            var.set("")
        self.tabla_docentes.selection_remove(self.tabla_docentes.selection())

    def _agregar_docente(self):
        try:
            docente = Docente(nombre=self.var_doc_nombre.get(), apellido=self.var_doc_apellido.get(),
                               area=self.var_doc_area.get(), dni=self.var_doc_dni.get())
            self.docente_dao.insertar(docente)
        except ValueError as error:
            messagebox.showerror("Datos inválidos", str(error))
            return
        except Exception as error:
            messagebox.showerror("Error al guardar", f"No se pudo agregar el docente. "
                                                       f"Verifique que el DNI no esté duplicado.\n{error}")
            return
        messagebox.showinfo("Éxito", "Docente agregado correctamente.")
        self._limpiar_form_docente()
        self._refrescar_docentes()
        self._refrescar_combobox_solicitantes()

    def _modificar_docente(self):
        if not self._requiere_administrador():
            return
        if not self._id_docente_seleccionado:
            messagebox.showwarning("Atención", "Seleccione un docente de la lista para modificar.")
            return
        try:
            docente = Docente(id_docente=self._id_docente_seleccionado,
                               nombre=self.var_doc_nombre.get(), apellido=self.var_doc_apellido.get(),
                               area=self.var_doc_area.get(), dni=self.var_doc_dni.get())
            self.docente_dao.actualizar(docente)
        except ValueError as error:
            messagebox.showerror("Datos inválidos", str(error))
            return
        except Exception as error:
            messagebox.showerror("Error al guardar", f"No se pudo modificar el docente.\n{error}")
            return
        messagebox.showinfo("Éxito", "Docente modificado correctamente.")
        self._limpiar_form_docente()
        self._refrescar_docentes()
        self._refrescar_combobox_solicitantes()

    def _eliminar_docente(self):
        if not self._requiere_administrador():
            return
        if not self._id_docente_seleccionado:
            messagebox.showwarning("Atención", "Seleccione un docente de la lista para eliminar.")
            return
        confirmar = messagebox.askyesno("Confirmar eliminación", "¿Está seguro de eliminar este docente?")
        if not confirmar:
            return
        try:
            self.docente_dao.eliminar(self._id_docente_seleccionado)
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo eliminar el docente.\n{error}")
            return
        messagebox.showinfo("Éxito", "Docente eliminado correctamente.")
        self._limpiar_form_docente()
        self._refrescar_docentes()
        self._refrescar_combobox_solicitantes()

    def _seleccionar_docente(self, evento):
        seleccion = self.tabla_docentes.selection()
        if not seleccion:
            return
        valores = self.tabla_docentes.item(seleccion[0], "values")
        self._id_docente_seleccionado = int(valores[0])
        self.var_doc_apellido.set(valores[1])
        self.var_doc_nombre.set(valores[2])
        self.var_doc_area.set(valores[3])
        self.var_doc_dni.set(valores[4])

    def _refrescar_docentes(self):
        for fila in self.tabla_docentes.get_children():
            self.tabla_docentes.delete(fila)
        for docente in self.docente_dao.obtener_todos():
            self.tabla_docentes.insert("", "end", values=(
                docente.id_docente, docente.apellido, docente.nombre,
                docente.area, docente.dni,
            ))

    # ==================================================================
    # TAB PRÉSTAMOS
    # ==================================================================
    def _construir_tab_prestamos(self):
        contenedor = self.tab_prestamos
        panel_form = ttk.LabelFrame(contenedor, text="Registrar préstamo")
        panel_form.pack(fill="x", padx=8, pady=8)

        self.var_prestamo_libro = tk.StringVar()
        self.var_prestamo_tipo = tk.StringVar(value=TIPOS_SOLICITANTE[0])
        self.var_prestamo_solicitante = tk.StringVar()
        self.var_prestamo_fecha = tk.StringVar(value=datetime.now().strftime(FORMATO_FECHA))
        self.var_prestamo_fecha_est = tk.StringVar(
            value=(datetime.now() + timedelta(days=14)).strftime(FORMATO_FECHA))

        self._mapa_libros = {}        # "título (disp: n)" -> id_libro
        self._mapa_solicitantes = {}  # "Apellido, Nombre" -> id

        ttk.Label(panel_form, text="Libro*").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.combo_prestamo_libro = ttk.Combobox(panel_form, textvariable=self.var_prestamo_libro,
                                                  state="readonly", width=32)
        self.combo_prestamo_libro.grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(panel_form, text="Tipo de solicitante*").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        combo_tipo = ttk.Combobox(panel_form, textvariable=self.var_prestamo_tipo,
                                   values=TIPOS_SOLICITANTE, state="readonly", width=12)
        combo_tipo.grid(row=0, column=3, padx=4, pady=4)
        combo_tipo.bind("<<ComboboxSelected>>", lambda e: self._refrescar_combobox_solicitantes())

        ttk.Label(panel_form, text="Solicitante*").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        self.combo_prestamo_solicitante = ttk.Combobox(panel_form, textvariable=self.var_prestamo_solicitante,
                                                        state="readonly", width=24)
        self.combo_prestamo_solicitante.grid(row=0, column=5, padx=4, pady=4)

        ttk.Label(panel_form, text="Fecha préstamo*").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(panel_form, textvariable=self.var_prestamo_fecha, width=12).grid(
            row=1, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(panel_form, text="Fecha dev. estimada*").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(panel_form, textvariable=self.var_prestamo_fecha_est, width=12).grid(
            row=1, column=3, sticky="w", padx=4, pady=4)
        ttk.Label(panel_form, text="(formato DD/MM/AAAA)").grid(row=1, column=4, columnspan=2, sticky="w", padx=4, pady=4)

        panel_botones = ttk.Frame(contenedor)
        panel_botones.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(panel_botones, text="Registrar préstamo", command=self._registrar_prestamo).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Registrar devolución", command=self._registrar_devolucion).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Eliminar registro", command=self._eliminar_prestamo).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Exportar listado a PDF", command=self._exportar_prestamos_pdf).pack(side="right", padx=4)

        columnas = ("id", "libro", "solicitante", "tipo", "f_prestamo", "f_est", "f_real", "estado")
        encabezados = ("ID", "Libro", "Solicitante", "Tipo", "F. Préstamo", "F. Dev. Estimada", "F. Dev. Real", "Estado")
        self.tabla_prestamos = ttk.Treeview(contenedor, columns=columnas, show="headings", height=13)
        for col, enc in zip(columnas, encabezados):
            self.tabla_prestamos.heading(col, text=enc)
            self.tabla_prestamos.column(col, width=110, anchor="center")
        self.tabla_prestamos.column("libro", width=170, anchor="w")
        self.tabla_prestamos.column("solicitante", width=150, anchor="w")
        self.tabla_prestamos.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._refrescar_combobox_libros_prestamo()
        self._refrescar_combobox_solicitantes()

    def _refrescar_combobox_libros_prestamo(self):
        self._mapa_libros = {}
        opciones = []
        for libro in self.libro_dao.obtener_todos():
            etiqueta = f"{libro.titulo} (disp: {libro.disponibles})"
            self._mapa_libros[etiqueta] = libro.id_libro
            opciones.append(etiqueta)
        if hasattr(self, "combo_prestamo_libro"):
            self.combo_prestamo_libro["values"] = opciones
            self.var_prestamo_libro.set("")

    def _refrescar_combobox_solicitantes(self):
        self._mapa_solicitantes = {}
        opciones = []
        if self.var_prestamo_tipo.get() == "Estudiante":
            for est in self.estudiante_dao.obtener_todos():
                etiqueta = f"{est.apellido}, {est.nombre} ({est.grado})"
                self._mapa_solicitantes[etiqueta] = est.id_estudiante
                opciones.append(etiqueta)
        else:
            for doc in self.docente_dao.obtener_todos():
                etiqueta = f"{doc.apellido}, {doc.nombre}"
                self._mapa_solicitantes[etiqueta] = doc.id_docente
                opciones.append(etiqueta)
        if hasattr(self, "combo_prestamo_solicitante"):
            self.combo_prestamo_solicitante["values"] = opciones
            self.var_prestamo_solicitante.set("")

    def _registrar_prestamo(self):
        etiqueta_libro = self.var_prestamo_libro.get()
        etiqueta_solicitante = self.var_prestamo_solicitante.get()

        if etiqueta_libro not in self._mapa_libros:
            messagebox.showwarning("Atención", "Seleccione un libro válido.")
            return
        if etiqueta_solicitante not in self._mapa_solicitantes:
            messagebox.showwarning("Atención", "Seleccione un solicitante válido.")
            return
        if not _validar_fecha(self.var_prestamo_fecha.get()) or not _validar_fecha(self.var_prestamo_fecha_est.get()):
            messagebox.showerror("Fecha inválida", "Las fechas deben tener formato DD/MM/AAAA.")
            return

        id_libro = self._mapa_libros[etiqueta_libro]
        libro = self.libro_dao.obtener_por_id(id_libro)
        if not libro or libro.disponibles <= 0:
            messagebox.showerror("Sin disponibilidad", "No hay ejemplares disponibles de este libro.")
            return

        try:
            prestamo = Prestamo(
                id_libro=id_libro,
                tipo_solicitante=self.var_prestamo_tipo.get(),
                id_solicitante=self._mapa_solicitantes[etiqueta_solicitante],
                fecha_prestamo=self.var_prestamo_fecha.get().strip(),
                fecha_devolucion_estimada=self.var_prestamo_fecha_est.get().strip(),
                estado="Prestado",
            )
            self.prestamo_dao.insertar(prestamo)
            self.libro_dao.actualizar_disponibles(id_libro, -1)
        except ValueError as error:
            messagebox.showerror("Datos inválidos", str(error))
            return
        except Exception as error:
            messagebox.showerror("Error al guardar", f"No se pudo registrar el préstamo.\n{error}")
            return

        messagebox.showinfo("Éxito", "Préstamo registrado correctamente.")
        self._refrescar_prestamos()
        self._refrescar_libros()
        self._refrescar_combobox_libros_prestamo()

    def _registrar_devolucion(self):
        seleccion = self.tabla_prestamos.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un préstamo de la lista.")
            return
        valores = self.tabla_prestamos.item(seleccion[0], "values")
        id_prestamo, estado_actual = int(valores[0]), valores[7]
        if estado_actual == "Devuelto":
            messagebox.showinfo("Información", "Este préstamo ya fue devuelto.")
            return
        confirmar = messagebox.askyesno("Confirmar devolución", "¿Confirma la devolución de este libro?")
        if not confirmar:
            return
        try:
            prestamo = self.prestamo_dao.obtener_por_id(id_prestamo)
            self.prestamo_dao.registrar_devolucion(id_prestamo, datetime.now().strftime(FORMATO_FECHA))
            if prestamo:
                self.libro_dao.actualizar_disponibles(prestamo.id_libro, 1)
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo registrar la devolución.\n{error}")
            return
        messagebox.showinfo("Éxito", "Devolución registrada correctamente.")
        self._refrescar_prestamos()
        self._refrescar_libros()
        self._refrescar_combobox_libros_prestamo()

    def _eliminar_prestamo(self):
        seleccion = self.tabla_prestamos.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un préstamo de la lista para eliminar.")
            return
        valores = self.tabla_prestamos.item(seleccion[0], "values")
        id_prestamo, estado = int(valores[0]), valores[7]
        confirmar = messagebox.askyesno("Confirmar eliminación", "¿Está seguro de eliminar este registro de préstamo?")
        if not confirmar:
            return
        try:
            prestamo = self.prestamo_dao.obtener_por_id(id_prestamo)
            self.prestamo_dao.eliminar(id_prestamo)
            if estado == "Prestado" and prestamo:
                self.libro_dao.actualizar_disponibles(prestamo.id_libro, 1)
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo eliminar el préstamo.\n{error}")
            return
        messagebox.showinfo("Éxito", "Registro eliminado correctamente.")
        self._refrescar_prestamos()
        self._refrescar_libros()
        self._refrescar_combobox_libros_prestamo()

    def _refrescar_prestamos(self):
        for fila in self.tabla_prestamos.get_children():
            self.tabla_prestamos.delete(fila)
        for p in self.prestamo_dao.obtener_todos_detallado():
            self.tabla_prestamos.insert("", "end", values=(
                p["id_prestamo"], p["titulo_libro"], p["solicitante"], p["tipo_solicitante"],
                p["fecha_prestamo"], p["fecha_devolucion_estimada"],
                p["fecha_devolucion_real"] or "-", p["estado"],
            ))

    def _exportar_prestamos_pdf(self):
        self._exportar_treeview_pdf(self.tabla_prestamos, "Listado de préstamos",
                                     ("ID", "Libro", "Solicitante", "Tipo", "F. Préstamo",
                                      "F. Dev. Estimada", "F. Dev. Real", "Estado"))

    # ==================================================================
    # TAB BÚSQUEDA AVANZADA
    # ==================================================================
    def _construir_tab_busqueda(self):
        contenedor = self.tab_busqueda

        # Igual que en la pestaña Libros: filtros a la izquierda y vista
        # previa de la tapa del libro seleccionado a la derecha.
        fila_superior = ttk.Frame(contenedor)
        fila_superior.pack(fill="x", padx=8, pady=8)

        panel_portada = ttk.LabelFrame(fila_superior, text="Portada del libro")
        panel_portada.pack(side="right", fill="y", padx=(8, 0))

        panel_filtros = ttk.LabelFrame(fila_superior, text="Filtros de búsqueda de libros")
        panel_filtros.pack(side="left", fill="both", expand=True)

        self._imagen_portada_busqueda = None
        self.lbl_portada_busqueda = self._crear_recuadro_portada(panel_portada)

        self.var_busq_titulo = tk.StringVar()
        self.var_busq_autor = tk.StringVar()
        self.var_busq_genero = tk.StringVar(value="Todos")
        self.var_busq_ciclo = tk.StringVar(value="Todos")
        self.var_busq_edad = tk.StringVar(value="Todos")
        self.var_busq_disponibles = tk.BooleanVar(value=False)
        self.var_busq_orden = tk.StringVar(value=ORDENES_BUSQUEDA[0])

        ttk.Label(panel_filtros, text="Título").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(panel_filtros, textvariable=self.var_busq_titulo, width=20).grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(panel_filtros, text="Autor").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(panel_filtros, textvariable=self.var_busq_autor, width=20).grid(row=0, column=3, padx=4, pady=4)

        ttk.Label(panel_filtros, text="Género").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        ttk.Combobox(panel_filtros, textvariable=self.var_busq_genero, values=["Todos"] + GENEROS,
                     state="readonly", width=16).grid(row=0, column=5, padx=4, pady=4)

        ttk.Label(panel_filtros, text="Ciclo").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(panel_filtros, textvariable=self.var_busq_ciclo, values=["Todos"] + CICLOS,
                     state="readonly", width=16).grid(row=1, column=1, padx=4, pady=4)

        ttk.Label(panel_filtros, text="Edad recomendada").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        ttk.Combobox(panel_filtros, textvariable=self.var_busq_edad,
                     values=["Todos", "Sin especificar"] + EDADES_RECOMENDADAS,
                     state="readonly", width=16).grid(row=1, column=3, padx=4, pady=4)

        ttk.Checkbutton(panel_filtros, text="Sólo con ejemplares disponibles",
                         variable=self.var_busq_disponibles).grid(row=1, column=4, columnspan=2, sticky="w", padx=4, pady=4)

        ttk.Label(panel_filtros, text="Ordenar por").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        combo_orden = ttk.Combobox(panel_filtros, textvariable=self.var_busq_orden,
                                    values=ORDENES_BUSQUEDA, state="readonly", width=20)
        combo_orden.grid(row=2, column=1, padx=4, pady=4)
        # Al cambiar el criterio se reordena la lista en el acto, sin tener
        # que volver a presionar "Buscar".
        combo_orden.bind("<<ComboboxSelected>>", lambda e: self._ejecutar_busqueda(avisar_si_vacio=False))

        ttk.Label(panel_filtros, text="(también puede ordenar haciendo clic en el título de cada columna)",
                  foreground="#666666").grid(row=2, column=2, columnspan=4, sticky="w", padx=4, pady=4)

        panel_botones = ttk.Frame(contenedor)
        panel_botones.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(panel_botones, text="Buscar", command=self._ejecutar_busqueda).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Limpiar filtros", command=self._limpiar_busqueda).pack(side="left", padx=4)
        ttk.Button(panel_botones, text="Exportar resultados a PDF",
                   command=self._exportar_busqueda_pdf).pack(side="right", padx=4)
        self.var_pdf_portadas_busqueda = tk.BooleanVar(value=False)
        ttk.Checkbutton(panel_botones, text="Incluir portadas en el PDF",
                         variable=self.var_pdf_portadas_busqueda).pack(side="right", padx=4)

        columnas = ("id", "titulo", "autor", "editorial", "isbn", "genero", "edad",
                    "ciclo", "stock", "disponibles", "tapa")
        encabezados = ("ID", "Título", "Autor", "Editorial", "ISBN", "Género", "Edad",
                       "Ciclo", "Stock", "Disp.", "Tapa")
        # Columnas cuyo encabezado permite reordenar los resultados, y el
        # criterio de ORDENES_BUSQUEDA al que corresponde cada una.
        orden_por_columna = {
            "id": ("ID (menor a mayor)", "ID (mayor a menor)"),
            "titulo": ("Título (A-Z)", "Título (Z-A)"),
            "autor": ("Autor (A-Z)",),
            "ciclo": ("Ciclo",),
            "genero": ("Género",),
            "edad": ("Edad recomendada",),
            "stock": ("Stock (menor a mayor)", "Stock (mayor a menor)"),
        }
        self.tabla_busqueda = ttk.Treeview(contenedor, columns=columnas, show="headings", height=13)
        for col, enc in zip(columnas, encabezados):
            if col in orden_por_columna:
                self.tabla_busqueda.heading(
                    col, text=enc,
                    command=lambda c=col: self._ordenar_por_columna(orden_por_columna[c]))
            else:
                self.tabla_busqueda.heading(col, text=enc)
            self.tabla_busqueda.column(col, width=100, anchor="center")
        self.tabla_busqueda.column("titulo", width=180, anchor="w")
        self.tabla_busqueda.column("autor", width=140, anchor="w")
        self.tabla_busqueda.column("tapa", width=60, anchor="center")
        self.tabla_busqueda.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tabla_busqueda.bind("<<TreeviewSelect>>", self._seleccionar_libro_busqueda)

    def _ordenar_por_columna(self, criterios):
        """
        Reordena los resultados al hacer clic en el encabezado de una columna.
        Si la columna admite dos sentidos (como Título A-Z / Z-A), cada clic
        alterna entre ellos.
        """
        actual = self.var_busq_orden.get()
        if actual in criterios:
            siguiente = criterios[(criterios.index(actual) + 1) % len(criterios)]
        else:
            siguiente = criterios[0]
        self.var_busq_orden.set(siguiente)
        self._ejecutar_busqueda(avisar_si_vacio=False)

    def _seleccionar_libro_busqueda(self, evento):
        """Muestra la tapa del libro elegido en los resultados de la búsqueda."""
        seleccion = self.tabla_busqueda.selection()
        if not seleccion:
            return
        valores = self.tabla_busqueda.item(seleccion[0], "values")
        try:
            id_libro = int(valores[0])
        except (ValueError, IndexError):
            return
        datos = self.libro_dao.obtener_portada(id_libro)
        self._mostrar_portada(self.lbl_portada_busqueda, datos, "_imagen_portada_busqueda")

    def _limpiar_busqueda(self):
        self.var_busq_titulo.set("")
        self.var_busq_autor.set("")
        self.var_busq_genero.set("Todos")
        self.var_busq_ciclo.set("Todos")
        self.var_busq_edad.set("Todos")
        self.var_busq_disponibles.set(False)
        self.var_busq_orden.set(ORDENES_BUSQUEDA[0])
        self._mostrar_portada(self.lbl_portada_busqueda, None, "_imagen_portada_busqueda")
        for fila in self.tabla_busqueda.get_children():
            self.tabla_busqueda.delete(fila)

    def _ejecutar_busqueda(self, avisar_si_vacio=True):
        resultados = self.libro_dao.busqueda_avanzada(
            titulo=self.var_busq_titulo.get().strip(),
            autor=self.var_busq_autor.get().strip(),
            genero=self.var_busq_genero.get(),
            ciclo=self.var_busq_ciclo.get(),
            edad=self.var_busq_edad.get(),
            solo_disponibles=self.var_busq_disponibles.get(),
            orden=self.var_busq_orden.get(),
        )
        for fila in self.tabla_busqueda.get_children():
            self.tabla_busqueda.delete(fila)
        for libro in resultados:
            self.tabla_busqueda.insert("", "end", values=(
                libro.id_libro, libro.titulo, libro.autor, libro.editorial, libro.isbn,
                libro.genero, libro.edad_recomendada, libro.ciclo, libro.stock, libro.disponibles,
                "Sí" if libro.tiene_portada() else "-",
            ))
        self._mostrar_portada(self.lbl_portada_busqueda, None, "_imagen_portada_busqueda")
        if not resultados and avisar_si_vacio:
            messagebox.showinfo("Búsqueda", "No se encontraron libros con esos criterios.")

    def _exportar_busqueda_pdf(self):
        self._exportar_treeview_pdf(self.tabla_busqueda, "Resultados de búsqueda avanzada",
                                     ("ID", "Título", "Autor", "Editorial", "ISBN",
                                      "Género", "Edad", "Ciclo", "Stock", "Disp.", "Tapa"),
                                     incluir_portadas=self.var_pdf_portadas_busqueda.get())

    # ==================================================================
    # Exportación a PDF (genérica, a partir de cualquier Treeview)
    # ==================================================================
    def _exportar_treeview_pdf(self, treeview, titulo_reporte, encabezados,
                                incluir_portadas=False):
        """
        Genera el PDF con las filas que se están viendo en la tabla indicada.

        Si 'incluir_portadas' es True, se agrega al comienzo de cada fila la
        imagen pequeña de la tapa del libro (la primera columna de la tabla
        debe ser el ID del libro).
        """
        filas = [treeview.item(item, "values") for item in treeview.get_children()]
        if not filas:
            messagebox.showwarning("Sin datos", "No hay registros para exportar.")
            return

        nombre_sugerido = titulo_reporte.lower().replace(" ", "_") + ".pdf"
        destino = filedialog.asksaveasfilename(
            title="Guardar PDF", defaultextension=".pdf",
            initialfile=nombre_sugerido, filetypes=[("Archivo PDF", "*.pdf")],
        )
        if not destino:
            return

        miniaturas = self._obtener_miniaturas(filas) if incluir_portadas else None

        try:
            ExportadorPDF.exportar(destino, titulo_reporte, list(encabezados), filas,
                                    imagenes=miniaturas)
        except Exception as error:
            messagebox.showerror("Error al exportar", f"No se pudo generar el PDF.\n{error}")
            return
        messagebox.showinfo("Exportación completa", f"PDF generado correctamente en:\n{destino}")

    def _obtener_miniaturas(self, filas):
        """
        Devuelve una lista, del mismo largo que 'filas', con la miniatura de
        la portada de cada libro (o None si no tiene). El ID del libro se
        toma de la primera columna de cada fila.
        """
        miniaturas = []
        for fila in filas:
            datos = None
            try:
                datos = self.libro_dao.obtener_portada(int(fila[0]))
            except (ValueError, TypeError, IndexError):
                datos = None
            miniaturas.append(imagenes.miniatura_para_pdf(datos))
        return miniaturas

"""Regresiones de listados, columnas visibles y PDF. GUI con DISPLAY disponible."""
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz
from PIL import Image

import cdd
from conexion import ConexionDB
from dao import LibroDAO
from exportador_pdf import ExportadorPDF
from gui import AplicacionBiblioteca
from modelos import Libro, CICLOS


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Requiere pantalla o Xvfb')
class ListadosPDFTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original = ConexionDB._ruta_base_datos
        ConexionDB._ruta_base_datos = str(Path(self.tmp.name) / 'biblioteca.db')
        ConexionDB.inicializar_base_datos()
        cdd.inicializar()
        buffer = io.BytesIO()
        Image.new('RGB', (120, 180), '#477979').save(buffer, 'JPEG')
        dao = LibroDAO()
        self.id = dao.insertar(Libro('Sociedad, cultura y educación', 'Autora & colaborador',
            'Divulgación', '', 'Tercer Ciclo', 3, editorial='Editorial de prueba',
            isbn='9781234567897', portada=buffer.getvalue()), codigo_cdd='306.43')
        dao.insertar(Libro('Matemática para aprender', 'Otro autor', 'Otro', '',
                          'Segundo Ciclo', 2), codigo_cdd='372.7')
        dao.insertar(Libro('Libro sin notación', 'Tercer autor', 'Cuento', '',
                          'Inicial', 1))
        self.app = AplicacionBiblioteca()
        self.app._ejecutar_busqueda(avisar_si_vacio=False)
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        ConexionDB._ruta_base_datos = self.original
        self.tmp.cleanup()

    def menu_busqueda(self):
        def recorrer(widget):
            for hijo in widget.winfo_children():
                yield hijo
                yield from recorrer(hijo)
        boton = next(w for w in recorrer(self.app.tab_busqueda)
                     if w.winfo_class() == 'TMenubutton')
        return self.app.nametowidget(boton['menu'])

    def ocultar(self, *columnas):
        tabla = self.app.tabla_busqueda
        menu = self.menu_busqueda()
        for col in columnas:
            menu.invoke(tuple(tabla['columns']).index(col))

    def test_columnas_cdd_ciclo_y_seleccion(self):
        self.assertIn('Tercer Ciclo', CICLOS)
        for tabla in [self.app.tabla_libros, self.app.tabla_busqueda]:
            filas = [tabla.item(i, 'values') for i in tabla.get_children()]
            fila = next(f for f in filas if int(f[0]) == self.id)
            self.assertEqual(fila[11:13], ('306.43', 'Sociología de la educación'))
        self.app.var_busq_ciclo.set('Tercer Ciclo')
        self.app._ejecutar_busqueda(False)
        self.assertEqual(len(self.app.tabla_busqueda.get_children()), 1)
        self.app.tabla_libros.selection_set(next(i for i in self.app.tabla_libros.get_children()
            if int(self.app.tabla_libros.item(i, 'values')[0]) == self.id))
        self.app._seleccionar_libro(None)
        self.assertEqual(self.app.var_libro_cdd.get(), '306.43')
        self.assertEqual(self.app.var_libro_ciclo.get(), 'Tercer Ciclo')

    def test_menu_no_deja_ocultar_todas_y_restaurar(self):
        tabla = self.app.tabla_busqueda
        menu = self.menu_busqueda()
        for col in tabla['columns']:
            menu.invoke(tuple(tabla['columns']).index(col))
        self.assertEqual(len(tabla['displaycolumns']), 1)
        menu.invoke(len(tabla['columns']) + 1)
        self.assertEqual(tuple(tabla['displaycolumns']), tuple(tabla['columns']))
        self.ocultar('isbn', 'edad')
        antes = tuple(tabla['displaycolumns'])
        self.app._limpiar_busqueda()
        self.app._ejecutar_busqueda(False)
        self.assertEqual(tuple(tabla['displaycolumns']), antes)

    def test_pdf_solo_columnas_visibles_con_portadas_e_id_oculto(self):
        self.ocultar('id', 'isbn', 'edad', 'editorial', 'tapa', 'stock', 'disponibles')
        destino = str(Path(self.tmp.name) / 'columnas_visibles.pdf')
        self.app.var_pdf_portadas_busqueda.set(True)
        with patch('gui.filedialog.asksaveasfilename', return_value=destino), \
             patch('gui.messagebox.showinfo'), patch('gui.messagebox.showerror') as error, \
             patch.object(self.app.libro_dao, 'obtener_portada', wraps=self.app.libro_dao.obtener_portada) as portadas:
            self.app._exportar_busqueda_pdf()
        error.assert_not_called()
        self.assertIn(self.id, [c.args[0] for c in portadas.call_args_list])
        with fitz.open(destino) as pdf:
            texto = ''.join(p.get_text() for p in pdf)
            for oculto in ['ISBN', 'Edad', '9781234567897', 'Editorial de prueba']:
                self.assertNotIn(oculto, texto)
            self.assertIn('306.43', texto)
            self.assertIn('Sociología', texto)
            self.assertIn('Tercer Ciclo', texto)
            self.assertTrue(any(p.get_images() for p in pdf))
            for pagina in pdf:
                for palabra in pagina.get_text('words'):
                    self.assertGreaterEqual(palabra[0], 35)
                    self.assertLessEqual(palabra[2], pagina.rect.width - 35)

    def test_pdf_catalogo_completo_y_una_columna(self):
        for columnas in [('cdd',), tuple(self.app.tabla_libros['columns'])]:
            self.app.tabla_libros.configure(displaycolumns=columnas)
            destino = str(Path(self.tmp.name) / 'catalogo.pdf')
            with patch('gui.filedialog.asksaveasfilename', return_value=destino), \
                 patch('gui.messagebox.showinfo'), patch('gui.messagebox.showerror') as error:
                self.app._exportar_libros_pdf()
            error.assert_not_called()
            with fitz.open(destino) as pdf:
                self.assertIn('306.43', ''.join(p.get_text() for p in pdf))


class AmpliacionCatalogoTest(unittest.TestCase):
    def test_nuevos_codigos_fuentes_y_no_equivalencias_inventadas(self):
        tmp = tempfile.TemporaryDirectory()
        original = ConexionDB._ruta_base_datos
        try:
            ConexionDB._ruta_base_datos = str(Path(tmp.name) / 'biblioteca.db')
            ConexionDB.inicializar_base_datos()
            cdd.inicializar()
            for codigo, descripcion in [('306.43', 'Sociología de la educación'),
                ('A861', 'Poesía argentina'), ('A862', 'Teatro argentino'),
                ('A864', 'Ensayo argentino'), ('A863.9282', 'Narrativa infantil y juvenil argentina'),
                ('R37', 'Diccionarios de educación'), ('RE37', 'Enciclopedias de educación'),
                ('560', 'Paleontología y animales prehistóricos'),
                ('371.10251', 'Didáctica de las matemáticas')]:
                self.assertEqual(cdd.clasificar(codigo).descripcion, descripcion)
                self.assertTrue(cdd.clasificar(codigo).fuente)
            self.assertEqual(cdd.clasificar('X306.43').estado, 'pendiente')
        finally:
            ConexionDB._ruta_base_datos = original
            tmp.cleanup()

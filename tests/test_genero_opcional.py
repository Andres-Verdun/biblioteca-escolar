import tempfile
import unittest
from pathlib import Path

import cdd
from conexion import ConexionDB
from dao import LibroDAO
from modelos import Libro


class GeneroOpcionalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ruta_original = ConexionDB._ruta_base_datos
        ConexionDB._ruta_base_datos = str(Path(self.tmp.name) / 'biblioteca.db')
        ConexionDB.inicializar_base_datos()
        cdd.inicializar()
        self.dao = LibroDAO()

    def tearDown(self):
        ConexionDB._ruta_base_datos = self.ruta_original
        self.tmp.cleanup()

    def libro(self, genero):
        return Libro('Un libro', 'Una autora', genero, '', 'Primer Ciclo', 2)

    def test_alta_sin_genero(self):
        for genero in ['', None, '   ']:
            id_libro = self.dao.insertar(self.libro(genero))
            self.assertEqual(self.dao.obtener_por_id(id_libro).genero, '')
        self.assertEqual(len(self.dao.busqueda_avanzada(genero='Todos')), 3)

    def test_quitar_genero_sin_alterar_notacion(self):
        id_libro = self.dao.insertar(self.libro('Cuento'), codigo_cdd='863.9282')
        libro = self.dao.obtener_por_id(id_libro)
        libro.genero = ''
        self.dao.actualizar(libro)
        recuperado = self.dao.obtener_por_id(id_libro)
        self.assertEqual(recuperado.genero, '')
        self.assertEqual(recuperado.stock, 2)
        self.assertEqual(cdd.obtener(id_libro), '863.9282')
        self.assertEqual(len(self.dao.busqueda_avanzada(genero='Cuento')), 0)
        recuperado.genero = 'Novela'
        self.dao.actualizar(recuperado)
        self.assertEqual(len(self.dao.busqueda_avanzada(genero='Novela')), 1)


if __name__ == '__main__':
    unittest.main()

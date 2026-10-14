import csv
import tempfile
import unittest
from pathlib import Path

import cdd
from conexion import ConexionDB
from dao import LibroDAO
from modelos import Libro


class NotacionesCDDTest(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta_original = ConexionDB._ruta_base_datos
        ConexionDB._ruta_base_datos = str(Path(self.temporal.name) / 'biblioteca.db')
        ConexionDB.inicializar_base_datos()
        cdd.inicializar()

    def tearDown(self):
        ConexionDB._ruta_base_datos = self.ruta_original
        self.temporal.cleanup()

    def libro(self, **kwargs):
        return Libro('Un libro', 'Una autora', 'Cuento', '', 'Primer Ciclo', 2, **kwargs)

    def test_normalizacion_y_notaciones_compuestas(self):
        for entrada, esperado in [('re030', 'RE 030'), (' r 806.0 - 3 ', 'R 806.0-3'),
                                  ('3-e372.4', '3-E 372.4'), ('L347.91/95', 'L 347.91/95'),
                                  ('R929[82]', 'R 929[82]'), ('A863', 'A 863')]:
            with self.subTest(entrada=entrada):
                self.assertEqual(cdd.normalizar(entrada), esperado)
        for invalida in ['863.', '1234', 'RE', 'R 8..3', '3-E 372.4 BAL', 'R 929[82', 'R -343']:
            self.assertFalse(cdd.codigo_valido(invalida), invalida)
        self.assertTrue(cdd.codigo_valido(''))

    def test_clasificaciones_y_sectores_no_se_confunden(self):
        casos = [('RE030', 'Enciclopedias generales'), ('R806.0-3', 'Diccionarios de español y lexicología'),
                 ('L343', 'Código penal'), ('S511', 'Matemáticas'), ('E372.4', 'Libros de lectura'),
                 ('1-E 51', 'Matemáticas'), ('PL681.3', 'Informática'), ('863.9932', 'Narrativa argentina')]
        for codigo, descripcion in casos:
            with self.subTest(codigo=codigo):
                resultado = cdd.clasificar(codigo)
                self.assertEqual(resultado.estado, 'exacta')
                self.assertEqual(resultado.descripcion, descripcion)
        self.assertEqual(cdd.clasificar('800').descripcion, 'Literatura')
        self.assertIn('lingüística', cdd.clasificar('R800').descripcion)
        self.assertEqual(cdd.clasificar('R863').estado, 'pendiente')
        self.assertEqual(cdd.clasificar('A863').estado, 'pendiente')
        general = cdd.clasificar('863.9282')
        self.assertEqual(general.estado, 'general')
        self.assertEqual(general.codigo_base, '800')
        self.assertIn('requiere revisión', general.texto())

    def test_actualizacion_de_catalogo_preserva_datos_previos(self):
        id_libro = LibroDAO().insertar(self.libro())
        # Simula notación guardada con la versión anterior, sin normalización.
        with ConexionDB.conectar() as con:
            con.execute('INSERT INTO libro_cdd VALUES (?,?)', (id_libro, 'A863'))
            con.execute("UPDATE cdd_bnm SET descripcion='Descripción vieja' WHERE codigo='RE 030'")
        cdd.inicializar()
        cdd.inicializar()
        self.assertEqual(cdd.obtener(id_libro), 'A863')
        self.assertEqual(cdd.consultar('RE030')[0], 'Enciclopedias generales')
        self.assertEqual(LibroDAO().obtener_por_id(id_libro).stock, 2)

    def test_guardado_modificacion_borrado_y_cascada(self):
        dao = LibroDAO()
        id_libro = dao.insertar(self.libro(), codigo_cdd='re030')
        self.assertEqual(cdd.obtener(id_libro), 'RE 030')
        dao.actualizar(self.libro(id_libro=id_libro), codigo_cdd='863.9932')
        self.assertEqual(cdd.obtener(id_libro), '863.9932')
        dao.actualizar(self.libro(id_libro=id_libro), codigo_cdd='')
        self.assertEqual(cdd.obtener(id_libro), '')
        cdd.guardar(id_libro, 'L343')
        dao.eliminar(id_libro)
        self.assertEqual(cdd.obtener(id_libro), '')

    def test_transaccion_no_deja_libros_parcialmente_guardados(self):
        dao = LibroDAO()
        with self.assertRaises(ValueError):
            dao.insertar(self.libro(), codigo_cdd='inválido')
        self.assertEqual(dao.obtener_todos(), [])
        id_libro = dao.insertar(self.libro(), codigo_cdd='RE030')
        modificado = self.libro(id_libro=id_libro)
        modificado.titulo = 'Otro título'
        with self.assertRaises(ValueError):
            dao.actualizar(modificado, codigo_cdd='863.')
        self.assertEqual(dao.obtener_por_id(id_libro).titulo, 'Un libro')
        self.assertEqual(cdd.obtener(id_libro), 'RE 030')

    def test_catalogo_busqueda_y_formato(self):
        with open(cdd._ruta_recurso('cdd_bnm.csv'), encoding='utf-8', newline='') as f:
            filas = list(csv.DictReader(f))
        codigos = [cdd.normalizar(f['codigo']) for f in filas]
        self.assertEqual(len(codigos), len(set(codigos)))
        self.assertEqual(len(cdd.catalogo()), len(filas))
        self.assertEqual(cdd.catalogo('NARRATIVA ARGENTINA')[0][0], '863.9932')
        self.assertEqual(cdd.catalogo('sin resultados improbables'), [])


if __name__ == '__main__':
    unittest.main()

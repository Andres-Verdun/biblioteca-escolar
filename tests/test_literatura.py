"""Equivalencias literarias, notaciones escolares y actualización de bases existentes."""
import csv
import tempfile
import unittest
from pathlib import Path

import cdd
from conexion import ConexionDB
from dao import LibroDAO
from modelos import Libro


class LiteraturaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original = ConexionDB._ruta_base_datos
        ConexionDB._ruta_base_datos = str(Path(self.tmp.name) / 'biblioteca.db')
        ConexionDB.inicializar_base_datos()
        cdd.inicializar()

    def tearDown(self):
        ConexionDB._ruta_base_datos = self.original
        self.tmp.cleanup()

    def test_formas_literarias_y_lenguas(self):
        casos = {
            '808.87': 'Humor y sátira',
            '808.88': 'Antologías y refranes',
            '808.0681': 'Poesía infantil',
            '808.0682': 'Teatro infantil',
            '813': 'Narrativa estadounidense en inglés',
            '822': 'Teatro inglés',
            '833': 'Narrativa alemana',
            '843': 'Narrativa francesa',
            '853': 'Narrativa italiana',
            '864.9932': 'Ensayos argentinos',
            '860.9921': 'Literatura mexicana',
            '860.9933': 'Literatura chilena',
            '869.8992': 'Literatura brasileña',
            '897': 'Literatura amerindia',
            'A866': 'Cartas argentinas',
            'A863.08': 'Antologías de narrativa argentina',
        }
        for codigo, descripcion in casos.items():
            with self.subTest(codigo=codigo):
                resultado = cdd.clasificar(codigo)
                self.assertEqual(resultado.estado, 'exacta')
                self.assertEqual(resultado.texto(), descripcion)
                self.assertTrue(resultado.fuente)
                self.assertNotIn('PDF', resultado.texto())

    def test_notaciones_escolares_con_auxiliares(self):
        for codigo, esperado in [('s860[82]-1', 'Poesía argentina'),
                                 ('S860[82]-2', 'Teatro argentino'),
                                 ('S 860[82]-3', 'Narrativa argentina'),
                                 ('s860[7/8]', 'Literatura latinoamericana')]:
            resultado = cdd.clasificar(codigo)
            self.assertEqual(resultado.estado, 'exacta')
            self.assertEqual(resultado.descripcion, esperado)
            self.assertEqual(resultado.sector, 'Enseñanza secundaria')
        for invalido in ['S 860[82]-', 'S 860[7/]', 'S 860[82]-X', 'S 860[82', 'S 860[[82]]-1']:
            self.assertFalse(cdd.codigo_valido(invalido), invalido)

    def test_no_se_confunden_bnm_cdd_y_prefijos(self):
        # Preservar las adaptaciones históricas aunque otros sumarios difieran.
        self.assertEqual(cdd.clasificar('804').descripcion, 'Colecciones de cuentos')
        self.assertEqual(cdd.clasificar('868').descripcion, 'Antologías de literatura española')
        self.assertEqual(cdd.clasificar('R 800').descripcion, 'Diccionarios de lingüística y señales')
        self.assertEqual(cdd.clasificar('A863').descripcion, 'Narrativa argentina')
        self.assertEqual(cdd.clasificar('863').descripcion, 'Narrativa española')
        self.assertEqual(cdd.clasificar('S 861').descripcion, 'Literatura española y latinoamericana')
        self.assertEqual(cdd.clasificar('861').descripcion, 'Poesía española')
        self.assertEqual(cdd.clasificar('X813').estado, 'pendiente')
        self.assertEqual(cdd.clasificar('A813').estado, 'pendiente')
        self.assertEqual(cdd.clasificar('843.123456').estado, 'general')
        self.assertEqual(cdd.clasificar('843.123456').codigo_base, '843')

    def test_ampliacion_reconoce_libros_ya_guardados(self):
        dao = LibroDAO()
        id_libro = dao.insertar(Libro('Una obra', 'Autora', 'Poesía', '', 'Primer Ciclo', 2),
                                codigo_cdd='808.0681')
        con = ConexionDB.conectar()
        try:
            with con: con.execute("DELETE FROM cdd_bnm WHERE codigo='808.0681'")
        finally:
            ConexionDB.cerrar(con)
        self.assertEqual(cdd.clasificar(cdd.obtener(id_libro)).estado, 'general')
        cdd.inicializar()
        cdd.inicializar()
        self.assertEqual(cdd.clasificar(cdd.obtener(id_libro)).texto(), 'Poesía infantil')
        self.assertEqual(dao.obtener_por_id(id_libro).stock, 2)
        self.assertEqual(cdd.obtener(id_libro), '808.0681')

    def test_fuentes_y_busqueda_del_catalogo(self):
        self.assertIn('oclc.org', cdd.clasificar('813').fuente)
        self.assertIn('bnm.educacion.gob.ar', cdd.clasificar('864.9932').fuente)
        self.assertIn('upla.cl', cdd.clasificar('808.0682').fuente)
        self.assertIn('808.0682', {f[0] for f in cdd.catalogo('TEATRO INFANTIL')})
        with open(cdd._ruta_recurso('cdd_bnm.csv'), encoding='utf-8', newline='') as f:
            filas = list(csv.DictReader(f))
        self.assertEqual(len(filas), len({cdd.normalizar(f['codigo']) for f in filas}))
        for fila in filas:
            self.assertTrue(fila['descripcion'])
            self.assertTrue(fila['fuente'] or fila['pagina'])


if __name__ == '__main__':
    unittest.main()

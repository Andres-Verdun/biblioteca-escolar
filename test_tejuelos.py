"""Pruebas del generador de tejuelos (ejecutar: python -m unittest test_tejuelos)."""

import os
import tempfile
import unittest

from tejuelos import generar_tejuelos_pdf, sigla_autor


class TestTejuelos(unittest.TestCase):
    def test_autores(self):
        ejemplos = {
            "Jorge Luis Borges": "BOR",
            "Borges, Jorge Luis": "BOR",
            "García Márquez, Gabriel": "GAR",
            "Gabriel García Márquez": "MAR",
            "María Elena Walsh": "WAL",
            "Saint-Exupéry, Antoine de": "SAI",
            "de la Cruz, Juan": "CRU",
        }
        for autor, esperado in ejemplos.items():
            with self.subTest(autor=autor):
                self.assertEqual(sigla_autor(autor), esperado)

    def test_sin_autor(self):
        with self.assertRaises(ValueError):
            sigla_autor(" ")

    def test_pdf(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "tejuelos.pdf")
            registros = [
                {"cdd": "863", "autor": "Jorge Luis Borges", "id_libro": 42, "stock": 2},
                {"cdd": "", "autor": "María Elena Walsh", "id_libro": 4, "stock": 1},
            ]
            self.assertEqual(generar_tejuelos_pdf(ruta, registros, True, True), 2)
            with open(ruta, "rb") as archivo:
                self.assertEqual(archivo.read(4), b"%PDF")
            self.assertGreater(os.stat(ruta).st_size, 1500)

    def test_sin_cdd(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with self.assertRaises(ValueError):
                generar_tejuelos_pdf(os.path.join(carpeta, "x.pdf"),
                                     [{"cdd": "", "autor": "Borges"}])


if __name__ == "__main__":
    unittest.main()

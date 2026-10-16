"""Rutas de datos y persistencia entre instalaciones, sin usar datos reales."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import conexion
from conexion import ConexionDB
from dao import LibroDAO
from modelos import Libro
import cdd
import organizacion as org


class InstalacionTest(unittest.TestCase):
    def test_script_conserva_base_del_proyecto(self):
        with patch.object(sys,'frozen',False,create=True):
            self.assertEqual(conexion._obtener_directorio_base(),str(Path(conexion.__file__).parent))

    def test_windows_empaquetado_separa_datos_y_programa(self):
        with tempfile.TemporaryDirectory(prefix='Biblioteca con espacios ') as tmp:
            for ejecutable in ('version1/BibliotecaEscolar.exe','version2/BibliotecaEscolar.exe'):
                with patch.object(sys,'frozen',True,create=True),patch.object(sys,'platform','win32'),patch.object(sys,'executable',str(Path(tmp)/ejecutable)),patch.dict(os.environ,{'LOCALAPPDATA':tmp}):
                    self.assertEqual(conexion._obtener_directorio_base(),str(Path(tmp)/'BibliotecaEscolar360'))

    def test_fallback_sin_localappdata(self):
        with patch.object(sys,'frozen',True,create=True),patch.object(sys,'platform','win32'),patch.dict(os.environ,{},clear=True),patch('os.path.expanduser',return_value='/perfil'):
            self.assertEqual(conexion._obtener_directorio_base(),os.path.join('/perfil','AppData','Local','BibliotecaEscolar360'))

    def test_actualizar_conserva_catalogo_portada_y_ubicaciones(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta=str(Path(tmp)/'datos nuevos'/'biblioteca.db')
            with patch.object(ConexionDB,'_ruta_base_datos',ruta):
                ConexionDB.inicializar_base_datos();cdd.inicializar();org.inicializar()
                lugar=org.crear_ubicacion('B1-E1')
                libro=Libro('Libro conservado','Autora','','','Tercer Ciclo',2,portada=b'portada de prueba')
                id_libro=LibroDAO().insertar(libro,codigo_cdd='A863',organizacion=dict(id_ubicacion=lugar,etiqueta='cuento',franjas=[]))
                for _ in range(2):
                    ConexionDB.inicializar_base_datos();cdd.inicializar();org.inicializar()
                guardado=LibroDAO().obtener_por_id(id_libro)
                self.assertEqual(guardado.titulo,'Libro conservado')
                self.assertEqual(guardado.portada,b'portada de prueba')
                self.assertEqual(cdd.obtener(id_libro),'A 863')
                self.assertEqual(org.obtener(id_libro)['ubicacion'],'B1-E1')
                self.assertEqual(org.obtener(id_libro)['etiqueta'],'cuento')


if __name__=='__main__':unittest.main()

import tempfile
import shutil
import unittest
from pathlib import Path
import fitz
import cdd
import organizacion as org
from conexion import ConexionDB
from dao import LibroDAO
from modelos import Libro
from etiquetas_pdf import generar, ANCHO, ALTO, POR_PAGINA


class OrganizacionTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.original=ConexionDB._ruta_base_datos
        ConexionDB._ruta_base_datos=str(Path(self.tmp.name)/'biblioteca.db')
        ConexionDB.inicializar_base_datos()
        cdd.inicializar()
        self.dao=LibroDAO()
        # Simula base anterior sin ubicaciones ni etiquetas.
        self.id=self.dao.insertar(Libro('Libro anterior','Una autora','','','Tercer Ciclo',3), codigo_cdd='863.9282')
        org.inicializar()

    def tearDown(self):
        ConexionDB._ruta_base_datos=self.original
        self.tmp.cleanup()

    def test_migracion_idempotente_y_portabilidad(self):
        org.inicializar()
        org.inicializar()
        self.assertEqual(self.dao.obtener_por_id(self.id).stock,3)
        self.assertEqual(cdd.obtener(self.id),'863.9282')
        self.assertEqual(org.obtener(self.id)['ubicacion'],'')
        ubicacion=org.crear_ubicacion('Estante azul')
        org.guardar(self.id,ubicacion,'novela_policial')
        org.inicializar()
        self.assertEqual(org.obtener(self.id)['id_ubicacion'],ubicacion)
        self.assertEqual(org.listar_ubicaciones()[0]['libros'],1)
        copia=str(Path(self.tmp.name)/'copia.db')
        shutil.copy(ConexionDB._ruta_base_datos,copia)
        ConexionDB._ruta_base_datos=copia
        org.inicializar()
        self.assertEqual(org.obtener(self.id)['ubicacion'],'Estante azul')
        self.assertEqual(cdd.obtener(self.id),'863.9282')

    def test_ubicaciones_nombres_duplicados_renombrar_y_eliminar(self):
        ubicacion=org.crear_ubicacion('  Estante   azul ')
        for nombre in ['ESTANTE AZUL','estante azul']:
            with self.assertRaises(ValueError):org.crear_ubicacion(nombre)
        org.guardar(self.id,ubicacion,'cuento')
        org.renombrar_ubicacion(ubicacion,'Rincón de cuentos')
        self.assertEqual(org.obtener(self.id)['ubicacion'],'Rincón de cuentos')
        with self.assertRaises(ValueError):org.eliminar_ubicacion(ubicacion)
        org.guardar(self.id,etiqueta='cuento')
        org.eliminar_ubicacion(ubicacion)
        self.assertEqual(org.listar_ubicaciones(),[])
        self.assertEqual(org.obtener(self.id)['etiqueta'],'cuento')

    def test_filtros_ubicacion_color_y_sin_asignar(self):
        ubicacion=org.crear_ubicacion('Mueble 1')
        otro=self.dao.insertar(Libro('Otro','Autor','','','Inicial',1),codigo_cdd='863.9282',
            organizacion=dict(id_ubicacion=ubicacion,etiqueta='cuento',franjas=[]))
        org.guardar(self.id,ubicacion,'novela_policial')
        self.assertEqual(len(self.dao.busqueda_avanzada(ubicacion_id=ubicacion)),2)
        self.assertEqual([l.id_libro for l in self.dao.busqueda_avanzada(etiqueta='cuento')],[otro])
        org.guardar(self.id)
        self.assertEqual([l.id_libro for l in self.dao.busqueda_avanzada(ubicacion_id=0,etiqueta='')],[self.id])
        self.assertEqual(cdd.obtener(self.id),cdd.obtener(otro))

    def test_atomicidad_y_cascada(self):
        ubicacion=org.crear_ubicacion('Sala')
        libro=self.dao.obtener_por_id(self.id)
        libro.titulo='Cambio que debe revertirse'
        with self.assertRaises(ValueError):
            self.dao.actualizar(libro,codigo_cdd='372.7',organizacion=dict(id_ubicacion=999999,etiqueta='cuento',franjas=[]))
        self.assertEqual(self.dao.obtener_por_id(self.id).titulo,'Libro anterior')
        self.assertEqual(cdd.obtener(self.id),'863.9282')
        org.guardar(self.id,ubicacion,'teatro')
        self.dao.eliminar(self.id)
        self.assertNotIn(self.id,org.obtener_todos())
        org.eliminar_ubicacion(ubicacion)

    def test_franjas_y_colores_independientes_del_genero_cdd(self):
        with self.assertRaises(ValueError):org.guardar(self.id,etiqueta='antologia')
        org.guardar(self.id,etiqueta='antologia',franjas=['amarillo','verde','amarillo'])
        self.assertEqual(org.obtener(self.id)['franjas'],['amarillo','verde'])
        self.assertEqual(len(org.paleta('antologia',org.obtener(self.id)['franjas'])),2)
        org.guardar(self.id,etiqueta='novela_policial',franjas=['verde'])
        self.assertEqual(org.obtener(self.id)['franjas'],[])
        self.assertEqual(org.ETIQUETAS['novela_policial'][2],'P')
        self.assertEqual(org.ETIQUETAS['cuento_terror'][2],'T')
        self.assertEqual(self.dao.obtener_por_id(self.id).genero,'')
        self.assertEqual(cdd.obtener(self.id),'863.9282')
        with self.assertRaises(ValueError):org.guardar(self.id,etiqueta='desconocida')

    def test_pdf_medidas_cantidad_y_salto_de_pagina(self):
        ruta=str(Path(self.tmp.name)/'etiquetas.pdf')
        item=dict(titulo='Novela de prueba',codigo='A863',ubicacion='Estante azul',etiqueta='novela_policial',franjas=[])
        generar(ruta,[item]*(POR_PAGINA+1))
        with fitz.open(ruta) as pdf:
            self.assertEqual(len(pdf),2)
            total=0
            for pagina in pdf:
                rectangulos=[d['rect'] for d in pagina.get_drawings()
                    if abs(d['rect'].width-ANCHO)<.01 and abs(d['rect'].height-ALTO)<.01 and d['color'] is not None]
                total+=len(rectangulos)
                for rect in rectangulos:
                    self.assertGreater(rect.x0,0)
                    self.assertGreater(rect.y0,0)
                    self.assertLess(rect.x1,pagina.rect.width)
                    self.assertLess(rect.y1,pagina.rect.height-15)
                self.assertIn('CDD: A863',pagina.get_text())
                self.assertIn('Estante azul',pagina.get_text())
            self.assertEqual(total,POR_PAGINA+1)

    def test_pdf_antologia_textos_largos_y_datos_vacios(self):
        ruta=str(Path(self.tmp.name)/'antologia.pdf')
        generar(ruta,[dict(titulo='Un título muy largo '*30,codigo='863.9282',ubicacion='Un lugar '*35,
            etiqueta='antologia',franjas=['verde','naranja','fucsia']),dict(titulo='Sin datos')])
        with fitz.open(ruta) as pdf:
            self.assertEqual(len(pdf),1)
            self.assertIn('Sin ubicación',pdf[0].get_text())
            self.assertIn('Antologías',pdf[0].get_text())
            for palabra in pdf[0].get_text('words'):
                self.assertGreaterEqual(palabra[0],0)
                self.assertLessEqual(palabra[2],pdf[0].rect.width)
        with self.assertRaises(ValueError):generar(ruta,[])


if __name__=='__main__':unittest.main()

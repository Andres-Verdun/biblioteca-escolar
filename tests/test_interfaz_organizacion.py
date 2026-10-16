import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import fitz
import cdd
import organizacion as org
from conexion import ConexionDB
from dao import LibroDAO
from gui import AplicacionBiblioteca
from modelos import Libro


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requiere pantalla o Xvfb')
class InterfazOrganizacionTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.original=ConexionDB._ruta_base_datos
        ConexionDB._ruta_base_datos=str(Path(self.tmp.name)/'biblioteca.db')
        ConexionDB.inicializar_base_datos()
        cdd.inicializar()
        self.id=LibroDAO().insertar(Libro('Una novela','Autora','','','Tercer Ciclo',2),codigo_cdd='863.9282')
        self.app=AplicacionBiblioteca()
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        ConexionDB._ruta_base_datos=self.original
        self.tmp.cleanup()

    def test_crear_asignar_filtrar_y_reabrir_libro(self):
        a=self.app
        a.var_nombre_ubicacion.set('Estante azul')
        a._crear_ubicacion()
        uid=org.listar_ubicaciones()[0]['id_ubicacion']
        iid=a.tabla_libros.get_children()[0]
        a.tabla_libros.selection_set(iid)
        a._seleccionar_libro(None)
        a.var_libro_ubicacion.set('Estante azul')
        a.var_libro_etiqueta.set(org.nombre_etiqueta('novela_policial'))
        a.es_administrador=True
        with patch('gui.messagebox.showinfo'),patch('gui.messagebox.showerror') as error:
            a._modificar_libro()
        error.assert_not_called()
        self.assertEqual(org.obtener(self.id)['id_ubicacion'],uid)
        self.assertEqual(org.obtener(self.id)['etiqueta'],'novela_policial')
        a.var_busq_ubicacion.set('Estante azul')
        a.var_busq_etiqueta.set(org.nombre_etiqueta('novela_policial'))
        a._ejecutar_busqueda(False)
        filas=[a.tabla_busqueda.item(i,'values') for i in a.tabla_busqueda.get_children()]
        self.assertEqual(len(filas),1)
        self.assertEqual(filas[0][13:15],('Estante azul',org.nombre_etiqueta('novela_policial')))
        self.assertEqual(cdd.obtener(self.id),'863.9282')
        self.assertEqual(a.tabla_ubicaciones.item(str(uid),'values')[1],'1')
        a.tabla_libros.selection_set(a.tabla_libros.get_children()[0])
        a._seleccionar_libro(None)
        self.assertEqual(a.var_libro_ubicacion.get(),'Estante azul')
        self.assertEqual(a.var_libro_etiqueta.get(),org.nombre_etiqueta('novela_policial'))

    def test_cdd_asigna_etiqueta_y_respeta_correccion_manual(self):
        a=self.app
        a._limpiar_form_libro()
        a.var_libro_cdd.set('861.9282')
        self.assertEqual(a.var_libro_etiqueta.get(),org.nombre_etiqueta('poesia'))
        a.var_libro_cdd.set('862.9282')
        self.assertEqual(a.var_libro_etiqueta.get(),org.nombre_etiqueta('teatro'))
        a.var_libro_etiqueta.set(org.nombre_etiqueta('cuento_terror'))
        a.var_libro_cdd.set('863.9282')
        self.assertEqual(a.var_libro_etiqueta.get(),org.nombre_etiqueta('cuento_terror'))
        a._usar_etiqueta_cdd()
        self.assertEqual(a.var_libro_etiqueta.get(),org.nombre_etiqueta('novela'))
        a.var_libro_cdd.set('370')
        self.assertEqual(a.var_libro_etiqueta.get(),'')
        a.var_libro_cdd.set('861')
        a.var_libro_cdd.set('notación inválida')
        self.assertEqual(a.var_libro_etiqueta.get(),'')

    def test_etiqueta_guardada_no_se_reemplaza_y_automatica_se_guarda(self):
        a=self.app
        a.tabla_libros.selection_set(a.tabla_libros.get_children()[0])
        a._seleccionar_libro(None)
        self.assertEqual(a.var_libro_etiqueta.get(),'')
        a._usar_etiqueta_cdd()
        self.assertEqual(a.var_libro_etiqueta.get(),org.nombre_etiqueta('novela'))
        a.es_administrador=True
        with patch('gui.messagebox.showinfo'):
            a._modificar_libro()
        self.assertEqual(org.obtener(self.id)['etiqueta'],'novela')
        a.tabla_libros.selection_set(a.tabla_libros.get_children()[0])
        a._seleccionar_libro(None)
        a.var_libro_cdd.set('861')
        self.assertEqual(a.var_libro_etiqueta.get(),org.nombre_etiqueta('novela'))

    def test_renombrar_y_colores_antologia(self):
        a=self.app
        uid=org.crear_ubicacion('Sala')
        org.guardar(self.id,uid,'antologia',['amarillo','verde'])
        a._refrescar_libros()
        a._cargar_organizacion(self.id)
        self.assertEqual(a._franjas_antologia,['amarillo','verde'])
        self.assertEqual(str(a.boton_franjas['state']),'normal')
        a.tabla_ubicaciones.selection_set(str(uid))
        a.es_administrador=True
        with patch('interfaz_organizacion.simpledialog.askstring',return_value='Mueble verde'):
            a._renombrar_ubicacion()
        self.assertEqual(org.obtener(self.id)['ubicacion'],'Mueble verde')
        self.assertIn('Mueble verde',a.combo_libro_ubicacion['values'])
        self.assertEqual(a.var_libro_ubicacion.get(),'Mueble verde')

    def test_generar_etiquetas_y_reporte_con_id_oculto(self):
        a=self.app
        uid=org.crear_ubicacion('Estante azul')
        org.guardar(self.id,uid,'cuento_terror')
        a._refrescar_libros()
        a._ejecutar_busqueda(False)
        ruta=str(Path(self.tmp.name)/'etiquetas.pdf')
        a._generar_etiquetas(ruta,{self.id:3})
        with fitz.open(ruta) as pdf:
            self.assertEqual(pdf[0].get_text().count('CDD: 863.9282'),3)
            self.assertIn('Estante azul',pdf[0].get_text())
            self.assertIn('Cuento de terror',pdf[0].get_text())
        tabla=a.tabla_busqueda
        tabla.configure(displaycolumns=('titulo','ubicacion','etiqueta_color'))
        ruta=str(Path(self.tmp.name)/'reporte.pdf')
        with patch('gui.filedialog.asksaveasfilename',return_value=ruta),patch('gui.messagebox.showinfo'),patch('gui.messagebox.showerror') as error:
            a._exportar_busqueda_pdf()
        error.assert_not_called()
        with fitz.open(ruta) as pdf:
            texto=pdf[0].get_text()
            self.assertIn('Ubicación',texto)
            self.assertIn('Estante azul',texto)
            self.assertIn('Cuento de terror',texto)
            self.assertNotIn('ISBN',texto)

    def test_cola_imprimir_cantidades_por_titulo(self):
        a=self.app
        a.tabla_libros.selection_set(a.tabla_libros.get_children())
        a._imprimir_etiquetas(a.tabla_libros)
        ventana=next(w for w in a.winfo_children() if w.winfo_class()=='Toplevel')
        def descendientes(w):
            for h in w.winfo_children():
                yield h
                yield from descendientes(h)
        widgets=list(descendientes(ventana))
        cola=next(w for w in widgets if w.winfo_class()=='Treeview')
        cola.selection_set(cola.get_children())
        boton=next(w for w in widgets if w.winfo_class()=='TButton' and w['text']=='Cambiar cantidad de seleccionados')
        with patch('interfaz_organizacion.simpledialog.askinteger',return_value=2):boton.invoke()
        self.assertEqual(int(cola.set(str(self.id),'cantidad')),2)
        boton=next(w for w in widgets if w.winfo_class()=='TButton' and w['text']=='Generar PDF')
        ruta=str(Path(self.tmp.name)/'cola.pdf')
        with patch('interfaz_organizacion.filedialog.asksaveasfilename',return_value=ruta),patch('interfaz_organizacion.messagebox.showinfo'):
            boton.invoke()
        with fitz.open(ruta) as pdf:self.assertEqual(pdf[0].get_text().count('CDD: 863.9282'),2)

    def test_imprimir_por_tipo_sin_seleccionar_libros(self):
        a=self.app
        a._imprimir_etiquetas(a.tabla_libros)
        ventana=next(w for w in a.winfo_children() if w.winfo_class()=='Toplevel')
        def descendientes(w):
            for h in w.winfo_children():
                yield h
                yield from descendientes(h)
        widgets=list(descendientes(ventana))
        modos=next(w for w in widgets if w.winfo_class()=='TNotebook')
        self.assertEqual(modos.tab(modos.select(),'text'),'Por tipo y cantidad')
        combo=next(w for w in widgets if w.winfo_class()=='TCombobox')
        cantidad=next(w for w in widgets if w.winfo_class()=='TSpinbox')
        agregar=next(w for w in widgets if w.winfo_class()=='TButton' and w['text']=='Agregar a la lista')
        combo.set(org.nombre_etiqueta('cuento_terror'))
        cantidad.set('20')
        agregar.invoke()
        combo.set(org.nombre_etiqueta('poesia'))
        cantidad.set('3')
        agregar.invoke()
        boton=next(w for w in widgets if w.winfo_class()=='TButton' and w['text']=='Generar PDF por tipo')
        ruta=str(Path(self.tmp.name)/'por_tipo.pdf')
        with patch('interfaz_organizacion.filedialog.asksaveasfilename',return_value=ruta),patch('interfaz_organizacion.messagebox.showinfo'):
            boton.invoke()
        with fitz.open(ruta) as pdf:
            texto=''.join(p.get_text() for p in pdf)
            self.assertEqual(len(pdf),2)
            self.assertEqual(texto.count('Cuento de terror'),20)
            self.assertEqual(texto.count('Poesía y formas poéticas'),3)
            self.assertNotIn('CDD:',texto)
            self.assertNotIn('Ubic.',texto)
            self.assertNotIn('Una novela',texto)
        self.assertEqual(org.obtener(self.id)['etiqueta'],'')

    def test_etiquetas_libres_validacion_y_antologias(self):
        ruta=str(Path(self.tmp.name)/'libres.pdf')
        for pedido in ([],[{'etiqueta':'cuento','cantidad':0}],
                       [{'etiqueta':'cuento','cantidad':1001}],
                       [{'etiqueta':'antologia','cantidad':1}],
                       [{'etiqueta':'inexistente','cantidad':1}]):
            with self.subTest(pedido=pedido),self.assertRaises(ValueError):
                self.app._generar_etiquetas_libres(ruta,pedido)
            self.assertFalse(Path(ruta).exists())
        self.app._generar_etiquetas_libres(ruta,[
            {'etiqueta':'antologia','franjas':['amarillo','verde'],'cantidad':2}])
        with fitz.open(ruta) as pdf:
            self.assertEqual(pdf[0].get_text().count('Antologías'),2)
            rectangulos=[d['rect'] for d in pdf[0].get_drawings() if abs(d['rect'].width-70*72/25.4)<.01 and abs(d['rect'].height-20*72/25.4)<.01]
            self.assertTrue(rectangulos)


if __name__=='__main__':unittest.main()

"""Pantallas de ubicaciones, clasificación cromática y cola de impresión."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import cdd
import organizacion as org
from etiquetas_pdf import generar


class InterfazOrganizacion:
    def _campos_organizacion(self, panel):
        self.var_libro_ubicacion = tk.StringVar()
        self.var_libro_etiqueta = tk.StringVar()
        self._franjas_antologia = []
        self._etiqueta_manual = False
        self._asignando_etiqueta = False
        self._claves_por_etiqueta = {org.nombre_etiqueta(k):k for k in org.ETIQUETAS}
        ttk.Label(panel,text='Ubicación').grid(row=3,column=0,sticky='w',padx=4,pady=4)
        self.combo_libro_ubicacion = ttk.Combobox(panel,textvariable=self.var_libro_ubicacion,state='readonly',width=18)
        self.combo_libro_ubicacion.grid(row=3,column=1,padx=4,pady=4)
        ttk.Button(panel,text='Gestionar ubicaciones',command=lambda:self.notebook.select(self.tab_ubicaciones)).grid(row=3,column=2,padx=4)
        ttk.Label(panel,text='Etiqueta de color').grid(row=4,column=0,sticky='w',padx=4,pady=4)
        self.combo_libro_etiqueta = ttk.Combobox(panel,textvariable=self.var_libro_etiqueta,
            values=['']+list(self._claves_por_etiqueta),state='readonly',width=48)
        self.combo_libro_etiqueta.grid(row=4,column=1,columnspan=3,sticky='w',padx=4,pady=4)
        self.boton_franjas = ttk.Button(panel,text='Colores de antología…',command=self._elegir_franjas,state='disabled')
        self.boton_franjas.grid(row=4,column=4,columnspan=2,padx=4)
        self.vista_etiqueta = tk.Canvas(panel,width=120,height=24,highlightthickness=1,highlightbackground='#aaaaaa')
        self.vista_etiqueta.grid(row=4,column=6,columnspan=2,padx=4)
        self.var_libro_etiqueta.trace_add('write',self._cambio_etiqueta)
        self.var_origen_etiqueta = tk.StringVar()
        ttk.Label(panel,textvariable=self.var_origen_etiqueta).grid(row=5,column=0,columnspan=6,sticky='w',padx=4)
        ttk.Button(panel,text='Usar etiqueta del CDD',command=self._usar_etiqueta_cdd).grid(row=5,column=6,columnspan=2,padx=4,pady=4)
        self.var_libro_cdd.trace_add('write',lambda *_:self._sugerir_etiqueta_cdd())

    def _cambio_etiqueta(self, *_):
        if not self._asignando_etiqueta:
            self._etiqueta_manual = True
            self.var_origen_etiqueta.set('Elección manual: se conserva aunque cambie el CDD.')
        self._actualizar_vista_etiqueta()

    def _usar_etiqueta_cdd(self):
        self._etiqueta_manual = False
        self._sugerir_etiqueta_cdd()

    def _sugerir_etiqueta_cdd(self):
        if self._etiqueta_manual:
            return
        clave = org.sugerir_etiqueta(self.var_libro_cdd.get())
        self._asignando_etiqueta = True
        try:
            self._franjas_antologia = []
            self.var_libro_etiqueta.set(org.nombre_etiqueta(clave))
        finally:
            self._asignando_etiqueta = False
        self.var_origen_etiqueta.set(
            'Propuesta del CDD: puede cambiarla (narrativa propone Novela).'
            if clave else 'Sin propuesta de color para este CDD: seleccione una etiqueta si corresponde.')

    def _actualizar_vista_etiqueta(self):
        clave = self._claves_por_etiqueta.get(self.var_libro_etiqueta.get(),'')
        self.boton_franjas.configure(state='normal' if clave=='antologia' else 'disabled')
        self.vista_etiqueta.delete('all')
        colores=org.paleta(clave,self._franjas_antologia) or ['#FFFFFF']
        for n,color in enumerate(colores):
            self.vista_etiqueta.create_rectangle(n*120/len(colores),0,(n+1)*120/len(colores),24,fill=color,outline='')
        if clave and org.ETIQUETAS[clave][2]:
            self.vista_etiqueta.create_text(60,12,text=org.ETIQUETAS[clave][2],font=('Arial',12,'bold'))

    def _elegir_franjas(self):
        ventana=tk.Toplevel(self)
        ventana.title('Colores presentes en la antología')
        ventana.transient(self)
        ventana.grab_set()
        variables={clave:tk.BooleanVar(master=ventana,value=clave in self._franjas_antologia) for clave in org.COLORES}
        for fila,(clave,(nombre,color)) in enumerate(org.COLORES.items()):
            tk.Label(ventana,bg=color,width=4,relief='solid',bd=1).grid(row=fila,column=0,padx=10,pady=3)
            ttk.Checkbutton(ventana,text=nombre,variable=variables[clave]).grid(row=fila,column=1,sticky='w',padx=10)
        def aceptar():
            seleccion=[k for k,v in variables.items() if v.get()]
            if not seleccion:
                messagebox.showwarning('Colores','Seleccione al menos un color.',parent=ventana)
                return
            self._franjas_antologia=seleccion
            self._actualizar_vista_etiqueta()
            ventana.destroy()
        ttk.Button(ventana,text='Guardar colores',command=aceptar).grid(row=len(variables),column=0,columnspan=2,pady=10)

    def _leer_organizacion(self):
        nombre=self.var_libro_ubicacion.get()
        if nombre and nombre not in self._ubicaciones_por_nombre:
            raise ValueError('La ubicación seleccionada ya no existe. Elija otra.')
        clave=self._claves_por_etiqueta.get(self.var_libro_etiqueta.get(),'')
        return org.validar(self._ubicaciones_por_nombre.get(nombre),clave,self._franjas_antologia)

    def _cargar_organizacion(self,id_libro):
        datos=org.obtener(id_libro)
        self._franjas_antologia=datos['franjas']
        self.var_libro_ubicacion.set(datos['ubicacion'])
        self.var_libro_etiqueta.set(org.nombre_etiqueta(datos['etiqueta']))
        self._actualizar_vista_etiqueta()

    def _limpiar_organizacion(self):
        self.var_libro_ubicacion.set('')
        self._franjas_antologia=[]
        self.var_libro_etiqueta.set('')
        self._usar_etiqueta_cdd()

    def _construir_tab_ubicaciones(self):
        panel=self.tab_ubicaciones
        ttk.Label(panel,text='Creá los nombres de los lugares de la biblioteca y asignalos después a cada libro.').pack(anchor='w',padx=12,pady=12)
        barra=ttk.Frame(panel)
        barra.pack(fill='x',padx=12,pady=6)
        self.var_nombre_ubicacion=tk.StringVar()
        ttk.Label(barra,text='Nombre').pack(side='left',padx=4)
        ttk.Entry(barra,textvariable=self.var_nombre_ubicacion,width=48).pack(side='left',padx=4)
        ttk.Button(barra,text='Crear ubicación',command=self._crear_ubicacion).pack(side='left',padx=4)
        ttk.Button(barra,text='Renombrar seleccionada',command=self._renombrar_ubicacion).pack(side='left',padx=4)
        ttk.Button(barra,text='Eliminar seleccionada',command=self._eliminar_ubicacion).pack(side='left',padx=4)
        self.tabla_ubicaciones=ttk.Treeview(panel,columns=('nombre','libros'),show='headings')
        self.tabla_ubicaciones.heading('nombre',text='Ubicación')
        self.tabla_ubicaciones.heading('libros',text='Títulos asignados')
        self.tabla_ubicaciones.column('nombre',width=500)
        self.tabla_ubicaciones.column('libros',width=130,stretch=False,anchor='center')
        self.tabla_ubicaciones.pack(fill='both',expand=True,padx=12,pady=8)
        ttk.Label(panel,text='Renombrar actualiza todos los libros vinculados. Para eliminar un lugar, primero reubicá sus libros.').pack(anchor='w',padx=12,pady=10)

    def _refrescar_ubicaciones(self):
        ubicaciones=org.listar_ubicaciones()
        self._ubicaciones_por_nombre={u['nombre']:u['id_ubicacion'] for u in ubicaciones}
        nombres=list(self._ubicaciones_por_nombre)
        self.combo_libro_ubicacion.configure(values=['']+nombres)
        self.combo_busq_ubicacion.configure(values=['Todas','Sin ubicación']+nombres)
        if self.var_libro_ubicacion.get() not in nombres:
            self.var_libro_ubicacion.set('')
        if self.var_busq_ubicacion.get() not in ['Todas','Sin ubicación']+nombres:
            self.var_busq_ubicacion.set('Todas')
        self.tabla_ubicaciones.delete(*self.tabla_ubicaciones.get_children())
        for u in ubicaciones:
            self.tabla_ubicaciones.insert('','end',iid=str(u['id_ubicacion']),values=(u['nombre'],u['libros']))

    def _crear_ubicacion(self):
        try:
            org.crear_ubicacion(self.var_nombre_ubicacion.get())
        except ValueError as error:
            messagebox.showerror('Ubicación',str(error))
            return
        self.var_nombre_ubicacion.set('')
        self._refrescar_ubicaciones()

    def _renombrar_ubicacion(self):
        if not self._requiere_administrador():return
        seleccion=self.tabla_ubicaciones.selection()
        if not seleccion:
            messagebox.showwarning('Ubicación','Seleccione una ubicación.')
            return
        anterior=self.tabla_ubicaciones.item(seleccion[0],'values')[0]
        nuevo=simpledialog.askstring('Renombrar ubicación','Nuevo nombre:',initialvalue=anterior,parent=self)
        if nuevo is None:return
        try:
            org.renombrar_ubicacion(int(seleccion[0]),nuevo)
        except ValueError as error:
            messagebox.showerror('Ubicación',str(error))
            return
        nuevo=' '.join(nuevo.split())
        for var in [self.var_libro_ubicacion,self.var_busq_ubicacion]:
            if var.get()==anterior:var.set(nuevo)
        self._refrescar_ubicaciones()
        self._refrescar_libros()
        self._ejecutar_busqueda(False)

    def _eliminar_ubicacion(self):
        if not self._requiere_administrador():return
        seleccion=self.tabla_ubicaciones.selection()
        if not seleccion:
            messagebox.showwarning('Ubicación','Seleccione una ubicación.')
            return
        if not messagebox.askyesno('Eliminar ubicación','¿Eliminar la ubicación seleccionada?',parent=self):return
        try:
            org.eliminar_ubicacion(int(seleccion[0]))
        except ValueError as error:
            messagebox.showerror('Ubicación',str(error))
            return
        self._refrescar_ubicaciones()

    def _filtros_organizacion(self,panel):
        self.var_busq_ubicacion=tk.StringVar(value='Todas')
        self.var_busq_etiqueta=tk.StringVar(value='Todas')
        ttk.Label(panel,text='Ubicación').grid(row=3,column=0,sticky='w',padx=4,pady=4)
        self.combo_busq_ubicacion=ttk.Combobox(panel,textvariable=self.var_busq_ubicacion,state='readonly',width=20)
        self.combo_busq_ubicacion.grid(row=3,column=1,padx=4,pady=4)
        ttk.Label(panel,text='Etiqueta de color').grid(row=3,column=2,sticky='w',padx=4,pady=4)
        ttk.Combobox(panel,textvariable=self.var_busq_etiqueta,state='readonly',width=43,
            values=['Todas','Sin etiqueta']+list(self._claves_por_etiqueta)).grid(row=3,column=3,columnspan=3,sticky='w',padx=4)

    def _filtro_ubicacion(self):
        nombre=self.var_busq_ubicacion.get()
        if nombre=='Todas':return None
        if nombre=='Sin ubicación':return 0
        if nombre not in self._ubicaciones_por_nombre:
            raise ValueError('La ubicación del filtro ya no existe.')
        return self._ubicaciones_por_nombre[nombre]

    def _filtro_etiqueta(self):
        nombre=self.var_busq_etiqueta.get()
        if nombre=='Todas':return None
        if nombre=='Sin etiqueta':return ''
        return self._claves_por_etiqueta[nombre]

    def _imprimir_etiquetas(self,tabla):
        """Prepara una cola con cantidades independientes por título."""
        seleccion=tabla.selection()
        if not seleccion:
            messagebox.showwarning('Etiquetas','Seleccione uno o varios libros de la tabla (Ctrl o Mayús).')
            return
        ventana=tk.Toplevel(self)
        ventana.title('Imprimir etiquetas de 7 × 2 cm')
        ventana.geometry('760x460')
        ventana.transient(self)
        ventana.grab_set()
        ttk.Label(ventana,text='Elegí la cantidad por libro. Se usarán los datos guardados del catálogo.').pack(pady=10)
        marco=ttk.Frame(ventana)
        marco.pack(fill='both',expand=True,padx=12)
        cola=ttk.Treeview(marco,columns=('titulo','cantidad'),show='headings',height=12)
        cola.heading('titulo',text='Libro')
        cola.heading('cantidad',text='Cantidad de etiquetas')
        cola.column('titulo',width=530)
        cola.column('cantidad',width=160,stretch=False)
        barra=ttk.Scrollbar(marco,orient='vertical',command=cola.yview)
        cola.configure(yscrollcommand=barra.set)
        barra.pack(side='right',fill='y')
        cola.pack(fill='both',expand=True)
        for iid in seleccion:
            valores=tabla.item(iid,'values')
            cola.insert('','end',iid=str(valores[0]),values=(valores[1],1))
        def cantidad():
            ids=cola.selection()
            if not ids:return
            valor=simpledialog.askinteger('Cantidad','Cantidad de etiquetas para los libros seleccionados:',
                initialvalue=1,minvalue=1,maxvalue=1000,parent=ventana)
            if valor is not None:
                for iid in ids:cola.set(iid,'cantidad',valor)
        ttk.Button(ventana,text='Cambiar cantidad de seleccionados',command=cantidad).pack(pady=6)
        ttk.Label(ventana,text='A4 · 22 etiquetas por hoja · Imprimir al 100 % / Tamaño real, sin ajustar.').pack(pady=4)
        def exportar():
            pedido={int(i):int(cola.set(i,'cantidad')) for i in cola.get_children()}
            ruta=filedialog.asksaveasfilename(parent=ventana,title='Guardar etiquetas',defaultextension='.pdf',
                initialfile='etiquetas_biblioteca.pdf',filetypes=[('PDF','*.pdf')])
            if not ruta:return
            try:
                self._generar_etiquetas(ruta,pedido)
            except (ValueError,OSError) as error:
                messagebox.showerror('Etiquetas',str(error),parent=ventana)
                return
            messagebox.showinfo('Etiquetas','PDF generado. Imprimí al 100 % / Tamaño real.',parent=ventana)
            ventana.destroy()
        ttk.Button(ventana,text='Generar PDF',command=exportar).pack(pady=10)

    def _generar_etiquetas(self,ruta,pedido):
        if not pedido or any(not isinstance(n,int) or not 1<=n<=1000 for n in pedido.values()):
            raise ValueError('Indique entre 1 y 1000 etiquetas por libro.')
        codigos=cdd.obtener_codigos()
        datos=org.obtener_todos()
        etiquetas=[]
        for id_libro,cantidad in pedido.items():
            libro=self.libro_dao.obtener_por_id(id_libro)
            if libro is None:raise ValueError('Uno de los libros seleccionados ya no existe.')
            detalle=datos.get(id_libro,{})
            item=dict(titulo=libro.titulo,codigo=codigos.get(id_libro,''),
                ubicacion=detalle.get('ubicacion',''),etiqueta=detalle.get('etiqueta',''),franjas=detalle.get('franjas',[]))
            etiquetas.extend([item]*cantidad)
        generar(ruta,etiquetas)

"""Ventana de opciones para imprimir tejuelos bibliotecarios en PDF."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import cdd
from tejuelos import generar_tejuelos_pdf


def abrir_dialogo_tejuelos(app):
    """Abre las opciones a partir de la pestaña Libros de la aplicación."""
    libros = app.libro_dao.obtener_todos()
    if not libros:
        messagebox.showwarning("Tejuelos", "Todavía no hay libros registrados.", parent=app)
        return

    seleccionados = {
        int(app.tabla_libros.item(item, "values")[0])
        for item in app.tabla_libros.selection()
    }

    ventana = tk.Toplevel(app)
    ventana.title("Generar tejuelos bibliotecarios")
    ventana.resizable(False, False)
    ventana.transient(app)
    ventana.grab_set()

    marco = ttk.Frame(ventana, padding=16)
    marco.pack(fill="both", expand=True)
    ttk.Label(marco, text="Etiquetas para el lomo del libro", font=("Arial", 12, "bold")).pack(anchor="w")
    ttk.Label(marco, text="Formato: 7 × 2 cm, en hojas A4 listas para imprimir.").pack(anchor="w", pady=(3, 12))

    alcance = tk.StringVar(value="seleccionados" if seleccionados else "todos")
    opciones = ttk.LabelFrame(marco, text="Libros a incluir", padding=8)
    opciones.pack(fill="x", pady=(0, 8))
    ttk.Radiobutton(opciones, text=f"Seleccionados ({len(seleccionados)})",
                    variable=alcance, value="seleccionados",
                    state="normal" if seleccionados else "disabled").pack(anchor="w")
    ttk.Radiobutton(opciones, text=f"Todo el catálogo ({len(libros)} títulos)",
                    variable=alcance, value="todos").pack(anchor="w")

    incluir_registro = tk.BooleanVar(value=False)
    repetir_stock = tk.BooleanVar(value=True)
    ttk.Checkbutton(marco, text="Incluir ID de registro del catálogo (no es número de inventario)",
                    variable=incluir_registro).pack(anchor="w", pady=3)
    ttk.Checkbutton(marco, text="Una etiqueta por ejemplar según stock",
                    variable=repetir_stock).pack(anchor="w", pady=3)
    ttk.Label(marco, text="Cada etiqueta lleva CDD + tres letras del apellido del autor.\n"
                            "Los libros sin CDD se excluyen, previa advertencia.",
              justify="left", foreground="#555555").pack(anchor="w", pady=(9, 12))

    def generar():
        elegidos = [libro for libro in libros
                    if alcance.get() == "todos" or libro.id_libro in seleccionados]
        registros = []
        sin_cdd = []
        for libro in elegidos:
            codigo = cdd.obtener(libro.id_libro).strip()
            if not codigo:
                sin_cdd.append(libro.titulo)
                continue
            registros.append({
                "cdd": codigo, "autor": libro.autor,
                "id_libro": libro.id_libro, "stock": libro.stock,
            })

        if sin_cdd:
            muestra = "\n".join(f"• {nombre}" for nombre in sin_cdd[:5])
            resto = f"\n... y {len(sin_cdd) - 5} más." if len(sin_cdd) > 5 else ""
            continuar = messagebox.askyesno(
                "Libros sin CDD",
                f"Hay {len(sin_cdd)} libro(s) sin CDD que no se incluirán:\n"
                f"{muestra}{resto}\n\n¿Continuar con los restantes?",
                parent=ventana,
            )
            if not continuar:
                return

        total = sum(registro["stock"] if repetir_stock.get() else 1
                    for registro in registros)
        if total == 0:
            messagebox.showwarning("Tejuelos", "No hay etiquetas para generar. Revisá el CDD y el stock.",
                                   parent=ventana)
            return
        if total > 400 and not messagebox.askyesno(
                "Muchas etiquetas", f"Se generarán {total} etiquetas. ¿Continuar?",
                parent=ventana):
            return

        destino = filedialog.asksaveasfilename(
            parent=ventana, title="Guardar tejuelos en PDF",
            defaultextension=".pdf", initialfile="tejuelos_biblioteca.pdf",
            filetypes=[("Archivo PDF", "*.pdf")],
        )
        if not destino:
            return
        try:
            cantidad = generar_tejuelos_pdf(
                destino, registros, incluir_registro.get(), repetir_stock.get()
            )
        except (OSError, ValueError) as error:
            messagebox.showerror("Error al generar PDF", str(error), parent=ventana)
            return
        ventana.destroy()
        messagebox.showinfo("Tejuelos listos",
                            f"Se generaron {cantidad} etiquetas en:\n{destino}", parent=app)

    botones = ttk.Frame(marco)
    botones.pack(fill="x", pady=(4, 0))
    ttk.Button(botones, text="Cancelar", command=ventana.destroy).pack(side="right", padx=(8, 0))
    ttk.Button(botones, text="Generar PDF", command=generar).pack(side="right")

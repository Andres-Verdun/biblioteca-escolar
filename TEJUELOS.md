# Tejuelos bibliotecarios (Biblioteca Escolar 360)

Esta función añade a la pestaña **Libros** el botón **Generar tejuelos (PDF)**. No cambia la base de datos ni elimina las exportaciones existentes.

## ¿Qué lleva el tejuelo?

Cada etiqueta de **7 × 2 cm** muestra:

1. **Código CDD** ya guardado en la ficha de ese libro.
2. **Tres primeras letras del apellido del autor**, en mayúsculas y sin tildes.
3. **ID de registro (opcional)**, identificado como "Reg.". El ID de un libro del catálogo **no es** un número de inventario individual por ejemplar.

Ejemplo: un libro con CDD 863, autor Jorge Luis Borges e ID 42 se imprime como 863 / BOR / Reg. 42 (este último solo si se activa la opción).

## Cómo generar el PDF

1. Abrí el programa y entrá en **Libros**.
2. Opcionalmente, seleccioná uno o varios libros en la tabla.
3. Presioná **Generar tejuelos (PDF)**.
4. Elegí **Seleccionados** o **Todo el catálogo**.
5. Activá o desactivá **Incluir ID de registro** y **Una etiqueta por ejemplar según stock**.
6. Elegí dónde guardar el PDF. Después imprimilo en **A4, escala 100 % / tamaño real** (no "ajustar a página").

Los libros sin CDD se excluyen **previa advertencia**; completá ese campo desde la ficha del libro.

## Cómo escribir el autor

- Jorge Luis Borges → BOR.
- Borges, Jorge Luis → BOR.
- García Márquez, Gabriel → GAR.

En nombres sin coma, el sistema presupone que la **última palabra es el apellido**. Para apellidos compuestos conviene escribir **Apellido(s), Nombre(s)** en la ficha: Gabriel García Márquez produciría MAR, mientras que García Márquez, Gabriel produce GAR.

La sigla se calcula al generar el PDF: no se modifica el autor almacenado ni se añade una columna.

## Compatibilidad y seguridad

- Utiliza ReportLab, ya utilizado por el sistema.
- No realiza cambios de esquema, datos, préstamos, portadas ni stock.
- **Antes de actualizar el ejecutable**, respaldá biblioteca.db desde el menú de la aplicación y volvé a generar el .exe con el BAT de compilación del repositorio.
- No reemplaces tu archivo biblioteca.db al actualizar.

## Pruebas

En la carpeta del proyecto, ejecutá: python -m unittest test_tejuelos -v

Verifica siglas de autor, acentos, ausencia de CDD y creación de un PDF de ejemplo.

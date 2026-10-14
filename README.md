# Biblioteca Escolar 360

Aplicación de escritorio en Python/Tkinter con inventario, préstamos y base SQLite.

## Rama Notaciones-CDD

En **Libros**, escribir una notación en **Notación CDD/BNM**. La descripción
se actualiza automáticamente. **Catálogo CDD…** permite buscar por código o
por tema y seleccionar una entrada con doble clic o con el botón de selección.
Guardar con **Agregar** o **Modificar** (esta última opción conserva el acceso
administrador ya existente).

Ejemplos:

| Notación | Resultado |
| --- | --- |
| RE 030 | Referencia: enciclopedias generales |
| R 806.0-3 | Diccionarios de español |
| L 343 | Código penal |
| S 511 | Enseñanza secundaria: matemáticas |
| 1-E 372.4 | EGB, primer ciclo: libros de lectura |
| E 372.4 / 3-E 372.4 | EGB, tercer ciclo: libros de lectura |
| PL 681.3 | Polimodal: informática |
| 863.9932 / A863 | Narrativa argentina |
| 372.7 | Enseñanza de las matemáticas |
| 635.9 | Jardinería y floricultura |
| 863.9282 | Narrativa infantil y juvenil en español |
| 861.9282 | Poesía infantil en español |
| 862.9282 | Teatro infantil en español |
| 808.068 / 808.0683 | Literatura infantil / narrativa infantil |

Se aceptan mayúsculas/minúsculas y prefijos unidos (`re030`). Se normalizan
al guardar (`RE 030`), conservando ceros iniciales, decimales y signos.
Las notaciones históricas se conservan sin reescritura automática.

### Fuente y alcance

[Manual de notaciones de CDD adaptado por la Biblioteca Nacional de Maestros](https://bnm.educacion.gob.ar/digital/documentos/EL006553.pdf),
basado en la 20.ª edición. El manual explica que los sectores especiales
conservan notaciones CDU (páginas 5–6 del PDF). Por eso **no se elimina el
prefijo para interpretar su número como CDD**: `800` y `R 800` son diferentes.
R es referencia; RE, enciclopedias; L, legislación; S, secundaria; EGB se
identifica por ciclo (1-E/2-E/3-E); PL, Polimodal. Son denominaciones del manual
histórico, independientes del campo Ciclo del formulario.

`cdd_bnm.csv` contiene **190 entradas seleccionadas**: 175 del manual BNM y
15 equivalencias de fichas editoriales y catálogos bibliotecarios. La columna
`fuente` conserva la referencia de cada equivalencia; cuando está vacía se
utiliza el manual BNM. Las páginas del manual se cuentan desde 1 del PDF.
Las fuentes y páginas se conservan como documentación interna y no aparecen
en la clasificación del formulario ni en las columnas del selector.
Las descripciones son rótulos resumidos; consultar el manual para sus notas
sobre cuándo usar cada notación. No es una transcripción completa ni cubre
cualquier notación que pueda aparecer impresa en un libro.

- **Coincidencia exacta:** muestra sólo la clasificación (y el sector cuando corresponde).
- **Categoría general:** para un número CDD simple de tres cifras que no está
  en el catálogo, busca primero un código padre documentado, luego la división de decenas y
  finalmente la clase de centenas. Aclara que la subclasificación
  requiere revisión. No se atribuye una descripción específica por aproximación.
- **Pendiente:** guarda códigos válidos desconocidos; identifica el sector si
  está documentado. Los prefijos no documentados se conservan sin inventar equivalencias.
  `A863` ahora se reconoce como narrativa argentina, documentada por la
  Biblioteca Nacional en la ficha de *Tres historias pringlenses*.

Se actualiza el catálogo al iniciar sin borrar libros, préstamos o códigos
registrados. Libro y notación se guardan en una única transacción. La notación
es opcional: dejarla vacía al modificar elimina sólo ese dato.
La notación y su clasificación aparecen en el formulario, el catálogo de
libros, los resultados de búsqueda y sus reportes PDF. Los libros sin notación
muestran ambas columnas vacías. Los códigos desconocidos conservan el aviso
de revisión; la búsqueda no deduce clasificaciones desde el título del libro.

## Ejecutar y comprobar

```bash
python -m pip install pillow reportlab
python main.py
# Sólo para las pruebas de PDF (no es requisito para ejecutar el programa):
python -m pip install pymupdf
python -m unittest discover -s tests -v
```

Python debe incluir Tkinter. Para Windows, generar el ejecutable con
`USAR_ESTE_generar_ejecutable.bat`; la especificación incluida empaqueta
`cdd_bnm.csv`. Para probar esta versión se necesita ejecutar el código de esta
rama o regenerar el EXE; el ejecutable anterior no incorpora los cambios.

Antes de actualizar un equipo con datos reales, cerrar la aplicación y hacer
una copia de `biblioteca.db`. Conservar esa base junto al nuevo ejecutable.

## Equivalencias complementarias

Los rótulos de las quince entradas complementarias son descripciones prácticas
basadas en los usos de las fichas citadas en el CSV. No son una transcripción
de encabezamientos oficiales de una edición completa de CDD, ni equivalencias
atribuidas al manual BNM. No determinan por sí solos la edad recomendada.

Al iniciar, la aplicación incorpora las entradas nuevas también a bases
existentes: los libros con `A863` o `372.7` ya guardados muestran automáticamente
la clasificación actualizada, sin volver a cargarlos.

## Columnas visibles y Tercer Ciclo

En **Libros** y **Búsqueda avanzada**, abrir **Columnas visibles** y marcar
o desmarcar ID, título, autor, editorial, ISBN, género, edad, ciclo, stock,
disponibles, tapa, CDD o clasificación. Siempre debe quedar al menos una
columna. **Mostrar todas** restaura el listado completo. Las barras de
desplazamiento permiten ver las columnas anchas.

La elección se mantiene al buscar, ordenar o limpiar filtros durante la
sesión; cada tabla tiene su selección independiente. El PDF exporta sólo
las columnas visibles y en ese orden, con el mismo orden de filas. Ajusta
el ancho a la página y envuelve los textos largos. La opción **Incluir
portadas en el PDF** agrega las imágenes aunque el ID esté oculto.

**Tercer Ciclo** está disponible al cargar/modificar libros y en el filtro
de búsqueda. No modifica los ciclos de los libros ya guardados.

### Nuevas notaciones

Entre las incorporaciones: 306.43 (sociología de la educación), A860, A861,
A862, A864, A861.9282, A863.9282; diccionarios R y enciclopedias RE por tema;
371.102 y sus notaciones de didáctica; geología, paleontología, biología,
ecología, botánica y zoología. Cada equivalencia conserva su fuente. Los
prefijos de letras se interpretan sólo si están documentados en el catálogo.

Las pruebas de interfaz se ejecutan cuando hay pantalla disponible (DISPLAY
en Linux/Xvfb o una sesión Windows). Comprueban el menú de columnas, Tercer
Ciclo, selección de libros y PDFs con ID oculto y portadas.

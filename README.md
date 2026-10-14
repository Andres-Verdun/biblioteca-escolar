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

`cdd_bnm.csv` contiene **132 entradas seleccionadas**: 124 del manual BNM y
8 equivalencias de fichas editoriales y catálogos bibliotecarios. La columna
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
La clasificación se consulta en el formulario y el selector; no se agregaron
filtros ni columnas CDD a los reportes PDF en esta etapa.

## Ejecutar y comprobar

```bash
python -m pip install pillow reportlab
python main.py
python -m unittest discover -s tests -v
```

Python debe incluir Tkinter. Para Windows, generar el ejecutable con
`USAR_ESTE_generar_ejecutable.bat`; la especificación incluida empaqueta
`cdd_bnm.csv`. Para probar esta versión se necesita ejecutar el código de esta
rama o regenerar el EXE; el ejecutable anterior no incorpora los cambios.

Antes de actualizar un equipo con datos reales, cerrar la aplicación y hacer
una copia de `biblioteca.db`. Conservar esa base junto al nuevo ejecutable.

## Equivalencias complementarias

Los rótulos de las ocho entradas complementarias son descripciones prácticas
basadas en los usos de las fichas citadas en el CSV. No son una transcripción
de encabezamientos oficiales de una edición completa de CDD, ni equivalencias
atribuidas al manual BNM. No determinan por sí solos la edad recomendada.

Al iniciar, la aplicación incorpora las entradas nuevas también a bases
existentes: los libros con `A863` o `372.7` ya guardados muestran automáticamente
la clasificación actualizada, sin volver a cargarlos.

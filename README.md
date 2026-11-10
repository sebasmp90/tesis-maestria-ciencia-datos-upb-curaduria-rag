# Desarrollo de una metodología de curaduría de bases de conocimiento para sistemas RAG en entidades públicas: el caso del POT de Medellín

Trabajo de grado de la **Maestría en Ciencia de Datos** de la **Universidad Pontificia Bolivariana** (Medellín, 2026).

- **Autores:** Sebastián Camilo Muñoz Palacio e Iván Andrés Velasco Arias
- **Director:** Leonardo Betancur Agudelo

## Resumen

Adoptar sistemas de recuperación aumentada con generación en entidades públicas enfrenta un obstáculo previo: la información no está preparada para la inteligencia artificial. El corpus normativo del seguimiento al Plan de Ordenamiento Territorial de Medellín lo ilustra: repite textos entre documentos y se compone de normas que se derogan y modifican entre sí, lo que produce colisiones semánticas, fragmentos parecidos en contenido pero incompatibles en vigencia. Se desarrolla una metodología de curaduría de bases de conocimiento para entidades públicas. Una revisión sistemática de 734 registros, sintetizada en veintiún estudios, mostró que las técnicas no se habían evaluado en conjunto ni en español. Con esa evidencia se diseñó un procedimiento de siete pasos que segmenta el corpus por artículo, construye el grafo de modificaciones y derogaciones, determina la vigencia de cada unidad y la contrasta con una segunda fuente, y conserva lo histórico rotulado. Aplicado a treinta y seis normas ya convertidas a texto y a sus derogatorias, registradas a mano, produjo en segundos una base de 9.529 registros, sin modelos de lenguaje. En setenta preguntas calificadas a ciegas, el sistema respondió satisfactoriamente el 57 % de las preguntas con la base curada, frente al 33 % del sistema de referencia y al 51 % de la mejor versión sobre el corpus original. En las preguntas de colisión, las citas a normas que no regían bajaron del 35 % al 10 % frente al sistema de referencia, sin significación estadística. La base curada no mejoró la abstención ante preguntas sin respuesta.

**Palabras clave:** curaduría de datos; recuperación aumentada con generación; base de conocimiento; vigencia normativa; ordenamiento territorial.

## Resultados principales

| Medida, banco de prueba de 70 preguntas | Sistema de referencia | Base curada |
|---|---|---|
| Respuestas satisfactorias | 33 % | 57 % |
| Respuestas satisfactorias en preguntas de colisión | 10 % | 60 % |
| Citas a normas que no regían, en colisión | 35 % | 10 % |
| Respuestas con alucinación | 26 % | 17 % |
| Citas exactas al artículo esperado | 14 % | 68 % |

La base curada del caso se construyó en 3 segundos, con reglas y sin modelos de lenguaje: 36 normas, 9.529 registros y 340 relaciones de modificación y derogación.

## Contenido del repositorio

| Carpeta | Contenido |
|---|---|
| `informe/` | El informe final en Word y en Markdown, y sus 14 figuras en `figuras/` |
| `resumen/` | `resumen_del_proyecto.html`: una página que explica el trabajo para quien no lo conoce, con un ejemplo real y la línea de tiempo del caso de estudio. Se abre con doble clic en cualquier navegador |
| `Anexo_A/` a `Anexo_I/` | Los archivos de soporte, en una carpeta por anexo (ver abajo) |

| Carpeta | Anexo | Contenido |
|---|---|---|
| `Anexo_A/` | Protocolo y exportación de la búsqueda | Protocolo de la revisión y los tres archivos exportados de Dimensions el 1 de agosto de 2026 (734 registros) |
| `Anexo_B/` | Registro completo del cribado | Los 692 registros con su decisión y su razón, el flujo PRISMA y los 107 elegibles |
| `Anexo_C/` | Matriz de extracción | Núcleo de 21 estudios, calidad, libro de códigos, trazabilidad del arbitraje, verificación de 80 y no recuperados |
| `Anexo_D/` | Auditoría por muestreo | Informe de la auditoría de la extracción |
| `Anexo_F/` | Bancos de preguntas | Los tres bancos de 70 preguntas y el prompt con que se formularon |
| `Anexo_G/` | Calificación y acuerdo entre calificadores | Calificación ciega, cruce con las condiciones y segundo calificador |
| `Anexo_I/` | Código, corpus, base curada y plan de análisis | Scripts de Python, corpus en Markdown, base curada, respuestas de las corridas y plan de análisis fechado, con su propio `LEEME.md` |

Los anexos E y H están dentro del informe.

## Reproducir los resultados

Desde la carpeta `Anexo_I/`:

1. `python codigo/curar.py` reconstruye la base curada (9.529 registros) en `curaduria/`, idéntica byte a byte a la publicada en `base_curada/unidades.jsonl.zip`, que va comprimida porque GitHub no admite archivos tan grandes desde el navegador.
2. `python codigo/validar_curaduria.py ../Anexo_F/banco_agente_D.csv` ejecuta el control de salida contra el banco de prueba.
3. `python codigo/analisis.py` reproduce las pruebas estadísticas y las tablas de la sección 7.1.3.7 del informe a partir de la calificación del Anexo G.

Los tres pasos corren con Python 3.12, `numpy`, `scipy` y `openpyxl`, sin tarjeta gráfica ni modelos de lenguaje. Para indexar y consultar se necesitan además LangChain, Chroma y Ollama con `qwen3:8b` y `nomic-embed-text`. Las instrucciones completas están en `Anexo_I/LEEME.md`.

## Notas

- **Versión pública del informe.** La portada omite los números de cédula y los identificadores institucionales de los autores y del director; el resto del documento es el mismo que se entregó a la universidad.
- **Datos personales.** El corpus reúne normas públicas del Distrito de Medellín. En la tabla de beneficiarios del Decreto 838 de 2023 se omitieron los nombres y los números de documento, por protección de datos personales (Ley 1581 de 2012); las cifras de la base curada no cambian. Las calificaciones de los funcionarios se publican sin nombres.
- **Uso de inteligencia artificial.** El informe declara, etapa por etapa, el uso de inteligencia artificial generativa como apoyo (sección 1.2 y Tabla 1).
- **Derechos.** La titularidad del trabajo se rige por el Estatuto de Propiedad Intelectual de la Universidad Pontificia Bolivariana. Para reutilizar el contenido, citen el trabajo y consulten a los autores.

## Cómo citar

Muñoz Palacio, S. C., y Velasco Arias, I. A. (2026). *Desarrollo de una metodología de curaduría de bases de conocimiento para sistemas RAG en entidades públicas: el caso del POT de Medellín* [Trabajo de grado de maestría, Universidad Pontificia Bolivariana].

# Anexo A. Parte 1. Protocolo de la revisión sistemática

Metodología de curaduría de bases de conocimiento para sistemas RAG en entidades públicas: el caso del POT de Medellín. Sebastián Muñoz Palacio e Iván Velasco Arias. Maestría en Ciencia de Datos, Universidad Pontificia Bolivariana.

Este anexo tiene dos partes. La primera reproduce el protocolo tal como quedó fijado en el anteproyecto, entregado el 31 de julio de 2026, antes de la exportación definitiva de la búsqueda (1 de agosto de 2026). La segunda lista los ajustes hechos durante la ejecución; todos están declarados en el informe, con la sección donde se tratan.

## 1. Protocolo fijado en el anteproyecto (31 de julio de 2026)

### 1.1 Texto de la Fase 1, sin cambios

> Corresponde a la comprensión del negocio y del estado de la técnica. Se ejecuta una revisión sistemática diseñada según los lineamientos de Kitchenham y Charters (2007) y reportada conforme a la declaración PRISMA 2020 (Page et al., 2021), de la cual se adoptan los ítems aplicables a revisiones sin metaanálisis estadístico. La revisión responde a la pregunta de qué técnicas se han reportado para preparar, curar y estructurar corpus documentales previo a su incorporación en bases de conocimiento de sistemas RAG, y qué evidencia existe sobre su efecto en la consistencia de las respuestas, la reducción de alucinaciones y el costo de operación. Las búsquedas se ejecutan en Dimensions como base principal, complementada con Scopus, ACM Digital Library, IEEE Xplore y arXiv, con una cadena de tres bloques (técnica, componente de interés y problema abordado) documentada en el protocolo. Se incluyen artículos, ponencias arbitradas y prepublicaciones con evaluación empírica, en inglés o español, que aborden explícitamente la preparación del corpus; se excluyen los trabajos centrados en el componente generativo, las aplicaciones sin discusión de su base de conocimiento y los documentos sin método verificable. La búsqueda piloto fue ejecutada: identificó 734 registros, 692 tras la deduplicación, y no arrojó resultados anteriores a 2023, lo que refleja la juventud del campo. El cribado por título y resumen se realizó de forma asistida por inteligencia artificial, con registro de la decisión y su justificación para cada registro y verificación posterior por los dos investigadores, quienes resuelven las discrepancias por consenso. El proceso completo se documenta en un diagrama de flujo PRISMA, y de los estudios incluidos se extrae una matriz estructurada con el tipo de problema abordado, la técnica propuesta, el dominio, las métricas y los resultados, insumo directo de la fase siguiente.

### 1.2 Actividades del objetivo específico 1, sin cambios

| No | Actividad | Mes |
|---|---|---|
| 1 | Formular y calibrar el protocolo y la cadena de búsqueda; ejecutar la búsqueda y la deduplicación. | M1 |
| 2 | Cribar por título y resumen con verificación de los revisores; evaluar elegibilidad en texto completo. | M1 y M2 |
| 3 | Extraer datos en la matriz estructurada y sintetizar la taxonomía de técnicas. | M2 |

### 1.3 Cadena de búsqueda

La cadena es la de la búsqueda piloto, con la que se calibró el protocolo (actividad 1), y es la misma de la exportación definitiva. Se transcribe literal desde el encabezado de los tres archivos CSV de este anexo:

```
("retrieval augmented generation" OR "RAG")
AND ("knowledge base" OR "corpus" OR "document preprocessing" OR "chunking"
     OR "data curation" OR "knowledge curation")
AND ("knowledge conflict" OR "inconsistency" OR "contradiction" OR "hallucination"
     OR "outdated knowledge" OR "temporal misalignment")
```

| Parámetro | Valor |
|---|---|
| Base | Dimensions |
| Campos | Título y resumen |
| Años de publicación | 2023 a 2026 |
| Tipos de publicación | Article, Proceeding y Preprint, exportados por separado |
| Fecha de exportación | 1 de agosto de 2026 |
| Registros | 269 artículos, 195 ponencias y 270 preprints: 734 en total |

## 2. Ajustes durante la ejecución

| # | Ajuste | Dónde se declara en el informe |
|---|---|---|
| 1 | **Criterios de elegibilidad ampliados.** El anteproyecto pedía evaluación empírica. En la ejecución se admitieron también los estudios que aportan instrumentos de evaluación de una intervención sobre el corpus y las revisiones secundarias; estas se usan como marco conceptual y no como evidencia. Los capítulos de libro y las monografías se excluyeron, y los estudios sin acceso a texto completo se trataron como no recuperados, no como excluidos. | Sección 7.1.1.1, Tabla 8 y su nota |
| 2 | **Dimensions como única fuente efectiva.** Las fuentes complementarias no se consultaron por separado. Los 734 registros proceden de Dimensions, que indexa los preprints de arXiv y las actas de IEEE y ACM. | Sección 7.1.1.2 |
| 3 | **Verificación humana del cribado por muestreo.** La verificación de los dos investigadores recayó sobre la clasificación de una muestra aleatoria de 16 de los 80 estudios de verificación rápida (91 % de acuerdo). Las exclusiones no tuvieron una segunda revisión humana. En 649 de los 692 registros la primera pasada se hizo por el título. | Secciones 1.2, 7.1.1.3 y 7.3 |
| 4 | **Lectura completa limitada al núcleo.** De los 107 elegibles, los 27 del núcleo se asignaron a partir del título y solo esos se buscaron en texto completo; se recuperaron 21 y seis quedaron como no recuperados. Los otros 80 se valoraron por título y resumen, aunque la actividad 2 preveía evaluar la elegibilidad en texto completo. | Secciones 7.1.1.3 y 7.3 |
| 5 | **Instrumentos de extracción y calidad detallados en la ejecución.** La matriz se definió con 39 campos y vocabulario controlado. Las reglas de decisión escritas se agregaron después del primer cotejo entre revisores. La calidad se valoró con un instrumento de ocho criterios derivado de Kitchenham y Charters (2007), de 0 a 2 puntos cada uno. | Secciones 7.1.1.4 y 7.1.1.5, Anexo C |

## Referencias

Kitchenham, B., y Charters, S. (2007). *Guidelines for performing systematic literature reviews in software engineering* (Informe técnico EBSE-2007-01). Keele University y Durham University.

Page, M. J., McKenzie, J. E., Bossuyt, P. M., Boutron, I., Hoffmann, T. C., Mulrow, C. D., Shamseer, L., Tetzlaff, J. M., Akl, E. A., Brennan, S. E., Chou, R., Glanville, J., Grimshaw, J. M., Hróbjartsson, A., Lalu, M. M., Li, T., Loder, E. W., Mayo-Wilson, E., McDonald, S., … Moher, D. (2021). The PRISMA 2020 statement: An updated guideline for reporting systematic reviews. *BMJ, 372*, n71. https://doi.org/10.1136/bmj.n71

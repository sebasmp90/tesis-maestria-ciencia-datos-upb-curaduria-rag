# Tarea: construir un banco de preguntas de evaluación sobre un corpus normativo del POT de Medellín

## Contexto

Somos dos estudiantes de la Maestría en Ciencia de Datos de la UPB. Nuestro trabajo de grado diseña una metodología para curar bases de conocimiento de sistemas RAG (recuperación aumentada con generación) en entidades públicas, aplicada al Plan de Ordenamiento Territorial (POT) de Medellín: el Acuerdo 48 de 2014, los decretos que lo reglamentan, sus documentos técnicos de soporte (DTS) y las fichas de indicadores del Programa de Ejecución.

En la prueba de concepto vamos a comparar el mismo sistema RAG en dos condiciones: sobre el corpus original y sobre el corpus curado. Para eso necesitamos un banco de preguntas con su respuesta esperada. El problema central que la curaduría ataca es la **vigencia**: normas que se derogan, se modifican, se renumeran o se reproducen en otros documentos, de modo que un sistema sin curar puede dar la respuesta de una norma que ya no rige o citar una fuente derogada.

Tú eres un **formulador independiente**. Otra persona está construyendo su propio banco en paralelo y después compararemos los dos. Por eso:

- No busques, abras ni uses ningún banco de preguntas, plantilla con ejemplos u hoja de cálculo de preguntas que encuentres. Trabaja solo con los documentos del corpus.
- No te bases en preguntas que se te ocurran por conocimiento previo del POT: cada pregunta y cada respuesta tienen que salir de los documentos que te entrego.

## Insumo

Los documentos del corpus están en Markdown (convertidos desde PDF): [ADJUNTAR O INDICAR DÓNDE ESTÁN LOS ARCHIVOS .md].

## Paso 1. Inventario antes de formular

Antes de escribir una sola pregunta, haz un inventario y muéstramelo:

1. Lista de documentos: tipo (acuerdo, decreto, resolución, DTS, ficha de indicador, informe u otro), número y año, tema, y si es texto normativo o un documento que reproduce o explica la norma.
2. Relaciones de vigencia **que los propios documentos declaren**: qué acto modifica, deroga, adiciona, integra o renumera qué artículo de qué otro acto, con la fecha desde la que rige (la cláusula «rige a partir de…»; si rige desde su publicación, la fecha de la Gaceta). Incluye las derogatorias genéricas («deroga las disposiciones que le sean contrarias») como casos dudosos.
3. Lugares donde un mismo texto o una misma cifra aparece en dos documentos distintos, sobre todo si uno de ellos está derogado.
4. Documentos que se citan pero no están en el corpus.

Este inventario es la base del estrato de colisión. No inventes relaciones: si un documento no lo dice, no existe para esta tarea.

## Paso 2. Formular las preguntas

Formula **70 preguntas** que cumplan estas metas aproximadas (cada pregunta cuenta en las cuatro dimensiones a la vez):

| Dimensión | Categorías y meta |
|---|---|
| Tipo cognitivo | Conceptual 25 · Procedimental 20 · Compuesta 25 |
| Tipo de respuesta | Textual 30 · Numérica 25 · Entidad 15 |
| Fuente principal | Acuerdo 20 · Decreto o resolución 25 · DTS 10 · Ficha de indicador 15 |
| Estrato de vigencia | Normal 42 · Colisión 20 · Sin respuesta 8 |

Definiciones:

- **Conceptual:** qué es, qué dice o qué establece algo. **Procedimental:** cómo se hace, qué pasos, qué requisitos, quién lo tramita. **Compuesta:** exige combinar dos o más disposiciones o documentos.
- **Textual:** la respuesta es una explicación. **Numérica:** la respuesta es una cifra con unidad (metros, m², porcentajes, plazos, índices, alturas). **Entidad:** la respuesta es un nombre (un instrumento, una dependencia, un artículo, un polígono, un mapa).
- **Colisión:** la respuesta correcta depende de saber qué norma está vigente, porque en el corpus hay una versión derogada, modificada, renumerada o reproducida que se parece. Distribuye las 20 entre los tipos que encuentres en el inventario: derogación, modificación parcial de un parágrafo o numeral, renumeración o integración de artículos, misma regla en un instrumento derogado y en uno vigente, remisión a una norma que ya no rige, y fuente compilada desactualizada.
- **Sin respuesta:** preguntas plausibles para un funcionario del POT cuyo tema **no** está en el corpus. Verifica buscando en todos los documentos que la respuesta no esté. La respuesta esperada es que el sistema se abstenga o advierta que la base no contiene esa información. Si el tema está en un documento citado pero ausente del corpus, dilo así.
- **Fecha de consulta:** por defecto «Hoy». Al menos 6 de las preguntas de colisión deben preguntar por lo que regía en una fecha pasada concreta (dd/mm/aaaa), elegida dentro del periodo de vigencia de una versión anterior.

Reglas de redacción:

1. Redacta como preguntaría un funcionario o un ciudadano. No pongas el número de artículo cuando esa persona no lo sabría.
2. **Parafrasea.** No copies la frase del artículo en la pregunta: una pregunta que repite las palabras exactas de la norma la vuelve trivial para la búsqueda léxica y no mide nada.
3. Reparte las preguntas entre todos los documentos del corpus. No más del 30 % puede apoyarse en un mismo documento.
4. Una pregunta, una respuesta verificable. Nada de preguntas de opinión ni de interpretación jurídica abierta.
5. Si para responder hace falta una interpretación jurídica que los documentos no resuelven (por ejemplo, una derogatoria tácita), no la descartes: márcala con vigencia «Por confirmar» y explica la duda en observaciones.

## Paso 3. Respuesta esperada de cada pregunta

- Escríbela fiel al texto normativo, sin agregar nada que el documento no diga.
- Si es numérica, pon la cifra también en la columna del valor, y la unidad en el texto.
- Identifica las unidades que la sustentan con el formato `{acto}:{artículo del acto}[.subunidad]`, donde el acto es el que **contiene** el texto. Ejemplos de formato: `A48-2014:a544`, `D2229-2019:a11`, `D2148-2015:a9.p2` (parágrafo 2). Si el texto vigente lo introdujo un decreto modificatorio, el identificador es el del decreto modificatorio, y en la columna «Instrumento y artículo» se escribe cómo se conoce ese artículo; por ejemplo: «Decreto 2148 de 2015, art. 7 (texto del Decreto 2229 de 2019, art. 11)».
- Copia en la columna de evidencia la frase exacta del documento que respalda la respuesta, entre comillas, con el nombre del archivo .md.
- Para colisión, explica en observaciones cuál es la respuesta equivocada que daría un sistema sin control de vigencia y de qué documento saldría.

## Paso 4. Entrega

Entrega **un archivo CSV en UTF-8** (separador coma, texto entre comillas dobles) con exactamente estas columnas, en este orden:

```
ID,Pregunta,Origen,Referencia del origen,Tipo cognitivo,Tipo de respuesta,Fuente principal,Estrato de vigencia,Fecha de consulta,¿Requiere varias fuentes?,Respuesta esperada,Valor esperado (numéricas),Unidades que la sustentan (id_texto),Instrumento y artículo,Vigencia de la fuente a la fecha,Formulada por,Estado,Validada por,Observaciones del funcionario,Evidencia literal,Observaciones del formulador
```

Valores permitidos (escríbelos exactamente así):

- ID: `AG-001` a `AG-070`
- Origen: `Formulada` · Referencia del origen: vacío
- Tipo cognitivo: `Conceptual`, `Procedimental`, `Compuesta`
- Tipo de respuesta: `Textual`, `Numérica`, `Entidad`
- Fuente principal: `Acuerdo`, `Decreto o resolución`, `DTS`, `Ficha de indicador`
- Estrato de vigencia: `Normal`, `Colisión`, `Sin respuesta`
- Fecha de consulta: `Hoy` o `dd/mm/aaaa`
- ¿Requiere varias fuentes?: `Sí`, `No`
- Vigencia de la fuente a la fecha: `Vigente`, `Derogada`, `Modificada`, `Por confirmar`, `No aplica`
- Formulada por: `Agente B` · Estado: `Borrador` · Validada por y Observaciones del funcionario: vacías

Después del CSV, entrega:

1. **El inventario del paso 1.**
2. **Una tabla de conteo** por dimensión y categoría contra la meta. Si alguna meta no se pudo cumplir porque el corpus no lo permite (por ejemplo, si no hay fichas de indicadores o no hay suficientes colisiones), dilo y explica cómo redistribuiste.
3. **La lista de preguntas con dudas:** las que marcaste «Por confirmar», las que dependen de un documento ausente y cualquier caso en que dos documentos se contradigan sin que esté claro cuál rige.

## Control antes de entregar

Revisa cada fila contra estas preguntas y corrige lo que falle:

- ¿La evidencia literal está realmente en el archivo que cito?
- ¿La respuesta esperada dice lo mismo que la evidencia, sin agregar nada?
- ¿El identificador de la unidad corresponde al acto que contiene el texto vigente a la fecha de consulta?
- En las de colisión, ¿expliqué cuál sería la respuesta equivocada y de dónde saldría?
- En las de sin respuesta, ¿busqué en todos los documentos y confirmé que no está?
- ¿La pregunta evita copiar las palabras exactas del artículo?

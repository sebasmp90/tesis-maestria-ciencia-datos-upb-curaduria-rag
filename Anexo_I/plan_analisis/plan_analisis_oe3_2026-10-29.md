# Plan de análisis del OE3 (fijado el 29 de octubre de 2026, antes de recibir la calificación humana)

Este plan se escribe antes de que Iván entregue la calificación ciega, para que las pruebas y los umbrales no se elijan a la vista de los resultados. Las métricas automáticas ya se vieron (ver `oe3_scripts_y_curaduria.md`), así que este plan solo es preregistrado para lo que sale de la calificación humana. Eso se declara en el informe.

## Datos

- **Banco principal:** D (70 preguntas: 42 Normal, 20 Colisión, 8 Sin respuesta), calificado completo por Iván. Se reporta con las 70 y sin las 21 solapadas con B (49).
- **Respaldo:** C y B, muestras de 30 (semilla 20261029), si se califican; si no, solo métricas automáticas.
- **Condiciones calificadas:** A_demo (corpus original, densa, sin prefijos; línea base), A_hibrida (mejor versión del corpus original), B (metodología completa) y B_bm25 (base curada, solo léxica).
- **Unidad de análisis:** la pregunta. Las comparaciones son pareadas: el mismo banco y las mismas preguntas en todas las condiciones.

## Variables por respuesta

- **Satisfactoria** (1/0, humana). En «Sin respuesta», 1 = se abstiene.
- **Error de vigencia** (derivada): 1 si la respuesta responde y «Cita fuente vigente» = 0; 0 en otro caso (incluida la abstención, que no cita nada).
- **Alucina** (1/0, humana).
- **Abstención** (automática, `se_abstuvo`).
- **Cita exacta** (automática, aproximación): el artículo citado como fuente principal coincide, a nivel de artículo, con alguna unidad esperada del banco. Se reporta como aproximación y no como medida humana.
- **Costo por consulta** (automático): tokens de entrada y salida, segundos por respuesta (mediana y p90).

## Comparación principal (una sola, para no multiplicar pruebas)

**B frente a A_demo, error de vigencia, estrato Colisión del banco D (20 preguntas).** Prueba de McNemar exacta (binomial sobre los pares discordantes), bilateral, α = 0,05. Se reporta la diferencia de proporciones con intervalo de confianza del 95 % por bootstrap pareado sobre preguntas (10.000 remuestreos, semilla 20261029).

Con 20 preguntas la potencia es baja: si la prueba no rechaza, se informa como «no concluyente», no como «sin efecto».

## Comparaciones secundarias (descriptivas, con corrección de Holm)

1. Las mismas pruebas para B_bm25 frente a A_demo y para B y B_bm25 frente a A_hibrida.
2. Error de vigencia en todo D (62 preguntas con respuesta) y en D sin solapadas.
3. Satisfactoria y alucinación por condición y por estrato, con IC del 95 %.

## Criterios de aceptación (Tabla 6 del informe), cómo se decide cada uno

| # | Criterio | Medida | Se cumple si |
|---|---|---|---|
| 1 | Vigencia de las fuentes citadas | Error de vigencia, Colisión de D | McNemar p < 0,05 a favor de B frente a A_demo |
| 2 | Fidelidad y precisión del contexto sin deterioro | Alucina (humana) y artículo esperado en el contexto (automática) | La alucinación de B no supera la de A_demo en más de 10 puntos y el artículo esperado en el contexto no es menor |
| 3 | Exactitud de las citas | Cita exacta (automática, aproximación) | B ≥ A_demo |
| 4 | Rehúso en «Sin respuesta» sin aumento en las respondibles | Abstención automática | B se abstiene más que A_demo en «Sin respuesta» y no más en las respondibles |
| 5 | Costo por consulta sin incremento | Tokens y segundos por respuesta; costo de curar aparte | La mediana de B no supera la de A_demo en más del 10 % |

El criterio 4 ya se ve fallido con las métricas automáticas de D (A_demo se abstiene en 8 de 8 «Sin respuesta»; B, en 4 de 8). Se reporta tal cual, con el matiz del desfase de corpus: tres de esas preguntas tienen contenido relacionado en el Acuerdo 48, que el banco D no consideró.

## Sustituciones frente a lo prometido en la sección 5.3

- **RAGAS (fidelidad, precisión del contexto):** no se ejecuta. Fidelidad → «Alucina» de la calificación humana. Precisión y recall del contexto → «artículo esperado» y «evidencia literal» en el contexto, calculadas automáticamente.
- **recall@k y nDCG:** se reporta «artículo esperado en el contexto», que equivale a un recall sobre el contexto entregado al modelo. nDCG no se calcula.
- **Acuerdo interevaluador:** si D tiene un solo evaluador, no se calcula kappa y se declara como limitación.
- **Importe en dólares:** no aplica (todo corre en local, en el servidor del director). El costo se reporta en tokens, tiempo y minutos de indexación.

## Casos que se reportan aparte

- **AG-161:** contradicción interna del Decreto 1143 de 2023; en la rúbrica se acepta cualquiera de las dos lecturas.
- **«Sin respuesta» de C y D con contenido relacionado en el Acuerdo 48** (en D: AG-204, AG-206 y AG-207): se reportan de las dos formas, contra la respuesta esperada y anotando el respaldo.

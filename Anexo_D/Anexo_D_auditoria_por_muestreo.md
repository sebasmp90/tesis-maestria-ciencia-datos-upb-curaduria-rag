# Anexo D. Informe de la auditoría por muestreo de la extracción

Metodología de curaduría de bases de conocimiento para sistemas RAG en entidades públicas: el caso del POT de Medellín. Sebastián Muñoz Palacio e Iván Velasco Arias. Maestría en Ciencia de Datos, Universidad Pontificia Bolivariana.

## 1. Procedimiento de selección

- **Marco de muestreo:** los diecisiete estudios del núcleo que no se sometieron a relectura durante la resolución de desacuerdos, ordenados alfabéticamente.
- **Método:** muestreo aleatorio simple con semilla declarada (20260915) sobre el marco ordenado alfabéticamente.
- **Muestra:** cinco estudios, el 23,8 % del núcleo: N02, N05, N07, N11 y N19. Tres de banda de calidad alta y dos de banda media; cuatro preprints y un artículo de revista; cuatro etapas distintas del pipeline.

## 2. Condiciones de la reclasificación

Cada estudio se reclasificó en condiciones ciegas. El revisor, una lectura asistida por inteligencia artificial y aislada de la extracción, recibió únicamente el texto completo del artículo y el libro de códigos (definiciones de campo, vocabularios controlados, reglas de decisión y descriptores de calidad), sin acceso a la matriz ni a ninguna clasificación previa. Se compararon veintiuna celdas por estudio: trece campos de vocabulario controlado y los ocho criterios de calidad, ciento cinco celdas en total.

## 3. Resultados de acuerdo

| Nivel de comparación | Acuerdo |
|---|---|
| Campos de vocabulario controlado | 51 / 65 = 78,5 % |
| Criterios de calidad | 30 / 40 = 75,0 % |
| Global, celda por celda | 81 / 105 = 77,1 % |
| Banda de calidad asignada | 5 / 5 = 100 % |

- **Ningún estudio cambió de banda:** las diferencias de puntaje total fueron de entre menos dos y más un punto sobre dieciséis.
- **El orden relativo se conserva:** de los diez pares comparables, nueve quedan ordenados igual.
- **La discrepancia es sobre todo sistemática:** el revisor independiente resultó en promedio 0,8 puntos más severo.

## 4. Análisis de las discrepancias

De las veinticuatro celdas discrepantes:

| Tipo | Celdas | Tratamiento |
|---|---|---|
| Defectos de la extracción original | 5 | Corregidos en la matriz, con su argumento en la hoja de trazabilidad |
| Sesgo de sobreatribución que la regla E controla | 4 | Confirman la función de la regla |
| Error del revisor independiente (declaró un efecto sobre el costo en un estudio que no lo mide) | 1 | Se mantuvo el valor de la extracción |
| Juicios limítrofes sobre criterios con más de una lectura defendible | 14 | Se mantuvo el valor de la extracción |

## 5. Consecuencias

1. El acuerdo del 100 % en la banda es el resultado relevante para la síntesis, porque la banda pondera la evidencia.
2. El recálculo aritmético del revisor independiente encontró en los cinco estudios discrepancias no registradas en la verificación previa. Por eso la proporción de estudios con cifras que no cuadran (sección 7.1.1.6 del informe) se enuncia como cota inferior: al menos diez de veintiuno.
3. Las correcciones de las cinco celdas defectuosas se incorporaron a la matriz del Anexo C.

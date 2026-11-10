# Anexo I. Código, base curada y plan de análisis

Prueba de concepto de la tesis *Desarrollo de una metodología de curaduría de bases de conocimiento para sistemas RAG en entidades públicas: el caso del POT de Medellín* (Muñoz Palacio y Velasco Arias, Maestría en Ciencia de Datos, UPB).

## Contenido

| Carpeta | Contenido |
|---|---|
| `codigo/` | `inventario.py` (paso 0, inventario manual de actos, fechas y derogatorias); `curar.py` (pasos 1 a 6, sin modelos de lenguaje); `validar_curaduria.py` (control de salida contra los bancos); `indexar.py`; `experimento.py`; `diagnostico_recuperacion.py`; `comun.py` y `config.py` (configuración fija de todas las condiciones); `muestra_calificacion.py` y `armar_calificacion.py` (hojas de calificación ciega); `analisis.py` (pruebas, intervalos, kappa y tablas del informe). |
| `instrucciones/` | `instrucciones_respuesta.md` (cómo responder una pregunta normativa y cómo citar) y `guardarrailes.md`. |
| `base_curada/` | `unidades.jsonl.zip` (la base: 9.529 registros con su vigencia y linaje, comprimida; descomprimida pesa 22 MB), `manifiesto.md`, `afectaciones.csv` (340 relaciones), `revision.csv` (70 casos para revisión), `pendientes.csv`, `reproducciones.csv` y `registro_costo.json`. |
| `corpus_A/` | Los 37 Markdown del corpus original: 31 decretos, el Acuerdo 48 de 2014 y los cinco archivos del caso ancla. Es la entrada de la condición A y de la curaduría. |
| `corridas_banco_D/` | Respuestas del banco D: `demo_A/` (sistema de referencia) y `exp2/` (A_hibrida, B, B_densa, B_bm25 y controles), con el contexto que recibió el modelo, los tiempos y los tokens. |
| `plan_analisis/` | Plan de análisis fijado el 29 de octubre de 2026, antes de recibir la calificación. |

## Condiciones (Tabla 20 del informe)

A_demo (corpus original, densa sin prefijos: réplica de la demostración del director), A (densa con prefijos), A_hibrida (densa y léxica), B (base curada con el contrato de consulta del paso 6), B_densa (solo densa) y B_bm25 (solo léxica).

## Requisitos

Python 3.12 con `numpy`, `scipy` y `openpyxl`. Para indexar y consultar, además, LangChain, Chroma y Ollama con `qwen3:8b` (temperatura 0, semilla 42, ventana de 8.192 tokens, razonamiento desactivado) y `nomic-embed-text`. Las rutas se resuelven desde la carpeta `Anexo_I/`, de modo que esta carpeta debe conservarse junto a `Anexo_F/` y `Anexo_G/`, como se entrega. Para indexar y consultar, copie los tres bancos del Anexo F en `Anexo_I/preguntas/`.

## Orden de ejecución

Los comandos se ejecutan desde la carpeta `Anexo_I/`.

1. `python codigo/curar.py`: construye la base curada en `curaduria/` (termina con «Listo: 9529 registros»). Los archivos resultantes son idénticos a los de `base_curada/`; solo cambia la fecha de corte del manifiesto, que es la del día de ejecución.
2. `python codigo/validar_curaduria.py ../Anexo_F/banco_agente_D.csv`: control de salida contra el banco D.
3. `python codigo/indexar.py A` y `python codigo/indexar.py B`; con `--prefijos`, los índices con prefijos de tarea.
4. `python codigo/experimento.py preguntas/banco_agente_D.csv --prefijos --etiqueta exp2_D`: corre las condiciones; `--simular` prueba el flujo sin GPU.
5. `python codigo/diagnostico_recuperacion.py preguntas/banco_agente_B.csv --prefijos`: diagnóstico de la recuperación sin modelo de lenguaje.
6. `python codigo/analisis.py`: lee la calificación y su cruce con las condiciones (Anexo G), el banco D (Anexo F) y las respuestas de `corridas_banco_D/`, y reproduce las pruebas y tablas de la sección 7.1.3.7 en `resultados/`. Los pasos 1, 2 y 6 no requieren GPU ni modelos.

`config.py` trae `CONTRATO_B = "v2"` (ensamblaje ajustado), la configuración fijada el 28 de octubre de 2026 y corrida sobre los bancos D y C el 29 de octubre.

## Notas

- La base de `base_curada/` se regeneró el 2 de noviembre de 2026 con el mismo script y los mismos insumos que la usada en las corridas; los conteos son idénticos a los de la Tabla 19. Correr `curar.py` sobre `corpus_A/` reproduce la misma base byte a byte.
- Frente a la versión que corrió en el servidor, solo se ajustaron rutas para que el código funcione dentro de esta carpeta: `config.py` resuelve las carpetas desde `Anexo_I/` y `analisis.py` lee la calificación y el cruce con las condiciones desde el Anexo G. La lógica de curaduría, consulta y análisis no cambió.
- El plan de análisis se entrega tal como se escribió el 29 de octubre: su «Tabla 6 del informe» corresponde a la Tabla 7 de la versión final, y `oe3_scripts_y_curaduria.md` es una nota interna que no se incluye.

- En el Decreto 838 de 2023 (`corpus_A/Decreto-0838-de-2023-adicion-al-0818-de-2021.md`) se omitieron, con la marca «[omitido]», los nombres y los números de documento de la tabla de beneficiarios, por protección de datos personales (Ley 1581 de 2012). La base de `base_curada/` se construyó con ese corpus; las cifras de la base no cambian.

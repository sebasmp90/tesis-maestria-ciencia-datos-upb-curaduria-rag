"""Configuración común del experimento del OE3.

Todo lo que debe ser IDÉNTICO en las condiciones A (corpus original) y
B (corpus curado) vive aquí: modelo, embeddings, instrucciones, k y
presupuesto de contexto. Si cambias algo, cámbialo aquí y queda
registrado en el manifiesto de cada corrida.
"""
from datetime import date
from pathlib import Path

# --- Carpetas (relativas a ~/tesis_oe3) ---------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent  # carpeta Anexo_I: corpus_A/, instrucciones/ y preguntas/ quedan al lado de codigo/
CORPUS_A_DIR = BASE_DIR / "corpus_A"          # Markdown tal cual se convirtieron
CURADURIA_DIR = BASE_DIR / "curaduria"        # salida de curar.py (condición B)
UNIDADES_B = CURADURIA_DIR / "unidades.jsonl"
INSTRUCCIONES_DIR = BASE_DIR / "instrucciones"
PREGUNTAS_DIR = BASE_DIR / "preguntas"
RESULTADOS_DIR = BASE_DIR / "resultados"
CHROMA_A_DIR = BASE_DIR / "chroma_A"          # índice propio de la condición A
CHROMA_B_DIR = BASE_DIR / "chroma_B"          # índice propio de la condición B

# --- Modelos (servidor del director, Ollama en Docker) ------------------
OLLAMA_URL = "http://localhost:11434"
CHAT_MODEL = "qwen3:8b"
EMBED_MODEL = "nomic-embed-text"
TEMPERATURA = 0
SEMILLA = 42
NUM_CTX = 8192          # Ollama trae 2048/4096 por defecto: sin esto recorta el contexto en silencio
RAZONAMIENTO = False    # Qwen3 "piensa" por defecto; False = respuesta directa y reproducible

# --- Condición A: igual que rag_demo.py del director ---------------------
CHUNK_SIZE_A = 500
CHUNK_OVERLAP_A = 80

# --- Recuperación (igual para A y B) -------------------------------------
PRESUPUESTO_CONTEXTO = 6000   # caracteres de contexto que recibe el modelo en ambas condiciones
K_CANDIDATOS = 30             # candidatos que se piden al índice antes de ensamblar

# --- Solo condición B: contrato de consulta del paso 6 -------------------
RRF_K = 60                    # fusión por rango recíproco de la búsqueda densa y la léxica (BM25)
CUPO_HISTORICO = 2            # unidades no vigentes a la fecha que entran rotuladas (0 = contrato estricto)
CUPO_HISTORICO_CHARS = 1800   # y como máximo esta parte del presupuesto de contexto
CUPO_HISTORICO_INTENCION = 4          # si la pregunta pide la historia de la norma (qué decía, por qué se derogó…)
CUPO_HISTORICO_INTENCION_CHARS = 3600
MAX_POR_INSTRUMENTO_1RA_VUELTA = 1   # cubrir instrumentos antes de repetir
PROFUNDIDAD_GRAFO = 1         # completar por el grafo (relaciones de la unidad)
MAX_AGREGADAS_GRAFO = 3

# Versión del ensamblaje de B. "v1" = el de exp1 (preregistrado). "v2" = corregido tras exp1:
# en exp1 el artículo esperado se perdía al ensamblar aunque la búsqueda lo tuviera arriba.
CONTRATO_B = "v2"
DIRECTOS_V2 = 3               # v2: los primeros del ranking entran siempre, sin regla de diversidad
CUPO_HISTORICO_HOY = 1        # v2: si la consulta es de hoy y no pide la historia, el canal histórico se reduce
CUPO_HISTORICO_HOY_CHARS = 900

# nomic-embed-text está entrenado con prefijos de tarea («search_query: » / «search_document: »).
# exp1 no los usaba (igual que el demo). Con --prefijos se usan en A y en B por igual, en índices aparte (*_prefijo).
PREFIJOS_EMBEDDINGS = False

FECHA_HOY = date.today().isoformat()   # fecha de la consulta «Hoy»; se le dice al modelo en todas las condiciones.
                                       # Al reanudar con --continuar se usa la de la corrida original.

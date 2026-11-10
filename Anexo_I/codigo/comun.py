"""Piezas compartidas por indexar.py y experimento.py."""
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from datetime import date

import config as C

# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------

def normalizar(texto: str) -> str:
    """minúsculas, sin tildes, sin marcas de Markdown y con espacios simples."""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = t.lower()
    t = re.sub(r"[*_`#>|]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


STOP = set(
    "a al algo ante antes como con contra cual cuales cuando de del desde donde dos e el ella ellas "
    "ellos en entre era es esa ese eso esta este esto fue ha han hasta la las le les lo los mas me "
    "mi muy ni no nos o otra otro para pero por que qu quien se sea segun ser si sin sobre son su "
    "sus tambien tiene tienen un una uno unos unas y ya cada debe deben puede pueden hay".split()
)


def tokens(texto: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", normalizar(texto)) if w not in STOP]


# ---------------------------------------------------------------------------
# BM25 en Python puro (rank_bm25 no está instalado en el servidor)
# ---------------------------------------------------------------------------

class BM25:
    def __init__(self, docs: dict[str, str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf: dict[str, Counter] = {}
        self.largo: dict[str, int] = {}
        df: Counter = Counter()
        for doc_id, texto in docs.items():
            tk = tokens(texto)
            c = Counter(tk)
            self.tf[doc_id] = c
            self.largo[doc_id] = len(tk)
            df.update(c.keys())
        n = max(len(docs), 1)
        self.prom = sum(self.largo.values()) / n if docs else 0
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}

    def buscar(self, consulta: str, ids_permitidos: set[str] | None, k: int) -> list[tuple[str, float]]:
        q = tokens(consulta)
        puntajes = []
        universo = ids_permitidos if ids_permitidos is not None else self.tf.keys()
        for doc_id in universo:
            c = self.tf.get(doc_id)
            if not c:
                continue
            s = 0.0
            dl = self.largo[doc_id]
            for w in q:
                f = c.get(w)
                if f:
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.prom))
            if s > 0:
                puntajes.append((doc_id, s))
        puntajes.sort(key=lambda x: -x[1])
        return puntajes[:k]


def rrf(*listas: list[str], k: int = 60) -> list[str]:
    """Fusión por rango recíproco de varias listas ordenadas de ids."""
    s: dict[str, float] = {}
    for lista in listas:
        for pos, doc_id in enumerate(lista):
            s[doc_id] = s.get(doc_id, 0.0) + 1.0 / (k + pos + 1)
    return [d for d, _ in sorted(s.items(), key=lambda x: -x[1])]


# ---------------------------------------------------------------------------
# Fecha de la consulta (contrato de consulta, paso 6)
# ---------------------------------------------------------------------------

MESES = {m: i + 1 for i, m in enumerate(
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split())}
MESES["setiembre"] = 9
PARTE_DEL_ANO = {"comienzos": (2, 15), "principios": (2, 15), "inicios": (2, 15),
                 "mediados": (6, 15), "finales": (12, 31), "fines": (12, 31)}


def _fecha_segura(a: int, m: int, d: int) -> str | None:
    try:
        return date(a, m, d).isoformat()
    except ValueError:
        return None


def detectar_fecha(pregunta: str) -> tuple[str, str]:
    """Devuelve (fecha ISO, regla que la detectó). Sin fecha explícita -> hoy.

    Solo se toman expresiones que preguntan por un momento: dd/mm/aaaa, «el 1 de junio de 2020»,
    «a mediados de 2020», «en junio de 2017», «antes de 2022». Un año suelto («el decreto de 2014»)
    no es una fecha de consulta, y tampoco la fecha que acompaña a un acto («Acuerdo 48 del 17 de
    diciembre de 2014», «Decreto 1143 de 2023»).
    """
    t = normalizar(pregunta)
    # quitar las fechas que identifican actos: «decreto 2148 de 2015», «acuerdo 48 del 17 de diciembre de 2014»
    t = re.sub(r"\b(decreto|acuerdo|resolucion|ley|gaceta)\s+(?:municipal\s+|distrital\s+|n[o°º.]*\s*)?\d+"
               r"(?:\s+(?:de|del)\s+(?:\d{1,2}\s+de\s+[a-z]+\s+de\s+)?\d{4})?", " ", t)
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", t)
    if m:
        d, mo, a = map(int, m.groups())
        f = _fecha_segura(a, mo, d)
        if f:
            return f, "dd/mm/aaaa"
    m = re.search(r"\b(\d{1,2})\s+de\s+(" + "|".join(MESES) + r")\s+de(?:l)?\s+(\d{4})\b", t)
    if m:
        f = _fecha_segura(int(m.group(3)), MESES[m.group(2)], int(m.group(1)))
        if f:
            return f, "día de mes de año"
    m = re.search(r"\b(comienzos|principios|inicios|mediados|finales|fines) de(?:l ano)? (\d{4})\b", t)
    if m:
        mo, d = PARTE_DEL_ANO[m.group(1)]
        return date(int(m.group(2)), mo, d).isoformat(), m.group(1)
    m = re.search(r"\b(" + "|".join(MESES) + r") de(?:l ano)? (\d{4})\b", t)
    if m:
        return date(int(m.group(2)), MESES[m.group(1)], 15).isoformat(), "mes de año"
    m = re.search(r"\bantes de(?:l ano)? (\d{4})\b", t)
    if m:
        return date(int(m.group(1)) - 1, 12, 31).isoformat(), "antes de año"
    return C.FECHA_HOY, "hoy"


INTENCION_HISTORICA = re.compile(
    r"(por que se (derogo|modifico|reemplazo|cambio|ajusto)|que (decia|establecia|regulaba|fijaba|buscaba)|"
    r"\bse derogo|\bfue derogad|\bderogad[oa]s?\b|\breemplazad|\bsustituid|\bnorma anterior|\bdecreto anterior|"
    r"\bantes de(?:l ano)? \d{4}|\bantes de (?:su|la) (?:revision|reforma|modificacion|derogatoria)|\banterior(es)?\b|"
    r"\bya no rige|\bregia\b|\bregulaban\b|"
    r"\bcuando se (reglamento|expidio|adopto|reviso)|\bque buscaban|\bse reviso|\bque decretos?\b.*\b(regularon|derogo|reemplazo))")


def intencion_historica(pregunta: str) -> bool:
    """La pregunta pide expresamente la historia de la norma (qué decía, por qué se derogó, qué había antes)."""
    return bool(INTENCION_HISTORICA.search(normalizar(pregunta)))


def fecha_num(iso: str | None, defecto: int) -> int:
    if not iso:
        return defecto
    return int(iso.replace("-", "")[:8])


# ---------------------------------------------------------------------------
# Instrucciones y llamada al modelo
# ---------------------------------------------------------------------------

def cargar_instrucciones() -> tuple[str, dict]:
    partes, versiones = [], {}
    for nombre in ("instrucciones_respuesta.md", "guardarrailes.md"):
        texto = (C.INSTRUCCIONES_DIR / nombre).read_text(encoding="utf-8")
        partes.append(texto.strip())
        m = re.search(r"Versión:\s*([\w.]+)", texto)
        versiones[nombre] = m.group(1) if m else "?"
    sistema = "\n\n".join(partes)
    sistema += f"\n\nFecha de hoy: {C.FECHA_HOY}."
    return sistema, versiones


def mensaje_usuario(contexto: str, pregunta: str) -> str:
    return f"Contexto:\n\n{contexto}\n\n---\n\nPregunta: {pregunta}"


def limpiar_respuesta(texto: str) -> tuple[str, str]:
    """Separa un posible bloque <think> de la respuesta."""
    m = re.search(r"<think>(.*?)</think>", texto, flags=re.S)
    pensamiento = m.group(1).strip() if m else ""
    limpio = re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()
    # El modelo a veces copia la cerca ``` del formato de las instrucciones: se quita (igual en todas las condiciones).
    limpio = re.sub(r"^```[a-zA-Z]*\s*\n?", "", limpio)
    limpio = re.sub(r"\n?\s*```\s*$", "", limpio).strip()
    return limpio, pensamiento


FRASE_ABSTENCION = "la base de conocimiento no contiene informacion"


def se_abstuvo(respuesta: str) -> bool:
    """Abstención = la respuesta empieza con la frase de abstención (no basta con mencionarla de paso)."""
    t = normalizar(respuesta)
    t = re.sub(r"^respuesta\s*:\s*", "", t)
    return t.startswith(FRASE_ABSTENCION) or (FRASE_ABSTENCION in t[:160])


def evidencias(campo: str) -> list[str]:
    """Frases de la columna «Evidencia literal»: «...» (archivo.md) | «...» (archivo.md)."""
    if not campo:
        return []
    frases = re.findall(r"«(.+?)»", campo, flags=re.S)
    return [f for f in frases if len(f.strip()) >= 8]


def evidencia_recuperada(frases: list[str], contexto: str) -> float | None:
    """Fracción de las frases de evidencia que aparecen (normalizadas) en el contexto."""
    if not frases:
        return None
    ctx = normalizar(contexto)
    ok = 0
    for f in frases:
        nf = normalizar(f)
        # basta un tramo central de 60 caracteres: tolera cortes de fragmento
        tramo = nf if len(nf) <= 60 else nf[len(nf) // 2 - 30: len(nf) // 2 + 30]
        ok += tramo in ctx
    return ok / len(frases)


def jsonl(path, filas):
    with open(path, "w", encoding="utf-8") as f:
        for fila in filas:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Modelos (reales en el servidor; simulados para probar el flujo sin GPU)
# ---------------------------------------------------------------------------

def embeddings(simular: bool = False):
    if simular:
        from langchain_core.embeddings import DeterministicFakeEmbedding
        base = DeterministicFakeEmbedding(size=256)
    else:
        from langchain_ollama import OllamaEmbeddings
        base = OllamaEmbeddings(model=C.EMBED_MODEL, base_url=C.OLLAMA_URL, num_ctx=2048)
    return _ConPrefijo(base) if C.PREFIJOS_EMBEDDINGS else base


try:
    from langchain_core.embeddings import Embeddings as _Emb
except Exception:  # pragma: no cover
    _Emb = object


class _ConPrefijo(_Emb):
    """Antepone los prefijos de tarea de nomic-embed-text a documentos y consultas."""
    def __init__(self, base):
        self.base = base

    def embed_documents(self, textos):
        return self.base.embed_documents([f"search_document: {t}" for t in textos])

    def embed_query(self, texto):
        return self.base.embed_query(f"search_query: {texto}")


def modelo_chat(simular: bool = False, nombre: str | None = None):
    if simular:
        from langchain_core.language_models.fake_chat_models import FakeListChatModel
        return FakeListChatModel(responses=[
            "Respuesta: (simulada) La base de conocimiento no contiene información para responder esta pregunta.\n\nFuentes:"
        ] * 10000)
    from langchain_ollama import ChatOllama
    return ChatOllama(model=nombre or C.CHAT_MODEL, base_url=C.OLLAMA_URL, temperature=C.TEMPERATURA,
                      seed=C.SEMILLA, num_ctx=C.NUM_CTX, reasoning=C.RAZONAMIENTO)


def dir_chroma(condicion: str, simular: bool):
    base = C.CHROMA_A_DIR if condicion == "A" else C.CHROMA_B_DIR
    if C.PREFIJOS_EMBEDDINGS:
        base = base.with_name(base.name + "_prefijo")
    return base.with_name(base.name + "_sim") if simular else base

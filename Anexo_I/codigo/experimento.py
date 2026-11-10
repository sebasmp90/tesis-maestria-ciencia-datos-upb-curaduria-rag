"""Corre el banco de preguntas en las condiciones del experimento y guarda los resultados.

    python experimento.py preguntas/banco.csv                    # las cuatro condiciones, todas las preguntas
    python experimento.py preguntas/banco.csv --limite 3         # prueba con 3 preguntas
    python experimento.py preguntas/banco.csv --ids AG-001,AG-063
    python experimento.py preguntas/banco.csv --condiciones A,B
    python experimento.py preguntas/banco.csv --modelo qwen3:14b --etiqueta exp2_qwen14b
    python experimento.py preguntas/banco.csv --continuar resultados/2026-10-28_153012_exp1

Condiciones:
    A           corpus original troceado a 500/80 y búsqueda densa (igual que el demo del director)
    B           base curada con el contrato de consulta completo (filtro de vigencia, híbrida, grafo, jerarquía)
    A_hibrida   control: corpus original con la misma búsqueda híbrida que B (densa + BM25), sin filtros
    B_densa     control: base curada con el contrato, pero con búsqueda solo densa
    B_bm25      variante: base curada con el contrato y búsqueda solo léxica (BM25), sin embeddings
Los dos controles permiten separar el efecto de la base curada del efecto de la búsqueda híbrida.
El modelo, las instrucciones, la temperatura y el presupuesto de contexto son los mismos en todas.

Salida en resultados/<fecha>_<etiqueta>/:
    manifiesto.json            qué se corrió y con qué configuración
    respuestas.jsonl           un registro por pregunta y condición (incluye el contexto)
    para_calificar_ciego.csv   respuestas en orden aleatorio, sin decir de qué condición son (para calificar)
    clave_ciego.csv            a qué condición corresponde cada respuesta (no se le entrega a quien califica)
    para_calificar.csv         las condiciones lado a lado, rotuladas (para el análisis, después de calificar)
    resumen.md                 métricas automáticas
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import platform
import random
import re
import statistics
import time
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, SystemMessage

import comun
import config as C

JERARQUIA = {"Acuerdo": 0, "Decreto": 1, "Resolución": 2, "DTS": 3, "Ficha": 4}
CONDICIONES = ("A", "B", "A_hibrida", "B_densa", "B_bm25")


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------------------
# Banco
# ---------------------------------------------------------------------------

def leer_banco(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        filas = [dict(r) for r in csv.DictReader(f)]
    if not filas or "ID" not in filas[0] or "Pregunta" not in filas[0]:
        raise SystemExit("El banco debe tener al menos las columnas «ID» y «Pregunta».")
    return [r for r in filas if (r.get("Pregunta") or "").strip()]


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def abrir_indice(cond_base: str, simular: bool) -> Chroma:
    """Abre el índice y comprueba que esté completo y que corresponda a la base actual."""
    carpeta = comun.dir_chroma(cond_base, simular)
    db = Chroma(collection_name=f"condicion_{cond_base}", embedding_function=comun.embeddings(simular),
                persist_directory=str(carpeta))
    n = db._collection.count()
    reg = carpeta / "registro_indexacion.json"
    if not n:
        raise SystemExit(f"El índice {cond_base} está vacío. Corre: python indexar.py {cond_base}")
    if not reg.exists():
        raise SystemExit(f"El índice {cond_base} quedó incompleto (no tiene registro). Corre: python indexar.py {cond_base} --reconstruir")
    r = json.loads(reg.read_text(encoding="utf-8"))
    if r.get("fragmentos") != n:
        raise SystemExit(f"El índice {cond_base} tiene {n} fragmentos y su registro dice {r.get('fragmentos')}. "
                         f"Corre: python indexar.py {cond_base} --reconstruir")
    if cond_base == "B" and r.get("sha256_unidades") != sha256(C.UNIDADES_B):
        raise SystemExit("La base curada cambió después de indexarla (se volvió a correr curar.py). "
                         "Corre: python indexar.py B --reconstruir")
    return db


# ---------------------------------------------------------------------------
# Mapa de líneas del corpus a unidades curadas (para medir la unidad esperada también en A)
# ---------------------------------------------------------------------------

class MapaUnidades:
    def __init__(self):
        self.por_archivo: dict[str, list[tuple[int, int, str]]] = {}
        if not C.UNIDADES_B.exists():
            return
        vistos = set()
        for linea in C.UNIDADES_B.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            u = json.loads(linea)
            if u.get("particion") not in ("activa", "historica") or not u.get("lineas") or u["id_texto"] in vistos:
                continue
            vistos.add(u["id_texto"])
            ini, fin = u["lineas"]
            self.por_archivo.setdefault(u["archivo"], []).append((ini, fin, u["id_texto"]))
        for v in self.por_archivo.values():
            v.sort()
        self.inicios = {k: [x[0] for x in v] for k, v in self.por_archivo.items()}

    def unidad(self, archivo: str, linea: int | None) -> str | None:
        if linea is None or archivo not in self.por_archivo:
            return None
        k = bisect.bisect_right(self.inicios[archivo], linea) - 1
        if k >= 0:
            ini, fin, uid = self.por_archivo[archivo][k]
            if ini <= linea <= fin:
                return uid
        return None


# ---------------------------------------------------------------------------
# Condición A (y su control A_hibrida)
# ---------------------------------------------------------------------------

class RecuperadorA:
    def __init__(self, simular: bool, hibrida: bool = False):
        self.db = abrir_indice("A", simular)
        self.hibrida = hibrida
        self.mapa = MapaUnidades()
        if hibrida:
            # los mismos fragmentos del índice A, regenerados con el mismo troceador (Chroma no deja leer 36 mil de una vez)
            from indexar import documentos_A
            self.docs = {i: (d.page_content, d.metadata) for i, d in documentos_A()}
            self.bm25 = comun.BM25({i: d for i, (d, _) in self.docs.items()})

    def contexto(self, pregunta: str):
        densos = self.db.similarity_search_with_score(pregunta, k=C.K_CANDIDATOS)
        candidatos = [(f"{d.metadata.get('archivo')}#{d.metadata.get('fragmento')}", d.page_content, d.metadata, round(float(s), 4))
                      for d, s in densos]
        if self.hibrida:
            orden = comun.rrf([c[0] for c in candidatos], [i for i, _ in self.bm25.buscar(pregunta, None, C.K_CANDIDATOS)], k=C.RRF_K)
            por_id = {c[0]: c for c in candidatos}
            candidatos = [por_id.get(i) or (i, self.docs[i][0], self.docs[i][1], None) for i in orden]
        partes, frags, usados = [], [], 0
        for cid, texto, md, dist in candidatos:
            n = len(frags) + 1
            bloque = f"[Fragmento {n} · archivo: {md.get('archivo')}]\n{texto}"
            if usados + len(bloque) > C.PRESUPUESTO_CONTEXTO:
                continue
            partes.append(bloque)
            frags.append({"pos": n, "archivo": md.get("archivo"), "fragmento": md.get("fragmento"), "linea": md.get("linea"),
                          "unidad_curada": self.mapa.unidad(md.get("archivo"), md.get("linea")),
                          "distancia": dist, "chars": len(bloque), "canal": "hibrido" if self.hibrida else "denso"})
            usados += len(bloque)
        return "\n\n".join(partes), frags, {"fecha_consulta": None, "regla_fecha": None, "intencion_historica": None}


# ---------------------------------------------------------------------------
# Condición B (y su control B_densa): contrato de consulta del paso 6
# ---------------------------------------------------------------------------

class RecuperadorB:
    def __init__(self, simular: bool, hibrida: bool = True, solo_lexica: bool = False):
        self.db = abrir_indice("B", simular)
        self.hibrida = hibrida
        self.solo_lexica = solo_lexica
        self.u: dict[str, dict] = {}
        for linea in C.UNIDADES_B.read_text(encoding="utf-8").splitlines():
            if linea.strip():
                x = json.loads(linea)
                x.setdefault("id", x["id_texto"])
                x["_vd"] = comun.fecha_num(x.get("vigente_desde"), 0)
                x["_vh"] = comun.fecha_num(x.get("vigente_hasta"), 99991231)
                x["_indexable"] = x.get("particion") in ("activa", "historica") and not x.get("id_canonico")
                self.u[x["id"]] = x
        self.por_id_texto: dict[str, list[str]] = {}
        self.por_acto: dict[str, list[str]] = {}
        for k, x in self.u.items():
            self.por_id_texto.setdefault(x["id_texto"], []).append(k)
            if x["_indexable"]:
                self.por_acto.setdefault(x["acto"], []).append(k)
        self.bm25 = comun.BM25({k: f"{x['firma']} {x['texto']}" for k, x in self.u.items() if x["_indexable"]})

    def _vigente(self, x, f):
        return x["_indexable"] and x["_vd"] <= f < x["_vh"]

    def _buscar(self, pregunta, f, vigentes: bool, k: int) -> list[str]:
        if vigentes:
            filtro = {"$and": [{"indexable": True}, {"vd": {"$lte": f}}, {"vh": {"$gt": f}}]}
        else:
            filtro = {"$and": [{"indexable": True}, {"$or": [{"vd": {"$gt": f}}, {"vh": {"$lte": f}}]}]}
        if self.solo_lexica:
            permitidos = {i for i, x in self.u.items() if x["_indexable"] and (self._vigente(x, f) == vigentes)}
            return [i for i, _ in self.bm25.buscar(pregunta, permitidos, k)]
        try:
            densos = [d.metadata["id"] for d, _ in self.db.similarity_search_with_score(pregunta, k=k, filter=filtro)]
        except Exception as e:  # no debería pasar; se avisa para no correr sin la parte densa sin saberlo
            log(f"  AVISO: la búsqueda densa con filtro falló ({type(e).__name__}: {e}); se usa solo BM25 en esta pregunta")
            densos = []
        densos = [d for d in densos if d in self.u]
        if not self.hibrida:
            return densos
        permitidos = {i for i, x in self.u.items() if x["_indexable"] and (self._vigente(x, f) == vigentes)}
        lexicos = [i for i, _ in self.bm25.buscar(pregunta, permitidos, k)]
        return comun.rrf(densos, lexicos, k=C.RRF_K)

    def _nombra_acto_no_vigente(self, pregunta, f) -> bool:
        """La pregunta nombra un decreto o acuerdo del corpus que no regía en la fecha de la consulta."""
        for tipo, num, anio in re.findall(r"\b(Decreto|Acuerdo)\s+(?:Municipal\s+|Distrital\s+)?(\d{1,4})\s+de\s+(\d{4})", pregunta, re.I):
            acto = (f"A{int(num)}-{anio}" if tipo.lower() == "acuerdo" else f"D{int(num):04d}-{anio}")
            ids = self.por_acto.get(acto)
            if ids and not any(self._vigente(self.u[i], f) for i in ids):
                return True
        return False

    def _bloque(self, x, n, f, fecha, historico):
        if historico:
            marca = (" · AÚN NO REGÍA EN LA FECHA DE LA CONSULTA" if x["_vd"] > f
                     else " · YA NO REGÍA EN LA FECHA DE LA CONSULTA (derogada o modificada)")
        elif fecha != C.FECHA_HOY:
            marca = f" · VIGENTE EN LA FECHA DE LA CONSULTA ({fecha})"
        else:
            marca = ""
        return f"[Fragmento {n}{marca}]\n{x['firma']}\n{x['texto']}"

    def contexto(self, pregunta: str):
        fecha, regla = comun.detectar_fecha(pregunta)
        f = comun.fecha_num(fecha, 0)
        historia = comun.intencion_historica(pregunta) or self._nombra_acto_no_vigente(pregunta, f)
        cupo_n = C.CUPO_HISTORICO_INTENCION if historia else C.CUPO_HISTORICO
        cupo_chars = C.CUPO_HISTORICO_INTENCION_CHARS if historia else C.CUPO_HISTORICO_CHARS
        v2 = C.CONTRATO_B == "v2"
        if v2 and not historia and fecha == C.FECHA_HOY:
            cupo_n, cupo_chars = C.CUPO_HISTORICO_HOY, C.CUPO_HISTORICO_HOY_CHARS

        def tamaño(i, historico=False):
            return len(self._bloque(self.u[i], 99, f, fecha, historico)) + 2

        # 1. canal histórico (rotulado), con cupo fijo; más amplio si la pregunta pide la historia de la norma
        hist, reserva = [], 0
        if cupo_n:
            for i in self._buscar(pregunta, f, vigentes=False, k=C.K_CANDIDATOS)[:cupo_n * 3]:
                t = tamaño(i, True)
                if len(hist) < cupo_n and reserva + t <= cupo_chars:
                    hist.append(i)
                    reserva += t
        presupuesto = C.PRESUPUESTO_CONTEXTO - reserva

        # 2. candidatos vigentes a la fecha: densos + léxicos fusionados
        ranking = self._buscar(pregunta, f, vigentes=True, k=C.K_CANDIDATOS)

        # 3. ensamblaje por complementariedad
        elegidos, canal, usados = [], {}, 0

        def agregar(i, como):
            nonlocal usados
            t = tamaño(i)
            if i in canal or usados + t > presupuesto:
                return False
            elegidos.append(i)
            canal[i] = como
            usados += t
            return True

        vistos = {}

        def por_instrumento():                                    # cubrir instrumentos antes que repetir
            for i in ranking[:10]:
                ins = self.u[i]["instrumento"]
                if vistos.get(ins, 0) < C.MAX_POR_INSTRUMENTO_1RA_VUELTA and agregar(i, "ranking"):
                    vistos[ins] = vistos.get(ins, 0) + 1

        def por_grafo():                                          # completar por el grafo (profundidad 1)
            agregadas = 0
            for i in list(elegidos):
                for rel in self.u[i].get("relacionados", []):
                    for j in self.por_id_texto.get(rel, []):
                        if agregadas < C.MAX_AGREGADAS_GRAFO and self._vigente(self.u[j], f) and agregar(j, "grafo"):
                            agregadas += 1

        if not v2:                                                # v1 (exp1): diversidad → grafo → resto
            por_instrumento()
            por_grafo()
            for i in ranking:
                agregar(i, "ranking")
        else:                                                     # v2: directos → diversidad → resto del top 10 → grafo → resto
            for i in ranking[:C.DIRECTOS_V2]:
                if agregar(i, "ranking"):
                    ins = self.u[i]["instrumento"]
                    vistos[ins] = vistos.get(ins, 0) + 1
            por_instrumento()
            for i in ranking[:10]:
                agregar(i, "ranking")
            por_grafo()
            for i in ranking:
                agregar(i, "ranking")

        # 4. ordenar por jerarquía normativa y, dentro, por fecha del instrumento y artículo
        elegidos.sort(key=lambda i: (JERARQUIA.get(self.u[i].get("tipo_documento"), 9),
                                     self.u[i].get("vigente_desde") or "", self.u[i].get("orden", 0)))
        partes, frags = [], []
        for i in elegidos + hist:
            x = self.u[i]
            historico = i in hist
            n = len(frags) + 1
            bloque = self._bloque(x, n, f, fecha, historico)
            partes.append(bloque)
            frags.append({"pos": n, "id": i, "id_texto": x["id_texto"], "instrumento": x["instrumento"],
                          "rotulo": x.get("rotulo"), "estado": x.get("estado"), "archivo": x.get("archivo"),
                          "chars": len(bloque), "canal": "historico" if historico else canal[i]})
        return "\n\n".join(partes), frags, {"fecha_consulta": fecha, "regla_fecha": regla, "intencion_historica": historia}


# ---------------------------------------------------------------------------
# Métricas automáticas por pregunta
# ---------------------------------------------------------------------------

# Abreviaturas que usan los bancos para nombrar una unidad (solo afecta la medición, no la búsqueda).
# «anexo» sin número: en los decretos del corpus cada acto tiene un único anexo (anexo1).
ALIAS_UNIDAD = {"titulo": "encabezado", "enc": "encabezado", "cons": "considerandos", "anexo": "anexo1"}


def unidad_base(id_texto: str) -> str:
    """D1143-2023:a3.p2 -> d1143-2023:a3 (comparación a nivel de artículo)."""
    acto, _, resto = id_texto.strip().partition(":")
    resto = resto.split('.')[0].split('#')[0].strip().lower()
    resto = ALIAS_UNIDAD.get(resto, resto)
    return f"{acto.strip()}:{resto}".lower()


def gold_recuperado(fila: dict, frags: list[dict]) -> float | None:
    """Fracción de las unidades esperadas (a nivel de artículo) que llegaron al contexto.
    En B se lee del fragmento; en A, de la unidad curada que contiene la línea del fragmento."""
    gold = [g for g in (fila.get("Unidades que la sustentan (id_texto)") or "").split(";") if g.strip()]
    if not gold or not frags:
        return None
    presentes = {unidad_base(fr.get("id_texto") or fr.get("unidad_curada") or "") for fr in frags}
    if presentes == {":"}:
        return None
    return sum(unidad_base(g) in presentes for g in gold) / len(gold)


# ---------------------------------------------------------------------------
# Corrida
# ---------------------------------------------------------------------------

def leer_jsonl_tolerante(ruta: Path) -> list[dict]:
    """Lee respuestas.jsonl descartando una última línea cortada (p. ej. por un corte de luz)."""
    buenas, registros = [], []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        try:
            registros.append(json.loads(linea))
            buenas.append(linea)
        except json.JSONDecodeError:
            log("  AVISO: se descarta una línea incompleta de respuestas.jsonl (la corrida se cortó escribiéndola)")
    ruta.write_text("".join(l + "\n" for l in buenas), encoding="utf-8")
    return registros


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("banco", type=Path)
    ap.add_argument("--condiciones", default=",".join(CONDICIONES))
    ap.add_argument("--ids", default="")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--modelo", default=C.CHAT_MODEL)
    ap.add_argument("--etiqueta", default="exp1")
    ap.add_argument("--continuar", type=Path, default=None, help="carpeta de una corrida interrumpida")
    ap.add_argument("--simular", action="store_true", help="modelos falsos, para probar el flujo sin GPU")
    ap.add_argument("--prefijos", action="store_true", help="usar los índices con prefijos de nomic (indexar.py ... --prefijos)")
    a = ap.parse_args()
    if a.prefijos:
        C.PREFIJOS_EMBEDDINGS = True

    banco = leer_banco(a.banco)
    if a.ids:
        quiero = {x.strip() for x in a.ids.split(",")}
        banco = [r for r in banco if r["ID"] in quiero]
    if a.limite:
        banco = banco[:a.limite]
    condiciones = [c.strip() for c in a.condiciones.split(",") if c.strip()]
    for c in condiciones:
        if c not in CONDICIONES:
            raise SystemExit(f"Condición desconocida: {c}. Opciones: {', '.join(CONDICIONES)}")

    if a.continuar:
        salida = a.continuar
        if not (salida / "manifiesto.json").exists():
            raise SystemExit(f"No encuentro {salida / 'manifiesto.json'}: revisa la carpeta de la corrida.")
        previo = json.loads((salida / "manifiesto.json").read_text(encoding="utf-8"))
        C.FECHA_HOY = previo.get("fecha_hoy", C.FECHA_HOY)       # la fecha «hoy» de la corrida no cambia al reanudar
        a.modelo = previo.get("modelo", a.modelo)
        C.PREFIJOS_EMBEDDINGS = previo.get("prefijos_embeddings", False)
        C.CONTRATO_B = previo.get("B", {}).get("contrato", "v1")   # el ensamblaje de B tampoco cambia (exp1 no lo registraba: v1)
    else:
        salida = C.RESULTADOS_DIR / f"{time.strftime('%Y-%m-%d_%H%M%S')}_{a.etiqueta}"
        if salida.exists():
            raise SystemExit(f"Ya existe {salida}. Usa otra etiqueta o --continuar.")
    salida.mkdir(parents=True, exist_ok=True)
    ruta_jsonl = salida / "respuestas.jsonl"
    hechos = set()
    if ruta_jsonl.exists():
        hechos = {(r["id"], r["condicion"]) for r in leer_jsonl_tolerante(ruta_jsonl)}

    sistema, versiones = comun.cargar_instrucciones()
    llm = comun.modelo_chat(a.simular, a.modelo)

    manifiesto = {
        "experimento": a.etiqueta,
        "descripcion": f"{a.modelo} · embeddings {C.EMBED_MODEL} · condiciones {condiciones}",
        "inicio": time.strftime("%Y-%m-%d %H:%M:%S"),
        "banco": str(a.banco), "sha256_banco": sha256(a.banco), "preguntas": len(banco), "condiciones": condiciones,
        "modelo": a.modelo, "embeddings": C.EMBED_MODEL, "temperatura": C.TEMPERATURA, "semilla": C.SEMILLA,
        "num_ctx": C.NUM_CTX, "razonamiento": C.RAZONAMIENTO, "presupuesto_contexto": C.PRESUPUESTO_CONTEXTO,
        "k_candidatos": C.K_CANDIDATOS, "chunk_A": [C.CHUNK_SIZE_A, C.CHUNK_OVERLAP_A], "rrf_k": C.RRF_K,
        "B": {"cupo_historico": C.CUPO_HISTORICO, "cupo_historico_chars": C.CUPO_HISTORICO_CHARS,
              "cupo_historico_intencion": C.CUPO_HISTORICO_INTENCION,
              "cupo_historico_intencion_chars": C.CUPO_HISTORICO_INTENCION_CHARS,
              "profundidad_grafo": C.PROFUNDIDAD_GRAFO, "max_agregadas_grafo": C.MAX_AGREGADAS_GRAFO,
              "contrato": C.CONTRATO_B, "directos_v2": C.DIRECTOS_V2,
              "cupo_historico_hoy": C.CUPO_HISTORICO_HOY, "cupo_historico_hoy_chars": C.CUPO_HISTORICO_HOY_CHARS},
        "prefijos_embeddings": C.PREFIJOS_EMBEDDINGS,
        "fecha_hoy": C.FECHA_HOY, "instrucciones": versiones, "simulado": a.simular,
        "python": platform.python_version(),
    }
    for cond in ("A", "B"):
        reg = comun.dir_chroma(cond, a.simular) / "registro_indexacion.json"
        if reg.exists():
            manifiesto[f"indice_{cond}"] = json.loads(reg.read_text(encoding="utf-8"))
    nombre_manifiesto = "manifiesto_continuacion.json" if a.continuar else "manifiesto.json"
    (salida / nombre_manifiesto).write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")

    fabrica = {"A": lambda: RecuperadorA(a.simular), "A_hibrida": lambda: RecuperadorA(a.simular, hibrida=True),
               "B": lambda: RecuperadorB(a.simular), "B_densa": lambda: RecuperadorB(a.simular, hibrida=False),
               "B_bm25": lambda: RecuperadorB(a.simular, solo_lexica=True)}
    with open(ruta_jsonl, "a", encoding="utf-8") as fout:
        for cond in condiciones:
            pendientes = [f for f in banco if (f["ID"], cond) not in hechos]
            if not pendientes:
                continue
            log(f"Condición {cond}: cargando índice…")
            rec = fabrica[cond]()
            for n, fila in enumerate(banco, 1):
                if (fila["ID"], cond) in hechos:
                    continue
                q = fila["Pregunta"].strip()
                t0 = time.time()
                ctx, frags, meta = rec.contexto(q)
                t1 = time.time()
                resp = llm.invoke([SystemMessage(content=sistema), HumanMessage(content=comun.mensaje_usuario(ctx, q))])
                t2 = time.time()
                texto, pensamiento = comun.limpiar_respuesta(resp.content if isinstance(resp.content, str) else str(resp.content))
                pensamiento = pensamiento or (getattr(resp, "additional_kwargs", {}) or {}).get("reasoning_content", "")
                uso = getattr(resp, "usage_metadata", None) or {}
                registro = {
                    "id": fila["ID"], "condicion": cond, "modelo": a.modelo, "pregunta": q,
                    "estrato": fila.get("Estrato de vigencia", ""), "fecha_banco": fila.get("Fecha de consulta", ""),
                    **meta,
                    "respuesta": texto, "pensamiento": pensamiento,
                    "se_abstuvo": comun.se_abstuvo(texto),
                    "evidencia_en_contexto": comun.evidencia_recuperada(comun.evidencias(fila.get("Evidencia literal", "")), ctx),
                    "gold_en_contexto": gold_recuperado(fila, frags),
                    "fragmentos": frags, "contexto_chars": len(ctx), "contexto": ctx,
                    "seg_recuperacion": round(t1 - t0, 2), "seg_generacion": round(t2 - t1, 2),
                    "tokens_entrada": uso.get("input_tokens"), "tokens_salida": uso.get("output_tokens"),
                }
                fout.write(json.dumps(registro, ensure_ascii=False) + "\n")
                fout.flush()
                log(f"[{cond}] {n}/{len(banco)} {fila['ID']}  {registro['seg_generacion']} s  "
                    f"{'abstención' if registro['se_abstuvo'] else ''}")

    escribir_tablas(salida, banco)
    log(f"\nResultados en {salida}")


def escribir_tablas(salida: Path, banco: list[dict]):
    registros = leer_jsonl_tolerante(salida / "respuestas.jsonl")
    por = {(r["id"], r["condicion"]): r for r in registros}
    conds = [c for c in CONDICIONES if any(r["condicion"] == c for r in registros)]

    def fuentes(r):
        if not r:
            return ""
        return " | ".join(f.get("id_texto") or f"{f.get('archivo')}#{f.get('fragmento')}" for f in r["fragmentos"])

    # tabla rotulada (para el análisis)
    columnas = ["ID", "Estrato de vigencia", "Fecha de consulta", "Tipo cognitivo", "Tipo de respuesta",
                "Pregunta", "Respuesta esperada", "Instrumento y artículo"]
    for c in conds:
        columnas += [f"{c} · respuesta", f"{c} · fragmentos", f"{c} · evidencia en contexto"]
    with open(salida / "para_calificar.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(columnas)
        for fila in banco:
            base = [fila.get(k, "") for k in columnas[:8]]
            for c in conds:
                r = por.get((fila["ID"], c))
                ev = "" if not r or r["evidencia_en_contexto"] is None else round(r["evidencia_en_contexto"], 2)
                base += [r["respuesta"] if r else "", fuentes(r), ev]
            w.writerow(base)

    # tabla ciega (para calificar): una fila por respuesta, en orden aleatorio, sin la condición
    filas_ciegas, clave = [], []
    azar = random.Random(C.SEMILLA)
    for fila in banco:
        rs = [por[(fila["ID"], c)] for c in conds if (fila["ID"], c) in por]
        azar.shuffle(rs)
        for k, r in enumerate(rs, 1):
            codigo = f"{fila['ID']}-R{k}"
            filas_ciegas.append([codigo, fila["ID"], fila.get("Estrato de vigencia", ""), fila.get("Fecha de consulta", ""),
                                 fila["Pregunta"], fila.get("Respuesta esperada", ""), fila.get("Instrumento y artículo", ""),
                                 fila.get("Evidencia literal", ""), r["respuesta"], "", "", "", ""])
            clave.append([codigo, r["condicion"]])
    with open(salida / "para_calificar_ciego.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Código", "ID", "Estrato de vigencia", "Fecha de consulta", "Pregunta", "Respuesta esperada",
                    "Instrumento y artículo esperado", "Evidencia literal", "Respuesta del sistema",
                    "Satisfactoria (1/0)", "Cita fuente vigente (1/0/NA)", "Alucina (1/0)", "Observación"])
        w.writerows(filas_ciegas)
    with open(salida / "clave_ciego.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Código", "Condición"])
        w.writerows(clave)

    # resumen automático
    lineas = ["# Resumen automático", "", f"Corrida: `{salida.name}`", "",
              "Las métricas de calidad (satisfactoria, vigencia de la cita, alucinación) se califican a mano en "
              "`para_calificar_ciego.csv`. Aquí van solo las que se calculan solas.", ""]
    lineas += ["| Métrica | " + " | ".join(conds) + " |", "|---|" + "---|" * len(conds)]

    def fila_metrica(nombre, fn):
        vals = []
        for c in conds:
            rs = [r for r in registros if r["condicion"] == c]
            v = fn(rs)
            vals.append("—" if v is None else v)
        lineas.append(f"| {nombre} | " + " | ".join(str(v) for v in vals) + " |")

    def media(xs):
        xs = [x for x in xs if x is not None]
        return round(statistics.mean(xs), 3) if xs else None

    fila_metrica("Preguntas respondidas", lambda rs: len(rs))
    fila_metrica("Abstención en «Sin respuesta» (debería ser alta)",
                 lambda rs: media([1.0 * r["se_abstuvo"] for r in rs if r["estrato"] == "Sin respuesta"]))
    fila_metrica("Abstención en las demás (debería ser baja)",
                 lambda rs: media([1.0 * r["se_abstuvo"] for r in rs if r["estrato"] != "Sin respuesta"]))
    for est in ("Normal", "Colisión"):
        fila_metrica(f"Evidencia literal en el contexto · {est}",
                     lambda rs, est=est: media([r["evidencia_en_contexto"] for r in rs if r["estrato"] == est]))
        fila_metrica(f"Artículo esperado en el contexto · {est}",
                     lambda rs, est=est: media([r["gold_en_contexto"] for r in rs if r["estrato"] == est]))
    fila_metrica("Segundos por respuesta (mediana)",
                 lambda rs: round(statistics.median([r["seg_generacion"] for r in rs]), 2) if rs else None)
    fila_metrica("Segundos por respuesta (p90)",
                 lambda rs: round(sorted(r["seg_generacion"] for r in rs)[int(0.9 * (len(rs) - 1))], 2) if rs else None)
    fila_metrica("Tokens de entrada (media)", lambda rs: media([r["tokens_entrada"] for r in rs]))
    fila_metrica("Tokens de salida (media)", lambda rs: media([r["tokens_salida"] for r in rs]))
    fila_metrica("Caracteres de contexto (media)", lambda rs: media([r["contexto_chars"] for r in rs]))
    lineas += ["", "«Artículo esperado en el contexto» compara a nivel de artículo: cuenta aunque llegue otra parte del mismo artículo. "
               "En A se calcula ubicando cada fragmento en la unidad curada que contiene su línea."]
    fechas = [r for r in registros if r["condicion"] == "B" and (r.get("fecha_consulta") != C.FECHA_HOY or r.get("intencion_historica"))]
    if fechas:
        lineas += ["", "## Preguntas con fecha pasada o intención histórica (condición B)", "",
                   "| ID | Fecha del banco | Fecha detectada | Regla | Intención histórica |", "|---|---|---|---|---|"]
        lineas += [f"| {r['id']} | {r['fecha_banco']} | {r['fecha_consulta']} | {r['regla_fecha']} | {'sí' if r.get('intencion_historica') else ''} |"
                   for r in fechas]
    (salida / "resumen.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

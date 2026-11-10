"""Construye UNA VEZ el índice de cada condición, cada uno en su propia carpeta.

    python indexar.py A            # corpus original, fragmentos de 500/80 como el demo
    python indexar.py B            # corpus curado (requiere curaduria/unidades.jsonl)
    python indexar.py A --reconstruir   # borra y vuelve a construir

Si el índice ya existe, no hace nada: así no se duplican fragmentos
(el problema del rag_demo.py, que agregaba los documentos en cada pregunta).
Deja un registro de costo (fragmentos, caracteres, minutos) en
<carpeta del índice>/registro_indexacion.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

import comun
import config as C

LOTE = 128


def documentos_A() -> list[tuple[str, Document]]:
    from langchain_community.document_loaders import TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    archivos = sorted(C.CORPUS_A_DIR.glob("*.md"))
    if not archivos:
        raise SystemExit(f"No hay archivos .md en {C.CORPUS_A_DIR}")
    splitter = RecursiveCharacterTextSplitter(chunk_size=C.CHUNK_SIZE_A, chunk_overlap=C.CHUNK_OVERLAP_A,
                                              add_start_index=True)   # no cambia los fragmentos: solo anota dónde empiezan
    salida = []
    for arch in archivos:
        docs = TextLoader(str(arch), encoding="utf-8").load()
        texto = docs[0].page_content
        for i, ch in enumerate(splitter.split_documents(docs)):
            inicio = ch.metadata.get("start_index", -1)
            linea = texto.count("\n", 0, inicio) + 1 if inicio >= 0 else -1
            ch.metadata = {"archivo": arch.name, "fragmento": i, "linea": linea}
            salida.append((f"{arch.name}#{i}", ch))
    return salida


def _limpio(v):
    if v is None:
        return ""
    if isinstance(v, (str, int, float, bool)):
        return v
    return json.dumps(v, ensure_ascii=False)


CAMPOS_B = ("id", "id_texto", "instrumento", "rotulo", "titulo", "alcance", "acto_fuente", "tipo_documento",
            "naturaleza_fuente", "estado", "acto_modificatorio", "id_canonico", "particion", "archivo")


def documentos_B() -> list[tuple[str, Document]]:
    if not C.UNIDADES_B.exists():
        raise SystemExit(f"Falta {C.UNIDADES_B}. Corre primero curar.py.")
    salida = []
    for linea in C.UNIDADES_B.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        u = json.loads(linea)
        u.setdefault("id", u["id_texto"])
        if u.get("particion") not in ("activa", "historica") or u.get("id_canonico"):
            continue          # copias, actos contiguos y cierres: quedan en la base pero nunca se recuperan
        md = {k: _limpio(u.get(k)) for k in CAMPOS_B}
        md["vd"] = comun.fecha_num(u.get("vigente_desde"), 0)
        md["vh"] = comun.fecha_num(u.get("vigente_hasta"), 99991231)
        md["indexable"] = True
        salida.append((u["id"], Document(page_content=f"{u['firma']}\n\n{u['texto']}", metadata=md)))
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("condicion", choices=["A", "B"])
    ap.add_argument("--reconstruir", action="store_true")
    ap.add_argument("--simular", action="store_true", help="embeddings falsos, para probar sin GPU")
    ap.add_argument("--prefijos", action="store_true", help="prefijos de tarea de nomic (índice aparte *_prefijo)")
    a = ap.parse_args()
    if a.prefijos:
        C.PREFIJOS_EMBEDDINGS = True

    carpeta: Path = comun.dir_chroma(a.condicion, a.simular)
    if a.reconstruir and carpeta.exists():
        shutil.rmtree(carpeta)
    db = Chroma(collection_name=f"condicion_{a.condicion}", embedding_function=comun.embeddings(a.simular),
                persist_directory=str(carpeta))
    ya = db._collection.count()
    if ya:
        if not (carpeta / "registro_indexacion.json").exists():
            raise SystemExit(f"El índice {a.condicion} quedó a medias (tiene {ya} fragmentos y no tiene registro). "
                             f"Corre: python indexar.py {a.condicion} --reconstruir")
        print(f"El índice {a.condicion}{' (con prefijos)' if a.prefijos else ''} ya existe con {ya} fragmentos en {carpeta}. Usa --reconstruir para rehacerlo.")
        return

    pares = documentos_A() if a.condicion == "A" else documentos_B()
    ids = [p[0] for p in pares]
    if len(set(ids)) != len(ids):
        repetidos = sorted({i for i in ids if ids.count(i) > 1})[:10]
        raise SystemExit(f"Hay identificadores repetidos, por ejemplo: {repetidos}")

    t0 = time.time()
    for i in range(0, len(pares), LOTE):
        lote = pares[i:i + LOTE]
        db.add_documents([d for _, d in lote], ids=[k for k, _ in lote])
        if (i // LOTE) % 20 == 0 or i + LOTE >= len(pares):
            print(f"  {min(i + LOTE, len(pares))}/{len(pares)} fragmentos", flush=True)
    minutos = (time.time() - t0) / 60

    registro = {
        "condicion": a.condicion,
        "fragmentos": len(pares),
        "caracteres": sum(len(d.page_content) for _, d in pares),
        "archivos": len({d.metadata.get("archivo") for _, d in pares}),
        "minutos_embeddings": round(minutos, 2),
        "modelo_embeddings": C.EMBED_MODEL if not a.simular else "simulado",
        "chunk_size": C.CHUNK_SIZE_A if a.condicion == "A" else "unidad normativa",
        "chunk_overlap": C.CHUNK_OVERLAP_A if a.condicion == "A" else 0,
        "fecha": time.strftime("%Y-%m-%d %H:%M"),
        "prefijos_embeddings": C.PREFIJOS_EMBEDDINGS,
    }
    if a.condicion == "B":
        registro["sha256_unidades"] = hashlib.sha256(C.UNIDADES_B.read_bytes()).hexdigest()
    (carpeta / "registro_indexacion.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nListo: {registro}")


if __name__ == "__main__":
    main()

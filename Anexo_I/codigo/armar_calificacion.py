"""Arma el archivo ciego de calificación de un banco juntando condiciones de varias corridas.

    python armar_calificacion.py preguntas/banco_agente_D.csv calificacion/D \
        --corrida resultados/<corrida_demo>:A=A_demo \
        --corrida resultados/<corrida_exp2>:A_hibrida,B,B_bm25 \
        [--muestra calificacion/muestra_banco_agente_C.csv]

Cada --corrida es «carpeta:condiciones». Una condición puede renombrarse con «=»
(A=A_demo: la A de la corrida sin prefijos, como el demo del director).
Produce, en la carpeta de salida:
  para_calificar_ciego.csv  una fila por respuesta, sin la condición, en orden aleatorio dentro de cada pregunta
  clave_ciego.csv           código → condición y corrida (no se entrega a quien califica)
"""
import argparse
import csv
import json
import random
from pathlib import Path

SEMILLA = 42


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("banco", type=Path)
    ap.add_argument("salida", type=Path)
    ap.add_argument("--corrida", action="append", required=True)
    ap.add_argument("--muestra", type=Path, default=None)
    a = ap.parse_args()

    banco = [f for f in csv.DictReader(open(a.banco, encoding="utf-8-sig")) if (f.get("Pregunta") or "").strip()]
    if a.muestra:
        ids = {f["ID"] for f in csv.DictReader(open(a.muestra, encoding="utf-8-sig"))}
        banco = [f for f in banco if f["ID"] in ids]
    ids_banco = {f["ID"] for f in banco}

    respuestas = {}
    orden_conds = []
    for spec in a.corrida:
        carpeta, _, conds = spec.rpartition(":")
        carpeta = Path(carpeta)
        mapa = {}
        for c in conds.split(","):
            origen, _, nombre = c.partition("=")
            mapa[origen.strip()] = (nombre or origen).strip()
        filas = [json.loads(l) for l in open(carpeta / "respuestas.jsonl", encoding="utf-8") if l.strip()]
        for r in filas:
            if r["condicion"] in mapa and r["id"] in ids_banco:
                nombre = mapa[r["condicion"]]
                respuestas[(r["id"], nombre)] = (r, carpeta.name)
        for n in mapa.values():
            if n in orden_conds:
                raise SystemExit(f"La condición {n} aparece dos veces.")
            orden_conds.append(n)

    faltan = [(i, c) for i in sorted(ids_banco) for c in orden_conds if (i, c) not in respuestas]
    if faltan:
        raise SystemExit(f"Faltan {len(faltan)} respuestas, por ejemplo {faltan[:5]}: revisa las corridas.")

    azar = random.Random(SEMILLA)
    ciegas, clave = [], []
    for f in banco:
        rs = [respuestas[(f["ID"], c)] + (c,) for c in orden_conds]
        azar.shuffle(rs)
        for k, (r, corrida, cond) in enumerate(rs, 1):
            codigo = f"{f['ID']}-R{k}"
            ciegas.append([codigo, f["ID"], f.get("Estrato de vigencia", ""), f.get("Fecha de consulta", ""),
                           f["Pregunta"], f.get("Respuesta esperada", ""), f.get("Instrumento y artículo", ""),
                           f.get("Evidencia literal", ""), r["respuesta"], "", "", "", ""])
            clave.append([codigo, f["ID"], cond, corrida, f.get("Estrato de vigencia", ""),
                          f.get("Coincide con banco B", ""), r.get("se_abstuvo"), r.get("gold_en_contexto")])
    a.salida.mkdir(parents=True, exist_ok=True)
    with open(a.salida / "para_calificar_ciego.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Código", "ID", "Estrato de vigencia", "Fecha de consulta", "Pregunta", "Respuesta esperada",
                    "Instrumento y artículo esperado", "Evidencia literal", "Respuesta del sistema",
                    "Satisfactoria (1/0)", "Cita fuente vigente (1/0/NA)", "Alucina (1/0)", "Observación"])
        w.writerows(ciegas)
    with open(a.salida / "clave_ciego.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Código", "ID", "Condición", "Corrida", "Estrato de vigencia", "Coincide con banco B",
                    "Se abstuvo (automático)", "Artículo esperado en el contexto"])
        w.writerows(clave)
    print(f"{len(banco)} preguntas × {len(orden_conds)} condiciones ({', '.join(orden_conds)}) = {len(ciegas)} filas → {a.salida}")


if __name__ == "__main__":
    main()

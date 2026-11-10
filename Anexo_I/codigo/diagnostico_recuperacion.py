"""Diagnóstico de la recuperación, sin modelo de lenguaje (segundos).

    python diagnostico_recuperacion.py preguntas/banco_agente_B.csv
    python diagnostico_recuperacion.py preguntas/banco_agente_B.csv --prefijos   # además, con los índices *_prefijo

Para cada variante de búsqueda y ensamblaje mide si el artículo esperado llega al
contexto (la misma métrica «Artículo esperado en el contexto» de resumen.md).
No genera respuestas: solo arma el contexto que recibiría el modelo.
Sirve para decidir el exp2 con el banco de desarrollo, antes de probar con un banco no visto.
"""
import argparse
import csv
import time
from pathlib import Path
from collections import defaultdict

import config as C
import experimento as E


def medir(nombre, recuperador, banco, filas_csv, tabla):
    por = defaultdict(list)
    for f in banco:
        if f.get("Estrato de vigencia") == "Sin respuesta":
            continue
        _, frags, _ = recuperador.contexto(f["Pregunta"])
        g = E.gold_recuperado(f, frags) or 0.0
        por[f["Estrato de vigencia"]].append(g)
        por["Todas"].append(g)
        filas_csv.append({"variante": nombre, "ID": f["ID"], "estrato": f["Estrato de vigencia"],
                          "articulo_esperado_en_contexto": g, "fragmentos": len(frags)})
    tabla[nombre] = {k: sum(v) / len(v) for k, v in por.items()}
    t = tabla[nombre]
    print(f"  {nombre:38s} Normal {t.get('Normal', 0):.3f} · Colisión {t.get('Colisión', 0):.3f} · Todas {t['Todas']:.3f}", flush=True)


class SinDensa:
    """Envoltura que apaga la parte densa de B (solo BM25)."""
    def __init__(self, r):
        self.r = r

    def contexto(self, pregunta):
        original = self.r.db.similarity_search_with_score
        self.r.db.similarity_search_with_score = lambda *a, **k: []
        try:
            return self.r.contexto(pregunta)
        finally:
            self.r.db.similarity_search_with_score = original


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("banco")
    ap.add_argument("--prefijos", action="store_true", help="medir también con los índices con prefijos de nomic")
    ap.add_argument("--simular", action="store_true", help="índices simulados, solo para probar el flujo")
    a = ap.parse_args()
    E.log = lambda *x, **k: None
    banco = E.leer_banco(Path(a.banco))
    filas, tabla = [], {}
    for pref in ([False, True] if a.prefijos else [False]):
        C.PREFIJOS_EMBEDDINGS = pref
        etiqueta = " +prefijos" if pref else ""
        print(f"\nÍndices {'con' if pref else 'sin'} prefijos de nomic:", flush=True)
        ra, rah = E.RecuperadorA(a.simular), E.RecuperadorA(a.simular, hibrida=True)
        rb, rbd = E.RecuperadorB(a.simular), E.RecuperadorB(a.simular, hibrida=False)
        medir("A densa" + etiqueta, ra, banco, filas, tabla)
        medir("A híbrida" + etiqueta, rah, banco, filas, tabla)
        for v in ("v1", "v2"):
            C.CONTRATO_B = v
            medir(f"B {v} híbrida" + etiqueta, rb, banco, filas, tabla)
            medir(f"B {v} densa" + etiqueta, rbd, banco, filas, tabla)
            medir(f"B {v} solo BM25" + etiqueta, SinDensa(rb), banco, filas, tabla)
    C.CONTRATO_B = "v2"
    salida = C.RESULTADOS_DIR / f"diagnostico_{time.strftime('%Y-%m-%d_%H%M%S')}.csv"
    salida.parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print(f"\nDetalle por pregunta en {salida}")


if __name__ == "__main__":
    main()

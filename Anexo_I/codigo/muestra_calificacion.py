"""Muestra aleatoria estratificada de preguntas para calificar (se fija ANTES de ver respuestas).

    python muestra_calificacion.py preguntas/banco_agente_C.csv --n 30

Reparte el tamaño de la muestra entre los estratos de vigencia en proporción a su tamaño
(método del mayor resto, con al menos 1 por estrato) y elige al azar dentro de cada estrato
con una semilla fija. Guarda la lista en calificacion/muestra_<banco>.csv.
"""
import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

SEMILLA_MUESTRA = 20261029   # fijada el 29-10-2026, antes de correr los bancos C y D


def asignar(tamaños: dict[str, int], n: int) -> dict[str, int]:
    total = sum(tamaños.values())
    cuotas = {e: n * t / total for e, t in tamaños.items()}
    asig = {e: max(1, int(c)) for e, c in cuotas.items()}
    restos = sorted(tamaños, key=lambda e: cuotas[e] - int(cuotas[e]), reverse=True)
    i = 0
    while sum(asig.values()) < n:
        e = restos[i % len(restos)]
        if asig[e] < tamaños[e]:
            asig[e] += 1
        i += 1
    while sum(asig.values()) > n:
        e = max(asig, key=lambda k: asig[k] - cuotas[k])
        asig[e] -= 1
    return asig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("banco", type=Path)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--semilla", type=int, default=SEMILLA_MUESTRA)
    a = ap.parse_args()
    filas = list(csv.DictReader(open(a.banco, encoding="utf-8-sig")))
    por = defaultdict(list)
    for f in filas:
        por[f["Estrato de vigencia"]].append(f["ID"])
    asig = asignar({e: len(v) for e, v in por.items()}, a.n)
    azar = random.Random(a.semilla)
    elegidas = []
    for e in sorted(por):
        ids = sorted(por[e])
        elegidas += [(i, e) for i in sorted(azar.sample(ids, asig[e]))]
    salida = Path(__file__).resolve().parent / "calificacion" / f"muestra_{a.banco.stem}.csv"
    salida.parent.mkdir(exist_ok=True)
    with open(salida, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ID", "Estrato de vigencia", "semilla", "n"])
        for i, e in elegidas:
            w.writerow([i, e, a.semilla, a.n])
    print(f"{len(elegidas)} preguntas · por estrato {asig} · semilla {a.semilla} → {salida}")


if __name__ == "__main__":
    main()

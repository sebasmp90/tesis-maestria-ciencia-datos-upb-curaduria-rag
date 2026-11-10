"""Control de salida de la curaduría contra el banco de preguntas.

    python validar_curaduria.py preguntas/banco_agente_B.csv

Para cada pregunta busca, en las unidades indexables de la base curada, la frase
de «Evidencia literal» y revisa tres cosas:
  1. que la frase esté en alguna unidad (la segmentación no la perdió);
  2. que esa unidad sea la que el banco espera (columna id_texto, a nivel de artículo);
  3. que esa unidad esté vigente en la fecha de la consulta (si no, el filtro de B la dejaría por fuera).
No usa modelos: es un chequeo de la base, no del sistema.
"""
import csv
import json
import sys
from collections import Counter

import comun
import config as C


# Abreviaturas que usan los bancos para nombrar una unidad (solo afecta la medición, no la búsqueda).
# «anexo» sin número: en los decretos del corpus cada acto tiene un único anexo (anexo1).
ALIAS_UNIDAD = {"titulo": "encabezado", "enc": "encabezado", "cons": "considerandos", "anexo": "anexo1"}


def base_art(id_texto: str) -> str:
    acto, _, resto = id_texto.strip().partition(":")
    resto = resto.split('.')[0].split('#')[0].strip().lower()
    resto = ALIAS_UNIDAD.get(resto, resto)
    return f"{acto.strip()}:{resto}".lower()


def main(ruta_banco):
    unidades = [json.loads(l) for l in C.UNIDADES_B.read_text(encoding="utf-8").splitlines() if l.strip()]
    idx = [u for u in unidades if u["particion"] in ("activa", "historica") and not u.get("id_canonico")]
    textos = [(u, comun.normalizar(u["texto"])) for u in idx]
    filas = list(csv.DictReader(open(ruta_banco, encoding="utf-8-sig")))
    salida, resumen = [], Counter()
    for f in filas:
        fecha, _ = comun.detectar_fecha(f["Pregunta"])
        fnum = comun.fecha_num(fecha, 0)
        gold = [g for g in (f.get("Unidades que la sustentan (id_texto)") or "").split(";") if g.strip()]
        frases = comun.evidencias(f.get("Evidencia literal", ""))
        if not frases or f.get("Estrato de vigencia") == "Sin respuesta":
            continue
        encontradas = []
        for fr in frases:
            nf = comun.normalizar(fr)
            tramo = nf if len(nf) <= 60 else nf[len(nf) // 2 - 30: len(nf) // 2 + 30]
            hits = [u for u, t in textos if tramo in t]
            encontradas.append(hits)
        todas = [u for hs in encontradas for u in hs]
        ids = sorted({base_art(u["id_texto"]) for u in todas})
        gold_b = {base_art(g) for g in gold}
        en_base = all(encontradas)
        coincide = bool(gold_b & set(ids)) if gold_b else None
        vig = [u for u in todas if base_art(u["id_texto"]) in gold_b]
        vigente = any(comun.fecha_num(u["vigente_desde"], 0) <= fnum < comun.fecha_num(u["vigente_hasta"], 99991231) for u in vig) if vig else None
        estado = "OK" if en_base and coincide and vigente else ("sin evidencia" if not en_base else ("otra unidad" if not coincide else "no vigente a la fecha"))
        resumen[estado] += 1
        salida.append({"ID": f["ID"], "Estrato": f["Estrato de vigencia"], "Fecha": fecha, "Esperada": "; ".join(gold),
                       "Unidades con la evidencia": " | ".join(f"{u['id_texto']} [{u['estado']}]" for u in todas[:6]),
                       "Resultado": estado})
    if not salida:
        raise SystemExit("El banco no trae preguntas con «Evidencia literal»: no hay nada que validar.")
    out = C.CURADURIA_DIR / "validacion_banco.csv"
    with open(out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(salida[0]))
        w.writeheader()
        w.writerows(salida)
    print(dict(resumen))
    for s in salida:
        if s["Resultado"] != "OK":
            print(f"{s['ID']:7s} {s['Resultado']:22s} esperada={s['Esperada'][:40]:40s} hallada={s['Unidades con la evidencia'][:110]}")
    print(f"\nDetalle en {out}")


if __name__ == "__main__":
    main(sys.argv[1])

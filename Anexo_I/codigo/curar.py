"""Construye la base curada (condición B) aplicando los pasos 0 a 6 de la metodología.

    python curar.py                 # lee corpus_A/*.md y escribe curaduria/
    python curar.py --diagnostico   # además imprime la numeración de artículos de cada acto

Entradas: los mismos Markdown de la condición A (corpus_A/) e inventario.py (paso 0).
Salidas en curaduria/:
    unidades.jsonl        las unidades con su firma y metadatos (lo que indexa indexar.py B)
    afectaciones.csv      registro de cambios: qué unidad modificó, derogó o adicionó a cuál (pasos 3 y 4)
    pendientes.csv        relaciones hacia actos que no están en el corpus (cola de pendientes)
    revision.csv          casos «por confirmar» y avisos para revisión humana
    reproducciones.csv    textos idénticos entre actos distintos (paso 5)
    manifiesto.md         fecha de corte, inventario, conteos por partición y estado (paso 6)
    registro_costo.json   tiempo de cada paso (registro transversal del costo de curar)

Ningún modelo de lenguaje interviene: todo son reglas sobre el texto. Nada se borra:
lo derogado pasa a la partición histórica y las copias quedan vinculadas a su fuente.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
import unicodedata
from collections import Counter, defaultdict

import comun
import config as C
import inventario as INV

MAX_CHARS = 1200          # tamaño máximo del texto de una unidad indexada (las largas se parten)
TIEMPOS: dict[str, float] = {}


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------

def sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def etiqueta(acto_id: str) -> str:
    tipo, num, anio, *_ = INV.ACTOS[acto_id]
    return f"{tipo} {num} de {anio}"


def fecha_vigor(acto_id: str) -> tuple[str, bool]:
    _, _, _, exp, pub, *_ = INV.ACTOS[acto_id]
    return (pub, False) if pub else (exp, True)


def ddmmaaaa(iso: str | None) -> str:
    if not iso:
        return ""
    a, m, d = iso.split("-")
    return f"{d}-{m}-{a}"


def id_acto_desde_texto(tipo: str, num: str, anio: str) -> str:
    pref = "A" if tipo.lower().startswith("acuerdo") else "D"
    n = num.lstrip("0") or "0"
    return f"{pref}{n}-{anio}" if pref == "A" else f"{pref}{int(n):04d}-{anio}"


ORDINALES = {"PRIMERO": 1, "SEGUNDO": 2, "TERCERO": 3, "CUARTO": 4, "QUINTO": 5, "SEXTO": 6, "SEPTIMO": 7,
             "OCTAVO": 8, "NOVENO": 9, "DECIMO": 10, "UNDECIMO": 11, "DUODECIMO": 12}


def num_ordinal(txt: str) -> int | None:
    t = sin_tildes(txt).upper().split()
    if not t:
        return None
    if t[0] == "DECIMO" and len(t) > 1 and t[1] in ORDINALES and ORDINALES[t[1]] < 10:
        return 10 + ORDINALES[t[1]]
    return ORDINALES.get(t[0])


def quitar_marcas(l: str) -> str:
    l = re.sub(r"</?(?:u|mark|sup|sub|span|b|i|em|strong)\b[^>]*>|~~|\*\*|__", "", l)
    l = re.sub(r"(?<![\w])_|_(?![\w])", "", l)
    return re.sub(r"[ \t]+", " ", l).strip()


# ---------------------------------------------------------------------------
# Paso 1. Limpieza determinista y segmentación por artículo
# ---------------------------------------------------------------------------

RUIDO = re.compile(r"^\s*(?:<!--.*-->|\**\s*Gaceta Oficial\s*\**\s*(?:N[º°o]?\s*\.?\s*\d{3,4})?\s*\**|\**N[º°]\s*\d{3,4}\**|\d{1,4}|Pág\.?\s*\d+)\s*$", re.I)
HDR = re.compile(
    r"^(?P<q>[“\"”‘'«]\s*)?(?P<w>ART[ÍI]CULO|Art[íi]culo|ARTíCULO)\s*"
    r"(?P<num>\d{1,3}(?:\s?[A-Z](?![a-záéíóú]))?|(?:D[ÉE]CIMO\s+)?(?:PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|S[ÉE]PTIMO|OCTAVO|NOVENO)|D[ÉE]CIMO|UND[ÉE]CIMO|DUOD[ÉE]CIMO|[%$&]\w?)"
    r"\s*(?:[°ºo](?![a-záéíóú]))?\s*(?P<p>[.:\-–)]|$|\s+[A-ZÁÉÍÓÚÑ])")
HDR_SIN_NUM = re.compile(r"^#{0,6}\s*\*\*\s*\.\s+(?P<tit>.+)")
ANUNCIO = re.compile(r"(quedar[aá]n?\s+as[ií]|queda\s+as[ií]|quedar[aá]n?\s+de\s+la\s+siguiente|pasar[aá]n?\s+a\s+ser|el\s+siguiente\s+tenor|su\s+nuevo\s+texto|as[ií]\s*:|:\s*$)", re.I)
PEGADO = re.compile(r"(?<=\S)\s+(?=(?:\*\*|<mark>)*\s*(?:ART[ÍI]CULO|Art[íi]culo)\s+(?:\d{1,3}\s?[A-Z]?|PRIMERO)\s*[°º]?\s*(?:\*\*)?\s*[.:\-–])")
CONTEXTO_PEGADO = re.compile(r"(DECRETA|ACUERDA|T[ÍI]TULO\s+[IVXL\d]|CAP[ÍI]TULO\s+[IVXL\d]|SECCI[ÓO]N\s+[IVXL\d]|Secci[óo]n\s+\d|SUBSECCI[ÓO]N|Subsecci[óo]n\s+\d)", re.I)


def despegar(lineas: list[str], desde: int) -> tuple[list[str], list[int]]:
    """Separa el encabezado de artículo que la conversión pegó a un título o al «DECRETA»."""
    lineas = list(lineas)
    for k in range(1, len(lineas) - 1):     # encabezado «colgado» al margen: «…los / ARTÍCULO 7°. / cuales pasarán…»
        cab = quitar_marcas(lineas[k])
        prev, sig = quitar_marcas(lineas[k - 1]), quitar_marcas(lineas[k + 1])
        if (re.fullmatch(r"ART[ÍI]CULO\s*\d{1,3}\s*[°ºo]?\s*[.:]?", cab) and prev and not re.search(r"[.:;”\"]$", prev)
                and sig[:1].islower()):
            lineas[k - 1], lineas[k] = lineas[k], lineas[k - 1]
    out, nums = [], []
    for k, l in enumerate(lineas):
        n = desde + k
        m = PEGADO.search(l)
        if m and CONTEXTO_PEGADO.search(l[:m.start()]) and len(l[:m.start()]) < 600:
            out += [l[:m.start()], l[m.start():].lstrip()]
            nums += [n, n]
        else:
            out.append(l)
            nums.append(n)
    return out, nums
CIERRE = re.compile(r"PUBL[ÍI]QUESE|COMUN[ÍI]QUESE\s+Y\s+C[ÚU]MPLASE|^\W{0,6}Dad[oa]\s+en\s+Medell[íi]n", re.I)
ANEXO = re.compile(r"^\s*(?:#{1,6}\s*)?(?:\*\*)?\s*(?:ANEXO\b|Anexo\s+(?:N[°º.o]*\s*)?\d)")
CONSIDERANDO = re.compile(r"^\W{0,12}CONSIDERANDO", re.I)
NOTAS_INI = re.compile(r"^\s*(Concordancias\b|Notas de Vigencia\b|NOTAS DE VIGENCIA|Legislaci[óo]n Anterior\b|Resumen de Notas de Vigencia|Jurisprudencia\b)", re.I)


def es_anidado(linea: str) -> bool:
    """Encabezado citado dentro de otro artículo: entre comillas o en cursiva."""
    ini = linea.lstrip("# >")[:14]
    return bool(re.match(r"^(\*\*)?\s*(_|“|\"|”|«)", ini) or "_“" in ini or "“ " in ini[:4])


def candidato_encabezado(linea: str):
    limpio = quitar_marcas(linea.lstrip("#> ").strip())
    m = HDR.match(limpio)
    if not m:
        return None
    raw = m.group("num").strip()
    if raw[0].isdigit():
        mm = re.match(r"(\d+)\s?([A-Z]?)", raw)
        n, letra = int(mm.group(1)), mm.group(2)
    else:
        n, letra = num_ordinal(raw), ""
    resto = limpio[m.end("num"):].lstrip(" °ºo.:-–)").strip()
    return {"n": n, "letra": letra, "raw": raw, "citado": bool(m.group("q")) or es_anidado(linea),
            "titulo": re.split(r"\s*\.\s+(?=[A-ZÁÉÍÓÚÑ¿“])|:\s", resto, maxsplit=1)[0].strip(" .")[:120]}


NOTA_INLINE = re.compile(r"<(?:Art[ií]culo|NOTA|Inciso|Par[aá]grafo|Numeral|Literal|Aparte)[^<>]{0,900}>", re.I)


def limpiar_compilacion(lineas: list[str]) -> tuple[list[str], list[str]]:
    """Separa los bloques de concordancias, notas de vigencia y legislación anterior (canal paralelo).

    Las líneas retiradas se reemplazan por líneas vacías para no alterar la numeración del archivo.
    El bloque «Legislación anterior» trae la versión anterior del mismo artículo, con su propio
    encabezado: solo termina cuando aparece un encabezado con otro número.
    """
    texto, notas, bloque, num_actual = [], [], None, None
    for l in lineas:
        l = re.sub(r"</?u>", "", l)
        c = candidato_encabezado(l)
        if NOTAS_INI.match(l):
            bloque = "anterior" if re.match(r"^\s*Legislaci", l, re.I) else "nota"
        elif bloque and (CONSIDERANDO.match(l) or re.match(r"^\W*(DECRETA|ACUERDA)\b", l)):
            bloque = None
        elif bloque and c and not (bloque == "anterior" and c["n"] == num_actual):
            bloque = None
        if bloque:
            notas.append(l)
            texto.append("")
            continue
        if c and not c["citado"]:
            num_actual = c["n"]
        m = NOTA_INLINE.findall(l)
        if m:
            notas += m
            l = NOTA_INLINE.sub("", l)
        texto.append(l)
    return texto, notas


def limpiar_texto(lineas: list[str]) -> str:
    out = [quitar_marcas(l) for l in lineas if not RUIDO.match(l)]
    t = "\n".join(out)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def segmentar(acto_id: str, lineas: list[str], numeros: list[int], diag: list):
    """Devuelve bloques [(clase, número, letra, título, líneas, línea inicial, inferido)].

    Regla secuencial: un encabezado es un artículo del acto si su número sigue al anterior.
    Los encabezados entre comillas o en cursiva, o los que aparecen después de «quedará así»
    sin ser el siguiente número, son artículos citados dentro de otro (el texto nuevo que
    introduce un decreto modificatorio) y se quedan dentro del artículo que los cita.
    """
    correcciones = INV.CORRECCIONES_ENCABEZADO.get(acto_id, {})
    sin_num = INV.SIN_NUMERO.get(acto_id)
    cabeceras = []          # (índice, n, letra, título, inferido)
    if sin_num:
        anclas = sorted(sin_num)
        pos = 0
        for i, l in enumerate(lineas):
            m = HDR_SIN_NUM.match(l)
            if m:
                pos += 1
                desfase = 0
                for p_, real in anclas:
                    if p_ <= pos:
                        desfase = real - p_
                cabeceras.append((i, pos + desfase, "", quitar_marcas(m.group("tit")).strip(" .")[:120], True))
    else:
        cands = []
        for i, l in enumerate(lineas):
            c = candidato_encabezado(l)
            forzado = correcciones.get(numeros[i], "no")
            if forzado != "no":
                if forzado is None:
                    continue
                c = c or {"titulo": "", "raw": str(forzado)}
                c.update(n=forzado, letra="", citado=False, forzado=True)
            if c is not None:
                cands.append((i, c))
        libres = [k for k, (_, c) in enumerate(cands) if not c["citado"]]
        pos_libre = {k: p_ for p_, k in enumerate(libres)}

        def siguientes(k, cuantos=2):
            p_ = pos_libre[k]
            return [cands[j][1]["n"] for j in libres[p_ + 1: p_ + 1 + cuantos]]

        ultimo, objetivos, ini_actual = None, set(), None
        for k, (i, c) in enumerate(cands):
            if c["n"] is None:                              # «ARTICULO %o.» (ruido de OCR)
                c["n"] = (ultimo or 0) + 1
            if c["citado"] and not c.get("forzado"):
                continue
            n, letra = c["n"], c["letra"]
            texto_prev = quitar_marcas(" ".join(lineas[ini_actual:i])) if ini_actual is not None else ""
            inicio = texto_prev[:700]
            anunciando = bool(VERBO.search(inicio[:450])) and bool(ANUNCIO.search(inicio))
            aceptar = False
            if c.get("forzado"):
                aceptar = True
            elif ultimo is None:
                aceptar = (n == 1 and not letra) or siguientes(k) == [n + 1, n + 2]
            elif anunciando:
                if n in objetivos:                          # mismo número que el artículo citado
                    aceptar = n == ultimo + 1 and not letra and siguientes(k, 1) != [n]
                else:
                    aceptar = ultimo < n <= ultimo + 4 and not letra
            elif ultimo < n <= ultimo + 4 and not letra:
                aceptar = True
            elif n == ultimo and not letra:              # numeración duplicada en el propio acto
                aceptar, c["letra"] = True, "bis"
            elif str(n).endswith("0") and len(str(n)) > 1 and int(str(n)[:-1]) == ultimo + 1:   # «4o» leído «40»
                c["n"], aceptar = ultimo + 1, True
            elif n > ultimo + 4 and not letra and siguientes(k) == [n + 1, n + 2]:
                aceptar = True                            # encabezados perdidos en la conversión: se resincroniza
            if not aceptar:
                continue
            if ultimo is not None and c["n"] > ultimo + 1 and c["letra"] != "bis":
                diag.append((acto_id, numeros[i], f"salto de numeración: {ultimo} → {c['n']}"))
            if c["letra"] == "bis":
                diag.append((acto_id, numeros[i], f"artículo {c['n']} duplicado en el acto"))
            cabeceras.append((i, c["n"], c["letra"], c["titulo"], False))
            ultimo, ini_actual = c["n"], i
            ventana = quitar_marcas(" ".join(lineas[i:i + 3]))
            ventana = re.split(r"quedar[aá]|queda\s+as|[“\"]", ventana)[0][:500]
            objetivos = {int(x) for x in re.findall(r"art[ií]culos?\s+(\d+)", ventana[12:], re.I)}
    if not sin_num and cabeceras and not INV.ACTOS[acto_id][7]:     # en los modificatorios, los citados confunden el control
        libres_finales = [c["n"] for i, c in cands if not c["citado"] and i >= int(len(lineas) * 0.85)]
        if libres_finales and max(libres_finales) > cabeceras[-1][1] and max(libres_finales) < 1000:
            diag.append((acto_id, numeros[cabeceras[-1][0]], f"el último encabezado del acto es el {max(libres_finales)} "
                         f"pero el último artículo reconocido es el {cabeceras[-1][1]}: puede haber artículos fundidos"))
    bloques = []
    ini_art = cabeceras[0][0] if cabeceras else len(lineas)
    pre = lineas[:ini_art]
    k = next((j for j, l in enumerate(pre) if CONSIDERANDO.match(l)), None)
    if k is None:
        bloques.append(("encabezado", None, "", "", pre, numeros[0], False))
    else:
        bloques.append(("encabezado", None, "", "", pre[:k], numeros[0], False))
        bloques.append(("considerandos", None, "", "", pre[k:], numeros[k], False))
    for j, (i, n, letra, tit, inf) in enumerate(cabeceras):
        fin = cabeceras[j + 1][0] if j + 1 < len(cabeceras) else len(lineas)
        cuerpo = lineas[i:fin]
        if j + 1 == len(cabeceras):          # último artículo: separar cierre y anexos
            c = next((x for x, l in enumerate(cuerpo) if CIERRE.search(l)), None)
            if c is None:                    # sin fórmula de cierre: los anexos empiezan en el primer «ANEXO»
                c = next((x for x, l in enumerate(cuerpo) if x > 0 and ANEXO.match(l)), None)
            if c is not None:
                cola = cuerpo[c:]
                cuerpo = cuerpo[:c]
                bloques.append(("articulo", n, letra, tit, cuerpo, numeros[i], inf))
                anexos = [x for x, l in enumerate(cola) if ANEXO.match(l) and not re.search(r"\s\d{2,3}\s*\**\s*$", l)]
                corte = anexos[0] if anexos else len(cola)
                if sum(len(l) for l in cola[:corte]) > 2500:     # después de las firmas viene contenido sin rótulo de anexo
                    lim = 0
                    for x, l in enumerate(cola[:corte]):
                        if x > 40 or (x > 3 and len(l.strip()) > 250):
                            break
                        lim = x + 1
                    anexos = [lim] + anexos
                    corte = lim
                bloques.append(("cierre", None, "", "", cola[:corte], numeros[i + c], False))
                for a_, x in enumerate(anexos):
                    y = anexos[a_ + 1] if a_ + 1 < len(anexos) else len(cola)
                    tit_anexo = quitar_marcas(cola[x].lstrip("# "))[:120] if ANEXO.match(cola[x]) else "Anexo sin título (contenido posterior a las firmas)"
                    mnum = re.search(r"ANEXO\s+(?:N[°º.o]*\s*)?(\d+)", tit_anexo, re.I)
                    bloques.append(("anexo", int(mnum.group(1)) if mnum else a_ + 1, "", tit_anexo, cola[x:y],
                                    numeros[i + c + x], False))
                continue
        bloques.append(("articulo", n, letra, tit, cuerpo, numeros[i], inf))
    return bloques


def partir(texto: str, maximo: int = MAX_CHARS) -> list[str]:
    if len(texto) <= maximo:
        return [texto]
    piezas, actual = [], ""
    for linea in texto.split("\n"):
        while len(linea) > maximo:                      # línea muy larga: cortar por oraciones
            corte = linea.rfind(". ", 0, maximo)
            corte = corte + 1 if corte > maximo // 3 else maximo
            if actual:
                piezas.append(actual.strip())
                actual = ""
            piezas.append(linea[:corte].strip())
            linea = linea[corte:]
        if len(actual) + len(linea) + 1 > maximo and actual:
            piezas.append(actual.strip())
            actual = ""
        actual += linea + "\n"
    if actual.strip():
        piezas.append(actual.strip())
    return [p for p in piezas if p]


# ---------------------------------------------------------------------------
# Paso 3. Grafo de afectaciones: fórmulas del lenguaje normativo
# ---------------------------------------------------------------------------

VERBO = re.compile(r"(Integrar\s+y\s+modificar|Modif[ií]quese|Modificar|Se\s+modifica|Modif[ií]case|Sustit[uú]yase|Subr[oó]guese|"
                   r"Adici[oó]nese|Adicionar|Se\s+adiciona|Actual[ií]cese|Der[oó]guese|Der[oó]gase|Derogar)\b", re.I)
NUM_ART = r"\d+(?:\s?[A-Z](?![A-Za-záéíóúÁÉÍÓÚñÑ]))?"
ART_OBJ = re.compile(r"\b[Aa]rt[ií]culos?\s*(?:N[°º.o]*\s*)?(" + NUM_ART + r")(?![\d])((?:\s*(?:,|y)\s*" + NUM_ART + r")*)")
EL_ART_SE_MODIFICA = re.compile(r"^\s*El\s+[Aa]rt[ií]culo\s+(\d+[A-Z]?)\S*\s+del\s+(Decreto|Acuerdo)\s+(?:Municipal\s+|Distrital\s+)?(\d{1,4})\s+de\s+(\d{4}).{0,200}?\bse\s+modifica", re.I)
PARCIAL = re.compile(r"\b(par[aá]grafos?|numeral(?:es)?|incisos?|literal(?:es)?|tabla|t[ií]tulo|cuadro|conformaci[oó]n|fila)\b.{0,160}\b(del|al|en\s+el)\s*$", re.I)
RENUM = re.compile(r"pasar[aá]n?\s+a\s+ser\s+el\s+[Aa]rt[ií]culo\s+(" + NUM_ART + ")")
DEC_EXPL = re.compile(r"\b(?:del|al)\s+(Decreto|Acuerdo)\s+(?:Municipal\s+|Distrital\s+|N[°º.o]*\s*)*(\d{1,4})\s+de(?:l)?\s+(\d{4})", re.I)
TITULO_EXCLUIDO = re.compile(r"^\W*(OBJETO|[ÁA]MBITO DE APLICACI[ÓO]N|ALCANCE|VIGENCIAS?\b.*|DEROGATORIAS?\b.*|"
                             r"R[ÉE]GIMEN DE TRANSICI.*|(ADICIONES|MODIFICACIONES)\b.*(DEROGATORIAS|ADICIONES|MODIFICACIONES).*)\W*$", re.I)
ALCANCE_TRAS = re.compile(r"^[^.]{0,80}?(?:,\s*|\s+en\s+su\s+|\s+y\s+(?:el\s+|la\s+|su\s+)?)(par[aá]grafos?|numeral(?:es)?|incisos?|literal(?:es)?|enunciado)\b", re.I)


def norm_num(s: str) -> str:
    return re.sub(r"\s+", "", s).upper()


def extraer_afectacion(acto_id: str, unidad: dict):
    if TITULO_EXCLUIDO.search(unidad["titulo"] or ""):
        return None
    cuerpo = quitar_marcas(unidad["texto_completo"])[:900]
    cuerpo = re.sub(r"\s+", " ", cuerpo)
    corte = re.search(r"quedar[aá]|[“\"]|su\s+texto\s+es\s+el\s+siguiente|el\s+texto\s+que\s+se\s+adiciona", cuerpo, re.I)
    zona = cuerpo[:corte.start() + 1] if corte else cuerpo
    cuerpo_sin_cab = re.sub(r"^\s*ART[ÍI]CULO\s*\S+\s*[°ºo]?\s*[.:\-–]?\s*", "", cuerpo, flags=re.I)
    me = EL_ART_SE_MODIFICA.search(cuerpo_sin_cab)
    if me:                                   # «El artículo 4º del Decreto 1569 de 2016, (…) se modifica y queda así»
        return {"op": "modifica", "destino": id_acto_desde_texto(me.group(2), me.group(3), me.group(4)),
                "articulos": [norm_num(me.group(1))], "nuevo_rotulo": norm_num(me.group(1)), "alcance": "", "explicito": True}
    mv = VERBO.search(zona[:420])
    if not mv:
        return None
    tras = zona[mv.end():]
    ma = ART_OBJ.search(tras[:260])
    if re.match(r"\s*(un|el\s+siguiente)\s+(nuevo\s+)?art[ií]culo\b", tras, re.I):
        ma = None
    if not ma and re.match(r"\s*(un|el\s+siguiente)\s+(nuevo\s+)?art[ií]culo", tras, re.I) and sin_tildes(mv.group(1)).lower().startswith(("adicion", "se adiciona")):
        mn = re.search(r"[Aa]rt[ií]culo\s+(" + NUM_ART + ")", cuerpo[mv.end() + 30:])   # «Se adiciona un artículo…: Artículo 8º.»
        if mn:
            return {"op": "adiciona", "destino": INV.ACTOS[acto_id][7] or "", "articulos": [norm_num(mn.group(1))],
                    "nuevo_rotulo": norm_num(mn.group(1)), "alcance": "", "explicito": False}
    if not ma:
        return None
    medio = tras[:ma.start()]
    if re.search(r"\bDecreto\b|\bAcuerdo\b", medio):        # «Modificar el Decreto X…» es el objeto, no un artículo
        return None
    numeros = [norm_num(ma.group(1))] + [norm_num(x) for x in re.findall(r"\d+\s?[A-Z]?", ma.group(2) or "")]
    resto = tras[ma.end():ma.end() + 320]
    md = DEC_EXPL.search(resto)
    if md:
        destino = id_acto_desde_texto(md.group(1), md.group(2), md.group(3))
    else:
        destino = INV.ACTOS[acto_id][7]
    verbo = sin_tildes(mv.group(1)).lower()
    tras_num = re.sub(r"^\s*,?\s*(?:de\s+la\s+|del\s+)?(?:secci[óo]n|cap[ií]tulo|t[ií]tulo|subsecci[óo]n)[^,]*,?", "", resto)
    tras_num = re.sub(r"^\s*,?\s*del\s+Decreto\s+(?:Municipal\s+|Distrital\s+)?\d+\s+de\s+\d{4}", "", tras_num, flags=re.I)
    mpar = ALCANCE_TRAS.search(resto) or ALCANCE_TRAS.search(tras_num)
    parcial = bool(PARCIAL.search(medio.strip())) or bool(mpar)
    mr = RENUM.search(cuerpo[:700])
    if verbo.startswith("integrar"):
        op = "integra"
    elif mr:
        op = "renumera"
    elif verbo.startswith(("adicion", "se adiciona")):
        op = "adiciona_subunidad" if parcial else "adiciona"
    elif verbo.startswith("derog"):
        op = "deroga_subunidad" if parcial else "deroga"
    elif verbo.startswith("actualic"):
        op = "modifica_parcial"
    else:
        op = "modifica_parcial" if parcial else "modifica"
    nuevo = norm_num(mr.group(1)) if mr else (numeros[0] if op in ("modifica", "adiciona") else None)
    if op == "integra":
        mr2 = RENUM.search(cuerpo[:700])
        nuevo = norm_num(mr2.group(1)) if mr2 else numeros[0]
    alcance = ""
    if parcial:
        if PARCIAL.search(medio.strip()):
            alcance = re.sub(r"^(?:el|la|los|las|un|una)\s+", "", medio.strip(), flags=re.I)
            alcance = re.sub(r"\s+(?:del|al|en\s+el)$", "", alcance, flags=re.I)[:80]
        else:
            alcance = re.split(r"[;:]|\bdel\s+Decreto|\bel\s+cual|\bquedar", (resto if ALCANCE_TRAS.search(resto) else tras_num)[mpar.start(1):], flags=re.I)[0].strip(" ,.")[:80]
    return {"op": op, "destino": destino, "articulos": numeros, "nuevo_rotulo": nuevo, "alcance": alcance,
            "explicito": bool(md)}


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnostico", action="store_true")
    a = ap.parse_args()
    C.CURADURIA_DIR.mkdir(exist_ok=True)
    t0 = time.time()
    diag: list[tuple] = []

    # ---------------- Paso 0: inventario ----------------
    faltan = [f for f in INV.SEGMENTOS if not (C.CORPUS_A_DIR / f).exists()]
    sobran = [p.name for p in C.CORPUS_A_DIR.glob("*.md") if p.name not in INV.SEGMENTOS]
    if faltan:
        raise SystemExit(f"Faltan en corpus_A: {faltan}")
    for s in sobran:
        diag.append((s, 0, "archivo sin inventariar: no entra a la base curada"))
    TIEMPOS["paso0_inventario_s"] = round(time.time() - t0, 2)

    # ---------------- Paso 1 y 2: segmentación y firma de identidad ----------------
    t1 = time.time()
    unidades: list[dict] = []
    por_texto: dict[str, list[dict]] = defaultdict(list)
    notas_compilacion: dict[str, list[str]] = {}
    for archivo, segmentos in INV.SEGMENTOS.items():
        todas = (C.CORPUS_A_DIR / archivo).read_text(encoding="utf-8").split("\n")
        for desde, hasta, acto, papel in segmentos:
            lineas = todas[desde - 1: hasta if hasta else len(todas)]
            if papel in ("contigua", "reproduccion"):
                texto = limpiar_texto(lineas)
                uid = f"{'CONTIGUO' if papel == 'contigua' else acto}:{papel}:{archivo}:{desde}"
                unidades.append({
                    "id": uid, "id_texto": uid, "acto": acto if papel == "reproduccion" else "",
                    "instrumento": etiqueta(acto) if papel == "reproduccion" else acto,
                    "instrumento_id": acto if papel == "reproduccion" else "", "rotulo": "Copia completa",
                    "rotulo_num": None, "titulo": "", "alcance": "Documento", "acto_fuente": "",
                    "tipo_documento": "", "naturaleza_fuente": "Reproducción" if papel == "reproduccion" else "Acto contiguo",
                    "id_fuente": "", "archivo": archivo, "lineas": [desde, hasta or len(todas)],
                    "fecha_expedicion": "", "fecha_publicacion": "", "fecha_estimada": False,
                    "vigente_desde": "", "vigente_hasta": "", "estado": "No aplica", "acto_modificatorio": "",
                    "id_canonico": acto if papel == "reproduccion" else "", "particion": papel,
                    "relacionados": [], "notas": [], "orden": 0, "texto": texto, "firma": "", "inferido": False})
                if papel == "reproduccion" and acto in INV.COMPILACIONES and INV.COMPILACIONES[acto][0] == archivo:
                    notas_compilacion[acto] = lineas
                continue
            notas = []
            if papel == "compilacion":
                lineas, notas = limpiar_compilacion(lineas)
            tipo, num, anio, exp, pub, gaceta, titulo_acto, _ = INV.ACTOS[acto]
            vd, estimada = fecha_vigor(acto)
            lineas, numeros = despegar(lineas, desde)
            for orden, (clase, n, letra, tit, cuerpo, linea_ini, inferido) in enumerate(segmentar(acto, lineas, numeros, diag)):
                texto = limpiar_texto(cuerpo)
                if not texto:
                    continue
                if clase == "articulo":
                    rot_num = f"{n}{letra}" if letra != "bis" else f"{n}bis"
                    id_texto = f"{acto}:a{rot_num}"
                    rotulo, alcance = f"Artículo {n}{' ' + letra if letra == 'bis' else letra}", "Artículo"
                elif clase == "anexo":
                    rot_num, id_texto, rotulo, alcance = None, f"{acto}:anexo{n}", tit or f"Anexo {n}", "Anexo"
                else:
                    rot_num, id_texto, rotulo, alcance = None, f"{acto}:{clase}", clase.capitalize(), clase.capitalize()
                if any(u["id_texto"] == id_texto for u in por_texto[id_texto]):
                    id_texto = f"{id_texto}_{orden}"
                base = {
                    "id_texto": id_texto, "acto": acto, "instrumento": etiqueta(acto), "instrumento_id": acto,
                    "rotulo": rotulo, "rotulo_num": rot_num, "titulo": tit, "alcance": alcance,
                    "acto_fuente": f"{etiqueta(acto)}" + (f", art. {rot_num}" if rot_num else ""),
                    "tipo_documento": tipo, "naturaleza_fuente": "Compilación" if papel == "compilacion" else "Gaceta",
                    "id_fuente": f"Gaceta Oficial {gaceta}" if gaceta else "", "archivo": archivo,
                    "lineas": [linea_ini, linea_ini + len(cuerpo) - 1],
                    "fecha_expedicion": exp, "fecha_publicacion": pub or "", "fecha_estimada": estimada,
                    "vigente_desde": vd, "vigente_hasta": "", "estado": "Vigente", "acto_modificatorio": "",
                    "id_canonico": "", "particion": "sin_contenido" if clase == "cierre" else "activa",
                    "relacionados": [], "notas": [], "orden": orden, "inferido": inferido,
                    "texto_completo": texto,
                }
                por_texto[id_texto].append(base)
                unidades.append(base)
            if notas:
                notas_compilacion.setdefault(acto, notas)
    TIEMPOS["paso1_2_segmentacion_s"] = round(time.time() - t1, 2)

    canon = [u for u in unidades if u["particion"] in ("activa", "sin_contenido")]
    for u in canon:
        if u["acto"] in INV.AVISOS_ACTO:
            u["aviso"] = INV.AVISOS_ACTO[u["acto"]]
    for acto, aviso in INV.AVISOS_ACTO.items():
        diag.append((acto, 0, aviso))
    por_id = {u["id_texto"]: u for u in canon}

    if a.diagnostico:
        por_acto = defaultdict(list)
        for u in canon:
            if u["rotulo_num"]:
                por_acto[u["acto"]].append(u["rotulo_num"])
        for acto, nums in por_acto.items():
            print(f"{acto}: {len(nums)} artículos · {' '.join(nums[:12])} … {' '.join(nums[-5:])}")

    # ---------------- Paso 3: grafo de afectaciones ----------------
    t3 = time.time()
    relaciones, pendientes = [], []
    for u in canon:
        if u["alcance"] != "Artículo":
            continue
        r = extraer_afectacion(u["acto"], u)
        if not r:
            continue
        r.update(origen=u["id_texto"], acto_origen=u["acto"], fecha=u["vigente_desde"], fuente="texto del acto")
        if r["destino"] not in INV.ACTOS:
            pendientes.append({"origen": u["id_texto"], "relacion": r["op"], "destino": r["destino"],
                               "articulos": ",".join(r["articulos"]), "motivo": "acto destino fuera del corpus"})
            continue
        if r["destino"] == u["acto"]:
            continue
        relaciones.append(r)
    for derogante, art, derogados in INV.DEROGACIONES_TOTALES:
        for d in derogados:
            relaciones.append({"op": "deroga_acto", "destino": d, "articulos": [], "origen": f"{derogante}:a{art}",
                               "acto_origen": derogante, "fecha": fecha_vigor(derogante)[0], "nuevo_rotulo": None,
                               "alcance": "acto completo", "explicito": True, "fuente": "inventario (artículo de vigencia)"})
    for derogante, art, destino, arts in INV.DEROGACIONES_PARCIALES:
        relaciones.append({"op": "deroga", "destino": destino, "articulos": arts, "origen": f"{derogante}:a{art}",
                           "acto_origen": derogante, "fecha": fecha_vigor(derogante)[0], "nuevo_rotulo": None,
                           "alcance": "", "explicito": True, "fuente": "inventario (artículo de vigencia)"})
    for derogante, art, destino, art_dest, alcance in INV.DEROGACIONES_SUBUNIDAD:
        relaciones.append({"op": "deroga_subunidad", "destino": destino, "articulos": [art_dest], "origen": f"{derogante}:a{art}",
                           "acto_origen": derogante, "fecha": fecha_vigor(derogante)[0], "nuevo_rotulo": None,
                           "alcance": alcance, "explicito": True, "fuente": "inventario (artículo de vigencia)"})
    # pendientes que solo declaran las notas de las compilaciones (p. ej. el Decreto 541 de 2022)
    for acto, notas in notas_compilacion.items():
        for m in re.finditer(r"(modificad|derogad|adicionad)\w*\s+por\s+el\s+art[ií]culo\s+(\d+)\s+del\s+Decreto\s+(\d{1,4})\s+de\s+(\d{4})",
                             " ".join(notas), re.I):
            d = id_acto_desde_texto("Decreto", m.group(3), m.group(4))
            if d not in INV.ACTOS and not any(p["destino"] == d and p["origen"] == acto for p in pendientes):
                pendientes.append({"origen": acto, "relacion": f"{m.group(1).lower()}o por (según la compilación)", "destino": d,
                                   "articulos": m.group(2), "motivo": "acto citado en las notas de vigencia y ausente del corpus"})
    TIEMPOS["paso3_grafo_s"] = round(time.time() - t3, 2)

    # ---------------- Paso 4: vigencia por linaje ----------------
    t4 = time.time()
    titular: dict[tuple, str] = {}                       # (instrumento, rótulo) -> id_texto que lo ocupa
    for u in canon:
        if u["rotulo_num"] and u["acto"] == u["instrumento_id"]:
            titular.setdefault((u["acto"], u["rotulo_num"]), u["id_texto"])
    registro = []

    def cerrar(uid, fecha, estado, origen):
        x = por_id.get(uid)
        if not x or x["vigente_hasta"]:
            return False
        x["vigente_hasta"], x["estado"] = fecha, estado
        x["acto_modificatorio"] = f"{etiqueta(origen.split(':')[0])}, art. {origen.split(':a')[-1]}" if ":a" in origen else etiqueta(origen.split(":")[0])
        x["particion"] = "historica" if x["particion"] == "activa" else x["particion"]
        return True

    relaciones.sort(key=lambda r: (r["fecha"], r["acto_origen"], por_id.get(r["origen"], {}).get("orden", 0)))
    for (fecha, acto_origen), grupo in _agrupar(relaciones):
        foto = dict(titular)                              # los destinos se resuelven contra la versión anterior al acto
        for r in grupo:
            o = por_id.get(r["origen"])
            if r.get("fuente", "").startswith("inventario") and r["op"] != "deroga":
                o = None                                  # la unidad de origen es el artículo de vigencia: no se reetiqueta
            T = r["destino"]
            if r["op"] == "deroga_acto":
                n = 0
                for x in canon:
                    if (x["instrumento_id"] == T or x["acto"] == T) and x["particion"] == "activa":
                        n += cerrar(x["id_texto"], fecha, "Derogada", r["origen"])
                registro.append(_reg(r, T, "", n))
                continue
            objetivos = [foto.get((T, a)) for a in r["articulos"]]
            if o is not None and r["op"] in ("modifica", "renumera", "integra", "adiciona", "modifica_parcial",
                                             "adiciona_subunidad", "deroga_subunidad"):
                o["instrumento"], o["instrumento_id"] = etiqueta(T), T
                o["acto_fuente"] = f"{etiqueta(o['acto'])}, art. {o['rotulo_num']}"
            if r["op"] in ("modifica", "renumera", "integra", "deroga"):
                for a_, obj in zip(r["articulos"], objetivos):
                    if obj is None:
                        diag.append((r["origen"], 0, f"{r['op']}: no se encontró el art. {a_} de {T} en el corpus"))
                        continue
                    est = "Derogada" if r["op"] == "deroga" else "Modificada"
                    if cerrar(obj, fecha, est, r["origen"]):
                        if o is not None:
                            por_id[obj]["relacionados"].append(o["id_texto"])
                            o["relacionados"].append(obj)
                    registro.append(_reg(r, obj, a_, 1))
            if o is not None and r["op"] in ("modifica", "renumera", "integra", "adiciona", "modifica_parcial", "adiciona_subunidad"):
                tras = re.split(r"quedar[aá]n?\s+(?:as[ií]|de\s+la\s+siguiente\s+manera)\s*:?|queda\s+as[ií]\s*:?|as[ií]\s*:|(?:Decreto|Acuerdo)[^:.]{0,40}\d{4}\s*:", quitar_marcas(o["texto_completo"]), maxsplit=1)
                if len(tras) == 2:
                    mt = re.search(r"(?:[Aa]rt[ií]culo|ART[ÍI]CULO)\s*\d+\s*[A-Z]?\s*[°ºo]?\s*[.:\-–]\s*([^.\n]{4,90})", tras[1][:400])
                    mt2 = re.match(r"\W*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ ,]{6,90})", tras[1][:200])
                    if mt or mt2:
                        o["titulo"] = (mt or mt2).group(1).strip(" .:")
            if (o is not None and r["op"] in ("modifica", "renumera", "integra") and objetivos and objetivos[0]
                    and VERBO.match(o["titulo"] or "")):
                o["titulo"] = por_id[objetivos[0]]["titulo"]      # el título citado no se pudo leer: se usa el del artículo que reemplaza
            if o is not None and r["op"] in ("modifica", "renumera", "integra", "adiciona"):
                nuevo = r["nuevo_rotulo"] or r["articulos"][0]
                o["rotulo"], o["rotulo_num_instrumento"] = f"Artículo {nuevo}", nuevo
                titular[(T, nuevo)] = o["id_texto"]
                if r["op"] == "adiciona":
                    registro.append(_reg(r, "", nuevo, 1))
            if r["op"] in ("modifica_parcial", "adiciona_subunidad", "deroga_subunidad"):
                for a_, obj in zip(r["articulos"], objetivos):
                    if obj is None:
                        diag.append((r["origen"], 0, f"{r['op']}: no se encontró el art. {a_} de {T} en el corpus"))
                        continue
                    x = por_id[obj]
                    if o is not None and x["titulo"]:
                        o["titulo"] = x["titulo"]
                    if not x["vigente_hasta"]:
                        x["estado"] = "Vigente (modificada parcialmente)"
                        verbo_n = {"deroga_subunidad": "derogada", "adiciona_subunidad": "adicionada"}.get(r["op"], "modificada")
                        art_o = r["origen"].split(":a")[-1] if ":a" in r["origen"] else "?"
                        x["notas"].append(f"{r['alcance'] or 'parte'} {verbo_n} por el {etiqueta(acto_origen)}, art. {art_o}, desde {ddmmaaaa(fecha)}")
                    if o is not None:
                        x["relacionados"].append(o["id_texto"])
                        o["relacionados"].append(obj)
                        o["rotulo"] = f"Artículo {a_} ({r['alcance'] or 'parte'})"
                    registro.append(_reg(r, obj, a_, 1))

    # Segundo detector: compilaciones con notas de vigencia
    revision = []
    for acto, (archivo, corte) in INV.COMPILACIONES.items():
        texto = "\n".join(notas_compilacion.get(acto, []))
        derogados_comp = set()
        for m in re.finditer(r"(?:ART[ÍI]CULO|Art[íi]culo)\s+(\d+[A-Z]?)[oº°]?\.?[^\n]{0,200}\n?[^\n]{0,200}?[Dd]erogado", texto):
            derogados_comp.add(m.group(1))
        for x in canon:
            if x["instrumento_id"] != acto or x["estado"] != "Derogada":
                continue
            rot = x.get("rotulo_num_instrumento") or x["rotulo_num"]
            if rot in derogados_comp:
                continue
            if x["vigente_hasta"] > corte:
                # la compilación tiene corte anterior a la derogación: no es un desacuerdo, es una fuente
                # compilada desactualizada (tipo 8 de la taxonomía). La derogación expresa se acepta.
                x["notas"].append(f"la compilación del normograma (corte {ddmmaaaa(corte)}) es anterior a esta derogación "
                                  f"y todavía presenta este texto como vigente")
                revision.append({"id_texto": x["id_texto"], "motivo": "fuente compilada desactualizada",
                                 "detalle": f"la compilación (corte {ddmmaaaa(corte)}) no recoge la derogación del "
                                            f"{ddmmaaaa(x['vigente_hasta'])} por el {x['acto_modificatorio']}",
                                 "riesgo": "informativo: un sistema que use la compilación citaría una norma derogada"})
                continue
            lectura_comp = f"según la compilación del normograma (corte {ddmmaaaa(corte)}) está vigente"
            lectura_reg = f"según {x['acto_modificatorio']} fue derogado el {ddmmaaaa(x['vigente_hasta'])}"
            x["estado"] = "Por confirmar"
            x["notas"].append(f"{lectura_comp}; {lectura_reg}")
            x["fecha_derogacion_registro"] = x["vigente_hasta"]
            x["vigente_hasta"], x["particion"] = "", "activa"
            revision.append({"id_texto": x["id_texto"], "motivo": "los dos detectores discrepan",
                             "detalle": f"{lectura_comp}; {lectura_reg}", "riesgo": "alto: podría estar derogada"})
    TIEMPOS["paso4_vigencia_s"] = round(time.time() - t4, 2)

    # Control de salida del paso 3: cotejo con la lista del artículo de vigencia de cada acto
    revision += cotejar(canon, registro)

    # ---------------- Paso 5: reproducciones ----------------
    t5 = time.time()
    huellas = defaultdict(list)
    for x in canon:
        if x["particion"] in ("activa", "historica") and len(x["texto_completo"]) > 300:
            h = hashlib.md5(comun.normalizar(x["texto_completo"]).encode()).hexdigest()
            huellas[h].append(x["id_texto"])
    reproducciones = [{"unidades": " | ".join(v), "actos": " | ".join(sorted({i.split(':')[0] for i in v}))}
                      for v in huellas.values() if len({i.split(":")[0] for i in v}) > 1]
    TIEMPOS["paso5_reproducciones_s"] = round(time.time() - t5, 2)

    # ---------------- Paso 6: partición, firma y manifiesto ----------------
    t6 = time.time()
    salida = []
    for x in unidades:
        if x["particion"] in ("contigua", "reproduccion"):
            salida.append(x)
            continue
        firma = construir_firma(x)
        partes = partir(x.pop("texto_completo")) if x["particion"] != "sin_contenido" else [x.pop("texto_completo")]
        for k, p in enumerate(partes, 1):
            y = dict(x)
            y["id"] = x["id_texto"] if len(partes) == 1 else f"{x['id_texto']}#{k}"
            y["parte"] = f"{k}/{len(partes)}"
            y["firma"] = firma if len(partes) == 1 else firma[:-1] + f" · parte {k} de {len(partes)}]"
            y["texto"] = p
            y["relacionados"] = sorted(set(x["relacionados"]))[:8]
            salida.append(y)
    comun.jsonl(C.UNIDADES_B, salida)

    _csv(C.CURADURIA_DIR / "afectaciones.csv", registro)
    _csv(C.CURADURIA_DIR / "pendientes.csv", pendientes)
    revision += [{"id_texto": d[0], "motivo": "aviso de segmentación o grafo", "detalle": d[2], "riesgo": "medio",
                  "linea": d[1]} for d in diag]
    _csv(C.CURADURIA_DIR / "revision.csv", revision)
    _csv(C.CURADURIA_DIR / "reproducciones.csv", reproducciones)
    TIEMPOS["paso6_base_s"] = round(time.time() - t6, 2)
    TIEMPOS["total_s"] = round(time.time() - t0, 2)
    (C.CURADURIA_DIR / "registro_costo.json").write_text(json.dumps(TIEMPOS, indent=2), encoding="utf-8")
    escribir_manifiesto(salida, registro, pendientes, revision, reproducciones)
    print(f"Listo: {len(salida)} registros en {C.UNIDADES_B} · {TIEMPOS['total_s']} s")
    print(Counter(x["particion"] for x in salida))


def cotejar(canon, registro):
    """Compara lo que cada acto declara en su artículo de vigencia (modifica / adiciona / deroga los
    artículos …) con las relaciones que quedaron en el registro. Las diferencias van a revisión."""
    tipo_de = {"modifica": "modifica", "modifica_parcial": "modifica", "renumera": "modifica", "integra": "modifica",
               "adiciona_subunidad": "modifica", "adiciona": "adiciona", "deroga": "deroga", "deroga_subunidad": "deroga"}
    reg = defaultdict(lambda: defaultdict(set))
    for r in registro:
        t = tipo_de.get(r["relacion"])
        if t and r["articulo_destino"]:
            reg[r["origen"].split(":")[0]][t].add(str(r["articulo_destino"]).upper())
    num = r"\d+(?:\s?(?![yY]\b)[A-Za-z]\b)?"
    patrones = {
        "modifica": r"modific\w*\s+(?:sus\s+|los\s+)?art[ií]culos?\s*:?\s*(.+?)(?=;|\badiciona|\by\s+deroga|\bdel\s+Decreto|\bLos\s+dem|$)",
        "adiciona": r"adicion\w*\s+(?:al\s+mismo,\s*)?(?:los\s+)?art[ií]culos?\s+(.+?)(?=;|\by\s+deroga|\bal\s+Decreto|\bdel\s+Decreto|\bLos\s+dem|$)",
        "deroga": r"derog\w*\s+(?:expresamente\s+)?(?:los\s+|el\s+)?art[ií]culos?\s+(.+?)(?=;|\bdel\s+Decreto|\be\s+integra|\bLos\s+dem|$)"}
    salida = []
    for u in canon:
        if u["alcance"] != "Artículo" or not re.search(r"vigencia|derogatori|modificaciones\s+y", u["titulo"] or "", re.I):
            continue
        t = re.sub(r"\s+", " ", quitar_marcas(u.get("texto_completo", "")))
        for tipo, pat in patrones.items():
            m = re.search(pat, t, re.I)
            if not m:
                continue
            declarados = {re.sub(r"\s", "", x).upper() for x in re.findall(num, m.group(1))}
            faltan = sorted(declarados - reg[u["acto"]][tipo], key=lambda z: (len(z), z))
            if faltan:
                salida.append({"id_texto": u["id_texto"], "motivo": "cotejo con el artículo de vigencia",
                               "detalle": f"declara que {tipo} los artículos {', '.join(faltan)} y el registro no tiene esa relación",
                               "riesgo": "medio: posible relación no extraída o artículo no segmentado"})
    return salida


def _agrupar(relaciones):
    grupo, clave = [], None
    for r in relaciones:
        k = (r["fecha"], r["acto_origen"])
        if k != clave and grupo:
            yield clave, grupo
            grupo = []
        clave = k
        grupo.append(r)
    if grupo:
        yield clave, grupo


def _reg(r, destino_id, articulo, n):
    return {"fecha": r["fecha"], "origen": r["origen"], "relacion": r["op"], "acto_destino": r["destino"],
            "articulo_destino": articulo, "unidad_destino": destino_id, "alcance": r.get("alcance", ""),
            "unidades_afectadas": n, "fuente_de_la_relacion": r.get("fuente", "")}


def construir_firma(x):
    partes = [x["instrumento"]]
    rot = x["rotulo"]
    if x["alcance"] == "Artículo":
        rot = rot.replace("Artículo", "art.")
    partes.append(rot + (" (número inferido)" if x.get("inferido") else ""))
    if x["titulo"] and x["alcance"] in ("Artículo", "Anexo") and len(x["titulo"]) > 3 and x["titulo"] != x["rotulo"]:
        partes.append(x["titulo"][:70].rstrip(" .:"))
    if x["instrumento_id"] != x["acto"]:
        partes.append(f"texto dado por el {x['acto_fuente']}")
    if x["naturaleza_fuente"] == "Compilación":
        partes.append("según compilación")
    if x.get("aviso"):
        partes.append("AVISO: " + x["aviso"])
    e = x["estado"]
    if e == "Vigente":
        partes.append(f"vigente desde {ddmmaaaa(x['vigente_desde'])}")
    elif e.startswith("Vigente (modificada"):
        partes.append(f"vigente desde {ddmmaaaa(x['vigente_desde'])}, con partes modificadas por otra norma")
    elif e == "Modificada":
        partes.append(f"modificado por el {x['acto_modificatorio']} desde {ddmmaaaa(x['vigente_hasta'])}")
    elif e == "Derogada":
        partes.append(f"derogado por el {x['acto_modificatorio']} desde {ddmmaaaa(x['vigente_hasta'])}")
    elif e == "Por confirmar":
        partes.append("vigencia por confirmar: " + (x["notas"][-1] if x["notas"] else ""))
    return "[" + " · ".join(p for p in partes if p) + "]"


def _csv(ruta, filas):
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        if not filas:
            f.write("sin registros\n")
            return
        campos = list(dict.fromkeys(k for fila in filas for k in fila))
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)


def escribir_manifiesto(salida, registro, pendientes, revision, reproducciones):
    unid = {}
    for x in salida:
        unid.setdefault(x["id_texto"], x)
    lin = ["# Manifiesto de la base curada", "", f"Fecha de corte: {C.FECHA_HOY}", "",
           "## Instrumentos incorporados", "", "| Acto | Instrumento | Fecha desde la que rige | Unidades | Estado predominante |",
           "|---|---|---|---|---|"]
    por_acto = defaultdict(list)
    for x in unid.values():
        if x["particion"] in ("activa", "historica"):
            por_acto[x["acto"]].append(x)
    for acto in sorted(INV.ACTOS, key=lambda k: fecha_vigor(k)[0]):
        xs = por_acto.get(acto, [])
        vd, est = fecha_vigor(acto)
        estado = Counter(x["estado"] for x in xs).most_common(1)[0][0] if xs else "—"
        lin.append(f"| {acto} | {etiqueta(acto)} | {ddmmaaaa(vd)}{' (estimada)' if est else ''} | {len(xs)} | {estado} |")
    lin += ["", "## Unidades por partición y estado", "", "| Partición | Estado | Unidades | Fragmentos indexables |", "|---|---|---|---|"]
    c1 = Counter((x["particion"], x["estado"]) for x in unid.values())
    c2 = Counter((x["particion"], x["estado"]) for x in salida)
    for (p, e), n in sorted(c1.items()):
        lin.append(f"| {p} | {e} | {n} | {c2[(p, e)] if p in ('activa', 'historica') else 0} |")
    lin += ["", f"## Registro de afectaciones: {len(registro)} relaciones", "",
            "| Relación | Cantidad |", "|---|---|"]
    for k, n in Counter(r["relacion"] for r in registro).most_common():
        lin.append(f"| {k} | {n} |")
    lin += ["", f"## Cola de pendientes: {len(pendientes)}", ""]
    for d in sorted({p["destino"] for p in pendientes}):
        lin.append(f"- {d}")
    lin += ["", f"## Casos para revisión humana: {len(revision)}", ""]
    for r in revision[:40]:
        lin.append(f"- `{r['id_texto']}`: {r['detalle']}")
    if len(revision) > 40:
        lin.append(f"- … y {len(revision) - 40} más en revision.csv")
    lin += ["", f"## Reproducciones entre actos: {len(reproducciones)} grupos (ver reproducciones.csv)", "",
            "## Documentos citados que la base no contiene", "",
            "La base no contiene los documentos técnicos de soporte, las fichas de indicadores ni los actos de la cola de pendientes. "
            "Una pregunta sobre ellos debe responderse diciendo que la base no tiene esa información.", ""]
    (C.CURADURIA_DIR / "manifiesto.md").write_text("\n".join(lin), encoding="utf-8")


if __name__ == "__main__":
    main()

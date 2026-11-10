"""Análisis preregistrado del OE3 (plan_analisis_oe3.md) sobre la calificación ciega del banco D."""
from pathlib import Path
import csv, json, re, sys, statistics
from collections import defaultdict
import numpy as np
import openpyxl
from scipy.stats import binomtest

# Rutas dentro de la carpeta de anexos: Anexo_I/codigo/ junto a Anexo_F/ y Anexo_G/
AQUI = Path(__file__).resolve().parent
ANEXOS = AQUI.parent.parent
CALIF = ANEXOS / 'Anexo_G' / 'calificacion_ciega_OE3_D_final.xlsx'      # calificación final (hoja D)
CRUCE = ANEXOS / 'Anexo_G' / 'resultados_calificacion_D_OE3.xlsx'       # condición de cada código (hoja Datos)
BANCO = ANEXOS / 'Anexo_F' / 'banco_agente_D.csv'
RUNS = AQUI.parent / 'corridas_banco_D'
SALIDA = AQUI.parent / 'resultados'; SALIDA.mkdir(exist_ok=True)
SEMILLA = 20261029
CONDS = ['A_demo', 'A_hibrida', 'B', 'B_bm25']
CORR = {'AG-206-R1': '1', 'AG-149-R1': '1', 'AG-201-R1': 'NA_hist', 'AG-201-R4': 'NA_hist'}  # correcciones del 4-nov (Iván)
A48 = {'AG-203-R4', 'AG-204-R3', 'AG-204-R4', 'AG-207-R2', 'AG-208-R1', 'AG-208-R2'}

# --- calificación + clave -----------------------------------------------------------
g = openpyxl.load_workbook(CALIF, data_only=True)['D']
gh = [c.value for c in g[1]]
calif = {r[0]: dict(zip(gh, r)) for r in g.iter_rows(min_row=2, values_only=True) if r[0]}
# La clave de calificación (código -> condición) se entrega ya cruzada en la hoja «Datos» del Anexo G
k = openpyxl.load_workbook(CRUCE, data_only=True)['Datos']
kh = [c.value for c in k[1]]
clave = {}
for r in k.iter_rows(min_row=2, values_only=True):
    if not r[0]:
        continue
    d = dict(zip(kh, r))
    clave[r[0]] = {'ID': d['ID'], 'Condición': d['Condición'], 'Estrato de vigencia': d['Estrato'],
                   'Coincide con banco B': 'Solapada' if str(d['Solapada con B']) == 'Sí' else 'No',
                   'Se abstuvo (automático)': str(str(d['Se abstuvo (auto)']) in ('1', 'True')),
                   'Artículo esperado en el contexto': d['Artículo esperado en el contexto']}
assert set(calif) == set(clave) and len(calif) == 280

banco = {f['ID']: f for f in csv.DictReader(open(BANCO, encoding='utf-8-sig'))}

# --- respuestas (para costo y cita exacta) -------------------------------------------
resp = {}
for carpeta, mapa in [('demo_A', {'A': 'A_demo'}),
                      ('exp2', {'A_hibrida': 'A_hibrida', 'B': 'B', 'B_bm25': 'B_bm25'})]:
    for l in open(RUNS / carpeta / 'respuestas.jsonl', encoding='utf-8'):
        r = json.loads(l)
        if r['condicion'] in mapa:
            resp[(r['id'], mapa[r['condicion']])] = r

def base_art(t):
    alias = {'titulo': 'encabezado', 'enc': 'encabezado', 'cons': 'considerandos', 'anexo': 'anexo1'}
    a, _, rest = t.strip().partition(':')
    rest = rest.split('.')[0].split('#')[0].strip().lower()
    return f"{a.strip()}:{alias.get(rest, rest)}".lower()

PAT = re.compile(r"(Decreto|Acuerdo)\s+(?:Municipal\s+|Distrital\s+)?(?:N[°o.º]\s*)?0*(\d+)\s+de\s+(\d{4})[^\n]*?(?:art(?:ículo|\.)?\s*(\d+[A-Z]?))?", re.I)
PAR = re.compile(r"(Decreto|Acuerdo)\s+(?:Municipal\s+|Distrital\s+)?(?:N[°o.º]\s*)?0*(\d+)\s+de\s+(\d{4})\W{0,4}(?:·\s*)?(?:art(?:ículo|\.)?\s*(\d+[A-Za-z]?))?", re.I)

def citas_primera_linea(texto):
    fu = texto.split('Fuentes:')[-1] if 'Fuentes:' in texto else ''
    lineas = [l for l in fu.splitlines() if l.strip()]
    if not lineas:
        return set()
    out = set()
    for m in PAR.finditer(lineas[0]):
        tipo, n, y, art = m.groups()
        acto = f"A{int(n)}-{y}" if tipo.lower().startswith('acu') else f"D{int(n):04d}-{y}"
        if art:
            out.add(f"{acto}:a{art.lower()}".lower())
    return out

# --- tabla por respuesta ---------------------------------------------------------------
filas = []
for cod, c in calif.items():
    kk = clave[cod]
    cond, qid = kk['Condición'], kk['ID']
    r = resp[(qid, cond)]
    gold = {base_art(x) for x in (banco[qid]['Unidades que la sustentan (id_texto)'] or '').split(';') if x.strip()}
    cit = citas_primera_linea(r['respuesta'])
    cita_ok = None
    if not r['se_abstuvo'] and gold:
        cita_ok = int(bool(cit & gold))
    cita0 = str(c['Cita fuente vigente (1/0/NA)'])
    cita = CORR.get(cod, cita0)
    filas.append(dict(cod=cod, id=qid, cond=cond, estrato=kk['Estrato de vigencia'],
                      solapada=(kk['Coincide con banco B'] == 'Solapada'),
                      sat=int(c['Satisfactoria (1/0)']), cita=cita,
                      err_vig=int(cita == '0'), aluc=int(c['Alucina (1/0)']),
                      aluc_sinA48=0 if cod in A48 else int(c['Alucina (1/0)']),
                      abst_auto=(str(kk['Se abstuvo (automático)']) == 'True'),
                      abst_humana=(cita0 == 'NA'),
                      gold_ctx=float(kk['Artículo esperado en el contexto']) if kk['Artículo esperado en el contexto'] not in (None, '', 'None') else None,
                      cita_exacta=cita_ok,
                      seg=r['seg_recuperacion'] + r['seg_generacion'],
                      tok_in=r['tokens_entrada'], tok_out=r['tokens_salida']))

json.dump(filas, open(SALIDA / 'filas_analisis.json', 'w', encoding='utf-8'), ensure_ascii=False)
por = {(f['id'], f['cond']): f for f in filas}

# --- utilidades ----------------------------------------------------------------------
def mcnemar(ids, var, c1, c2):
    a = [por[(i, c1)][var] for i in ids]; b = [por[(i, c2)][var] for i in ids]
    n10 = sum(x == 1 and y == 0 for x, y in zip(a, b)); n01 = sum(x == 0 and y == 1 for x, y in zip(a, b))
    p = binomtest(min(n10, n01), n10 + n01, 0.5).pvalue if n10 + n01 else 1.0
    return dict(p1=sum(a) / len(a), p2=sum(b) / len(b), n=len(ids), b=n10, c=n01, p=p, k1=sum(a), k2=sum(b))

def boot(ids, var, c1, c2, n=10000):
    rng = np.random.default_rng(SEMILLA)
    a = np.array([por[(i, c1)][var] for i in ids]); b = np.array([por[(i, c2)][var] for i in ids])
    idx = rng.integers(0, len(ids), size=(n, len(ids)))
    d = a[idx].mean(1) - b[idx].mean(1)
    return a.mean() - b.mean(), np.percentile(d, 2.5), np.percentile(d, 97.5)

def holm(ps):
    orden = sorted(range(len(ps)), key=lambda i: ps[i]); m = len(ps); adj = [0] * m; prev = 0
    for r, i in enumerate(orden):
        v = min(1, (m - r) * ps[i]); prev = max(prev, v); adj[i] = prev
    return adj

def wilson(k, n, z=1.96):
    if n == 0: return (float('nan'),) * 2
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); s = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** .5)
    return (c - s) / d, (c + s) / d

ids_all = sorted(banco)
ids_nosol = [i for i in ids_all if banco[i]['Coincide con banco B'] != 'Solapada']
est = {i: banco[i]['Estrato de vigencia'] for i in ids_all}
sub = lambda ids, e: [i for i in ids if est[i] == e]
resp_ids = lambda ids: [i for i in ids if est[i] != 'Sin respuesta']

R = {}
# 1. Principal
for nombre, ids in [('70', ids_all), ('49', ids_nosol)]:
    col = sub(ids, 'Colisión')
    m = mcnemar(col, 'err_vig', 'B', 'A_demo'); m['boot'] = boot(col, 'err_vig', 'B', 'A_demo')
    R[f'principal_{nombre}'] = m
# 2. Secundarias familia 1 (Colisión)
for nombre, ids in [('70', ids_all), ('49', ids_nosol)]:
    col = sub(ids, 'Colisión'); tests = [('B_bm25', 'A_demo'), ('B', 'A_hibrida'), ('B_bm25', 'A_hibrida')]
    res = [mcnemar(col, 'err_vig', a, b) | {'par': f'{a} vs {b}', 'boot': boot(col, 'err_vig', a, b)} for a, b in tests]
    for r_, adj in zip(res, holm([r_['p'] for r_ in res])): r_['p_holm'] = adj
    R[f'sec1_{nombre}'] = res
# 3. Secundarias familia 2 (todas las respondibles)
res = []
for nombre, ids in [('70', ids_all), ('49', ids_nosol)]:
    for a, b in [('B', 'A_demo'), ('B_bm25', 'A_demo'), ('B', 'A_hibrida'), ('B_bm25', 'A_hibrida')]:
        rr = resp_ids(ids); res.append(mcnemar(rr, 'err_vig', a, b) | {'par': f'{a} vs {b}', 'banco': nombre, 'boot': boot(rr, 'err_vig', a, b)})
for r_, adj in zip(res, holm([r_['p'] for r_ in res])): r_['p_holm'] = adj
R['sec2'] = res

# 4. Descriptivas por condición y estrato
desc = {}
for nombre, ids in [('70', ids_all), ('49', ids_nosol)]:
    for e in ['Todas', 'Normal', 'Colisión', 'Sin respuesta', 'SR7']:
        qs = ids if e == 'Todas' else ([i for i in sub(ids, 'Sin respuesta') if i != 'AG-207'] if e == 'SR7' else sub(ids, e))
        for c in CONDS:
            fs = [por[(i, c)] for i in qs]
            n = len(fs)
            d = {}
            for v in ['sat', 'err_vig', 'aluc', 'aluc_sinA48']:
                kx = sum(f[v] for f in fs); d[v] = (kx, n, *wilson(kx, n))
            d['abst_auto'] = sum(f['abst_auto'] for f in fs); d['abst_humana'] = sum(f['abst_humana'] for f in fs)
            g_ = [f['gold_ctx'] for f in fs if f['gold_ctx'] is not None]; d['gold'] = (sum(g_) / len(g_)) if g_ else None
            ce = [f['cita_exacta'] for f in fs if f['cita_exacta'] is not None]; d['cita_exacta'] = (sum(ce), len(ce))
            d['seg_med'] = statistics.median(f['seg'] for f in fs); d['seg_p90'] = float(np.percentile([f['seg'] for f in fs], 90))
            d['tok_in'] = statistics.median(f['tok_in'] for f in fs); d['tok_out'] = statistics.median(f['tok_out'] for f in fs)
            desc[(nombre, e, c)] = d
R['desc'] = {f'{a}|{b}|{c}': v for (a, b, c), v in desc.items()}
# AG-161
R['AG161'] = {c: {k_: por[('AG-161', c)][k_] for k_ in ['sat', 'cita', 'aluc']} for c in CONDS}
json.dump(R, open(SALIDA / 'resultados_analisis.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)

# --- impresión ------------------------------------------------------------------------
def fmt_m(m):
    d, lo, hi = m['boot']
    return (f"{m.get('par','B vs A_demo')}: {m['k1']}/{m['n']} vs {m['k2']}/{m['n']} · discordantes b={m['b']} c={m['c']} · "
            f"p={m['p']:.4f}" + (f" · p_Holm={m['p_holm']:.4f}" if 'p_holm' in m else '') + f" · dif={d:+.3f} [{lo:+.3f}, {hi:+.3f}]")
for nombre in ['70', '49']:
    print(f"\n== PRINCIPAL ({nombre} preguntas; Colisión) ==\n ", fmt_m(R[f'principal_{nombre}']))
    print(f" Secundarias familia 1 (Colisión, Holm):")
    for m in R[f'sec1_{nombre}']: print('  ', fmt_m(m))
print("\n== Secundarias familia 2 (respondibles, Holm sobre 8) ==")
for m in R['sec2']: print('  ', m['banco'], fmt_m(m))
for nombre in ['70', '49']:
    print(f"\n== DESCRIPTIVAS banco D ({nombre}) ==")
    for e in ['Todas', 'Normal', 'Colisión', 'Sin respuesta', 'SR7']:
        print(f" -- {e}")
        for c in CONDS:
            d = desc[(nombre, e, c)]
            f = lambda v: f"{d[v][0]}/{d[v][1]} ({d[v][0]/d[v][1]:.0%}) [{d[v][2]:.2f}-{d[v][3]:.2f}]"
            ce = d['cita_exacta']
            print(f"   {c:9s} sat {f('sat')} · err_vig {f('err_vig')} · aluc {f('aluc')} · aluc_sinA48 {d['aluc_sinA48'][0]} · abst auto {d['abst_auto']} / hum {d['abst_humana']} · gold {d['gold'] if d['gold'] is None else round(d['gold'],3)} · cita_exacta {ce[0]}/{ce[1]} · seg med {d['seg_med']:.2f} p90 {d['seg_p90']:.2f} · tok {d['tok_in']:.0f}/{d['tok_out']:.0f}")
print('\nAG-161', R['AG161'])

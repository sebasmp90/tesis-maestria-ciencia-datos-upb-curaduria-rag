"""Paso 0 de la metodología aplicado al corpus del OE3: inventario de actos.

Es la parte manual de la curaduría: dice qué acto hay en cada archivo, entre
qué líneas, qué papel cumple esa copia (canónica, reproducción, compilación o
acto contiguo fuera de alcance), sus fechas y las derogatorias totales que
declara cada acto en su artículo de vigencia. Todo lo demás (artículos,
modificaciones artículo por artículo, vigencias) lo calcula curar.py.

Fechas: `pub` es la fecha de la Gaceta (desde la que rige). Cuando el archivo
no la trae, se usa la de expedición y queda marcada como estimada.
Las líneas son las de los archivos .md entregados el 26-oct-2026.
"""

# id: (tipo, número, año, expedición, publicación o None, gaceta, título corto, modifica_a por defecto)
ACTOS = {
    "A48-2014":  ("Acuerdo", "48", 2014, "2014-12-17", "2014-12-17", "4267", "Plan de Ordenamiento Territorial de Medellín", None),
    "D0327-1997": ("Decreto", "0327", 1997, "1997-04-16", "1997-07-04", "667", "Ventas estacionarias y elementos de servicios varios", None),
    "D0566-2011": ("Decreto", "0566", 2011, "2011-03-25", None, "", "Incorporación de áreas de cesión pública", None),
    "D0847-2014": ("Decreto", "0847", 2014, "2014-05-30", None, "4235", "Reglamento del Consejo Consultivo de Ordenamiento", None),
    "D0473-2015": ("Decreto", "0473", 2015, "2015-04-06", None, "4243", "Plan parcial Colinas del Porvenir", None),
    "D1152-2015": ("Decreto", "1152", 2015, "2015-07-02", None, "", "Cálculo y cobro de obligaciones urbanísticas en dinero", None),
    "D1626-2015": ("Decreto", "1626", 2015, "2015-10-07", None, "4347", "Correcciones de la cartografía oficial del POT", None),
    "D2053-2015": ("Decreto", "2053", 2015, "2015-12-17", "2015-12-23", "4348", "Macroproyecto MEDRío Río Centro", None),
    "D2077-2015": ("Decreto", "2077", 2015, "2015-12-21", "2015-12-29", "4352", "Macroproyecto MEDRío Río Norte", None),
    "D2078-2015": ("Decreto", "2078", 2015, "2015-12-21", "2015-12-29", "4352", "Macroproyecto MEDRío Río Sur", None),
    "D2148-2015": ("Decreto", "2148", 2015, "2015-12-30", "2016-01-08", "4355", "Aprovechamiento económico del espacio público", None),
    "D1569-2016": ("Decreto", "1569", 2016, "2016-10-06", None, "4406", "Consejo de Direccionamiento Estratégico del POT", None),
    "D0127-2017": ("Decreto", "0127", 2017, "2017-02-15", None, "4431", "Modifica el Decreto 1569 de 2016", "D1569-2016"),
    "D0621-2017": ("Decreto", "0621", 2017, "2017-08-08", None, "4460", "Modifica el Decreto 1569 de 2016", "D1569-2016"),
    "D1091-2017": ("Decreto", "1091", 2017, "2017-12-13", None, "4486", "Indemnizaciones en adquisición de inmuebles", None),
    "D0522-2018": ("Decreto", "0522", 2018, "2018-07-19", "2018-07-23", "4536", "Modifica y adiciona el Decreto 2148 de 2015", "D2148-2015"),
    "D1006-2018": ("Decreto", "1006", 2018, "2018-12-12", None, "4569", "Modifica y adiciona el Decreto 2053 de 2015", "D2053-2015"),
    "D2195-2019": ("Decreto", "2195", 2019, "2019-10-31", "2019-11-13", "4641", "Modifica y adiciona el Decreto 2078 de 2015", "D2078-2015"),
    "D2229-2019": ("Decreto", "2229", 2019, "2019-11-08", "2019-11-13", "4641", "Manual del aprovechamiento económico del espacio público", "D2148-2015"),
    "D2480-2019": ("Decreto", "2480", 2019, "2019-12-26", None, "4657", "Modifica el Decreto 2077 de 2015 (Tricentenario)", "D2077-2015"),
    "D2481-2019": ("Decreto", "2481", 2019, "2019-12-26", None, "4657", "Plan parcial Palermo", None),
    "D2482-2019": ("Decreto", "2482", 2019, "2019-12-26", None, "4657", "Revisa y ajusta la Subzona 2 de Río Centro", "D2053-2015"),
    "D2502-2019": ("Decreto", "2502", 2019, "2019-12-27", None, "", "Áreas de cesión y obligaciones urbanísticas", None),
    "D0242-2021": ("Decreto", "0242", 2021, "2021-07-01", None, "", "Modifica el Decreto 2502 de 2019", "D2502-2019"),
    "D0818-2021": ("Decreto", "0818", 2021, "2021-10-01", None, "4879", "Política de protección a moradores", None),
    "D0265-2022": ("Decreto", "0265", 2022, "2022-04-07", None, "", "Cartografía oficial del POT", None),
    "D1137-2022": ("Decreto", "1137", 2022, "2022-12-16", "2023-02-02", "5086", "Adiciona el Decreto 0818 de 2021", "D0818-2021"),
    "D0838-2023": ("Decreto", "0838", 2023, "2023-10-04", "2023-10-09", "5232", "Adiciona el Decreto 0818 de 2021", "D0818-2021"),
    "D0887-2023": ("Decreto", "0887", 2023, "2023-10-17", None, "5273", "Modifica el plan parcial Colinas del Porvenir", "D0473-2015"),
    "D1098-2023": ("Decreto", "1098", 2023, "2023-12-19", "2023-12-27", "5285", "Revisión del macroproyecto Río Sur", None),
    "D1113-2023": ("Decreto", "1113", 2023, "2023-12-19", "2023-12-27", "5285", "Revisión del macroproyecto Río Norte", None),
    "D1143-2023": ("Decreto", "1143", 2023, "2023-12-21", None, "5292", "Reglamento del Consejo Consultivo de Ordenamiento", None),
    "D1156-2023": ("Decreto", "1156", 2023, "2023-12-22", None, "5292", "Consejo de Direccionamiento Estratégico del POT", None),
    "D1166-2023": ("Decreto", "1166", 2023, "2023-12-26", "2023-12-29", "5289", "Revisión del macroproyecto Río Centro", None),
    "D0787-2024": ("Decreto", "0787", 2024, "2024-09-30", None, "5458", "Modifica el plan parcial Palermo", "D2481-2019"),
    "D0472-2025": ("Decreto", "0472", 2025, "2025-06-06", None, "5604", "Ajusta el Decreto 1098 de 2023 (Río Sur)", "D1098-2023"),
}

# Segmentos por archivo: (línea desde, línea hasta o None = fin del archivo, acto o etiqueta, papel)
# papel: canonica · compilacion (fuente compilada; si es la única fuente, es la canónica) ·
#        reproduccion (otra copia de un acto ya incorporado) · contigua (acto ajeno al POT en la misma Gaceta)
SEGMENTOS = {
    "Acuerdo_048_2014_POT_Medellin_Gaceta_4267.md": [(1, None, "A48-2014", "canonica")],
    "Decreto_0327_de_1997.md": [(1, None, "D0327-1997", "canonica")],
    "Decreto_0566_de_2011.md": [(1, 157, "D0566-2011", "canonica"), (158, None, "Decreto 568 de 2011 (inicio)", "contigua")],
    "DECRETO_0847_DE_2014.md": [(1, None, "D0847-2014", "canonica")],
    "Decreto_0473_de_2015.md": [(1, None, "D0473-2015", "canonica")],
    "Decreto_1152_de_2015.md": [(1, None, "D1152-2015", "canonica")],
    "Decreto_1626_de_2015_Gaceta_4347.md": [(1, None, "D1626-2015", "canonica")],
    "Decreto_2053_de_2015_GACETA_4348_CENTRO.md": [
        (1, 1117, "Gaceta 4348: actos anteriores", "contigua"),
        (1118, 14259, "D2053-2015", "canonica"),
        (14260, None, "Gaceta 4348: actos posteriores", "contigua")],
    "Decreto_2077_de_2015_GACETA_4352_NORTE.md": [
        (1, 61, "Gaceta 4352: portada", "contigua"),
        (62, 8022, "D2077-2015", "canonica"),
        (8023, 15093, "D2078-2015", "canonica"),
        (15094, None, "Gaceta 4352: actos posteriores", "contigua")],
    "Decreto_2078_de_2015_Gaceta_4352_Sur.md": [
        (1, 95, "Gaceta 4352: portada", "contigua"),
        (96, 7326, "D2077-2015", "reproduccion"),
        (7327, 13781, "D2078-2015", "reproduccion"),
        (13782, None, "Gaceta 4352: actos posteriores", "contigua")],
    "Decreto_2148_de_2015_Gaceta_4355.md": [(1, 45, "Gaceta 4355: final de otro decreto", "contigua"), (46, None, "D2148-2015", "canonica")],
    "Decreto_2148_de_2015_compilado.md": [(1, None, "D2148-2015", "reproduccion")],
    "Decreto_1569_de_2016.md": [(1, None, "D1569-2016", "canonica")],
    "Decreto_0127_de_2017.md": [(1, None, "D0127-2017", "canonica")],
    "Decreto_0621_de_2017.md": [(1, None, "D0621-2017", "canonica")],
    "Decreto_Municipal_1091_de_2017.md": [(1, None, "D1091-2017", "canonica")],
    "Decreto_0522_de_2018_Gaceta_4536.md": [(1, None, "D0522-2018", "canonica")],
    "Decreto_1006_de_2018.md": [(1, None, "D1006-2018", "canonica")],
    "Decreto_2195_de_2019.md": [(1, None, "D2195-2019", "compilacion")],
    "Decreto_2229_de_2019_compilado.md": [(1, None, "D2229-2019", "compilacion")],
    "Decreto_2480_de_2019_Reemplaza_la_regulaci_n.md": [(1, None, "D2480-2019", "canonica")],
    "Decreto-2481-de-2019.md": [(1, None, "D2481-2019", "canonica")],
    "Decreto_2482_2019_ajustes_Subzona2.md": [(1, None, "D2482-2019", "canonica")],
    "Decreto_Municipal_2502_de_2019.md": [(1, None, "D2502-2019", "canonica")],
    "Decreto_Municipal_0242_de_2021.md": [(1, None, "D0242-2021", "canonica")],
    "Decreto_Municipal_0818_de_2021___Protección_a_moradores.md": [(1, None, "D0818-2021", "canonica")],
    "Decreto_Municipal_0265_de_2022_Cartografia_oficial_del_POT.md": [(1, None, "D0265-2022", "canonica")],
    "Decreto-1137-de-2022-adicion-al-0818-de-2021.md": [
        (1, 188, "Gaceta 5086: Decreto 1062 de 2022", "contigua"),
        (189, 288, "D1137-2022", "canonica"),
        (289, None, "Gaceta 5086: Decreto 32 de 2023 y otros", "contigua")],
    "Decreto-0838-de-2023-adicion-al-0818-de-2021.md": [
        (1, 146, "Gaceta 5232: actos anteriores", "contigua"),
        (147, 270, "D0838-2023", "canonica"),
        (271, None, "Gaceta 5232: Resolución 202350081150", "contigua")],
    "Decreto_887_del_17_de_octubre_de_2023.md": [(1, None, "D0887-2023", "canonica")],
    "Decreto_1098_de_2023_Gaceta_Oficial_5285.md": [
        (1, 38, "Gaceta 5285: portada", "contigua"),
        (39, 8222, "D1098-2023", "canonica"),
        (8223, None, "D1113-2023", "reproduccion")],
    "Decreto_Distrital_1113_de_2023.md": [
        (1, 30, "Gaceta 5285: portada", "contigua"),
        (31, 8001, "D1098-2023", "reproduccion"),
        (8002, None, "D1113-2023", "canonica")],
    "Decreto_Distrital_1143_de_2023___Consejo_Consultivo_de_Ordenamiento.md": [(1, None, "D1143-2023", "canonica")],
    "Decreto_Distrital_1156_de_2023.md": [(1, None, "D1156-2023", "canonica")],
    "Decreto_Distrital_1166_de_2023_Gaceta-5289-Rio-Centro-29-Dic-1.md": [
        (1, 26, "Gaceta 5289: portada", "contigua"),
        (27, 8683, "D1166-2023", "canonica"),
        (8684, None, "Gaceta 5289: Decreto 1167 de 2023", "contigua")],
    "Decreto_Distrital_0787_de_2024.md": [(1, None, "D0787-2024", "canonica")],
    "Decreto_Distrital_0472_de_2025.md": [(1, None, "D0472-2025", "canonica")],
}

# Derogatorias totales declaradas en el artículo de vigencia de cada acto
# (acto que deroga, su artículo, actos derogados). Las genéricas («las que le sean
# contrarias») no se usan para derogar nada.
DEROGACIONES_TOTALES = [
    ("D1143-2023", "15", ["D0847-2014"]),
    ("D1156-2023", "13", ["D1569-2016", "D0127-2017", "D0621-2017"]),
    ("D0818-2021", "58", ["D1091-2017"]),
    ("D2502-2019", "73", ["D0566-2011", "D1152-2015"]),
    ("D0265-2022", "65", ["D1626-2015"]),
    ("D1113-2023", "254", ["D2077-2015", "D2480-2019"]),
    ("D1166-2023", "349", ["D2053-2015", "D1006-2018", "D2482-2019"]),
    ("D1098-2023", "277", ["D2078-2015", "D2195-2019"]),
    ("D2229-2019", "19", ["D0327-1997"]),
]

# Derogatorias parciales que el acto declara en su artículo de vigencia
# (acto que deroga, su artículo, acto afectado, artículos derogados)
DEROGACIONES_PARCIALES = [
    ("D0522-2018", "31", "D2148-2015", ["3", "10"]),
    ("D2229-2019", "19", "D2148-2015", ["20", "21"]),
    ("D1006-2018", "52bis", "D2053-2015", ["114", "124", "153", "163", "172"]),   # el segundo «Artículo 52» es el de vigencia
    ("D2195-2019", "49", "D2078-2015", ["108", "118", "128", "150", "160", "171", "181", "191", "201", "211", "221", "231"]),
    ("D2482-2019", "88", "D2053-2015", ["190", "195", "212", "225", "229", "230", "231", "238", "241", "255",
                                         "256", "257", "269", "271", "273", "280", "282", "284", "291", "293", "295"]),
]

# Derogatorias de subunidades (parágrafo, numeral) declaradas en el artículo de vigencia:
# (acto que deroga, su artículo, acto afectado, artículo afectado, alcance)
DEROGACIONES_SUBUNIDAD = [
    ("D0242-2021", "17", "D2502-2019", "11", "numerales 5 y 6"),
    ("D2229-2019", "19", "D2148-2015", "27", "numeral 8"),
]

# Segundo detector de vigencia (paso 4): compilaciones con notas de vigencia y su fecha de corte.
COMPILACIONES = {
    "D2148-2015": ("Decreto_2148_de_2015_compilado.md", "2019-06-15"),
}

# Correcciones de numeración que la regla secuencial no puede resolver sola (paso 1).
# acto: {número de línea del encabezado en el archivo: número correcto o None para rechazarlo}
CORRECCIONES_ENCABEZADO = {
    "D0787-2024": {67: 1},       # el artículo 1 (Objeto) sale numerado «7» en el archivo
    "D2148-2015": {1637: 32},    # «de ARTÍCULO 32°.»: la conversión pegó una palabra antes del encabezado
    "D0327-1997": {360: 8, 518: 15},   # OCR: «ARTÍCULO 80.» es el 8 y «ARTICULO 150.» es el 15
    "A48-2014": {1371: 64},      # la conversión rotula «Artículo 60» el artículo 64
    "D0265-2022": {983: 64},     # «Artículo. 64.» con punto después de la palabra
}

# Avisos que la curaduría no pudo resolver y que deben viajar en la firma de todas las unidades del acto.
AVISOS_ACTO = {
    "D0473-2015": ("segmentación no confiable: el archivo es OCR con dos columnas mezcladas; "
                   "los artículos 16 y 20 fueron modificados por el Decreto 887 de 2023"),
}

# Actos cuya conversión perdió los números de artículo («###### **. TÍTULO.**»).
# Anclas: (posición del encabezado en el orden del archivo, número real según el Decreto 2480 de 2019)
SIN_NUMERO = {
    "D2077-2015": [(1, 1), (37, 37), (56, 58), (92, 94), (189, 192)],
}

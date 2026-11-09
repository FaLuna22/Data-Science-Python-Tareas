"""Respuestas esperadas de la evaluación, calculadas de forma INDEPENDIENTE al agente.

    uv run evaluacion/verdades.py

- BCRP: se piden directamente a la API pública (https://estadisticas.bcrp.gob.pe/estadisticas/series/api), sin pasar
  por el servidor MCP del proyecto.
- ENAHO: las cifras publicadas por el INEI (27.6 %, 39.3 %, 5.5 %, Cajamarca 45.0 % de la referencia de la sesión 16)
  y, para las preguntas combinadas, un cálculo propio con la SUMARIA a nivel de HOGAR (factor07 × mieperho), es decir
  por un camino distinto al de la skill limpiando-enaho (personas con facpob07).
Las verdades se fijaron ANTES de correr el experimento y no se modificaron después.
"""
import json
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"


def bcrp(codigo, periodo):
    j = httpx.get(f"{API}/{codigo}/json/{periodo}/{periodo}", timeout=60).json()
    return float(j["periods"][0]["values"][0])


s = pd.read_stata(RAIZ / "datos/966-Modulo34/sumaria-2024.dta", convert_categoricals=False)
w = s.factor07 * s.mieperho
alim = s[[c for c in s.columns if c.startswith(("gru11", "gru12", "gru13", "gru14"))]].fillna(0).sum(axis=1)
peso = alim / s.gashog2d * 100
ext = s.pobreza == 1
pobre = s.pobreza <= 2
peso_ext = float(np.average(peso[ext], weights=w[ext]))
gasto_pc_pobres = float(np.average((s.gashog2d / s.mieperho / 12)[pobre], weights=w[pobre]))

v = {
    "ipc_dic24": bcrp("PN01273PM", "2024-12"),
    "alim_dic22": bcrp("PN09822PM", "2022-12"),
    "referencia_dic24": bcrp("PD04722MM", "2024-12"),
    "pbi_2024": bcrp("PM04923AA", "2024"),
    "tc_2024": bcrp("PM05242PA", "2024"),
    "pobreza_nac_hogar": float(np.average(pobre, weights=w) * 100),
    "pobreza_ext_hogar": float(np.average(ext, weights=w) * 100),
    "pobreza_rural_hogar": float(np.average(pobre[s.estrato >= 6], weights=w[s.estrato >= 6]) * 100),
    "pobreza_cajamarca_hogar": float(np.average(pobre[s.ubigeo.str[:2] == "06"], weights=w[s.ubigeo.str[:2] == "06"]) * 100),
    "peso_alimentos_pobres_extremos": peso_ext,
    "gasto_pc_pobres_soles": gasto_pc_pobres,
}
v["combinada_exposicion"] = v["alim_dic22"] * peso_ext / 100
v["combinada_gasto_usd"] = gasto_pc_pobres / v["tc_2024"]
print(json.dumps({k: round(x, 4) for k, x in v.items()}, indent=2))
(RAIZ / "evaluacion" / "verdades.json").write_text(json.dumps({k: round(x, 6) for k, x in v.items()}, indent=2))

"""Calcula los indicadores de brecha digital 2015-2025 y exporta los datos del dashboard.

Cada indicador es una proporción ponderada con su error estándar linealizado por conglomerado
(conglome), que es la unidad primaria de muestreo de la ENAHO. Se ignora la estratificación, lo que
hace los intervalos algo más anchos (conservadores).

Salidas:
  datos/procesados/indicadores.csv    tabla larga con valor, IC 95 % y tamaño de muestra
  datos/procesados/validacion.txt      comparación con cifras oficiales del INEI
  web/data/indicadores.json            datos compactos para el dashboard
"""
from __future__ import annotations

import json
from pathlib import Path

import sys

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
PROC = RAIZ / "datos" / "procesados"
WEB = RAIZ / "web" / "data"

IND_PERSONA = {
    "usa_internet": "Personas de 6+ años que usaron internet el mes anterior",
    "usa_diario": "Personas de 6+ años que usan internet a diario",
    "usa_celular": "Personas de 6+ años que usaron internet desde el celular",
    "usa_computadora": "Personas de 6+ años que usaron internet desde una computadora o laptop",
}
IND_HOGAR = {
    "celular": "Hogares con al menos un celular",
    "internet": "Hogares con conexión a internet (fija o móvil desde 2023)",
    "internet_fijo": "Hogares con internet fijo",
    "internet_solo_movil": "Hogares que solo tienen internet móvil",
    "tel_fijo": "Hogares con teléfono fijo",
    "sin_tic": "Hogares sin teléfono, celular, cable ni internet",
}
DIM_PERSONA = ["nacional", "departamento", "sexo", "grupo_edad", "lengua", "quintil", "pobreza"]
DIM_HOGAR = ["nacional", "departamento", "quintil", "pobreza"]
N_MIN = 30  # celdas con menos observaciones no se publican


def apilar(df: pd.DataFrame) -> pd.DataFrame:
    """Duplica los registros para tener ámbito (Total/Urbano/Rural) y geo (Perú/departamento)."""
    amb = pd.concat([df.assign(ambito="Total"), df.assign(ambito=df.area)], ignore_index=True)
    return amb


def proporciones(df: pd.DataFrame, por: list[str], y: str, w: str) -> pd.DataFrame:
    d = df[por + ["conglome", y, w]].dropna(subset=[y])
    if d.empty:
        return pd.DataFrame()
    d = d.assign(_wy=d[w] * d[y])
    g = d.groupby(por, observed=True)
    res = g.agg(W=(w, "sum"), WY=("_wy", "sum"), n=(y, "size")).reset_index()
    res["p"] = res.WY / res.W
    d = d.merge(res[por + ["p", "W"]], on=por)
    d["_z"] = d[w] * (d[y] - d.p) / d.W
    c = d.groupby(por + ["conglome"], observed=True)._z.sum().reset_index()
    c["_z2"] = c._z ** 2
    v = c.groupby(por, observed=True).agg(nc=("_z", "size"), s2=("_z2", "sum")).reset_index()
    res = res.merge(v, on=por)
    res["se"] = np.sqrt(np.where(res.nc > 1, res.nc / (res.nc - 1) * res.s2, np.nan))
    res["indicador"] = y
    res["poblacion"] = res.W
    return res[por + ["indicador", "p", "se", "n", "poblacion"]]


def calcular(df: pd.DataFrame, indicadores: dict, dims: list[str], w: str, unidad: str) -> pd.DataFrame:
    base = apilar(df)
    salidas = []
    for dim in dims:
        if dim == "nacional":
            b = base.assign(geo="Perú", grupo="Total")
        elif dim == "departamento":
            b = base.assign(geo=base.departamento, grupo="Total")
        else:
            # desagregaciones sociales: nacional y por departamento
            b = pd.concat([base.assign(geo="Perú"), base.assign(geo=base.departamento)],
                          ignore_index=True).assign(grupo=lambda x: x[dim])
        b = b[b.grupo != "Otra"]
        for y in indicadores:
            r = proporciones(b, ["anio", "ambito", "geo", "grupo"], y, w)
            if not r.empty:
                salidas.append(r.assign(dimension="nacional" if dim == "departamento" else dim))
    out = pd.concat(salidas, ignore_index=True)
    out["unidad"] = unidad
    return out


def validar(tabla: pd.DataFrame, hog: pd.DataFrame) -> str:
    def val(ind, anio, geo="Perú", amb="Total", dim="nacional", grupo="Total"):
        f = tabla[(tabla.indicador == ind) & (tabla.anio == anio) & (tabla.geo == geo)
                  & (tabla.ambito == amb) & (tabla.dimension == dim) & (tabla.grupo == grupo)]
        return 100 * f.p.iloc[0]

    pob = {a: 100 * (g.factor07 * g.mieperho * (g.pobre == "Pobre")).sum() / (g.factor07 * g.mieperho).sum()
           for a, g in hog.groupby("anio")}
    filas = [
        ("Pobreza monetaria 2024 (sumaria, personas)", pob[2024], 27.6, "INEI, Informe técnico de pobreza 2016-2025"),
        ("Pobreza monetaria 2025 (sumaria, personas)", pob[2025], 25.7, "INEI, Informe técnico de pobreza 2016-2025"),
        ("Hogares con internet 2015", val("internet", 2015), 23.2, "INEI, Perú: Indicadores de TIC en los hogares 2015"),
        ("Personas 6+ que usan internet 2024", val("usa_internet", 2024), 80.2, "INEI, informe TIC III trim. 2024 (trimestral)"),
        ("Personas 6+ que usan internet 2025", val("usa_internet", 2025), 82.0, "INEI, informe TIC IV trim. 2025 (trimestral)"),
    ]
    lineas = ["Validación contra cifras oficiales (valores en %)", ""]
    for nombre, mio, ofi, fuente in filas:
        lineas.append(f"{nombre:<46} propio {mio:6.2f} | oficial {ofi:5.1f} | dif {mio - ofi:+5.2f}  ({fuente})")
    lineas.append("")
    lineas.append("Las cifras oficiales de uso de internet son trimestrales; la estimación propia es anual.")
    return "\n".join(lineas)


def exportar_web(tabla: pd.DataFrame) -> None:
    """nacional.json: Perú (todas las desagregaciones) + total de cada departamento (para el mapa).
    departamentos/<cod>.json: desagregaciones sociales de cada departamento (se cargan al elegirlo)."""
    (WEB / "departamentos").mkdir(parents=True, exist_ok=True)
    t = tabla[tabla.n >= N_MIN].copy()
    t["v"] = (100 * t.p).round(1)
    t["e"] = (100 * 1.96 * t.se).round(1)
    t["n"] = t.n.astype(int)
    cols = ["anio", "ambito", "geo", "dimension", "grupo", "indicador", "v", "e", "n"]
    t = t[cols].sort_values(cols[:6])

    def guardar(df: pd.DataFrame, ruta: Path, extra: dict | None = None) -> None:
        cuerpo = {"columnas": cols, "filas": df.to_numpy().tolist(), **(extra or {})}
        ruta.write_text(json.dumps(cuerpo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    meta = {
        "indicadores": {**{k: {"nombre": v, "unidad": "personas"} for k, v in IND_PERSONA.items()},
                        **{k: {"nombre": v, "unidad": "hogares"} for k, v in IND_HOGAR.items()}},
        "nota": "v = porcentaje; e = margen de error al 95 % (pp); n = observaciones en la muestra",
    }
    nacional = t[(t.geo == "Perú") | (t.dimension == "nacional")]
    guardar(nacional, WEB / "nacional.json", {"meta": meta})
    cod = {v: k for k, v in __import__("procesar_datos").DEPARTAMENTOS.items()}
    for geo, df in t[(t.geo != "Perú") & (t.dimension != "nacional")].groupby("geo"):
        guardar(df, WEB / "departamentos" / f"{cod[geo]}.json")
    print(f"web/data/nacional.json: {len(nacional):,} filas, {(WEB / 'nacional.json').stat().st_size / 1e3:.0f} KB")

    # GeoJSON simplificado: solo código y nombre, coordenadas a 4 decimales
    g = json.loads((RAIZ / "datos" / "originales" / "peru_departamental_simple.geojson").read_text(encoding="utf-8"))

    def redondear(c):
        return [redondear(x) for x in c] if isinstance(c[0], list) else [round(c[0], 4), round(c[1], 4)]

    for f in g["features"]:
        f["properties"] = {"cod": f["properties"]["FIRST_IDDP"],
                           "nombre": __import__("procesar_datos").DEPARTAMENTOS[f["properties"]["FIRST_IDDP"]]}
        f["geometry"]["coordinates"] = redondear(f["geometry"]["coordinates"])
    (WEB / "peru_departamentos.geojson").write_text(json.dumps(g, separators=(",", ":")), encoding="utf-8")
    (WEB / "indicadores.json").unlink(missing_ok=True)


def main() -> None:
    hog = pd.read_parquet(PROC / "hogares.parquet")
    per = pd.read_parquet(PROC / "personas.parquet")
    tp = calcular(per, IND_PERSONA, DIM_PERSONA, "factora07", "personas")
    th = calcular(hog, IND_HOGAR, DIM_HOGAR, "factor07", "hogares")
    tabla = pd.concat([tp, th], ignore_index=True)
    tabla["ic_inf"] = tabla.p - 1.96 * tabla.se
    tabla["ic_sup"] = tabla.p + 1.96 * tabla.se
    tabla.to_csv(PROC / "indicadores.csv", index=False, float_format="%.5f")
    print(f"indicadores.csv: {len(tabla):,} filas")
    texto = validar(tabla, hog)
    (PROC / "validacion.txt").write_text(texto, encoding="utf-8")
    print(texto)
    exportar_web(tabla)


if __name__ == "__main__":
    main()

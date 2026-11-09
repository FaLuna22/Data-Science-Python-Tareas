"""Mapa coroplético de la pobreza monetaria por departamento (ENAHO 2024), unido por código y no por nombre.

    uv run .claude/skills/mapeando-enaho/scripts/mapear.py                       # pobreza monetaria
    uv run .claude/skills/mapeando-enaho/scripts/mapear.py --indicador alimentos # % del gasto en alimentos

Reglas: unión ubigeo[:2] (texto, con cero) = FIRST_IDDP; exige 25 departamentos y ninguno sin dato; Lima (15) y
Callao (07) separados; escala secuencial de claro a oscuro que empieza en 0; leyenda con la unidad; compara con
referencias/pobreza_departamento_2024.csv (sesión 16) y guarda el PNG en mapas/ y la tabla en salidas/.
"""
import argparse
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
URL_GEO = ("https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/"
           "peru_departamental_simple.geojson")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indicador", choices=["pobreza", "alimentos"], default="pobreza")
    ap.add_argument("--raiz", default=".")
    a = ap.parse_args()
    raiz = Path(a.raiz).resolve()
    ruta = raiz / "salidas" / "personas_2024.parquet"
    if not ruta.exists():
        sys.exit("ERROR: no existe salidas/personas_2024.parquet. Corran primero la skill limpiando-enaho.")
    base = pd.read_parquet(ruta)

    col = "pobre" if a.indicador == "pobreza" else "peso_alimentos"
    escala = 100 if a.indicador == "pobreza" else 1
    m = base[col].notna()
    t = (base[m].groupby("departamento")
         .apply(lambda g: np.average(g[col].astype(float), weights=g.facpob07) * escala, include_groups=False)
         .rename("valor").reset_index())

    geo_local = raiz / "datos" / "peru_departamental_simple.geojson"
    geo = gpd.read_file(geo_local if geo_local.exists() else URL_GEO)
    geo["FIRST_IDDP"] = geo.FIRST_IDDP.astype(str).str.zfill(2)
    mapa = geo.merge(t, left_on="FIRST_IDDP", right_on="departamento", how="left", validate="1:1")

    errores = []
    if len(mapa) != 25:
        errores.append(f"el GeoJSON tiene {len(mapa)} polígonos, no 25")
    if mapa.valor.isna().any():
        errores.append("departamentos sin dato: " + ", ".join(mapa.loc[mapa.valor.isna(), "FIRST_IDDP"]))
    if not {"07", "15"} <= set(mapa.FIRST_IDDP[mapa.valor.notna()]):
        errores.append("Lima (15) o Callao (07) no están separados")
    if errores:
        sys.exit("ERROR en la unión territorial: " + "; ".join(errores))

    nombre_col = "NOMBDEP" if "NOMBDEP" in mapa.columns else mapa.columns[0]
    titulo, unidad, archivo = (
        ("Pobreza monetaria por departamento, Perú 2024", "% de personas en pobreza monetaria",
         "pobreza_departamento.png") if a.indicador == "pobreza" else
        ("Peso del gasto en alimentos por departamento, Perú 2024",
         "% del gasto total del hogar destinado a alimentos", "peso_alimentos_departamento.png"))

    fig, ax = plt.subplots(figsize=(7, 9))
    mapa.plot(column="valor", cmap="Reds", vmin=0, vmax=float(np.ceil(mapa.valor.max() / 5) * 5), ax=ax,
              edgecolor="white", linewidth=0.5, legend=True,
              legend_kwds={"label": unidad, "shrink": 0.6, "orientation": "horizontal", "pad": 0.02})
    for _, f in mapa.iterrows():
        p = f.geometry.representative_point()
        ax.annotate(f"{f.valor:.0f}", (p.x, p.y), ha="center", fontsize=6.5,
                    color="white" if f.valor > mapa.valor.max() * 0.6 else "black")
    ax.set_title(titulo, loc="left", fontsize=12)
    ax.set_axis_off()
    fig.text(0.02, 0.02, "Fuente: INEI, ENAHO 2024; límites: repositorio del curso (FIRST_IDDP).\n"
             "Ponderado con facpob07. Lima (15) y Callao (07) por separado.", fontsize=7, color="#555")
    (raiz / "mapas").mkdir(exist_ok=True)
    fig.savefig(raiz / "mapas" / archivo, dpi=200, bbox_inches="tight")
    plt.close(fig)

    tabla = mapa[["FIRST_IDDP", nombre_col, "valor"]].rename(columns={"FIRST_IDDP": "ccdd", nombre_col: "nombre"})
    tabla = tabla.sort_values("ccdd")
    if a.indicador == "pobreza":
        ref = pd.read_csv(AQUI.parent / "referencias" / "pobreza_departamento_2024.csv", dtype={"ccdd": str})
        tabla = tabla.merge(ref[["ccdd", "pobreza_pct"]].rename(columns={"pobreza_pct": "referencia_s16"}),
                            on="ccdd", how="left")
        tabla["diferencia"] = (tabla.valor.round(1) - tabla.referencia_s16).round(1)
    tabla.drop(columns=[]).to_csv(raiz / "salidas" / f"mapa_{a.indicador}_departamento.csv", index=False)
    print(tabla.round(2).to_string(index=False))
    print(f"\n25/25 departamentos con dato (unión ubigeo[:2] = FIRST_IDDP). -> mapas/{archivo}")
    if a.indicador == "pobreza":
        print(f"Máxima diferencia contra la referencia de la sesión 16: {tabla.diferencia.abs().max():.1f} pts")


if __name__ == "__main__":
    main()

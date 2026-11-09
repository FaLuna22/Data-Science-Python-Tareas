"""Gráficos ponderados de la ENAHO 2024 a partir de salidas/personas_2024.parquet.

    uv run .claude/skills/graficando-enaho/scripts/graficar.py area            # pobreza urbana vs rural
    uv run .claude/skills/graficando-enaho/scripts/graficar.py sexo            # pobreza por sexo
    uv run .claude/skills/graficando-enaho/scripts/graficar.py edad            # pobreza por grupo de edad
    uv run .claude/skills/graficando-enaho/scripts/graficar.py departamento    # 25 departamentos, ordenados
    uv run .claude/skills/graficando-enaho/scripts/graficar.py alimentos       # % del gasto en alimentos por condición
    uv run .claude/skills/graficando-enaho/scripts/graficar.py todos

Reglas: todo ponderado con facpob07, barras desde cero y ordenadas, un solo color (el resaltado solo marca el promedio
nacional), valor escrito en cada barra, título con qué y cuándo, nota con la fuente, PNG a 200 dpi en figuras/.
Imprime la tabla con las cifras de cada barra para que el agente las cite sin calcular a mano.
"""
import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

AZUL, GRIS, ROJO = "#1f4e79", "#9aa5b1", "#c0392b"
FUENTE = "Fuente: INEI, ENAHO 2024 (módulos 34 y 02). Residentes habituales, ponderado con facpob07."


def ponderar(base, col, valor="pobre"):
    def f(g):
        x = g[valor].astype(float)
        m = x.notna()
        return pd.Series({"valor": np.average(x[m], weights=g.facpob07[m]) * (100 if valor == "pobre" else 1),
                          "poblacion": g.facpob07.sum(), "n": len(g)})
    return base.groupby(col).apply(f, include_groups=False).reset_index()


def barras(t, etiqueta, titulo, archivo, xlabel="% de personas en pobreza monetaria", horizontal=False,
           referencia=None, figuras=Path("figuras")):
    fig, ax = plt.subplots(figsize=(8, 7.5 if horizontal else 4.6))
    if horizontal:
        t = t.sort_values("valor")
        colores = [AZUL] * len(t)
        ax.barh(t[etiqueta], t.valor, color=colores)
        for i, v in enumerate(t.valor):
            ax.text(v + 0.4, i, f"{v:.1f}", va="center", fontsize=8)
        ax.set_xlabel(xlabel)
        ax.set_xlim(0, t.valor.max() * 1.12)
        if referencia is not None:
            ax.axvline(referencia, color=ROJO, ls="--", lw=1)
            ax.text(referencia + 0.3, -0.9, f"Perú {referencia:.1f} %", color=ROJO, fontsize=8)
    else:
        ax.bar(t[etiqueta], t.valor, color=AZUL, width=0.6)
        for i, v in enumerate(t.valor):
            ax.text(i, v + 0.5, f"{v:.1f} %", ha="center", fontsize=10)
        ax.set_ylabel(xlabel)
        ax.set_ylim(0, t.valor.max() * 1.18)
        if referencia is not None:
            ax.axhline(referencia, color=ROJO, ls="--", lw=1)
            ax.text(len(t) - 0.5, referencia + 0.5, f"Perú {referencia:.1f} %", color=ROJO, fontsize=8, ha="right")
    ax.set_title(titulo, loc="left", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.01, 0.005, FUENTE, fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    figuras.mkdir(exist_ok=True)
    fig.savefig(figuras / archivo, dpi=200)
    plt.close(fig)
    print(f"\n{titulo}\n{t[[etiqueta, 'valor', 'poblacion', 'n']].round(2).to_string(index=False)}\n-> figuras/{archivo}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("grafico", choices=["area", "sexo", "edad", "departamento", "alimentos", "todos"])
    ap.add_argument("--raiz", default=".")
    a = ap.parse_args()
    raiz = Path(a.raiz).resolve()
    ruta = raiz / "salidas" / "personas_2024.parquet"
    if not ruta.exists():
        sys.exit("ERROR: no existe salidas/personas_2024.parquet. Corran primero la skill limpiando-enaho.")
    base = pd.read_parquet(ruta)
    figuras = raiz / "figuras"
    nac = np.average(base.pobre, weights=base.facpob07) * 100
    pedidos = ["area", "sexo", "edad", "departamento", "alimentos"] if a.grafico == "todos" else [a.grafico]

    for g in pedidos:
        if g == "area":
            t = ponderar(base, "area").sort_values("valor", ascending=False)
            barras(t, "area", f"La pobreza rural supera a la urbana en {t.valor.iloc[0] - t.valor.iloc[1]:.1f} "
                   "puntos\nPobreza monetaria por área de residencia, Perú 2024", "pobreza_area.png",
                   referencia=nac, figuras=figuras)
        elif g == "sexo":
            t = ponderar(base, "sexo").sort_values("valor", ascending=False)
            barras(t, "sexo", f"Mujeres y hombres tienen tasas de pobreza similares (brecha "
                   f"{t.valor.iloc[0] - t.valor.iloc[1]:.1f} pts)\nPobreza monetaria por sexo, Perú 2024",
                   "pobreza_sexo.png", referencia=nac, figuras=figuras)
        elif g == "edad":
            t = ponderar(base, "grupo_edad")
            barras(t, "grupo_edad", "Niñas, niños y adolescentes son el grupo más pobre\n"
                   "Pobreza monetaria por grupo de edad (años), Perú 2024", "pobreza_edad.png", referencia=nac,
                   figuras=figuras)
        elif g == "departamento":
            t = ponderar(base, "departamento_nombre")
            t["departamento_nombre"] = t.departamento_nombre.str[3:]
            mx, mn = t.loc[t.valor.idxmax()], t.loc[t.valor.idxmin()]
            barras(t, "departamento_nombre", f"La pobreza va de {mn.valor:.1f} % en {mn.departamento_nombre} a "
                   f"{mx.valor:.1f} % en {mx.departamento_nombre}\nPobreza monetaria por departamento, Perú 2024",
                   "pobreza_departamento.png", horizontal=True, referencia=nac, figuras=figuras)
        elif g == "alimentos":
            t = ponderar(base, "condicion", valor="peso_alimentos")
            orden = {"Pobre extremo": 0, "Pobre no extremo": 1, "No pobre": 2}
            t = t.sort_values("condicion", key=lambda s: s.map(orden))
            barras(t, "condicion", "Los hogares pobres destinan a alimentos una mayor parte de su gasto\n"
                   "Gasto en alimentos como % del gasto total del hogar, por condición de pobreza, Perú 2024",
                   "peso_alimentos_condicion.png", xlabel="% del gasto total del hogar (promedio por persona)",
                   referencia=np.average(base.peso_alimentos.dropna(),
                                         weights=base.facpob07[base.peso_alimentos.notna()]),
                   figuras=figuras)


if __name__ == "__main__":
    main()

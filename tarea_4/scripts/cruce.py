"""Cruce BCRP × ENAHO: cuánto del gasto total habría encarecido la inflación de alimentos según el peso de los
alimentos en el gasto de cada grupo. Usa el servidor MCP (funciones de mcp/server.py) y las salidas de las skills.

    uv run scripts/cruce.py        # escribe salidas/cruce_exposicion.csv y salidas/cruce_departamentos.txt

Exposición (pts del gasto total) = inflación de alimentos a 12 meses (BCRP, PN09822PM) × peso de alimentos (%) / 100.
Es una aproximación de primer orden: supone que la inflación de Lima aplica a todos los grupos y que la canasta no cambia.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "mcp"))
from server import resumen  # noqa: E402

fn = getattr(resumen, "fn", resumen)
r = fn("PN09822PM", "2022-01", "2024-12")
pico, dic22, dic24 = r["maximo"], fn("PN09822PM", "2022-12", "2022-12")["ultimo"], r["ultimo"]
ind = pd.read_csv(RAIZ / "salidas" / "indicadores.csv")
sel = ind[ind.grupo.isin(["nacional", "area", "condicion"])][["grupo", "categoria", "peso_alimentos_pct",
                                                              "pobreza_pct", "poblacion_expandida"]].copy()
for etiqueta, x in [("pico", pico), ("dic2022", dic22), ("dic2024", dic24)]:
    sel[f"exposicion_{etiqueta}_pts"] = (sel.peso_alimentos_pct * x["valor"] / 100).round(2)
sel.to_csv(RAIZ / "salidas" / "cruce_exposicion.csv", index=False)
print(f"Inflación de alimentos (PN09822PM): pico {pico['valor']:.2f} % ({pico['periodo']}), "
      f"dic-2022 {dic22['valor']:.2f} %, dic-2024 {dic24['valor']:.2f} %. Fuente: {r['fuente']}")
print(sel.to_string(index=False))

dep = ind[ind.grupo == "departamento"]
rho = np.corrcoef(dep.pobreza_pct, dep.peso_alimentos_pct)[0, 1]
txt = (f"Correlación (Pearson, 25 departamentos) entre pobreza monetaria y peso del gasto en alimentos: r = {rho:.3f}\n"
       f"Asociación descriptiva entre unidades territoriales, no causal. Fuente: salidas/indicadores.csv")
(RAIZ / "salidas" / "cruce_departamentos.txt").write_text(txt + "\n", encoding="utf-8")
print("\n" + txt)

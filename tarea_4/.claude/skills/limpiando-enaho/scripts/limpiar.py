"""Limpia la ENAHO 2024 (módulos 34 y 02 del INEI) y arma una base de personas con pobreza y factor de expansión.

    uv run .claude/skills/limpiando-enaho/scripts/limpiar.py            # desde la raíz de tarea_4
    uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024 --raiz .

Pipeline fijo (no se discute, por eso es un script):
  1. Leer los .dta con convert_categoricals=False y las llaves como texto (se conservan los ceros a la izquierda).
  2. Normalizar los nombres de columna a minúscula sin tildes (la columna del año llega como «aÑo»).
  3. Filtrar residentes habituales: ((p204 == 1) & (p205 == 2)) | ((p204 == 2) & (p206 == 1)).
  4. Unir personas (m) con hogares (1) por conglome, vivienda y hogar con merge(validate="m:1").
  5. Construir departamento = ubigeo[:2], urbano = estrato <= 5, pobre = pobreza <= 2, pobre_extremo = pobreza == 1,
     y el peso del gasto en alimentos del hogar (grupo 1 de la sumaria / gasto total bruto).
  6. Validar: llaves únicas, la unión no pierde ni duplica filas, 108,664 residentes, 25 departamentos y pobreza
     nacional ponderada a menos de 0.1 puntos del 27.6 % oficial. Si una validación esencial falla, sale con error.
  7. Guardar salidas/personas_2024.parquet, salidas/indicadores.csv y salidas/validacion.txt.

Toda cifra de personas se pondera con facpob07. Nada se ajusta a mano para que coincida con la referencia.
"""
import argparse
import sys
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

LLAVES = ["conglome", "vivienda", "hogar"]
CODIGO_INEI = {2024: 966}
REFERENCIA = {"pobreza_nacional": 27.6, "tolerancia": 0.1, "residentes": 108_664, "departamentos": 25,
              "urbano": 24.8, "rural": 39.3}
NOMBRES_DEP = {"01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa", "05": "Ayacucho",
               "06": "Cajamarca", "07": "Callao", "08": "Cusco", "09": "Huancavelica", "10": "Huánuco",
               "11": "Ica", "12": "Junín", "13": "La Libertad", "14": "Lambayeque", "15": "Lima",
               "16": "Loreto", "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
               "21": "Puno", "22": "San Martín", "23": "Tacna", "24": "Tumbes", "25": "Ucayali"}


def normalizar(cols):
    return [unicodedata.normalize("NFD", c).encode("ascii", "ignore").decode().lower().strip() for c in cols]


def buscar_dta(datos, codigo, modulo, patron):
    """Encuentra el .dta del módulo: carpeta ya descomprimida o el zip del INEI (lo descomprime)."""
    carpeta = datos / f"{codigo}-Modulo{modulo}"
    zipf = datos / f"{codigo}-Modulo{modulo}.zip"
    if not carpeta.exists() and zipf.exists():
        with zipfile.ZipFile(zipf) as z:
            z.extractall(datos)
    candidatos = sorted(carpeta.glob(patron)) if carpeta.exists() else []
    if not candidatos:
        sys.exit(f"ERROR: falta el módulo {modulo}. Bájenlo de https://proyectos.inei.gob.pe/iinei/srienaho/"
                 f"descarga/STATA/{codigo}-Modulo{modulo}.zip y déjenlo en {datos}/")
    return candidatos[0]


def leer(ruta, llaves):
    df = pd.read_stata(ruta, convert_categoricals=False)
    df.columns = normalizar(df.columns)
    for c in llaves + ["ubigeo"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    return df


def media_ponderada(x, w):
    m = x.notna() & w.notna()
    return float(np.average(x[m], weights=w[m]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anio", type=int, default=2024)
    ap.add_argument("--raiz", default=".", help="carpeta del proyecto (la que tiene datos/ y salidas/)")
    a = ap.parse_args()
    raiz = Path(a.raiz).resolve()
    datos, salidas = raiz / "datos", raiz / "salidas"
    salidas.mkdir(exist_ok=True)
    codigo = CODIGO_INEI.get(a.anio)
    if codigo is None:
        sys.exit(f"ERROR: solo está configurado 2024 (código INEI 966); pidieron {a.anio}.")

    # 1-2. leer y normalizar -------------------------------------------------------------------------------
    sumaria = leer(buscar_dta(datos, codigo, "34", f"sumaria-{a.anio}.dta"), LLAVES)
    miembros = leer(buscar_dta(datos, codigo, "02", f"enaho01-{a.anio}-200.dta"), LLAVES + ["codperso"])
    filas_miembros = len(miembros)

    # 3. residentes habituales -----------------------------------------------------------------------------
    residente = ((miembros.p204 == 1) & (miembros.p205 == 2)) | ((miembros.p204 == 2) & (miembros.p206 == 1))
    personas = miembros.loc[residente, LLAVES + ["codperso", "p207", "p208a", "facpob07"]].copy()

    # 5a. variables del hogar (sumaria) ----------------------------------------------------------------------
    alimentos = [c for c in sumaria.columns if c.startswith(("gru11", "gru12", "gru13", "gru14"))]
    hog = sumaria[LLAVES + ["ubigeo", "dominio", "estrato", "pobreza", "factor07", "mieperho", "gashog2d",
                            "inghog2d", "linea", "linpe"]].copy()
    hog["gasto_alimentos"] = sumaria[alimentos].fillna(0).sum(axis=1)
    hog["peso_alimentos"] = np.where(hog.gashog2d > 0, hog.gasto_alimentos / hog.gashog2d * 100, np.nan)
    hog["gasto_pc_mensual"] = hog.gashog2d / hog.mieperho / 12

    # 4. unir personas (muchas) con hogares (uno) ------------------------------------------------------------
    base = personas.merge(hog, on=LLAVES, how="left", validate="m:1", indicator=True)

    # 5b. indicadores ---------------------------------------------------------------------------------------
    base["departamento"] = base.ubigeo.str[:2]
    base["nombre_departamento"] = base.departamento.map(NOMBRES_DEP)
    base["urbano"] = base.estrato <= 5
    base["area"] = np.where(base.urbano, "Urbana", "Rural")
    base["pobre"] = base.pobreza <= 2
    base["pobre_extremo"] = base.pobreza == 1
    base["sexo"] = base.p207.map({1: "Hombre", 2: "Mujer"})
    base["grupo_edad"] = pd.cut(base.p208a, [-1, 13, 17, 29, 44, 59, 200],
                                labels=["0-13", "14-17", "18-29", "30-44", "45-59", "60+"]).astype(str)

    # 6. validaciones ---------------------------------------------------------------------------------------
    w = base.facpob07
    pob_nac = media_ponderada(base.pobre.astype(float), w) * 100
    pob_hog = float(np.average(sumaria.pobreza <= 2, weights=sumaria.factor07 * sumaria.mieperho) * 100)
    pob_urb = media_ponderada(base.loc[base.urbano, "pobre"].astype(float), w[base.urbano]) * 100
    pob_rur = media_ponderada(base.loc[~base.urbano, "pobre"].astype(float), w[~base.urbano]) * 100
    pob_ext = media_ponderada(base.pobre_extremo.astype(float), w) * 100
    deps = sorted(base.departamento.dropna().unique())
    checks = [
        ("Llaves únicas en la sumaria (conglome, vivienda, hogar)", not sumaria.duplicated(LLAVES).any(),
         f"{len(sumaria):,} hogares, {sumaria.duplicated(LLAVES).sum()} duplicados", True),
        ("Llaves únicas en miembros (+ codperso)", not miembros.duplicated(LLAVES + ["codperso"]).any(),
         f"{filas_miembros:,} filas, {miembros.duplicated(LLAVES + ['codperso']).sum()} duplicadas", True),
        ("Residentes habituales = 108,664", len(personas) == REFERENCIA["residentes"],
         f"{len(personas):,} de {filas_miembros:,} filas del módulo 02", True),
        ("La unión m:1 no duplica ni pierde personas", len(base) == len(personas) and (base._merge == "both").all(),
         f"{len(base):,} filas después de unir; sin pareja en la sumaria: {(base._merge != 'both').sum()}", True),
        ("Personas sin factor de expansión (facpob07)", base.facpob07.notna().all(),
         f"{base.facpob07.isna().sum()} sin factor", True),
        ("25 departamentos identificados (ubigeo[:2] = 01..25)", deps == sorted(NOMBRES_DEP),
         f"{len(deps)} códigos: {', '.join(deps)}", True),
        (f"Pobreza nacional ponderada (facpob07) a ≤ {REFERENCIA['tolerancia']} pts de 27.6 %",
         abs(pob_nac - REFERENCIA["pobreza_nacional"]) <= REFERENCIA["tolerancia"],
         f"{pob_nac:.2f} % (diferencia {pob_nac - REFERENCIA['pobreza_nacional']:+.2f} pts)", True),
        ("Pobreza nacional con la sumaria (factor07 × mieperho) a ≤ 0.1 pts de 27.6 %",
         abs(pob_hog - REFERENCIA["pobreza_nacional"]) <= REFERENCIA["tolerancia"], f"{pob_hog:.2f} %", True),
        ("Pobreza urbana ≈ 24.8 % (estrato ≤ 5)", abs(pob_urb - REFERENCIA["urbano"]) <= 0.15, f"{pob_urb:.2f} %",
         False),
        ("Pobreza rural ≈ 39.3 % (estrato ≥ 6)", abs(pob_rur - REFERENCIA["rural"]) <= 0.15, f"{pob_rur:.2f} %",
         False),
        ("Promedio simple ≠ ponderado (el factor sí cambia la cifra)",
         abs(base.pobre.mean() * 100 - pob_nac) > 0.5,
         f"simple {base.pobre.mean() * 100:.2f} % vs ponderado {pob_nac:.2f} %", False),
    ]

    lineas = [f"VALIDACIÓN ENAHO {a.anio} (INEI, código {codigo}) — {datetime.now():%Y-%m-%d %H:%M}",
              "Módulos: 34 (sumaria, hogares) y 02 (miembros, personas). Ponderador de personas: facpob07.", ""]
    for nombre, ok, detalle, esencial in checks:
        lineas.append(f"[{'PASA' if ok else 'FALLA'}]{' (esencial)' if esencial else ''} {nombre}: {detalle}")
    lineas += ["", "Cifras principales (% de personas, ponderadas):",
               f"  Pobreza monetaria nacional: {pob_nac:.2f} %  (redondeada {pob_nac:.1f} %; INEI 27.6 %)",
               f"  Pobreza extrema nacional:   {pob_ext:.2f} %",
               f"  Urbana / rural:             {pob_urb:.2f} % / {pob_rur:.2f} %",
               f"  Residentes habituales:      {len(personas):,} (población expandida {w.sum():,.0f})",
               "",
               f"Nota de redondeo: con personas y facpob07 la pobreza da {pob_nac:.2f} %; con la sumaria y",
               f"factor07 × mieperho (método de publicación del INEI) da {pob_hog:.2f} % ≈ 27.6 %. Las dos están dentro",
               "de la tolerancia de 0.1 pts: facpob07 está calibrado por persona y factor07 por hogar, por eso",
               "difieren en centésimas. Urbano/rural se definen con estrato <= 5; el INEI publica 24.8 % / 39.3 %."]
    fallas_esenciales = [n for n, ok, _, e in checks if e and not ok]
    lineas.append("")
    lineas.append("RESULTADO: " + ("TODAS LAS VALIDACIONES ESENCIALES PASAN" if not fallas_esenciales else
                                   "FALLAN VALIDACIONES ESENCIALES: " + "; ".join(fallas_esenciales)))
    (salidas / "validacion.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    if fallas_esenciales:
        sys.exit(1)

    # 7. guardar ------------------------------------------------------------------------------------------
    base = base.drop(columns="_merge")
    base["condicion"] = np.where(base.pobre_extremo, "Pobre extremo",
                                 np.where(base.pobre, "Pobre no extremo", "No pobre"))
    base["departamento_nombre"] = base.departamento + " " + base.nombre_departamento
    base.to_parquet(salidas / f"personas_{a.anio}.parquet", index=False)

    def tabla(grupo, col):
        filas = []
        for cat, g in (base.groupby(col) if col else [("Perú", base)]):
            filas.append({"grupo": grupo, "categoria": cat,
                          "pobreza_pct": round(media_ponderada(g.pobre.astype(float), g.facpob07) * 100, 2),
                          "pobreza_extrema_pct": round(media_ponderada(g.pobre_extremo.astype(float), g.facpob07) * 100, 2),
                          "peso_alimentos_pct": round(media_ponderada(g.peso_alimentos, g.facpob07), 2),
                          "gasto_pc_mensual_soles": round(media_ponderada(g.gasto_pc_mensual, g.facpob07), 1),
                          "poblacion_expandida": round(float(g.facpob07.sum())),
                          "pobres_expandidos": round(float(g.facpob07[g.pobre].sum())),
                          "n_muestra": len(g)})
        return filas

    ind = pd.DataFrame(tabla("nacional", None) + tabla("area", "area") + tabla("sexo", "sexo")
                       + tabla("grupo_edad", "grupo_edad") + tabla("condicion", "condicion")
                       + tabla("departamento", "departamento_nombre"))
    ind.to_csv(salidas / "indicadores.csv", index=False)
    print(f"\nGuardado: salidas/personas_{a.anio}.parquet ({len(base):,} personas), salidas/indicadores.csv "
          f"({len(ind)} filas), salidas/validacion.txt")


if __name__ == "__main__":
    main()

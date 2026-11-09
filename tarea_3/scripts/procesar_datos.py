"""Limpia y une los módulos 01, 03 y 34 de la ENAHO 2015-2025.

Salidas (ignoradas por git, se regeneran con este script):
  datos/procesados/hogares.parquet   un registro por hogar con entrevista completa o incompleta
  datos/procesados/personas.parquet  un registro por residente habitual de 6 años a más

Decisiones:
- Hogares: se conservan los que tienen registro en la sumaria (módulo 34), que es el universo
  con el que el INEI calcula pobreza; se pondera con factor07.
- Personas: residentes habituales (p204=1 y p205=2, o p204=2 y p206=1), 6 años a más; se pondera
  con factora07 (factor ajustado por grupos de edad, el que usa el INEI para indicadores de personas).
- Área: estrato 1-5 urbano, 6-8 rural (criterio del INEI).
- Departamento: los dos primeros dígitos del ubigeo (Lima y Callao por separado, 25 unidades).
- Quintil: gasto per cápita del hogar (gashog2d / mieperho), ponderado por personas, por año.
- Internet en el hogar (p1144): desde 2023 la pregunta incluye la conexión móvil (p114b1-3), por eso
  la serie del hogar se quiebra en 2023. La serie larga comparable es la de uso individual (p314a).
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ORIG = RAIZ / "datos" / "originales"
PROC = RAIZ / "datos" / "procesados"
ANIOS = range(2015, 2026)
LLAVE = ["conglome", "vivienda", "hogar"]

DEPARTAMENTOS = {
    "01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa", "05": "Ayacucho",
    "06": "Cajamarca", "07": "Callao", "08": "Cusco", "09": "Huancavelica", "10": "Huánuco",
    "11": "Ica", "12": "Junín", "13": "La Libertad", "14": "Lambayeque", "15": "Lima",
    "16": "Loreto", "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
    "21": "Puno", "22": "San Martín", "23": "Tacna", "24": "Tumbes", "25": "Ucayali",
}
LENGUA_INDIGENA = {1, 2, 3, 10, 11, 12, 13, 14, 15}


def leer(anio: int, modulo: str, columnas: list[str]) -> pd.DataFrame:
    """Lee solo las columnas pedidas del .dta principal del módulo (nombres en minúscula)."""
    z = zipfile.ZipFile(ORIG / f"enaho_{anio}_mod{modulo}.zip")
    patrones = {"01": rf"enaho01-{anio}-100\.dta$", "03": rf"enaho01a-{anio}-300\.dta$",
                "34": rf"sumaria-{anio}\.dta$"}
    nombre = next(n for n in z.namelist() if re.search(patrones[modulo], n, re.I))
    datos = io.BytesIO(z.read(nombre))
    disponibles = {c.lower(): c for c in pd.io.stata.StataReader(datos).variable_labels()}
    datos.seek(0)
    usar = [disponibles[c] for c in columnas if c in disponibles]
    df = pd.read_stata(datos, columns=usar, convert_categoricals=False)
    df.columns = [c.lower() for c in df.columns]
    for c in columnas:  # columnas que no existen ese año
        if c not in df:
            df[c] = np.nan
    for c in LLAVE:
        if c in df:
            df[c] = df[c].astype(str).str.strip()
    return df


def cuantil_ponderado(valor: pd.Series, peso: pd.Series, k: int = 5) -> pd.Series:
    orden = np.argsort(valor.to_numpy())
    acum = np.cumsum(peso.to_numpy()[orden]) / peso.sum()
    q = np.empty(len(valor), dtype=int)
    q[orden] = np.minimum((acum * k).astype(int) + 1, k)
    # el límite superior exacto de cada quintil cae en el quintil inferior
    return pd.Series(q, index=valor.index)


def sumaria(anio: int) -> pd.DataFrame:
    s = leer(anio, "34", LLAVE + ["ubigeo", "estrato", "factor07", "mieperho", "gashog2d", "pobreza"])
    s = s[s.mieperho > 0].copy()
    s["ubigeo"] = s.ubigeo.astype(str).str.zfill(6)
    s["cod_dep"] = s.ubigeo.str[:2]
    s["departamento"] = s.cod_dep.map(DEPARTAMENTOS)
    s["area"] = np.where(s.estrato <= 5, "Urbano", "Rural")
    s["pobreza"] = s.pobreza.map({1: "Pobre extremo", 2: "Pobre no extremo", 3: "No pobre"})
    s["pobre"] = np.where(s.pobreza == "No pobre", "No pobre", "Pobre")
    s["gasto_pc_mensual"] = s.gashog2d / s.mieperho / 12
    s["quintil"] = cuantil_ponderado(s.gasto_pc_mensual, s.factor07 * s.mieperho)
    s["quintil"] = "Q" + s.quintil.astype(str)
    return s[LLAVE + ["ubigeo", "cod_dep", "departamento", "area", "factor07", "mieperho",
                      "gasto_pc_mensual", "quintil", "pobreza", "pobre"]]


def hogares(anio: int, s: pd.DataFrame) -> pd.DataFrame:
    m = leer(anio, "01", LLAVE + ["result", "p1141", "p1142", "p1143", "p1144", "p1145",
                                   "p114b1", "p114b2", "p114b3"])
    m = m[m.result.isin([1, 2]) & m.p1144.notna()]
    h = s.merge(m, on=LLAVE, how="inner", validate="one_to_one")
    out = h[LLAVE + ["ubigeo", "cod_dep", "departamento", "area", "factor07", "mieperho",
                     "quintil", "pobreza", "pobre"]].copy()
    out["anio"] = anio
    out["tel_fijo"] = (h.p1141 == 1).astype(int)
    out["celular"] = (h.p1142 == 1).astype(int)
    out["tv_cable"] = (h.p1143 == 1).astype(int)
    out["internet"] = (h.p1144 == 1).astype(int)
    out["sin_tic"] = (h.p1145 == 1).astype(int)
    # Tipo de conexión: solo desde 2023
    tiene_tipo = h.p114b1.notna().any()
    out["internet_fijo"] = (h.p114b1 > 0).astype(float) if tiene_tipo else np.nan
    movil = (h.p114b2 > 0) | (h.p114b3 > 0)
    out["internet_solo_movil"] = (movil & ~(h.p114b1 > 0)).astype(float) if tiene_tipo else np.nan
    return out


def personas(anio: int, s: pd.DataFrame) -> pd.DataFrame:
    p = leer(anio, "03", LLAVE + ["codperso", "p204", "p205", "p206", "p207", "p208a", "p300a",
                                   "p314a", "p314d", "p314b1_1", "p314b1_2", "p314b1_6",
                                   "p314b1_8", "p314b1_9", "factora07"])
    residente = ((p.p204 == 1) & (p.p205 == 2)) | ((p.p204 == 2) & (p.p206 == 1))
    p = p[residente & (p.p208a >= 6) & p.p314a.isin([1, 2]) & p.factora07.notna()]
    p = p.merge(s.drop(columns=["factor07", "mieperho", "gasto_pc_mensual"]), on=LLAVE,
                how="inner", validate="many_to_one")
    out = p[LLAVE + ["codperso", "ubigeo", "cod_dep", "departamento", "area", "quintil",
                     "pobreza", "pobre", "factora07"]].copy()
    out["anio"] = anio
    out["sexo"] = p.p207.map({1: "Hombre", 2: "Mujer"})
    out["edad"] = p.p208a.astype(int)
    out["grupo_edad"] = pd.cut(p.p208a, [5, 11, 17, 24, 44, 64, 200],
                               labels=["6-11", "12-17", "18-24", "25-44", "45-64", "65+"]).astype(str)
    out["lengua"] = np.select([p.p300a == 4, p.p300a.isin(LENGUA_INDIGENA)],
                              ["Castellano", "Lengua indígena"], "Otra")
    out["usa_internet"] = (p.p314a == 1).astype(int)
    # Entre abril y setiembre de 2020 la entrevista fue telefónica y no se preguntó la frecuencia
    # ni el dispositivo a los usuarios: esos casos quedan como dato faltante, no como "no usa".
    usuario_sin_detalle = (p.p314a == 1) & p.p314d.isna()
    out["usa_diario"] = ((p.p314a == 1) & (p.p314d == 1)).astype(float).mask(usuario_sin_detalle)
    # Dispositivo: desde 2019 (las variables marcan el código cuando se usó, 0 si no)
    if p.p314b1_9.notna().any():
        dispositivos = p[["p314b1_1", "p314b1_2", "p314b1_6", "p314b1_8", "p314b1_9"]]
        sin_dispositivo = (p.p314a == 1) & dispositivos.isna().all(axis=1)
        out["usa_celular"] = (((p.p314b1_8 > 0) | (p.p314b1_9 > 0)) & (p.p314a == 1)).astype(float).mask(sin_dispositivo)
        compu = (p.p314b1_1 > 0) | (p.p314b1_2 > 0)
        out["usa_computadora"] = (compu & (p.p314a == 1)).astype(float).mask(sin_dispositivo)
    else:
        out["usa_celular"] = np.nan
        out["usa_computadora"] = np.nan
    return out


def main() -> None:
    PROC.mkdir(parents=True, exist_ok=True)
    H, P = [], []
    for anio in ANIOS:
        s = sumaria(anio)
        h, p = hogares(anio, s), personas(anio, s)
        print(f"{anio}: sumaria {len(s):,} | hogares {len(h):,} | personas 6+ {len(p):,}")
        H.append(h)
        P.append(p)
    hog = pd.concat(H, ignore_index=True)
    per = pd.concat(P, ignore_index=True)
    assert hog.departamento.notna().all() and per.departamento.notna().all()
    assert not hog.duplicated(["anio"] + LLAVE).any()
    assert not per.duplicated(["anio"] + LLAVE + ["codperso"]).any()
    hog.to_parquet(PROC / "hogares.parquet", index=False)
    per.to_parquet(PROC / "personas.parquet", index=False)
    print(f"Total: {len(hog):,} hogares y {len(per):,} personas")


if __name__ == "__main__":
    main()

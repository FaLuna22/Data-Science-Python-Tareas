"""Servidor MCP del BCRP: busca, descarga, resume y compara series oficiales del Banco Central de Reserva del Perú.

    uv run pytest -q                                              # 8 pruebas originales + 2 propias = 10 passed
    uv run mcp/server.py                                          # el servidor, por stdio
    claude mcp add --scope project bcrp -- uv run mcp/server.py   # conectarlo a Claude Code (ya está en .mcp.json)

Las cuentas las hace Python, no el modelo: así cada cifra sale de una llamada que se puede repetir.

Herramientas:
    buscar_series   palabras -> códigos de series del catálogo oficial (17 mil series)
    serie           código + periodo -> datos y URL de la fuente
    resumen         código + periodo -> primero, último, cambio, variación, promedio, máximo y mínimo
    correlacion     (propia) dos códigos + periodo -> alinea periodos, descarta faltantes y calcula Pearson
    graficar_serie  (propia) código + periodo -> PNG con título, unidades y fuente en figuras/
Recurso:  bcrp://serie/{codigo}   ficha descriptiva de la serie
Prompt:   informe(tema)            pide un informe que cite código, periodo y fuente de cada cifra
"""
import json
import re
import time
import unicodedata
from functools import cache
from pathlib import Path

import httpx
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
CATALOGO = RAIZ / "datos" / "catalogo_bcrp.csv"
CACHE = RAIZ / "datos" / "cache_bcrp"
FIGURAS = RAIZ / "figuras"
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}

mcp = FastMCP("bcrp", instructions=(
    "Series oficiales del Banco Central de Reserva del Perú (BCRP). Primero busca el código con buscar_series; "
    "luego usa resumen para variaciones, promedios y extremos, serie para los datos, correlacion para relacionar "
    "dos series y graficar_serie para una figura. No calcules a mano: cita siempre el código de la serie, el "
    "periodo y la URL de la fuente. Si una herramienta falla o no trae datos, dilo: no inventes cifras."))

PLURAL = {"diaria": "diarias", "mensual": "mensuales", "trimestral": "trimestrales", "anual": "anuales"}
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
         "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}


def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


@cache
def catalogo():
    """El catálogo oficial: 17 mil series en unos 7 MB. Se baja una vez y queda en datos/."""
    if not CATALOGO.exists():
        CATALOGO.parent.mkdir(parents=True, exist_ok=True)
        r = httpx.get(URL_CATALOGO, timeout=120)
        r.raise_for_status()
        CATALOGO.write_text(r.content.decode("latin-1"), encoding="utf-8")
    df = pd.read_csv(CATALOGO, sep=";", dtype=str).fillna("")
    df = df.rename(columns={"Código de serie": "codigo", "Categoría de serie": "categoria", "Grupo de serie": "grupo",
                            "Nombre de serie": "nombre", "Frecuencia": "frecuencia",
                            "Fecha de actualización": "actualizada", "Fecha de inicio": "inicio"})
    df["texto"] = (df.categoria + " " + df.grupo + " " + df.nombre).map(_sin_tildes)
    return df


def _ficha(codigo):
    fila = catalogo().query("codigo == @codigo")
    if fila.empty:
        raise ToolError(f"No existe el código de serie {codigo!r}. Búsquenlo con buscar_series.")
    f = fila.iloc[0]
    return {"codigo": f.codigo, "nombre": f"{f.grupo} - {f.nombre}", "categoria": f.categoria,
            "frecuencia": f.frecuencia, "inicio": f.inicio, "actualizada": f.actualizada}


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_series(texto: str, frecuencia: str | None = None, limite: int = 10) -> list[dict]:
    """Busca series del BCRP por palabras: todas deben aparecer en la categoría, el grupo o el nombre.

    Ejemplos: "ipc 12 meses", "tipo de cambio interbancario venta", "reservas internacionales netas",
    "tasa de referencia", "cobre precio". frecuencia: "Diaria", "Mensual", "Trimestral" o "Anual".
    Devuelve el código, el nombre completo, la frecuencia y desde cuándo hay datos. Si no hay resultados,
    prueben con menos palabras.
    """
    df = catalogo()
    m = pd.Series(True, index=df.index)
    for palabra in _sin_tildes(texto).split():
        m &= df.texto.str.contains(re.escape(palabra))
    if frecuencia:
        m &= df.frecuencia.str.lower() == frecuencia.lower()
    # primero las series vigentes y, entre ellas, las de nombre más corto (las más generales)
    sel = df[m]
    orden = sel.assign(vieja=sel.actualizada < "2025", largo=(sel.grupo + sel.nombre).str.len())
    return [_ficha(c) for c in orden.sort_values(["vieja", "largo"]).head(limite).codigo]


# --------------------------------------------------------------------------------------------- fechas y periodos

def _tipo(frecuencia):
    f = _sin_tildes(frecuencia)
    for clave in ("diaria", "mensual", "trimestral", "anual"):
        if clave in f:
            return clave
    raise ToolError(f"Frecuencia no soportada: {frecuencia!r}")


def _fecha_api(fecha, tipo):
    """Convierte la fecha que da el usuario ("2025-01", "2025-01-15", "2025-T1", "2025") al formato de la API."""
    fecha = str(fecha).strip()
    m = re.fullmatch(r"(\d{4})(?:-(T?)(\d{1,2}))?(?:-(\d{1,2}))?", fecha, flags=re.I)
    if not m:
        raise ToolError(f"Fecha {fecha!r} no válida. Usen 2025-01 (mensual), 2025-01-15 (diaria), 2025-T1 o 2025.")
    anio, _, mes, dia = m.groups()
    if tipo == "anual":
        return anio
    if tipo == "trimestral":
        return f"{anio}-{int(mes or 1)}"
    if tipo == "mensual":
        return f"{anio}-{int(mes or 1)}"
    return f"{anio}-{int(mes or 1):02d}-{int(dia or 1):02d}"


def _periodo(nombre, tipo):
    """Convierte el nombre que devuelve la API ("Ene.2025", "01.Oct.26", "T1.25", "2025") a ISO."""
    if tipo == "anual":
        return nombre.strip()
    if tipo == "mensual":
        mes, anio = nombre.split(".")
        return f"{int(anio)}-{MESES[_sin_tildes(mes)[:3]]:02d}"
    if tipo == "trimestral":
        t, anio = nombre.split(".")
        anio = int(anio) + (2000 if len(anio) == 2 else 0)
        return f"{anio}-T{int(t.upper().lstrip('T'))}"
    dia, mes, anio = nombre.split(".")
    anio = int(anio) + (2000 if len(anio) == 2 else 0)
    return f"{anio}-{MESES[_sin_tildes(mes)[:3]]:02d}-{int(dia):02d}"


def _descargar(url):
    """Pide la URL a la API con reintentos; guarda en disco lo que ya bajó (la API limita pedidos seguidos)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    archivo = CACHE / (re.sub(r"[^\w.-]", "_", url.removeprefix(API + "/")) + ".json")
    if archivo.exists():
        return json.loads(archivo.read_text(encoding="utf-8"))
    ultimo = None
    for intento in range(5):
        try:
            r = httpx.get(url, timeout=60, headers={"User-Agent": "mcp-bcrp-curso/1.0"})
            texto = r.content.decode("utf-8", errors="replace").strip()
            if texto.startswith("{"):
                datos = json.loads(texto)
                archivo.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
                return datos
            ultimo = f"HTTP {r.status_code}, respuesta no JSON"
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            ultimo = repr(e)
        time.sleep(2 * (intento + 1))
    raise ToolError(f"El BCRP no respondió con datos para {url} ({ultimo}). Reintenten en unos segundos.")


def _serie(codigo, desde, hasta):
    ficha = _ficha(codigo)
    tipo = _tipo(ficha["frecuencia"])
    url = f"{API}/{codigo}/json/{_fecha_api(desde, tipo)}/{_fecha_api(hasta, tipo)}"
    crudo = _descargar(url)
    datos = []
    for p in crudo.get("periods", []):
        valor = (p.get("values") or ["n.d."])[0]
        try:
            datos.append({"periodo": _periodo(p["name"], tipo), "valor": float(valor)})
        except (ValueError, TypeError):
            continue  # "n.d." u otros vacíos
    if not datos:
        raise ToolError(f"La serie {codigo} no tiene datos entre {desde} y {hasta}. Revisen el periodo "
                        f"(la serie empieza en {ficha['inicio']} y se actualizó el {ficha['actualizada']}).")
    return {"codigo": codigo, "nombre": ficha["nombre"], "frecuencia": ficha["frecuencia"], "datos": datos,
            "fuente": url}


@mcp.tool(annotations=SOLO_LECTURA)
def serie(codigo: str, desde: str, hasta: str) -> dict:
    """Descarga los datos oficiales de una serie del BCRP entre dos fechas, con la URL de la fuente.

    Úsenla después de buscar_series, cuando necesiten los valores periodo por periodo.
    Fechas: "2025-01" para series mensuales, "2025-01-15" para diarias, "2025-T1" para trimestrales y
    "2025" para anuales. Ejemplo: serie("PN01273PM", "2025-01", "2025-12").
    Devuelve {codigo, nombre, frecuencia, datos: [{periodo, valor}], fuente}. Los valores "n.d." se omiten.
    """
    return _serie(codigo, desde, hasta)


@mcp.tool(annotations=SOLO_LECTURA)
def resumen(codigo: str, desde: str, hasta: str) -> dict:
    """Resume una serie del BCRP en un periodo: primero, último, cambio, variación %, promedio, máximo y mínimo.

    Úsenla siempre que la pregunta pida un valor puntual, un promedio, un cambio o un extremo: así el modelo no
    hace cuentas a mano. Fechas como en serie. Ejemplo: resumen("PN01273PM", "2025-12", "2026-09").
    """
    s = _serie(codigo, desde, hasta)
    df = pd.DataFrame(s["datos"])
    primero, ultimo = df.iloc[0], df.iloc[-1]
    imax, imin = df.valor.idxmax(), df.valor.idxmin()
    cambio = ultimo.valor - primero.valor
    return {"codigo": codigo, "nombre": s["nombre"], "frecuencia": s["frecuencia"], "n": len(df),
            "primero": {"periodo": primero.periodo, "valor": float(primero.valor)},
            "ultimo": {"periodo": ultimo.periodo, "valor": float(ultimo.valor)},
            "cambio": round(float(cambio), 6),
            "variacion_pct": round(float(cambio / primero.valor * 100), 4) if primero.valor else None,
            "promedio": round(float(df.valor.mean()), 6),
            "maximo": {"periodo": df.periodo[imax], "valor": float(df.valor[imax])},
            "minimo": {"periodo": df.periodo[imin], "valor": float(df.valor[imin])},
            "fuente": s["fuente"]}


# ------------------------------------------------------------------------------------------- herramientas propias

@mcp.tool(annotations=SOLO_LECTURA)
def correlacion(codigo_a: str, codigo_b: str, desde: str, hasta: str) -> dict:
    """Mide cuánto se mueven juntas dos series del BCRP: alinea periodos y calcula la correlación de Pearson.

    Úsenla cuando pregunten si dos indicadores van de la mano (por ejemplo inflación y tasa de referencia, tipo de
    cambio y precio del cobre). Ambas series deben tener la misma frecuencia. Solo se usan los periodos con dato en
    las dos; los faltantes se descartan y se informan. Devuelve r (Pearson), r2, el número de periodos comunes, el
    promedio de cada serie y las dos URL de la fuente. Una correlación alta es una asociación, no causalidad.
    Ejemplo: correlacion("PN01273PM", "PD04722MM", "2023-01", "2026-09").
    """
    a, b = _serie(codigo_a, desde, hasta), _serie(codigo_b, desde, hasta)
    if _tipo(a["frecuencia"]) != _tipo(b["frecuencia"]):
        raise ToolError(f"Las frecuencias no coinciden: {codigo_a} es {a['frecuencia']} y {codigo_b} es "
                        f"{b['frecuencia']}. Elijan dos series con la misma frecuencia.")
    da = pd.DataFrame(a["datos"]).set_index("periodo").valor.rename("a")
    db = pd.DataFrame(b["datos"]).set_index("periodo").valor.rename("b")
    juntos = pd.concat([da, db], axis=1)
    comunes = juntos.dropna()
    if len(comunes) < 3:
        raise ToolError(f"Solo hay {len(comunes)} periodos con dato en ambas series: no alcanza para correlacionar.")
    r = float(comunes.a.corr(comunes.b))
    return {"codigo_a": codigo_a, "nombre_a": a["nombre"], "codigo_b": codigo_b, "nombre_b": b["nombre"],
            "desde": comunes.index[0], "hasta": comunes.index[-1], "n_comunes": len(comunes),
            "descartados": int(len(juntos) - len(comunes)), "r": round(r, 4), "r2": round(r * r, 4),
            "promedio_a": round(float(comunes.a.mean()), 4), "promedio_b": round(float(comunes.b.mean()), 4),
            "lectura": ("asociación positiva" if r > 0.3 else "asociación negativa" if r < -0.3 else
                        "asociación débil") + " (descriptiva, no causal)",
            "fuentes": [a["fuente"], b["fuente"]]}


@mcp.tool(annotations={"readOnlyHint": False, "openWorldHint": True})
def graficar_serie(codigo: str, desde: str, hasta: str, archivo: str | None = None,
                   unidad: str | None = None) -> dict:
    """Dibuja una serie del BCRP y guarda un PNG en figuras/, con título, periodo, unidades y fuente.

    Úsenla cuando pidan un gráfico o una figura de un indicador macroeconómico para un informe. Fechas como en serie.
    archivo: nombre del PNG (por defecto bcrp_<codigo>.png). unidad: texto del eje Y (por ejemplo "%").
    Devuelve la ruta del PNG y el resumen de la serie graficada.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = _serie(codigo, desde, hasta)
    df = pd.DataFrame(s["datos"])
    FIGURAS.mkdir(parents=True, exist_ok=True)
    ruta = FIGURAS / (archivo or f"bcrp_{codigo}.png")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(range(len(df)), df.valor, color="#1f4e79", lw=2)
    paso = max(1, len(df) // 10)
    ax.set_xticks(range(0, len(df), paso), df.periodo[::paso], rotation=45, ha="right")
    ax.set_title(f"{s['nombre']}\n{df.periodo.iloc[0]} a {df.periodo.iloc[-1]}", fontsize=11, loc="left")
    ax.set_ylabel(unidad or "valor")
    ax.grid(alpha=.3)
    ax.spines[["top", "right"]].set_visible(False)
    ultimo = df.iloc[-1]
    ax.annotate(f"{ultimo.valor:,.2f}", (len(df) - 1, ultimo.valor), textcoords="offset points", xytext=(4, 4))
    fig.text(0.01, 0.01, f"Fuente: BCRP, serie {codigo} ({s['fuente']})", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(ruta, dpi=200)
    plt.close(fig)
    return {"archivo": str(ruta.relative_to(RAIZ)), "codigo": codigo, "nombre": s["nombre"], "n": len(df),
            "ultimo": {"periodo": ultimo.periodo, "valor": float(ultimo.valor)}, "fuente": s["fuente"]}


# ------------------------------------------------------------------------------------------- recurso y prompt

@mcp.resource("bcrp://serie/{codigo}", mime_type="application/json")
def ficha_serie(codigo: str) -> str:
    """Ficha descriptiva de una serie del BCRP: nombre, categoría, frecuencia, inicio y última actualización."""
    f = _ficha(codigo)
    f["url_consulta"] = (f"https://estadisticas.bcrp.gob.pe/estadisticas/series/"
                         f"{PLURAL[_tipo(f['frecuencia'])]}/resultados/{codigo}/html")
    f["api"] = f"{API}/{codigo}/json"
    return json.dumps(f, ensure_ascii=False, indent=2)


@mcp.prompt
def informe(tema: str) -> str:
    """Informe breve sobre un indicador macroeconómico del Perú con cifras verificables del BCRP."""
    return (f"Escribe un informe breve sobre «{tema}» en el Perú usando solo el servidor MCP bcrp.\n"
            "1. Usa buscar_series para encontrar la serie oficial y explica por qué la elegiste.\n"
            "2. Usa resumen (y serie si hace falta) para el último dato, el cambio y los extremos del periodo.\n"
            "3. Si es útil, usa correlacion con otra serie y graficar_serie para una figura.\n"
            "4. Cada cifra debe ir con el código de la serie, el periodo y la URL de la fuente. No hagas cuentas a "
            "mano ni uses cifras de memoria; si una herramienta falla, dilo.\n"
            "5. Cierra con tres viñetas de interpretación y una de limitaciones (asociación no es causalidad).")


if __name__ == "__main__":
    mcp.run()

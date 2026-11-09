"""Evaluación del agente: las mismas 10 preguntas sin y con MCP/Skills, contra respuestas verificadas de antemano.

    uv run evaluacion/evaluar.py                        # modos A y B, con Sonnet, 3 en paralelo
    uv run evaluacion/evaluar.py --modos A --paralelo 5

Modo A (sin MCP ni Skills): claude -p sin ninguna herramienta (--tools ""), sin servidores MCP
    (--strict-mcp-config) y desde una carpeta vacía, así no puede leer archivos con las respuestas.
Modo B (con MCP y Skills): claude -p desde una copia del proyecto SIN evaluacion/, informes/ ni evidencias_ia/ (para
    que no pueda leer las verdades), con el servidor MCP bcrp, la herramienta Skill y Bash limitado a `uv run`.
Ambos modos: el mismo modelo, la misma instrucción, una sesión independiente por pregunta (--no-session-persistence).

Escribe evaluacion/resultados.csv (una fila por pregunta y modo) y evidencias_ia/evaluacion/<modo>_<id>.jsonl con la
transcripción completa de cada llamada.
"""
import argparse
import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
TMP = Path(os.environ.get("EVAL_TMP", "/tmp/eval_tarea4"))
LOGS = RAIZ / "evidencias_ia" / "evaluacion"
ESQUEMA = {"type": "object", "required": ["valor", "fuente"],
           "properties": {"valor": {"type": ["number", "null"]}, "unidad": {"type": "string"},
                          "fuente": {"type": "string"},
                          "comp_bcrp": {"type": ["number", "null"]}, "comp_enaho": {"type": ["number", "null"]},
                          "interpretacion": {"type": "string"}}}
INSTRUCCION = ("Responde con un solo número en «valor», en la unidad que pide la pregunta. Si no puedes saberlo con "
               "certeza, pon valor null: no estimes. En «fuente» di de dónde sale la cifra (serie, archivo o "
               "publicación) y en «interpretacion» una frase sobre qué significa. Usa las herramientas que tengas "
               "disponibles para obtener y calcular la cifra.\n\n")
HERRAMIENTAS = {"A": "ninguna (sin herramientas de Claude Code, sin MCP, sin Skills; carpeta vacía)",
                "B": "mcp__bcrp (5 herramientas), Skill (limpiando/graficando/mapeando-enaho), Bash(uv run:*), "
                     "Read, Glob, Grep"}


def preparar():
    """Carpeta vacía para A y copia del proyecto sin las verdades para B."""
    a = TMP / "modo_a"
    shutil.rmtree(a, ignore_errors=True)
    a.mkdir(parents=True)
    b = TMP / "modo_b"
    shutil.rmtree(b, ignore_errors=True)
    b.mkdir(parents=True)
    for x in ["mcp", ".claude", "salidas", "pyproject.toml", "uv.lock", ".mcp.json"]:
        src = RAIZ / x
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, b / x)
    for x in ["datos", ".venv"]:   # pesados: enlace simbólico
        (b / x).symlink_to(RAIZ / x)
    for x in ["figuras", "mapas"]:
        (b / x).mkdir()
    return {"A": a, "B": b}


def comando(pregunta, modo, modelo, carpetas):
    base = ["claude", "-p", INSTRUCCION + pregunta, "--output-format", "stream-json", "--verbose",
            "--json-schema", json.dumps(ESQUEMA), "--no-session-persistence", "--model", modelo,
            "--strict-mcp-config"]
    if modo == "A":
        return base + ["--tools", ""]
    return base + ["--mcp-config", str(carpetas["B"] / ".mcp.json"),
                   "--allowedTools", "mcp__bcrp", "Skill", "Bash(uv run:*)", "Read", "Glob", "Grep",
                   "--disallowedTools", "WebSearch", "WebFetch"]


def preguntar(q, modo, modelo, carpetas):
    t = time.time()
    try:
        proc = subprocess.run(comando(q.pregunta, modo, modelo, carpetas), capture_output=True, text=True,
                              timeout=900, cwd=carpetas[modo])
        salida, error = proc.stdout, proc.stderr[-300:]
    except subprocess.TimeoutExpired as e:
        salida, error = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), "timeout"
    segundos = round(time.time() - t, 1)
    (LOGS / f"{modo}_{q.id}.jsonl").write_text(salida, encoding="utf-8")
    herramientas, final = [], {}
    for linea in salida.splitlines():
        try:
            e = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "assistant":
            for c in e["message"]["content"]:
                if c.get("type") == "tool_use":
                    nombre = c["name"]
                    if nombre == "Skill":
                        nombre += ":" + str(c["input"].get("skill", c["input"].get("command", "")))
                    herramientas.append(nombre)
        if e.get("type") == "result":
            final = e
    r = final.get("structured_output") or {}
    return {"valor": r.get("valor"), "comp_bcrp": r.get("comp_bcrp"), "comp_enaho": r.get("comp_enaho"),
            "unidad_respondida": r.get("unidad", ""), "fuente_respondida": r.get("fuente", final.get("result", "")),
            "interpretacion": r.get("interpretacion", ""),
            "herramientas_usadas": " | ".join(dict.fromkeys(herramientas)) or "ninguna",
            "n_llamadas_herramientas": len(herramientas), "segundos": segundos, "turnos": final.get("num_turns"),
            "error": "" if final.get("subtype") == "success" else (final.get("subtype") or error)}


def dentro(x, verdad, tol):
    return x is not None and not pd.isna(x) and abs(float(x) - verdad) <= tol


def calificar(q, r):
    if r["valor"] is None:
        return "no sabe", ""
    ok = dentro(r["valor"], q.verdad, q.tolerancia)
    if q.tipo != "combinada":
        return ("acierta" if ok else "se equivoca"), ""
    # combinadas: exactitud de cada fuente + coherencia (el valor final sale de los dos componentes)
    ok_b = dentro(r["comp_bcrp"], q.comp_bcrp, q.comp_bcrp_tol)
    ok_e = dentro(r["comp_enaho"], q.comp_enaho, q.comp_enaho_tol)
    coherente = False
    if r["comp_bcrp"] and r["comp_enaho"]:
        esperado = (r["comp_bcrp"] * r["comp_enaho"] / 100 if q.id == "comb_exposicion"
                    else r["comp_enaho"] / r["comp_bcrp"])
        coherente = abs(esperado - r["valor"]) <= q.tolerancia
    detalle = f"BCRP {'ok' if ok_b else 'mal'}, ENAHO {'ok' if ok_e else 'mal'}, coherente {'sí' if coherente else 'no'}"
    if ok and ok_b and ok_e and coherente:
        return "acierta", detalle
    if ok or ok_b or ok_e:
        return "parcial", detalle
    return "se equivoca", detalle


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--modos", nargs="+", default=["A", "B"], choices=["A", "B"])
    p.add_argument("--modelo", default="sonnet")
    p.add_argument("--paralelo", type=int, default=3)
    a = p.parse_args()
    LOGS.mkdir(parents=True, exist_ok=True)
    carpetas = preparar()
    preguntas = pd.read_csv(RAIZ / "evaluacion" / "preguntas.csv")
    casos = [(q, m) for m in a.modos for q in preguntas.itertuples()]
    print(f"{len(casos)} llamadas a claude -p con {a.modelo}...", flush=True)
    with ThreadPoolExecutor(a.paralelo) as ex:
        respuestas = list(ex.map(lambda c: preguntar(c[0], c[1], a.modelo, carpetas), casos))

    filas = []
    for (q, m), r in zip(casos, respuestas):
        resultado, detalle = calificar(q, r)
        filas.append({"id": q.id, "tipo": q.tipo, "modo": m, "pregunta": q.pregunta, "verdad": q.verdad,
                      "tolerancia": q.tolerancia, "unidad": q.unidad, **r, "resultado": resultado,
                      "detalle_combinada": detalle, "herramientas_habilitadas": HERRAMIENTAS[m], "modelo": a.modelo})
    res = pd.DataFrame(filas)
    salida = RAIZ / "evaluacion" / "resultados.csv"
    if salida.exists() and set(a.modos) != {"A", "B"}:   # corrida parcial: reemplaza solo esos modos
        viejo = pd.read_csv(salida)
        res = pd.concat([viejo[~viejo.modo.isin(a.modos)], res], ignore_index=True)
    res.to_csv(salida, index=False)

    print("\n" + res.pivot(index="id", columns="modo", values="valor").to_string())
    tabla = res.groupby("modo").resultado.value_counts().unstack(fill_value=0)
    tabla["segundos_promedio"] = res.groupby("modo").segundos.mean().round(1)
    print("\n" + tabla.to_string())

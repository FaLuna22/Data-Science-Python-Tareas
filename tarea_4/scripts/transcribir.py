"""Convierte una transcripción stream-json de `claude -p` en Markdown legible (instrucción, llamadas y respuestas).

    uv run scripts/transcribir.py evidencias_ia/integracion/ejecucion_integrada.jsonl
"""
import json
import sys
from pathlib import Path


def bloque(texto, n=3000):
    texto = str(texto)
    return texto if len(texto) <= n else texto[:n] + f"\n… [{len(texto) - n} caracteres más en el .jsonl]"


def main(ruta):
    ruta = Path(ruta)
    out = [f"# Transcripción: {ruta.name}", ""]
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(linea)
        except json.JSONDecodeError:
            continue
        t = e.get("type")
        if t == "system" and e.get("subtype") == "init":
            skills = [s for s in e.get("skills", []) if "enaho" in s]
            out += [f"**Sesión:** modelo `{e.get('model')}`, carpeta `{e.get('cwd')}`",
                    f"**MCP:** {', '.join(s['name'] + ' (' + s['status'] + ')' for s in e.get('mcp_servers', []))}",
                    f"**Skills del proyecto cargadas:** {', '.join(skills)}", ""]
        elif t == "user":
            for c in e["message"]["content"] if isinstance(e["message"]["content"], list) else [
                    {"type": "text", "text": e["message"]["content"]}]:
                if c.get("type") == "text":
                    out += ["## 👤 Instrucción", "", bloque(c["text"]), ""]
                elif c.get("type") == "tool_result":
                    contenido = c.get("content")
                    if isinstance(contenido, list):
                        contenido = "\n".join(x.get("text", "") for x in contenido if isinstance(x, dict))
                    out += ["<details><summary>Resultado de la herramienta</summary>", "", "```", bloque(contenido),
                            "```", "</details>", ""]
        elif t == "assistant":
            for c in e["message"]["content"]:
                if c.get("type") == "text":
                    out += ["## 🤖 Claude", "", c["text"], ""]
                elif c.get("type") == "tool_use":
                    out += [f"### 🔧 `{c['name']}`", "", "```json",
                            bloque(json.dumps(c["input"], ensure_ascii=False, indent=2), 2500), "```", ""]
        elif t == "result":
            out += ["---", f"**Fin:** {e.get('subtype')}, {e.get('num_turns')} turnos, "
                           f"{e.get('duration_ms', 0) / 1000:.0f} s, costo US$ {e.get('total_cost_usd', 0):.2f}"]
    destino = ruta.with_suffix(".md")
    destino.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(destino)


if __name__ == "__main__":
    for r in sys.argv[1:]:
        main(r)

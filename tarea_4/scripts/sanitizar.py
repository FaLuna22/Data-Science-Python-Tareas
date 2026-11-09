"""Oculta información personal o de la cuenta en las transcripciones antes de publicarlas.

    uv run scripts/sanitizar.py evidencias_ia

- En el evento init deja solo las skills del proyecto (*-enaho) y los servidores MCP; quita plugins, rutas y sockets.
- Reemplaza en todo el texto los identificadores de organización/cuenta, correos y rutas temporales de la sesión.
"""
import json
import re
import sys
from pathlib import Path

PROYECTO = ("limpiando-enaho", "graficando-enaho", "mapeando-enaho")
QUITAR = ("plugins", "agents", "messaging_socket_path", "scratchpad_path", "startup_timing", "capabilities",
          "terminal_slash_commands", "memory_paths")
PATRONES = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z.]{2,}"), "[correo oculto]"),
    (re.compile(r"/root/\.claude/plugins/[^\s\"']+"), "[ruta de plugin oculta]"),
    (re.compile(r"/tmp/claude-0/[^\s\"']*?scratchpad"), "[scratchpad]"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "[id]"),
    (re.compile(r"(sk-ant-|ghp_|gho_|github_pat_)[A-Za-z0-9_-]+"), "[secreto oculto]"),
]


def limpiar_texto(s):
    for p, r in PATRONES:
        s = p.sub(r, s)
    return s


def limpiar_evento(e):
    if e.get("type") == "system" and e.get("subtype") == "init":
        for k in QUITAR:
            e.pop(k, None)
        for k in ("skills", "slash_commands"):
            if k in e:
                e[k] = [s for s in e[k] if s in PROYECTO or s.startswith("mcp__bcrp")]
        e["tools"] = [t for t in e.get("tools", []) if ":" not in t]
    return e


def main(carpeta):
    for f in Path(carpeta).rglob("*"):
        if f.suffix == ".jsonl":
            out = []
            for linea in f.read_text(encoding="utf-8").splitlines():
                try:
                    out.append(json.dumps(limpiar_evento(json.loads(linea)), ensure_ascii=False))
                except json.JSONDecodeError:
                    out.append(linea)
            f.write_text(limpiar_texto("\n".join(out)) + "\n", encoding="utf-8")
        elif f.suffix in (".md", ".txt", ".stderr"):
            f.write_text(limpiar_texto(f.read_text(encoding="utf-8")), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "evidencias_ia")

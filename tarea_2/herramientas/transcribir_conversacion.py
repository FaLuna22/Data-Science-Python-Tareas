"""Convierte la exportación de la sesión de Claude Code (transcript.jsonl) en un Markdown legible y seudonimizado.

    python tarea_2/herramientas/transcribir_conversacion.py ruta/transcript.jsonl ruta/seudonimos.json salida.md

Qué incluye: cada mensaje del usuario, cada respuesta de Claude y, para cada herramienta que usó, su nombre y una
línea con lo que hizo (descripción o comando abreviado). Los resultados de las herramientas se omiten: son largos
y traen texto de fuentes externas (por ejemplo, los nombres de las personas entrevistadas antes de seudonimizar).

Qué oculta: los nombres de personas particulares de la lista de seudónimos (con variantes de tildes), correos
electrónicos y los avisos internos de la aplicación (<system-reminder>, notificaciones de tareas en segundo plano).
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

OMITIR_HERRAMIENTAS = {"mcp__ccd_turn__update_plan", "mcp__ccd_turn__wrap_up", "ToolSearch", "TaskStop"}
CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def sin_tildes(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def patron(nombre: str) -> re.Pattern:
    """Patrón que acepta el nombre con o sin tildes y con s/z intercambiables (Vásquez, Vázquez, Vasquez)."""
    letras = []
    for c in sin_tildes(nombre):
        base = {"a": "[aáà]", "e": "[eéè]", "i": "[iíì]", "o": "[oóò]", "u": "[uúùü]", "s": "[sz]", "z": "[sz]"}
        letras.append(base.get(c.lower(), re.escape(c)) if c != " " else r"\s+")
    return re.compile(r"(?<!\w)" + "".join(letras) + r"(?!\w)", re.I)


def reemplazos(seudonimos: dict) -> list:
    pares = [(patron(n), s) for n, s in seudonimos.items()]
    # variantes y fragmentos que aparecieron en la conversación (por ejemplo, en patrones de búsqueda con grep)
    extras = {"Elena Durán": "PERSONA_1", "Elsa": "PERSONA_3", "Barrientos": "PERSONA_3", "Rientos": "PERSONA_3",
              "Isabel": "PERSONA_2", "Coronado": "PERSONA_5", "Mérida": "PERSONA_6", "Elberuf": "PERSONA_7",
              "Karine": "PERSONA_7", "Dosgrame": "PERSONA_8", "Carlos Ramírez": "PERSONA_9", "Rojas Prada": "PERSONA_10"}
    pares += [(patron(n), s) for n, s in extras.items()]
    pares.append((re.compile(r"Edgardo(?!\s+Rebagliati)", re.I), "PERSONA_10"))  # el hospital Edgardo Rebagliati se queda
    pares.append((re.compile(r"\bdur\[a[áa]\]n\b|\bv\[a[áa]\]\[sz\]quez\b|\bram\[i[íi]\]rez\b|\bm\[e[ée]\]rida\b", re.I), "…"))
    pares.sort(key=lambda p: -len(p[0].pattern))  # primero los nombres completos
    return pares


def limpiar(texto: str, pares: list) -> str:
    texto = re.sub(r"<system-reminder>.*?</system-reminder>", "", texto, flags=re.S)
    texto = CORREO.sub("[correo]", texto)
    for p, s in pares:
        texto = p.sub(s, texto)
    return texto.strip()


def resumen_herramienta(nombre: str, entrada: dict) -> str:
    if nombre in ("Bash", "PowerShell"):
        cmd = entrada.get("command", "").strip().splitlines()[0][:160]
        return f"{entrada.get('description', '')} — `{cmd}`"
    if nombre in ("Write", "Edit", "Read"):
        return Path(entrada.get("file_path", "")).name
    if nombre == "AskUserQuestion":
        return " / ".join(q["question"] for q in entrada.get("questions", []))
    if nombre.startswith("mcp__Claude_Browser__"):
        return entrada.get("action_summary") or entrada.get("url") or entrada.get("action") or entrada.get("query", "")
    return ", ".join(f"{k}={str(v)[:60]}" for k, v in entrada.items() if k not in ("content", "new_string", "old_string"))[:200]


def main(transcript: str, seudo: str, salida: str):
    pares = reemplazos(json.loads(Path(seudo).read_text(encoding="utf-8")))
    lineas = ["# Conversación de desarrollo con Claude Code · Tarea 2", "",
              "Exportada de la aplicación de escritorio de Claude Code y convertida con "
              "`herramientas/transcribir_conversacion.py`. Nombres de personas particulares seudonimizados "
              "(`PERSONA_n`), correos ocultos y resultados de herramientas omitidos.", ""]
    respuestas = {}
    eventos = [json.loads(l) for l in open(transcript, encoding="utf-8")]
    for d in eventos:  # respuestas del usuario a AskUserQuestion
        if d.get("type") == "user" and isinstance(d.get("message", {}).get("content"), list):
            for b in d["message"]["content"]:
                if b.get("type") == "tool_result" and "answered" in str(b.get("content", "")):
                    respuestas[b["tool_use_id"]] = str(b["content"])[:600]
    vistos = set()
    for d in eventos:
        adjunto = d.get("attachment") or {}
        if d.get("type") == "attachment" and adjunto.get("type") == "queued_command":  # mensaje enviado a mitad de un turno
            if str(adjunto.get("prompt", "")).lstrip().startswith(("<task-notification", "[SYSTEM", "<")):
                continue  # avisos automáticos de la aplicación, no mensajes del usuario
            hora = d.get("timestamp", "")[:16].replace("T", " ")
            lineas += [f"## Usuario (durante el turno) · {hora} UTC", "", limpiar(adjunto.get("prompt", ""), pares), ""]
            continue
        if d.get("type") not in ("user", "assistant") or d.get("isMeta") or d.get("isSidechain"):
            continue
        if d.get("uuid") in vistos:
            continue
        vistos.add(d.get("uuid"))
        hora = d.get("timestamp", "")[:16].replace("T", " ")
        contenido = d["message"]["content"]
        if d["type"] == "user" and isinstance(contenido, list) and all(b.get("type") == "text" for b in contenido):
            contenido = "\n\n".join(b["text"] for b in contenido)  # mensaje escrito en varios bloques de texto
        if d["type"] == "user" and isinstance(contenido, str):
            texto = limpiar(contenido, pares)
            if texto and not texto.startswith(("[SYSTEM NOTIFICATION", "<task-notification", "Tool loaded", "[Image")):
                lineas += [f"## Usuario · {hora} UTC", "", texto, ""]
            continue
        if d["type"] != "assistant":
            continue
        for b in contenido:
            if b.get("type") == "text" and b.get("text", "").strip():
                lineas += [f"**Claude** · {hora} UTC", "", limpiar(b["text"], pares), ""]
            elif b.get("type") == "tool_use" and b["name"] not in OMITIR_HERRAMIENTAS:
                nombre = b["name"].replace("mcp__Claude_Browser__", "navegador:").replace("mcp__ccd_", "app:")
                lineas.append(f"> 🔧 `{nombre}`: {limpiar(resumen_herramienta(b['name'], b.get('input', {})), pares)}")
                if b["id"] in respuestas:
                    lineas.append(f">   → respuesta: {limpiar(respuestas[b['id']], pares)}")
                lineas.append("")
    Path(salida).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"{salida}: {len(lineas)} líneas")


if __name__ == "__main__":
    main(*sys.argv[1:4])

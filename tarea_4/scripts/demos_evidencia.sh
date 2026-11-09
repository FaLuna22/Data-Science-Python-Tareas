#!/usr/bin/env bash
# Demos de evidencia: skills activadas por lenguaje natural y recurso/prompt del MCP desde Claude Code (claude -p).
# Uso (desde tarea_4/):  bash scripts/demos_evidencia.sh
set -u
H=(--model sonnet --output-format stream-json --verbose --strict-mcp-config --mcp-config .mcp.json
   --allowedTools "mcp__bcrp" "Skill" "Bash(uv run:*)" "Bash(ls:*)" "Read" "Glob" "Grep")
# Skills: un pedido en lenguaje natural, sin nombrar la skill (la base limpia no existe: debe limpiar primero)
claude -p "Haz un mapa de la pobreza monetaria por departamento con ENAHO 2024." "${H[@]}" \
  > evidencias_ia/skills/demo_mapa_lenguaje_natural.jsonl 2>&1
claude -p "Grafica la pobreza urbana y rural del Perú en 2024 con la ENAHO." "${H[@]}" \
  > evidencias_ia/skills/demo_grafico_lenguaje_natural.jsonl 2>&1
claude -p "/limpiando-enaho 2024" "${H[@]}" > evidencias_ia/skills/demo_invocacion_directa_limpiando.jsonl 2>&1
# MCP: recurso con @ y prompt con /
claude -p "@bcrp:bcrp://serie/PN01273PM ¿Desde cuándo hay datos de esta serie y con qué frecuencia?" "${H[@]}" \
  > evidencias_ia/mcp/demo_recurso.jsonl 2>&1
claude -p "/mcp__bcrp__informe inflación de alimentos" "${H[@]}" > evidencias_ia/mcp/demo_prompt_informe.jsonl 2>&1
claude -p "¿Cuál fue la inflación de Lima a 12 meses en setiembre de 2026? Cita el código de la serie y la fuente." \
  "${H[@]}" > evidencias_ia/mcp/demo_pregunta_bcrp.jsonl 2>&1
for f in evidencias_ia/skills/demo_*.jsonl evidencias_ia/mcp/demo_*.jsonl; do uv run scripts/transcribir.py "$f"; done

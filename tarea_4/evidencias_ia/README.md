# Evidencias del uso de IA

Toda la tarea se desarrolló con **Claude Code** en una sesión en la nube, sobre el repositorio
`FaLuna22/Data-Science-Python-Tareas`, rama `claude/github-issue-201-wyc5cb`. Cada vez que el agente usó el MCP o las
Skills, la ejecución se guardó completa con `claude -p --output-format stream-json`. Cada transcripción está en dos
formatos:

- `.jsonl`: la exportación completa, con instrucciones, llamadas a herramientas, resultados y respuesta final.
- `.md`: la misma transcripción en versión legible, generada con `scripts/transcribir.py`.

Antes de publicar se pasó `scripts/sanitizar.py`. Oculta correos, IDs de cuenta u organización, rutas de plugins y
secretos, y deja en el evento `init` solo las skills y el MCP del proyecto. No se usaron claves de API: el servidor del
BCRP no las necesita y `.mcp.json` no contiene ninguna.

## Índice

| Carpeta | Archivo | Qué muestra |
|---|---|---|
| `mcp/` | [`demo_pregunta_bcrp.md`](mcp/demo_pregunta_bcrp.md) | Pregunta en lenguaje natural respondida con `buscar_series` → `serie` (código, periodo y fuente) |
| `mcp/` | [`demo_prompt_informe.md`](mcp/demo_prompt_informe.md) | El prompt MCP `/mcp__bcrp__informe` usando `buscar_series`, `resumen`, `correlacion` y `graficar_serie` |
| `mcp/` | [`demo_recurso_lectura.md`](mcp/demo_recurso_lectura.md) | El recurso `bcrp://serie/PN01273PM` leído con `ReadMcpResourceTool` |
| `mcp/` | [`demo_recurso.md`](mcp/demo_recurso.md) | Intento con la mención `@bcrp:…`: en modo `-p` no se resolvió y el agente usó herramientas |
| `mcp/` | [`recurso_y_prompt_cliente_fastmcp.txt`](mcp/recurso_y_prompt_cliente_fastmcp.txt) | Herramientas, recurso y prompt listados y leídos con el cliente FastMCP |
| `skills/` | [`demo_mapa_lenguaje_natural.md`](skills/demo_mapa_lenguaje_natural.md) | *«Haz un mapa de la pobreza monetaria por departamento con ENAHO 2024.»* → `Skill: mapeando-enaho` → `Skill: limpiando-enaho` (no existía la base) → mapa de 25 departamentos |
| `skills/` | [`demo_grafico_lenguaje_natural.md`](skills/demo_grafico_lenguaje_natural.md) | *«Grafica la pobreza urbana y rural…»* → `Skill: graficando-enaho` |
| `skills/` | [`demo_invocacion_directa_limpiando.md`](skills/demo_invocacion_directa_limpiando.md) | Invocación directa `/limpiando-enaho 2024` y sus validaciones |
| `desarrollo/` | [`sesion_desarrollo.md`](desarrollo/sesion_desarrollo.md) | La conversación completa de desarrollo con Claude Code, exportada con `/export` y sanitizada |
| `integracion/` | [`prompt_integracion.md`](integracion/prompt_integracion.md) | La instrucción de la ejecución integrada |
| `integracion/` | [`ejecucion_integrada.md`](integracion/ejecucion_integrada.md) | **La ejecución que vale:** 4 herramientas MCP (`buscar_series`, `resumen`, `correlacion`, `graficar_serie`) y 3 skills (`mapeando-enaho`, `limpiando-enaho`, `graficando-enaho`) en una sola corrida, que termina en `informes/borrador_agente.md` |
| `integracion/` | [`intento1_sin_skill_tool.md`](integracion/intento1_sin_skill_tool.md) | Primer intento: usó el MCP, pero leyó los `SKILL.md` con `cat` en vez de activar las skills. Por eso se repitió |
| `evaluacion/` | `A_<id>.md`, `B_<id>.md` | Las 20 llamadas de la evaluación (10 preguntas × 2 modos) |

## Bitácora del desarrollo (sesión de Claude Code, 8–9 nov. 2026)

Todos los pasos los hizo Claude Code a pedido del estudiante (*«Nos piden el siguiente assignment: issue 201»*). El
estudiante revisó las cifras y los archivos.

| # | Paso | Resultado |
|---|---|---|
| 1 | Leer el enunciado (issue 201) y los materiales de las sesiones 04 (MCP) y 16 (Skills) del repositorio del curso | Requisitos, rúbrica y estructura de `tarea_4/` |
| 2 | Comprobar la red (INEI, BCRP) y `claude -p`; bajar los módulos 34 y 02 y el GeoJSON | `datos/` (ignorado por git) |
| 3 | Completar `mcp/server.py`: `serie`, `resumen`, `correlacion`, `graficar_serie`, el recurso y el prompt. Copiar las 8 pruebas originales sin cambios y agregar 2 | `uv run pytest` → 10 passed |
| 4 | Escribir `limpiar.py`. Revisar las etiquetas de la sumaria para definir el grupo 1 (alimentos). Agregar las validaciones | 108,664 residentes, 27.53 % / 27.58 %, 25 departamentos |
| 5 | Corregir un error: `condicion` y `departamento_nombre` se creaban después de guardar el parquet. Corregir la nota de redondeo (27.53 % redondea a 27.5 %) | Gráficos por departamento sin error |
| 6 | Escribir `graficar.py`, `mapear.py` y los `SKILL.md`. Revisar a ojo el mapa y un gráfico | 25/25 departamentos; diferencia máxima con la sesión 16: 0.5 pts |
| 7 | Primera ejecución integrada: no activó `Skill`. Se repitió pidiendo explícitamente la herramienta | Corrida válida con 4 herramientas MCP y 3 skills |
| 8 | Fijar las respuestas esperadas con `verdades.py` (API del BCRP directa y recálculo por hogar) **antes** de evaluar | `evaluacion/verdades.json` |
| 9 | Correr la evaluación: modo A en una carpeta vacía sin herramientas; modo B en una copia del proyecto sin las respuestas | A 3/10, B 9/10 |
| 10 | Verificar a mano 5 cifras (`salidas/verificacion_manual.txt`), cruzar BCRP × ENAHO (`scripts/cruce.py`) y escribir el informe, `comparacion.md` y el README | Entregables |

> **Conversación completa de desarrollo:** [`desarrollo/sesion_desarrollo.md`](desarrollo/sesion_desarrollo.md).
> Es la exportación (`/export` de Claude Code) de la sesión con la que se construyó todo el proyecto: instrucciones del
> estudiante, pasos del agente, archivos escritos, comandos ejecutados, correcciones y respuestas. Los comandos aparecen
> resumidos («Ran N shell commands»), así que su detalle está en las transcripciones `.jsonl` de las demás carpetas. Se
> le pasó `scripts/sanitizar.py`, que reemplazó los IDs de cuenta por `[id]`.

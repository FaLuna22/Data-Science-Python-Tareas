# Evidencias del uso de IA

La tarea se desarrolló con **Claude Code** (aplicación de escritorio) en una sola sesión, entre el 26 de octubre y el
9 de noviembre de 2026.

| Archivo | Qué muestra |
|---|---|
| `01.png` | Inicio de la conversación: el enlace al issue y las tres decisiones iniciales (repositorio, LLM y fuentes) |
| `02.png` | Instrucciones para las referencias manuales y la auditoría humana del LLM |
| `03.png` | Resultados finales de la evaluación (CER, WER y acuerdo LLM-humano) |
| [`conversacion_claude_code.md`](conversacion_claude_code.md) | La conversación completa en orden cronológico: cada mensaje, cada respuesta y cada herramienta usada |

`conversacion_claude_code.md` se generó a partir de la exportación de la sesión con
[`herramientas/transcribir_conversacion.py`](../herramientas/transcribir_conversacion.py). El script:

- reemplaza los nombres de personas particulares por los mismos seudónimos `PERSONA_n` del corpus;
- oculta correos electrónicos y los avisos internos de la aplicación;
- omite los resultados de las herramientas: son largos y traen texto de fuentes externas sin seudonimizar.

No se usaron claves de API: todos los modelos (PaddleOCR, EasyOCR, Whisper, Qwen3-ASR y Qwen2.5) corrieron en local.

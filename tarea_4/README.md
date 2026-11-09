# Tarea 4: agente de investigación socioeconómica del Perú (BCRP + ENAHO 2024)

> **Pregunta de investigación:** ¿Qué tan expuestos estuvieron los hogares pobres del Perú a la inflación de alimentos?
> Se contrasta la inflación de alimentos y bebidas del BCRP (2022–2024) con la pobreza monetaria y el peso del gasto en
> alimentos de la ENAHO 2024, por área, condición de pobreza y departamento.

**Informe final:** [`informes/informe_final.md`](informes/informe_final.md)

| Resultado | Valor |
|---|---|
| Pruebas del servidor MCP | **10 passed** (8 originales + 2 propias), en [`salidas/pruebas_mcp.txt`](salidas/pruebas_mcp.txt) |
| Pobreza monetaria nacional 2024 | **27.5 %** (27.53 % con personas y `facpob07`; 27.58 % con hogares; INEI 27.6 %) |
| Residentes habituales | **108,664** |
| Unidades territoriales en el mapa | **25 / 25** (Lima y Callao separados) |
| Pobreza urbana / rural | 24.7 % / 39.4 % |
| Evaluación: aciertos sin MCP/Skills → con MCP/Skills | **3/10 → 9/10** ([`evaluacion/comparacion.md`](evaluacion/comparacion.md)) |
| Ejecución integrada | 4 herramientas MCP + 3 skills en una sola corrida de Claude Code ([`evidencias_ia/integracion/ejecucion_integrada.md`](evidencias_ia/integracion/ejecucion_integrada.md)) |

**Respuesta corta.** La inflación de alimentos llegó a 13.2 % en febrero de 2023. Los hogares en pobreza extrema
gastan el 49 % de su presupuesto en alimentos y los no pobres, el 33 %. Por eso el mismo choque les encareció el costo
de vida unos 6.2 puntos, frente a 4.2 en los no pobres. La pobreza y el peso de los alimentos se concentran en los
mismos departamentos (r = 0.44). En 2024 la inflación de alimentos bajó a 1.25 % y esa exposición cayó a menos de
1 punto.

---

## 1. Objetivo

Construir un agente en Claude Code que responda preguntas sobre la situación socioeconómica del Perú con datos
oficiales. Las cifras tienen que venir de herramientas que se puedan volver a correr, no de la memoria del modelo. El
agente combina:

- un servidor MCP con las series del BCRP;
- tres Skills que limpian, grafican y mapean la ENAHO 2024 del INEI.

## 2. Arquitectura

```text
           pregunta en lenguaje natural
                       │
                ┌──────▼───────┐
                │  Claude Code │  plan → herramientas → verificación → informe
                └──┬────────┬──┘
     MCP (stdio)   │        │   Skills (.claude/skills/)
 ┌─────────────────▼──┐  ┌──▼─────────────────────────────────────────────┐
 │ mcp/server.py      │  │ limpiando-enaho → salidas/personas_2024.parquet│
 │  buscar_series     │  │                   salidas/validacion.txt       │
 │  serie / resumen   │  │                   salidas/indicadores.csv      │
 │  correlacion  *    │  │ graficando-enaho → figuras/*.png               │
 │  graficar_serie *  │  │ mapeando-enaho   → mapas/*.png (25 deptos)     │
 │  bcrp://serie/{c}  │  └──────────▲─────────────────────────────────────┘
 │  prompt informe    │             │ microdatos 966-Modulo34/02 (datos/)
 └────────┬───────────┘             │ GeoJSON departamental (FIRST_IDDP)
          │ API pública del BCRP    │
          ▼                         │
 estadisticas.bcrp.gob.pe      proyectos.inei.gob.pe
                       │
             scripts/cruce.py  → salidas/cruce_exposicion.csv (BCRP × ENAHO)
```

`*` = herramientas propias. Todas las cuentas se hacen en Python, dentro de las herramientas o de los scripts. El
modelo no calcula a mano.

## 3. Servidor MCP del BCRP ([`mcp/server.py`](mcp/server.py))

| Tipo | Nombre | Qué hace |
|---|---|---|
| Herramienta | `buscar_series(texto, frecuencia, limite)` | Busca entre las ~17 mil series del catálogo oficial por palabras |
| Herramienta | `serie(codigo, desde, hasta)` | Descarga los datos, convierte los periodos (`Ene.2025`, `01.Oct.26`, `T1.25`, `Set`) a formato ISO, omite `n.d.` y devuelve la URL de la fuente. Tiene reintentos y caché en disco |
| Herramienta | `resumen(codigo, desde, hasta)` | Primero, último, cambio, variación %, promedio, máximo y mínimo (con su periodo) |
| Herramienta propia | `correlacion(codigo_a, codigo_b, desde, hasta)` | Alinea los periodos de dos series, descarta los faltantes (e informa cuántos), calcula la r de Pearson y el r² y rechaza frecuencias distintas. Aclara que es una asociación, no causalidad |
| Herramienta propia | `graficar_serie(codigo, desde, hasta, archivo, unidad)` | PNG con título, periodo, unidad y fuente en `figuras/` |
| Recurso | `bcrp://serie/{codigo}` | Ficha de la serie: nombre, categoría, frecuencia, inicio, última actualización, URL de consulta y de la API |
| Prompt | `informe(tema)` | Pide un informe que cite el código, el periodo y la URL de cada cifra, y que avise si una herramienta falla |

**Pruebas** ([`mcp/test_server.py`](mcp/test_server.py)): las 8 originales de la sesión 04 están sin cambios. Se
agregaron 2 para `correlacion`:

- `test_correlacion_de_una_serie_consigo_misma_es_uno`: una serie consigo misma da r = 1.
- `test_correlacion_alinea_periodos_y_rechaza_frecuencias_distintas`: alinea 36 meses y lanza un error claro si se
  mezcla una serie mensual con una diaria.

## 4. Skills de la ENAHO ([`.claude/skills/`](.claude/skills/))

| Skill | Qué hace | Script | Salidas |
|---|---|---|---|
| [`limpiando-enaho`](.claude/skills/limpiando-enaho/SKILL.md) | Lee los módulos 34 y 02 con las llaves como texto y normaliza nombres. Filtra a los residentes habituales y une personas con hogares (`validate="m:1"`). Construye pobreza, departamento, área, sexo, edad y peso de los alimentos, pondera con `facpob07` y valida. Si falla una validación esencial, se detiene | `scripts/limpiar.py` | `salidas/personas_2024.parquet`, `salidas/validacion.txt`, `salidas/indicadores.csv` |
| [`graficando-enaho`](.claude/skills/graficando-enaho/SKILL.md) | Traduce el pedido a un gráfico: `area`, `sexo`, `edad`, `departamento`, `alimentos` o `todos`. Barras ponderadas desde cero, con el valor escrito, el promedio nacional, el título con el hallazgo y la fuente | `scripts/graficar.py` | `figuras/pobreza_*.png`, `figuras/peso_alimentos_condicion.png` |
| [`mapeando-enaho`](.claude/skills/mapeando-enaho/SKILL.md) | Mapa coroplético que une `ubigeo[:2]` con `FIRST_IDDP` (`validate="1:1"`). Exige 25 departamentos con dato y Lima y Callao separados. Usa una escala `Reds` desde 0, con la unidad en la leyenda, y se compara con la referencia de la sesión 16 | `scripts/mapear.py` | `mapas/pobreza_departamento.png`, `mapas/peso_alimentos_departamento.png`, `salidas/mapa_*.csv` |

Las skills de gráficos y mapas dicen: «Si no existe `salidas/personas_2024.parquet`, usa primero la skill
`limpiando-enaho`». En la demo [`evidencias_ia/skills/demo_mapa_lenguaje_natural.md`](evidencias_ia/skills/demo_mapa_lenguaje_natural.md),
el pedido *«Haz un mapa de la pobreza monetaria por departamento con ENAHO 2024»* activó `mapeando-enaho` y luego
`limpiando-enaho`, sin que se nombrara ninguna de las dos.

## 5. Fuentes de datos

| Fuente | Enlace | Uso |
|---|---|---|
| INEI, ENAHO 2024, módulo 34 (sumaria) | https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip | Pobreza, factor del hogar y gasto |
| INEI, ENAHO 2024, módulo 02 (miembros) | https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip | Residentes, sexo, edad y `facpob07` |
| Límites departamentales (GeoJSON) | https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson | Mapa |
| BCRP, series estadísticas | https://estadisticas.bcrp.gob.pe/estadisticas/series/ (API `…/series/api/<codigo>/json/<desde>/<hasta>`) | Inflación, tasa de referencia, PBI y tipo de cambio |
| Referencia de pobreza departamental (sesión 16) | [`.claude/skills/mapeando-enaho/referencias/pobreza_departamento_2024.csv`](.claude/skills/mapeando-enaho/referencias/pobreza_departamento_2024.csv) | Validar el mapa |

Los microdatos no se suben al repositorio: la carpeta `datos/` está en `.gitignore`.

## 6. Instalación con `uv`

```bash
git clone https://github.com/FaLuna22/Data-Science-Python-Tareas
cd Data-Science-Python-Tareas/tarea_4
uv sync                       # Python ≥ 3.11: fastmcp 4, pandas, pyarrow, geopandas, matplotlib, pytest

mkdir -p datos && cd datos    # microdatos (≈ 22 MB) y GeoJSON
curl -LO https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip
curl -LO https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip
unzip -o 966-Modulo34.zip && unzip -o 966-Modulo02.zip
curl -LO https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson
cd ..
```

La primera llamada al MCP baja el catálogo del BCRP (unos 7 MB) a `datos/catalogo_bcrp.csv`.

## 7. Conectar el MCP a Claude Code

El servidor ya está declarado en [`.mcp.json`](.mcp.json), que no contiene claves:

```json
{ "mcpServers": { "bcrp": { "type": "stdio", "command": "uv", "args": ["run", "mcp/server.py"] } } }
```

Para registrarlo desde cero:

```bash
claude mcp add --scope project bcrp -- uv run mcp/server.py
```

Abran `claude` en `tarea_4/`, acepten el servidor del proyecto y verifiquen con `/mcp`.

- **Recurso:** `@bcrp:bcrp://serie/PN01273PM`.
- **Prompt:** `/mcp__bcrp__informe inflación`.
- **Skills:** `/limpiando-enaho 2024`, `/graficando-enaho area`, `/mapeando-enaho`, o en lenguaje natural.

## 8. Reproducir el procesamiento y las pruebas

```bash
uv run pytest -q                                                      # 10 passed
uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024  # validacion.txt + indicadores.csv
uv run .claude/skills/graficando-enaho/scripts/graficar.py todos
uv run .claude/skills/mapeando-enaho/scripts/mapear.py
uv run .claude/skills/mapeando-enaho/scripts/mapear.py --indicador alimentos
uv run scripts/cruce.py                                               # cruce BCRP × ENAHO
uv run evaluacion/verdades.py                                         # respuestas esperadas (independientes)
uv run evaluacion/evaluar.py                                          # 10 preguntas × 2 modos → resultados.csv
```

## 9. Resultados de la evaluación

Detalle en [`evaluacion/comparacion.md`](evaluacion/comparacion.md) y [`evaluacion/resultados.csv`](evaluacion/resultados.csv).

| Modo | Aciertos | Errores | «No sé» | Segundos promedio |
|---|---:|---:|---:|---:|
| A: sin MCP ni Skills (sin herramientas, carpeta vacía) | 3 | 1 | 6 | 7.2 |
| B: con MCP y Skills (copia del proyecto sin las respuestas) | 9 | 0 | 1 | 14.0 |

Las preguntas son 4 del BCRP, 4 de la ENAHO y 2 combinadas. Las respuestas esperadas se fijaron antes con la API del
BCRP y con las cifras del INEI y un recálculo independiente ([`evaluacion/verdades.py`](evaluacion/verdades.py)).

## 10. Limitaciones y problemas encontrados

- **El IPC es de Lima Metropolitana.** Aplicarlo a hogares rurales y de otros departamentos es un supuesto. La ENAHO
  es de 2024 y la inflación cubre 2022–2024 (ver la sección 6 del informe).
- **Ponderación.** La pobreza con personas y `facpob07` (27.53 %) difiere en centésimas de la del método del INEI con
  hogares (27.58 %). Los departamentos difieren hasta 0.5 pts de la referencia de la sesión 16 (por ejemplo, Huánuco
  39.47 % frente a 39.0 %).
- **La primera corrida integrada no activó las skills con `Skill`.** El agente leyó los `SKILL.md` con `cat` y corrió
  los scripts directamente. Se repitió pidiendo explícitamente la herramienta `Skill`. Las dos corridas están en
  `evidencias_ia/integracion/`.
- **En la evaluación (modo B) las preguntas ENAHO se respondieron leyendo `salidas/indicadores.csv`, sin reactivar
  las skills.** Ese archivo es la salida validada de `limpiando-enaho`. La pregunta `comb_gasto_usd` quedó sin
  respuesta porque el agente intentó correr `python3` fuera de lo permitido (`uv run`).
- **En modo `-p` la mención `@bcrp:bcrp://…` no se resolvió.** El recurso sí se leyó con `ReadMcpResourceTool`
  ([`evidencias_ia/mcp/demo_recurso_lectura.md`](evidencias_ia/mcp/demo_recurso_lectura.md)) y con el cliente FastMCP
  ([`evidencias_ia/mcp/recurso_y_prompt_cliente_fastmcp.txt`](evidencias_ia/mcp/recurso_y_prompt_cliente_fastmcp.txt)).
- **La API del BCRP limita los pedidos seguidos.** El servidor reintenta y guarda en caché lo que ya bajó
  (`datos/cache_bcrp/`).

## 11. Ejemplo de una ejecución completa

```bash
rm -f salidas/personas_2024.parquet           # para que se vea la coordinación entre skills
claude -p "$(cat evidencias_ia/integracion/prompt_integracion.md)" --model sonnet \
  --strict-mcp-config --mcp-config .mcp.json --output-format stream-json --verbose \
  --allowedTools "mcp__bcrp" "Skill" "Bash(uv run:*)" "Bash(ls:*)" "Bash(cat:*)" Read Write Edit Glob Grep \
  > evidencias_ia/integracion/ejecucion_integrada.jsonl
uv run scripts/transcribir.py evidencias_ia/integracion/ejecucion_integrada.jsonl
```

En esa corrida ([`ejecucion_integrada.md`](evidencias_ia/integracion/ejecucion_integrada.md)) el agente hizo esto:

1. Escribió un plan.
2. Llamó `buscar_series` (×2), `resumen` (×2), `correlacion` y `graficar_serie`.
3. Activó `mapeando-enaho`. Como no existía la base limpia, activó `limpiando-enaho`, que corrió las validaciones.
4. Generó el mapa y activó `graficando-enaho` (gráficos de alimentos y de área).
5. Contrastó contra `validacion.txt` y la referencia de la sesión 16.
6. Escribió [`informes/borrador_agente.md`](informes/borrador_agente.md).

## 12. Evidencia del uso de IA

Todo está en [`evidencias_ia/`](evidencias_ia/README.md), con una subcarpeta por parte:

| Subcarpeta | Contenido |
|---|---|
| [`README.md`](evidencias_ia/README.md) | Índice y bitácora cronológica de la sesión de desarrollo con Claude Code. La exportación completa de esa sesión la agrega el estudiante (ver la nota al final del índice) |
| `mcp/` | Demos del MCP |
| `skills/` | Activación de las skills |
| `integracion/` | Las dos corridas integradas |
| `evaluacion/` | Las 20 transcripciones de la evaluación |

Cada transcripción está como `.jsonl` (exportación completa de `claude -p --output-format stream-json`) y como `.md`
legible. Se ocultaron correos, tokens y rutas de credenciales.

## Estructura

```text
tarea_4/
├── README.md  pyproject.toml  uv.lock  .mcp.json  .gitignore
├── mcp/                server.py, test_server.py
├── .claude/skills/     limpiando-enaho/ (SKILL.md, reference.md, scripts/limpiar.py)
│                       graficando-enaho/ (SKILL.md, scripts/graficar.py)
│                       mapeando-enaho/ (SKILL.md, scripts/mapear.py, referencias/)
├── scripts/            cruce.py, transcribir.py, demos_evidencia.sh
├── datos/              microdatos del INEI y caché del BCRP (ignorado por git)
├── salidas/            validacion.txt, indicadores.csv, pruebas_mcp.txt, verificacion_manual.txt, cruce_*, mapa_*
├── figuras/  mapas/
├── evaluacion/         preguntas.csv, verdades.py, evaluar.py, resultados.csv, comparacion.md
├── informes/           informe_final.md, borrador_agente.md (+ intento 1)
└── evidencias_ia/      desarrollo/, mcp/, skills/, integracion/, evaluacion/
```

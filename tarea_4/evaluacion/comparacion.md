# Evaluación: Claude Code sin y con el MCP del BCRP y las Skills de la ENAHO

Se hicieron las mismas 10 preguntas en dos modos, una sesión independiente por pregunta (`claude -p
--no-session-persistence`), con el mismo modelo (Claude Sonnet) y la misma instrucción. El script es
[`evaluar.py`](evaluar.py), los resultados están en [`resultados.csv`](resultados.csv) y la transcripción de cada
llamada en [`../evidencias_ia/evaluacion/`](../evidencias_ia/evaluacion/).

## Diseño

| | Modo A: sin MCP ni Skills | Modo B: con MCP y Skills |
|---|---|---|
| Herramientas habilitadas | Ninguna (`--tools ""`), sin servidores MCP (`--strict-mcp-config`) | `mcp__bcrp` (5 herramientas), `Skill` (las 3 skills del proyecto), `Bash(uv run:*)`, `Read`, `Glob`, `Grep`. Sin `WebSearch` ni `WebFetch` |
| Carpeta de trabajo | Vacía | Copia del proyecto **sin** `evaluacion/`, `informes/` ni `evidencias_ia/`, para que no pueda leer las respuestas esperadas |
| Instrucción | Igual: «Responde con un solo número en "valor"… si no puedes saberlo con certeza, pon null: no estimes… usa las herramientas que tengas» | Igual |
| Salida | JSON validado con `--json-schema`: `valor`, `fuente`, `interpretacion` y, en las combinadas, `comp_bcrp` y `comp_enaho` | Igual |

**Preguntas** ([`preguntas.csv`](preguntas.csv)): 4 del BCRP, 4 de la ENAHO y 2 que combinan ambas fuentes. Las
respuestas esperadas se fijaron **antes** de correr el experimento con [`verdades.py`](verdades.py), sin usar al
agente:

- **BCRP:** consulta directa a la API pública, sin pasar por el MCP.
- **ENAHO:** cifras publicadas por el INEI (27.6 %, 39.3 %, 5.5 %) y la referencia de la sesión 16 (Cajamarca
  45.0 %). Además, un recálculo propio con la sumaria a nivel de hogar (`factor07 × mieperho`), que es un camino
  distinto al de la skill (personas con `facpob07`).

La tolerancia se definió por adelantado:

| Tipo de cifra | Tolerancia |
|---|---|
| Porcentajes del BCRP | 0.05 pts (tasa de referencia: 0.01) |
| Pobreza nacional y extrema (ENAHO) | 0.15 pts |
| Pobreza rural (ENAHO) | 0.2 pts |
| Pobreza de Cajamarca (ENAHO) | 0.3 pts |
| Combinada de exposición | 0.1 pts |
| Combinada de gasto en US$ | 3 % (2.65 US$) |

En la ENAHO, la tolerancia cubre la diferencia entre ponderar personas y ponderar hogares.

**Criterio de las preguntas combinadas.** Se exigen tres cosas:

1. La exactitud del dato BCRP (`comp_bcrp`).
2. La exactitud del dato ENAHO (`comp_enaho`).
3. La coherencia: el valor final tiene que salir de los dos componentes con la fórmula que pide la pregunta.

Si se cumplen las tres, la respuesta es «acierta». Si se cumple alguna, es «parcial».

## Resultados

| Modo | Aciertos | Errores | «No sé» | Segundos promedio (mediana) |
|---|---:|---:|---:|---:|
| A: sin MCP ni Skills | **3 / 10** | 1 | 6 | 7.2 (6.6) |
| B: con MCP y Skills | **9 / 10** | 0 | 1 | 14.0 (12.1) |

| Pregunta | Esperado | A | B | Herramientas que usó B |
|---|---:|---:|---:|---|
| `bcrp_ipc_dic24` inflación 12 m, dic-2024 | 1.9663 | 1.97 ✅ | 1.97 ✅ | `buscar_series`, `serie` |
| `bcrp_alim_dic22` alimentos 12 m, dic-2022 | 12.6439 | null | 12.64 ✅ | `buscar_series`, `serie` |
| `bcrp_ref_dic24` tasa de referencia, dic-2024 | 5.00 | 5.00 ✅ | 5.00 ✅ | `buscar_series`, `serie` |
| `bcrp_pbi_2024` PBI real 2024 | 3.5153 | null | 3.52 ✅ | `buscar_series`, `serie` |
| `enaho_pob_nac` pobreza nacional | 27.6 | 27.60 ✅ | 27.60 ✅ | Bash (`salidas/indicadores.csv`, `validacion.txt`) |
| `enaho_pob_rural` pobreza rural | 39.3 | null | 39.44 ✅ | Bash (`indicadores.csv`) |
| `enaho_pob_ext` pobreza extrema | 5.5 | 5.70 ❌ | 5.50 ✅ | Bash, Read |
| `enaho_cajamarca` pobreza en Cajamarca | 45.0 | null | 44.99 ✅ | Bash (`indicadores.csv`) |
| `comb_exposicion` alimentos × peso | 6.2235 | null | 6.23 ✅ (12.64 × 49.27, coherente) | Bash, `buscar_series`, `resumen`, Read, Grep |
| `comb_gasto_usd` gasto pc pobres en US$ | 88.30 | null | null (TC 3.7582 ✅) | `buscar_series`, `resumen`, Glob, Read; Python bloqueado |

### Preguntas que mejoraron o empeoraron

- **Mejoraron (6):** `bcrp_alim_dic22`, `bcrp_pbi_2024`, `enaho_pob_rural`, `enaho_cajamarca` y `comb_exposicion`
  pasaron de «no sé» a acierto. `enaho_pob_ext` pasó de error (5.7 de memoria) a acierto (5.50).
- **Iguales (4):** las tres que A ya acertaba de memoria (`bcrp_ipc_dic24`, `bcrp_ref_dic24` y `enaho_pob_nac`, que
  son cifras redondas o muy citadas) y `comb_gasto_usd`, que quedó en «no sé» en los dos modos.
- **Empeoraron:** ninguna.

## Principales errores y hallazgos

1. **Sin herramientas, Claude casi no inventa.** De 10 preguntas, en 6 respondió «no sé». En la única que se equivocó
   (pobreza extrema 5.7 % frente a 5.5 %) dijo que la cifra venía «recordada de memoria» y que no pudo verificarla. En
   las dos combinadas intentó llamar a `Bash`, la herramienta estaba deshabilitada y terminó respondiendo «no sé».
2. **Con el MCP, las 4 preguntas del BCRP salen exactas.** En los 4 casos siguió el mismo camino:
   `buscar_series` → `serie`, con el código de la serie en la fuente.
3. **En el modo B, las preguntas ENAHO se respondieron sin activar las skills.** La base limpia y
   `salidas/indicadores.csv` ya existían, así que el agente las leyó con `Bash` (`cat`). Esto es correcto, porque esas
   salidas las produjo la skill `limpiando-enaho` y están validadas. Pero significa que la evaluación mide el valor de
   las **salidas** de las skills más que su activación. La activación se demuestra aparte, en
   `evidencias_ia/skills/` y en la ejecución integrada, donde se borró la base antes de correr.
4. **`comb_gasto_usd` falló por permisos, no por inventar.** El agente obtuvo bien el tipo de cambio con el MCP
   (`PM05242PA` = 3.7582). Pero el gasto per cápita de los pobres (extremos y no extremos juntos) no está precalculado
   en `indicadores.csv`, y para calcularlo intentó correr `python3` directamente, lo que la configuración no permitía
   (solo `uv run`). Respondió `null` y explicó por qué. Habría bastado agregar ese indicador a la skill, o permitir
   `uv run python`.
5. **Diferencia persona/hogar.** En la pobreza rural B dio 39.44 % frente a 39.3 % oficial. Entra en la tolerancia
   (0.2), pero muestra que ponderar personas (`facpob07`) da centésimas distintas que el método del INEI
   (`factor07 × mieperho`). Está documentado en `salidas/validacion.txt`.
6. **Tiempo.** B tarda en promedio el doble (14.0 s frente a 7.2 s) porque busca la serie, la descarga y lee archivos.
   La pregunta combinada más larga tomó 28 s y 14 llamadas a herramientas.

## Conclusión

El MCP y las Skills convierten a Claude de un modelo que sabe que no sabe (3/10, con 6 «no sé») en un agente que
responde con cifras verificables y citadas (9/10). Lo hace sin errores y a cambio de unos 7 segundos más por pregunta.
La mejora se concentra en lo que la memoria no cubre: series poco citadas (inflación de alimentos, PBI por tipo de
gasto), cortes territoriales (Cajamarca, rural) y cruces entre fuentes que exigen calcular.

Para que valga la pena, la herramienta tiene que cubrir el indicador que se pregunta. Cuando falta (`comb_gasto_usd`),
el agente no inventa, pero tampoco responde. Para la ENAHO, la mayor ganancia vino de tener una base limpia y validada
una sola vez, más que de reactivar la skill en cada pregunta.

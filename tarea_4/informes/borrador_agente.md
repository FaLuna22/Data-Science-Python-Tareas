# Borrador (agente): ¿Qué tan expuestos estuvieron los hogares pobres del Perú a la inflación de alimentos?

## 1. Pregunta
¿Qué tan expuestos estuvieron los hogares pobres a la inflación de alimentos? Se contrasta la inflación de alimentos y bebidas de Lima Metropolitana (BCRP, 2022–2024) con la pobreza monetaria y el peso del gasto en alimentos de los hogares (ENAHO 2024), por área, condición de pobreza y departamento.

## 2. Fuentes y método
- **BCRP** (servidor MCP `bcrp`; series mensuales, variación % a 12 meses, Lima Metropolitana):
  - `PN09822PM`: IPC Alimentos y Bebidas.
  - `PN01273PM`: IPC total.
  - Fuente: https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN09822PM/json/2022-1/2024-12 (y la misma ruta con `PN01273PM`).
  - Herramientas usadas: `buscar_series`, `resumen`, `correlacion`, `graficar_serie`.
- **ENAHO 2024** (INEI, módulos 34 y 02; residentes habituales; ponderado con `facpob07`). Se procesó con las skills `limpiando-enaho`, `mapeando-enaho` y `graficando-enaho`.
- Todas las cifras vienen de las herramientas, sin cálculos manuales. Salvo la fila «Rural − Urbana» de la tabla, que reporta el título de la figura (14.7 pts).
- La inflación es solo de Lima Metropolitana. La ENAHO cubre todo el país.

## 3. Hallazgos

| # | Hallazgo | Cifra | Fuente |
|---|---|---|---|
| 1 | La inflación de alimentos fue mayor que la total. Pico de alimentos: 13.16 % (feb-2023). Pico del IPC total: 8.81 % (jun-2022). | Promedio 2022–24: 7.62 % (alimentos) vs 5.51 % (total) | BCRP `PN09822PM`, `PN01273PM` |
| 2 | La inflación de alimentos cerró 2024 en 1.25 % (dic-2024), con un mínimo de 0.69 % en sep-2024. El IPC total cerró en 1.97 %. | 1.25 % vs 1.97 % | BCRP `PN09822PM`, `PN01273PM` |
| 3 | Alimentos y total se movieron casi juntos. | r = 0.976 (R² = 0.953, n = 36) | BCRP `correlacion` `PN09822PM`/`PN01273PM` |
| 4 | Los hogares pobres destinan más de su gasto a alimentos: pobres extremos 49.27 %, pobres no extremos 43.58 %, no pobres 33.26 % (nacional 36.41 %). | Brecha extremos vs no pobres: 16.0 pts (49.27 − 33.26) | `salidas/indicadores.csv`; `figuras/peso_alimentos_condicion.png` |
| 5 | Por área, la pobreza rural supera a la urbana (39.44 % vs 24.74 %; pobreza nacional 27.53 %). El peso de alimentos también: 48.03 % rural vs 33.69 % urbano. | Brecha de pobreza: 14.7 pts | `salidas/indicadores.csv`; `figuras/pobreza_area.png` |
| 6 | Por departamento hay mucha dispersión. Más pobres: Cajamarca 44.99 %, Loreto 42.61 %, Puno 40.42 %. Menos pobres: Ica 5.91 %, Moquegua 10.88 %, Madre de Dios 11.14 %. El peso de alimentos va de 30.25 % (Lima) a 47.05 % (Apurímac). | — | `salidas/mapa_pobreza_departamento.csv`; `salidas/indicadores.csv`; `mapas/pobreza_departamento.png` |

## 4. Figuras
- `figuras/bcrp_inflacion_alimentos.png` (serie `PN09822PM`, % var. 12 meses, 2022-01 a 2024-12)
- `figuras/peso_alimentos_condicion.png`
- `figuras/pobreza_area.png`
- `mapas/pobreza_departamento.png`

## 5. Validación y contraste
- `salidas/validacion.txt`: todas las validaciones esenciales pasan. Hay 108,664 residentes habituales, unión m:1 sin pérdidas y 25 departamentos. La pobreza nacional es 27.53 % (INEI 27.6 %; diferencia −0.07 pts). La pobreza urbana es 24.74 % y la rural 39.44 %.
- Mapa vs referencia de la sesión 16 (`referencias/pobreza_departamento_2024.csv`): 25/25 departamentos con dato. La diferencia máxima es 0.5 pts (Huánuco y Puno, +0.5). Eso es consistente con ponderar personas (`facpob07`) en vez de hogares.

## 6. Interpretación
La inflación de alimentos de Lima fue más alta que la general durante 2022–2023 y convergió a niveles bajos a fines de 2024. Los hogares pobres, sobre todo los extremos y los rurales, gastan una proporción mayor de su presupuesto en alimentos. Por eso un mismo aumento de precios de alimentos pesa más sobre ellos. Esta lectura es una asociación descriptiva, no un efecto causal medido.

## 7. Limitaciones
- El IPC es de Lima Metropolitana. No hay inflación de alimentos por departamento ni por área en estas fuentes. Extrapolarla al ámbito rural o a otras regiones es un supuesto.
- La ENAHO 2024 es un corte transversal. No se cruzó mes a mes con la inflación, ni se midió el efecto en bienestar. Tampoco se ajustó por consumo de autoconsumo o precios regionales.
- La pobreza se pondera por personas (`facpob07`). Los resultados difieren hasta 0.5 pts de la referencia por hogares.
- Los departamentos con pocas observaciones (p. ej. Madre de Dios, n = 2,045) tienen más error muestral. No se calcularon intervalos de confianza.

## 8. Reproducibilidad
```bash
uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024
uv run .claude/skills/mapeando-enaho/scripts/mapear.py --indicador pobreza
uv run .claude/skills/graficando-enaho/scripts/graficar.py alimentos
uv run .claude/skills/graficando-enaho/scripts/graficar.py area
```
Series BCRP: `PN09822PM`, `PN01273PM` (2022-01 a 2024-12) vía MCP `bcrp`.

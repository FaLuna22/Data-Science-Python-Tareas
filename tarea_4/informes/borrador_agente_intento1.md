# Borrador (agente): ¿Qué tan expuestos estuvieron los hogares pobres del Perú a la inflación de alimentos?

## 1. Pregunta
¿Qué tan expuestos estuvieron los hogares pobres del Perú a la inflación de alimentos en 2022–2024? Se contrasta la
inflación de alimentos y bebidas de Lima Metropolitana (BCRP) con la pobreza monetaria y el peso del gasto en
alimentos de los hogares (ENAHO 2024), por área, condición de pobreza y departamento.

## 2. Fuentes y método
- **BCRP** (servidor MCP `bcrp`, series mensuales, 2022-01 a 2024-12, n = 36):
  - `PN09822PM`: IPC Lima Metropolitana, var. % 12 meses, Alimentos y Bebidas.
  - `PN01273PM`: IPC Lima Metropolitana, var. % 12 meses, total.
  - Herramientas usadas: `buscar_series`, `resumen`, `correlacion`, `graficar_serie`. Ninguna falló.
  - URL: `https://estadisticas.bcrp.gob.pe/estadisticas/series/api/<código>/json/2022-1/2024-12`.
- **ENAHO 2024 (INEI, código 966)**, módulos 34 (sumaria) y 02 (miembros), residentes habituales (108,664 personas),
  ponderado con `facpob07`. Se limpió con la skill `limpiando-enaho` (se regeneró `salidas/personas_2024.parquet`, que no
  existía). Los gráficos y el mapa se hicieron con `graficando-enaho` y `mapeando-enaho`.
- Las cifras de la ENAHO salen de `salidas/indicadores.csv`, `salidas/mapa_pobreza_departamento.csv` y
  `salidas/mapa_alimentos_departamento.csv`, y de la salida impresa por los scripts. No se calculó nada a mano.
- El peso de alimentos es el % del gasto total del hogar destinado a alimentos, promediado por persona con `facpob07`.

## 3. Hallazgos
1. **La inflación de alimentos fue más alta y más volátil que la general** (BCRP, Lima Metropolitana).
   - Alimentos y bebidas (`PN09822PM`): pico de 13.16 % en 2023-02; promedio 2022-01 a 2024-12 de 7.62 %; mínimo de 0.69 %
     en 2024-09; cierre de 1.25 % en 2024-12.
   - IPC total (`PN01273PM`): pico de 8.81 % en 2022-06; promedio de 5.51 %; cierre de 1.97 % en 2024-12.
   - Los alimentos superaron al total en promedio por 2.1 pts (7.62 % frente a 5.51 %). Esa diferencia es una resta de dos
     promedios del `resumen`, no una cifra calculada por el servidor.
   - A fines de 2024 la inflación de alimentos (1.25 %) quedó por debajo de la total (1.97 %).
   - Ambas series se mueven casi juntas: r = 0.976, r² = 0.953, n = 36 (`correlacion`, `PN09822PM` frente a `PN01273PM`).
     Es una asociación descriptiva, no causal.
2. **Los hogares pobres gastan una parte mayor de su presupuesto en alimentos** (`salidas/indicadores.csv`, grupo `condicion`).

   | Condición | Peso de alimentos (% del gasto) | Población expandida |
   |---|---|---|
   | Pobre extremo | 49.27 | 1,878,051 |
   | Pobre no extremo | 43.58 | 7,522,396 |
   | No pobre | 33.26 | 24,747,318 |
   | Nacional | 36.41 | 34,147,768 |

   El pobre extremo destina 16.0 pts más que el no pobre (49.27 frente a 33.26). Una misma alza de precios de alimentos
   pega más en su presupuesto. El gasto per cápita mensual es de S/ 191.8 en pobres extremos y de S/ 958.6 en no pobres.
3. **El área rural combina más pobreza y más exposición** (`salidas/indicadores.csv`, grupo `area`; figura `pobreza_area.png`).
   - Pobreza: rural 39.44 % frente a urbana 24.74 %, una brecha de 14.7 pts.
   - Peso de alimentos: rural 48.03 % frente a urbano 33.69 %.
   - Pobreza extrema: rural 15.60 % frente a urbana 3.13 %.
4. **La geografía de la exposición no coincide del todo con la pobreza** (`salidas/mapa_pobreza_departamento.csv` y
   `salidas/mapa_alimentos_departamento.csv`).
   - Los departamentos más pobres son Cajamarca (44.99 %), Loreto (42.61 %) y Puno (40.42 %). Los menos pobres son Ica
     (5.91 %), Moquegua (10.88 %) y Madre de Dios (11.14 %).
   - El mayor peso de alimentos está en Apurímac (47.05 %), Puno (45.09 %) y Loreto (44.96 %). El menor, en Lima (30.25 %),
     Moquegua (31.44 %) y Callao (32.81 %).
   - Apurímac (pobreza 24.09 %) y Cusco (18.54 %; peso de alimentos 42.28 %) tienen una pobreza moderada pero una exposición
     alta, es decir, un presupuesto muy sensible a los alimentos. Puno y Loreto combinan ambas condiciones.
   - Lima destina 30.25 % del gasto a alimentos, el valor más bajo, pero la inflación del BCRP se mide solo en Lima
     Metropolitana (ver limitaciones).

## 4. Contraste con la validación y con la sesión 16
- `salidas/validacion.txt` (regenerado el 2026-11-09): todas las validaciones esenciales pasan.
  - La pobreza nacional ponderada es 27.53 % (INEI: 27.6 %; diferencia -0.07 pts) y 27.58 % con `factor07 × mieperho`.
  - Urbana 24.74 % y rural 39.44 % (INEI: 24.8 % y 39.3 %).
  - La unión de personas con hogares no duplica ni pierde filas: 108,664 de 108,664.
  - Hay 25 departamentos, sin duplicados.
- Mapa frente a la referencia de la sesión 16 (`.claude/skills/mapeando-enaho/referencias/pobreza_departamento_2024.csv`):
  la **diferencia máxima es 0.5 pts**, en Huánuco (+0.47) y Puno (+0.52). Las otras mayores son Amazonas (+0.4),
  Loreto (-0.4), Pasco (+0.3) y Tumbes (-0.3). Están dentro de lo esperado (~0.5 pts) por ponderar personas (`facpob07`)
  en lugar de hogares. El ranking de extremos coincide con la referencia.

## 5. Figuras
- `figuras/bcrp_inflacion_alimentos.png`: serie `PN09822PM`, 2022-01 a 2024-12 (% var. 12 meses).
- `figuras/peso_alimentos_condicion.png`: peso del gasto en alimentos por condición de pobreza.
- `figuras/pobreza_area.png`: pobreza urbana y rural.
- `mapas/pobreza_departamento.png`: mapa de pobreza monetaria por departamento.
- `mapas/peso_alimentos_departamento.png`: mapa del peso de alimentos. Es una salida previa de la sesión; su CSV no se
  regeneró en esta corrida (no se abrió la imagen).
- Las imágenes se generaron con los scripts, pero este borrador no las inspeccionó visualmente.

## 6. Interpretación
En 2022–2023 los alimentos subieron más que el nivel general de precios (pico de 13.2 % en febrero de 2023). Esa alza
cayó con más fuerza en los hogares donde los alimentos pesan casi la mitad del gasto: pobres extremos (49.3 %), pobres no
extremos (43.6 %) y el área rural (48.0 %). Estos grupos tienen menos margen para sustituir consumo o ahorrar. Hacia 2024
la presión cedió (1.25 % en diciembre), pero el efecto acumulado sobre el poder de compra de los hogares pobres no
desaparece con la caída de la tasa. La exposición también varía por departamento: es mayor en la sierra sur y la
Amazonía que en la costa y en Lima.

## 7. Limitaciones
- La inflación del BCRP es de **Lima Metropolitana**, no nacional ni por departamento. No mide los precios que enfrentan
  los hogares rurales ni los de otros departamentos, cuya canasta y precios pueden diferir.
- La ENAHO 2024 es un corte transversal: no se observa el gasto de 2022–2023 ni el cambio de comportamiento de los hogares.
  La exposición se aproxima con el peso del gasto en alimentos de 2024, que ya incorpora la sustitución.
- La canasta del IPC "Alimentos y Bebidas" no equivale a la definición de alimentos de la ENAHO (puede incluir o excluir
  consumo fuera del hogar, autoconsumo y bebidas).
- Una correlación de 0.976 entre alimentos y total es descriptiva. Con 36 meses y series muy autocorrelacionadas, la
  significancia no se evaluó.
- Lima y Callao figuran por separado en la ENAHO, pero el IPC se refiere a Lima Metropolitana (Lima + Callao). Las
  comparaciones territoriales con Lima Metropolitana son aproximadas.
- Las diferencias de hasta 0.5 pts con la sesión 16 vienen de ponderar personas y no hogares. No se ajustó ninguna cifra
  para que coincidiera.
- No se calcularon intervalos de confianza ni significancia estadística de las diferencias entre grupos.

## 8. Reproducibilidad
```bash
uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024
uv run .claude/skills/mapeando-enaho/scripts/mapear.py --indicador pobreza
uv run .claude/skills/graficando-enaho/scripts/graficar.py alimentos
uv run .claude/skills/graficando-enaho/scripts/graficar.py area
```
BCRP (MCP `bcrp`):
- `buscar_series("ipc alimentos y bebidas 12 meses")` y `buscar_series("ipc lima metropolitana 12 meses")`.
- `resumen`, `correlacion` y `graficar_serie` sobre `PN09822PM` y `PN01273PM` entre 2022-01 y 2024-12.
- `graficar_serie("PN09822PM", "2022-01", "2024-12", archivo="bcrp_inflacion_alimentos.png", unidad="% var. 12 meses")`.

Los microdatos están en `datos/` (excluido de git). Las series BCRP se actualizaron por última vez el 2026-10-08 según
`buscar_series`; una consulta posterior puede traer revisiones.

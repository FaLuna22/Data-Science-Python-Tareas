---
name: graficando-enaho
description: Hace gráficos ponderados de la pobreza monetaria de la ENAHO 2024 del INEI por área urbana y rural, sexo, grupo de edad, departamento o peso del gasto en alimentos según condición de pobreza. Úsala cuando pidan graficar, visualizar, comparar en barras o hacer una figura de la pobreza o de indicadores de hogares de la ENAHO.
argument-hint: "[area|sexo|edad|departamento|alimentos|todos]"
---
# Graficar la ENAHO 2024

1. Si no existe `salidas/personas_2024.parquet`, usa primero la skill `limpiando-enaho` y espera a que sus
   validaciones pasen.
2. Traduce el pedido a uno de estos gráficos y corre exactamente, desde la raíz del proyecto:
   ```bash
   uv run .claude/skills/graficando-enaho/scripts/graficar.py <grafico>
   ```
   | Pedido en lenguaje natural | `<grafico>` | Archivo |
   |---|---|---|
   | pobreza urbana vs rural, por área | `area` | `figuras/pobreza_area.png` |
   | pobreza por sexo, hombres y mujeres | `sexo` | `figuras/pobreza_sexo.png` |
   | pobreza por edad, niños, adultos mayores | `edad` | `figuras/pobreza_edad.png` |
   | comparar departamentos o regiones | `departamento` | `figuras/pobreza_departamento.png` |
   | gasto en alimentos, exposición a la inflación de alimentos | `alimentos` | `figuras/peso_alimentos_condicion.png` |
   | todos los anteriores | `todos` | los cinco |
3. El script imprime la tabla con el valor ponderado de cada barra, la población expandida y la muestra: cita esas
   cifras, no las recalcules a mano.
4. Interpreta la diferencia real (en puntos porcentuales) y recuerda que es una asociación descriptiva, no causal.

## Reglas que el script ya cumple
- Pondera siempre con `facpob07`; barras desde cero, ordenadas, un solo color y el valor escrito en cada barra.
- La línea roja punteada marca el promedio nacional.
- El título dice el hallazgo, qué se mide y cuándo; el eje dice la unidad (% de personas).
- Nota al pie: «Fuente: INEI, ENAHO 2024 (módulos 34 y 02)». PNG a 200 dpi en `figuras/`.

# Transcripción: demo_grafico_lenguaje_natural.jsonl

**Sesión:** modelo `claude-sonnet-5-5`, carpeta `/home/user/Data-Science-Python-Tareas/tarea_4`
**MCP:** bcrp (connected)
**Skills del proyecto cargadas:** graficando-enaho, limpiando-enaho, mapeando-enaho

### 🔧 `Skill`

```json
{
  "skill": "graficando-enaho"
}
```

<details><summary>Resultado de la herramienta</summary>

```
Launching skill: graficando-enaho
```
</details>

## 👤 Instrucción

Base directory for this skill: /home/user/Data-Science-Python-Tareas/tarea_4/.claude/skills/graficando-enaho

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


### 🔧 `Bash`

```json
{
  "command": "ls salidas/personas_2024.parquet 2>&1; ls"
}
```

<details><summary>Resultado de la herramienta</summary>

```
salidas/personas_2024.parquet
datos
evaluacion
evidencias_ia
figuras
informes
mapas
mcp
pyproject.toml
salidas
scripts
uv.lock
```
</details>

### 🔧 `Bash`

```json
{
  "command": "uv run .claude/skills/graficando-enaho/scripts/graficar.py area"
}
```

<details><summary>Resultado de la herramienta</summary>

```
warning: The `UV_NATIVE_TLS` environment variable is deprecated and will be removed in a future release. Use `UV_SYSTEM_CERTS` instead.

La pobreza rural supera a la urbana en 14.7 puntos
Pobreza monetaria por área de residencia, Perú 2024
  area  valor  poblacion       n
 Rural  39.44  6486385.0 36071.0
Urbana  24.74 27661382.0 72593.0
-> figuras/pobreza_area.png
```
</details>

### 🔧 `Read`

```json
{
  "file_path": "/home/user/Data-Science-Python-Tareas/tarea_4/figuras/pobreza_area.png"
}
```

<details><summary>Resultado de la herramienta</summary>

```

```
</details>

## 🤖 Claude

Gráfico guardado en `figuras/pobreza_area.png`.

**Pobreza monetaria por área, Perú 2024 (ENAHO, ponderada con `facpob07`)**

| Área | % en pobreza | Población expandida | Muestra |
|---|---|---|---|
| Rural | 39.4 % | 6 486 385 | 36 071 |
| Urbana | 24.7 % | 27 661 382 | 72 593 |

El promedio nacional es 27.5 %, marcado con la línea roja punteada.

La pobreza rural supera a la urbana en 14.7 puntos porcentuales. La tasa rural queda por encima del promedio nacional y la urbana por debajo. Esta es una asociación descriptiva entre área de residencia y pobreza, no una relación causal.

Aunque la tasa rural es mayor, en la población expandida hay más personas pobres en el área urbana. Esto se debe a que la población urbana es unas 4 veces mayor que la rural.

Puedo generar también los gráficos por sexo, edad, departamento o peso del gasto en alimentos.

---
**Fin:** success, 6 turnos, 10 s, costo US$ 0.09

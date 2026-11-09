# Transcripción: demo_mapa_lenguaje_natural.jsonl

**Sesión:** modelo `claude-sonnet-5-5`, carpeta `/home/user/Data-Science-Python-Tareas/tarea_4`
**MCP:** bcrp (connected)
**Skills del proyecto cargadas:** graficando-enaho, limpiando-enaho, mapeando-enaho

### 🔧 `Skill`

```json
{
  "skill": "mapeando-enaho"
}
```

<details><summary>Resultado de la herramienta</summary>

```
Launching skill: mapeando-enaho
```
</details>

## 👤 Instrucción

Base directory for this skill: /home/user/Data-Science-Python-Tareas/tarea_4/.claude/skills/mapeando-enaho

# Mapear la ENAHO 2024 por departamento

1. Si no existe `salidas/personas_2024.parquet`, usa primero la skill `limpiando-enaho` y espera a que sus
   validaciones pasen.
2. Corre exactamente, desde la raíz del proyecto (indicador por defecto: `pobreza`):
   ```bash
   uv run .claude/skills/mapeando-enaho/scripts/mapear.py --indicador pobreza
   ```
   Con `--indicador alimentos` mapea el % del gasto del hogar destinado a alimentos.
3. El script une `ubigeo[:2]` con `FIRST_IDDP` (texto con cero a la izquierda) con `validate="1:1"`, exige 25
   departamentos con dato y Lima (15) y Callao (07) separados. Si termina con `ERROR`, detente e informa.
   Nunca unas por nombre: «APURIMAC» no es «Apurímac».
4. Para la pobreza compara cada departamento con `referencias/pobreza_departamento_2024.csv` (sesión 16) e informa la
   diferencia máxima. Diferencias de hasta ~0.5 pts vienen de ponderar personas (`facpob07`) en vez de hogares.
5. Responde con la ruta del mapa (`mapas/pobreza_departamento.png`), los tres departamentos más y menos pobres y la
   tabla `salidas/mapa_pobreza_departamento.csv`.

## Reglas de diseño
Escala secuencial de claro a oscuro (`Reds`) que empieza en 0, nunca arcoíris; leyenda con la unidad
(% de personas); valor escrito en cada departamento; fuente al pie; PNG en `mapas/`.


### 🔧 `Bash`

```json
{
  "command": "ls salidas/personas_2024.parquet; ls"
}
```

<details><summary>Resultado de la herramienta</summary>

```
ls: cannot access 'salidas/personas_2024.parquet': No such file or directory
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

## 🤖 Claude

Falta la base de personas, así que uso primero la skill de limpieza.

### 🔧 `Skill`

```json
{
  "skill": "limpiando-enaho"
}
```

<details><summary>Resultado de la herramienta</summary>

```
Launching skill: limpiando-enaho
```
</details>

## 👤 Instrucción

Base directory for this skill: /home/user/Data-Science-Python-Tareas/tarea_4/.claude/skills/limpiando-enaho

# Limpiar la ENAHO 2024

1. Verifica que existan `datos/966-Modulo34.zip` y `datos/966-Modulo02.zip` (o sus carpetas descomprimidas).
   Si faltan, bájalos (966 = ENAHO 2024):
   ```bash
   mkdir -p datos && cd datos
   curl -LO https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip
   curl -LO https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip
   ```
2. Corre exactamente, desde la raíz del proyecto:
   ```bash
   uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024
   ```
3. Lee `salidas/validacion.txt`. Si dice `FALLAN VALIDACIONES ESENCIALES` o el script termina con código 1,
   **detente** e informa qué validación falló. Nunca ajustes cifras para que coincidan con la referencia.
4. Responde con cifras de `salidas/indicadores.csv` (ya ponderadas con `facpob07`) o calculando sobre
   `salidas/personas_2024.parquet` con `np.average(..., weights=facpob07)`. Nunca uses promedios simples.
5. Cita siempre: «Fuente: INEI, ENAHO 2024, módulos 34 y 02; residentes habituales; ponderado con facpob07».
6. Antes de usar una variable que no está en la base, lee `reference.md`.

## Qué valida el script (y por qué)

| Validación | Valor esperado |
|---|---|
| Residentes habituales | 108,664 de 117,721 filas del módulo 02 |
| Unión personas–hogares `validate="m:1"` | 108,664 filas antes y después, sin huérfanos |
| Departamentos (`ubigeo[:2]`) | 25 códigos, 01 a 25 |
| Pobreza nacional ponderada | 27.6 % ± 0.1 pts (27.53 % con facpob07; 27.58 % con factor07 × mieperho) |
| Urbano / rural (`estrato <= 5`) | 24.8 % / 39.3 % (aprox.) |


### 🔧 `Bash`

```json
{
  "command": "ls datos; ls .claude/skills/limpiando-enaho/scripts"
}
```

<details><summary>Resultado de la herramienta</summary>

```
966-Modulo02
966-Modulo02.zip
966-Modulo34
966-Modulo34.zip
cache_bcrp
catalogo_bcrp.csv
peru_departamental_simple.geojson
limpiar.py
```
</details>

## 🤖 Claude

Los datos ya están. Corro la limpieza.

### 🔧 `Bash`

```json
{
  "command": "uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024 2>&1 | tail -30; cat salidas/validacion.txt"
}
```

<details><summary>Resultado de la herramienta</summary>

```
warning: The `UV_NATIVE_TLS` environment variable is deprecated and will be removed in a future release. Use `UV_SYSTEM_CERTS` instead.
VALIDACIÓN ENAHO 2024 (INEI, código 966) — 2026-11-09 01:52
Módulos: 34 (sumaria, hogares) y 02 (miembros, personas). Ponderador de personas: facpob07.

[PASA] (esencial) Llaves únicas en la sumaria (conglome, vivienda, hogar): 33,691 hogares, 0 duplicados
[PASA] (esencial) Llaves únicas en miembros (+ codperso): 117,721 filas, 0 duplicadas
[PASA] (esencial) Residentes habituales = 108,664: 108,664 de 117,721 filas del módulo 02
[PASA] (esencial) La unión m:1 no duplica ni pierde personas: 108,664 filas después de unir; sin pareja en la sumaria: 0
[PASA] (esencial) Personas sin factor de expansión (facpob07): 0 sin factor
[PASA] (esencial) 25 departamentos identificados (ubigeo[:2] = 01..25): 25 códigos: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25
[PASA] (esencial) Pobreza nacional ponderada (facpob07) a ≤ 0.1 pts de 27.6 %: 27.53 % (diferencia -0.07 pts)
[PASA] (esencial) Pobreza nacional con la sumaria (factor07 × mieperho) a ≤ 0.1 pts de 27.6 %: 27.58 %
[PASA] Pobreza urbana ≈ 24.8 % (estrato ≤ 5): 24.74 %
[PASA] Pobreza rural ≈ 39.3 % (estrato ≥ 6): 39.44 %
[PASA] Promedio simple ≠ ponderado (el factor sí cambia la cifra): simple 25.61 % vs ponderado 27.53 %

Cifras principales (% de personas, ponderadas):
  Pobreza monetaria nacional: 27.53 %  (redondeada 27.5 %; INEI 27.6 %)
  Pobreza extrema nacional:   5.50 %
  Urbana / rural:             24.74 % / 39.44 %
  Residentes habituales:      108,664 (población expandida 34,147,768)

Nota de redondeo: con personas y facpob07 la pobreza da 27.53 %; con la sumaria y
factor07 × mieperho (método de publicación del INEI) da 27.58 % ≈ 27.6 %. Las dos están dentro
de la tolerancia de 0.1 pts: facpob07 está calibrado por persona y factor07 por hogar, por eso
difieren en centésimas. Urbano/rural se definen con estrato <= 5; el INEI publica 24.8 % / 39.3 %.

RESULTADO: TODAS LAS VALIDACIONES ESENCIALES PASAN

Guardado: salidas/personas_2024.parquet (108,664 personas), salidas/indicadores.csv (39 filas), salidas/validacion.txt
VALIDACIÓN ENAHO 2024 (INEI, código 966) — 2026-11-09 01:52
Módulos: 34 (sumaria, hogares) y 02 (miembros, personas). Ponderador de personas: facpob07.

[PASA] (esencial) Llaves únicas en la sumaria (conglome, vivienda, hogar): 33,691 hogares, 0 duplicados
[PASA] (esencial) Llaves únicas en miembros (+ codperso): 117,721 filas, 0 duplicadas
[PASA] (esencial) Residentes habituales = 108,664: 108,664 de 117,721 filas del módulo 02
[PASA] (esencial) La unión m:1 no duplica ni pierde personas: 108,664 filas después de unir; sin pareja en la sumaria: 0
[PASA] (esencial) Personas sin factor de expansión (facpob07): 0 sin factor
[PASA] (esencial) 25 departamentos identificados (ubigeo[:2] = 01..25): 25 códigos: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 2
… [1129 caracteres más en el .jsonl]
```
</details>

## 🤖 Claude

Las validaciones pasan. Ahora el mapa.

### 🔧 `Bash`

```json
{
  "command": "uv run .claude/skills/mapeando-enaho/scripts/mapear.py --indicador pobreza 2>&1 | grep -v UV_NATIVE; cat salidas/mapa_pobreza_departamento.csv"
}
```

<details><summary>Resultado de la herramienta</summary>

```
ccdd        nombre  valor  referencia_s16  diferencia
  01      AMAZONAS  26.08            25.7         0.4
  02        ANCASH  22.88            22.8         0.1
  03      APURIMAC  24.09            24.0         0.1
  04      AREQUIPA  15.77            15.8         0.0
  05      AYACUCHO  33.04            32.8         0.2
  06     CAJAMARCA  44.99            45.0         0.0
  07        CALLAO  33.77            33.9        -0.1
  08         CUSCO  18.54            18.5         0.0
  09  HUANCAVELICA  33.61            33.4         0.2
  10       HUANUCO  39.47            39.0         0.5
  11           ICA   5.91             6.0        -0.1
  12         JUNIN  18.61            18.5         0.1
  13   LA LIBERTAD  30.07            30.2        -0.1
  14    LAMBAYEQUE  14.05            14.0         0.1
  15          LIMA  26.89            27.1        -0.2
  16        LORETO  42.61            43.0        -0.4
  17 MADRE DE DIOS  11.14            11.1         0.0
  18      MOQUEGUA  10.88            11.0        -0.1
  19         PASCO  39.28            39.0         0.3
  20         PIURA  31.81            31.9        -0.1
  21          PUNO  40.42            39.9         0.5
  22    SAN MARTIN  21.99            22.0         0.0
  23         TACNA  23.88            24.0        -0.1
  24        TUMBES  26.60            26.9        -0.3
  25       UCAYALI  27.12            27.1         0.0

25/25 departamentos con dato (unión ubigeo[:2] = FIRST_IDDP). -> mapas/pobreza_departamento.png
Máxima diferencia contra la referencia de la sesión 16: 0.5 pts
ccdd,nombre,valor,referencia_s16,diferencia
01,AMAZONAS,26.080843165700845,25.7,0.4
02,ANCASH,22.881376210726383,22.8,0.1
03,APURIMAC,24.087954062591493,24.0,0.1
04,AREQUIPA,15.76741586055283,15.8,0.0
05,AYACUCHO,33.03981451389697,32.8,0.2
06,CAJAMARCA,44.994959870178555,45.0,0.0
07,CALLAO,33.768343569690856,33.9,-0.1
08,CUSCO,18.539294887094865,18.5,0.0
09,HUANCAVELICA,33.60816538847581,33.4,0.2
10,HUANUCO,39.47285686811669,39.0,0.5
11,ICA,5.913941993463537,6.0,-0.1
12,JUNIN,18.610376293651463,18.5,0.1
13,LA LIBERTAD,30.074527904870536,30.2,-0.1
14,LAMBAYEQUE,14.052567774678506,14.0,0.1
15,LIMA,26.88876927698789,27.1,-0.2
16,LORETO,42.605097583354215,43.0,-0.4
17,MADRE DE DIOS,11.135909180536798,11.1,0.0
18,MOQUEGUA,10.878088995930279,11.0,-0.1
19,PASCO,39.28183265566638,39.0,0.3
20,PIURA,31.811816660453022,31.9,-0.1
21,PUNO,40.41768260642672,39.9,0.5
22,SAN MARTIN,21.993788410877087,22.0,0.0
23,TACNA,23.883223476469283,24.0,-0.1
24,TUMBES,26.59678460945951,26.9,-0.3
25,UCAYALI,27.12314063300004,27.1,0.0
```
</details>

## 🤖 Claude

Hecho el mapa coroplético de pobreza monetaria por departamento, ENAHO 2024.

**Mapa:** `/home/user/Data-Science-Python-Tareas/tarea_4/mapas/pobreza_departamento.png`
**Tabla:** `/home/user/Data-Science-Python-Tareas/tarea_4/salidas/mapa_pobreza_departamento.csv`

**Validaciones:** pasaron todas las esenciales de la limpieza (108,664 residentes habituales). La pobreza nacional ponderada con `facpob07` da 27.53 %, frente al 27.6 % del INEI. La unión por ubigeo con `FIRST_IDDP` dio 25 de 25 departamentos, con Lima y Callao por separado.

**Más pobres:**
1. Cajamarca, 45.0 %
2. Loreto, 42.6 %
3. Puno, 40.4 %

**Menos pobres:**
1. Ica, 5.9 %
2. Moquegua, 10.9 %
3. Madre de Dios, 11.1 %

**Comparación con la sesión 16:** la diferencia máxima es de 0.5 pts (Huánuco y Puno). Está dentro de lo esperado por ponderar personas (`facpob07`) en vez de hogares.

El valor está escrito en cada departamento, con escala `Reds` desde 0, leyenda en % de personas y la fuente al pie.

Fuente: INEI, ENAHO 2024, módulos 34 y 02; residentes habituales; ponderado con facpob07.

---
**Fin:** success, 9 turnos, 16 s, costo US$ 0.11

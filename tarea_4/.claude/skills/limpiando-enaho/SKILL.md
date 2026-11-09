---
name: limpiando-enaho
description: Limpia y valida los módulos 34 (sumaria) y 02 (miembros) de la ENAHO 2024 del INEI y arma una base de personas con pobreza monetaria, departamento, área, sexo, edad, peso del gasto en alimentos y factor de expansión. Úsala cuando pidan limpiar, unir, validar o analizar la ENAHO, o calcular pobreza (nacional, urbana, rural, por departamento, sexo o edad), y siempre antes de graficando-enaho o mapeando-enaho si no existe salidas/personas_2024.parquet.
argument-hint: "[año]"
---
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

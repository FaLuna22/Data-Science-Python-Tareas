---
name: mapeando-enaho
description: Hace un mapa coroplético por departamento del Perú (25 unidades, Lima y Callao por separado) con la pobreza monetaria o el peso del gasto en alimentos de la ENAHO 2024 del INEI, uniendo por código ubigeo y FIRST_IDDP. Úsala cuando pidan un mapa, una distribución territorial o regional, o comparar la pobreza entre departamentos en un mapa.
argument-hint: "[pobreza|alimentos]"
---
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

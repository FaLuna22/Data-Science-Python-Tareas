Pregunta de investigación: ¿Qué tan expuestos estuvieron los hogares pobres del Perú a la inflación de alimentos?
Contrasta la inflación de alimentos y bebidas de Lima Metropolitana medida por el BCRP (2022–2024) con la pobreza
monetaria y el peso del gasto en alimentos de los hogares en la ENAHO 2024, por área, condición de pobreza y departamento.

Trabaja como agente de investigación, en este orden, y sin hacer cuentas a mano:
1. Escribe un plan de análisis corto.
2. Con el servidor MCP bcrp: usa buscar_series para encontrar la inflación de alimentos y bebidas a 12 meses y la
   inflación total a 12 meses de Lima Metropolitana; usa resumen para cada una entre 2022-01 y 2024-12 (pico, cierre de
   2024); usa correlacion entre las dos; y usa graficar_serie para guardar figuras/bcrp_inflacion_alimentos.png con la
   serie de alimentos (unidad "% var. 12 meses").
3. Con las skills del proyecto, ACTIVÁNDOLAS con la herramienta Skill (no leas los SKILL.md con cat ni corras
   los scripts por tu cuenta sin activar antes la skill): haz un mapa de la pobreza monetaria por departamento con la ENAHO 2024 (mapeando-enaho;
   si no existe la base limpia, primero limpiando-enaho) y un gráfico del peso del gasto en alimentos por condición de
   pobreza y otro de pobreza urbana y rural (graficando-enaho).
4. Contrasta: cita la validación (salidas/validacion.txt) y compara el mapa con la referencia de la sesión 16.
5. Escribe informes/borrador_agente.md con: pregunta, fuentes y método, al menos 3 hallazgos con cifras (cada cifra con
   su código de serie BCRP o archivo de salida ENAHO), las figuras generadas, interpretación, limitaciones y
   reproducibilidad. Si una herramienta falla o no trae datos, dilo: no inventes cifras.

# Referencia de variables · ENAHO 2024

## Llaves y lectura
- Hogar: `conglome`, `vivienda`, `hogar` (texto; conservar ceros a la izquierda). Persona: + `codperso`.
- Leer con `pd.read_stata(ruta, convert_categoricals=False)` y pasar los nombres a minúscula sin tildes (`aÑo` → `ano`).
- `ubigeo`: 6 dígitos como texto; `ubigeo[:2]` = departamento (01 Amazonas … 15 Lima, 07 Callao … 25 Ucayali).

## Módulo 34 · sumaria (una fila por hogar, 33,691)
| Variable | Significado |
|---|---|
| `pobreza` | 1 pobre extremo, 2 pobre no extremo, 3 no pobre |
| `factor07` | factor de expansión del hogar (para personas: `factor07 * mieperho`) |
| `mieperho` | miembros del hogar (sin trabajadoras del hogar ni pensionistas) |
| `estrato` | 1–5 urbano, 6–8 rural |
| `dominio` | 1–3 costa, 4–6 sierra, 7 selva, 8 Lima Metropolitana |
| `gashog2d` | gasto total bruto anual del hogar (soles) |
| `inghog2d` | ingreso neto total anual del hogar |
| `linea`, `linpe` | línea de pobreza total y extrema (soles por persona al mes) |
| `gru11hd` … `gru14hd6` | grupo 1 de gasto: alimentos (dentro y fuera del hogar, todas las formas de adquisición) |

## Módulo 02 · miembros (una fila por persona, 117,721)
| Variable | Significado |
|---|---|
| `p204` | ¿es miembro del hogar? (1 sí, 2 no) |
| `p205` | ¿estuvo ausente más de 30 días? (1 sí, 2 no) |
| `p206` | ¿estuvo presente más de 30 días? (1 sí, 2 no) |
| `p207` | sexo (1 hombre, 2 mujer) |
| `p208a` | edad en años |
| `facpob07` | factor de expansión de la persona |

Residente habitual: `((p204 == 1) & (p205 == 2)) | ((p204 == 2) & (p206 == 1))`.

## Variables que construye `limpiar.py`
`departamento`, `nombre_departamento`, `departamento_nombre`, `urbano`, `area`, `pobre`, `pobre_extremo`, `condicion`,
`sexo`, `grupo_edad` (0-13, 14-17, 18-29, 30-44, 45-59, 60+), `gasto_alimentos`, `peso_alimentos` (% del gasto total),
`gasto_pc_mensual` (gashog2d / mieperho / 12).

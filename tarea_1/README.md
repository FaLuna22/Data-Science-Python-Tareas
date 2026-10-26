# Tarea 1 – Noticias peruanas: del titular al clasificador

> **Pregunta del proyecto:** ¿Pueden convertir titulares peruanos en un clasificador de noticias?

Proyecto individual del curso *Data Science con Python* (QLAB PUCP). Se extraen titulares reales de **El Comercio**,
se etiquetan con supervisión débil usando un LLM local, se hace *fine-tuning* de **BETO** y se publica un dashboard en
Streamlit para clasificar titulares nuevos en vivo.

**Respuesta corta:** sí. Con solo 268 titulares de entrenamiento, BETO alcanza un **F1 macro de 0.914** en un test
reservado de 58 noticias, frente a **0.627** de la línea base zero-shot.

| Resultado (test reservado) | Valor |
| :--- | :---: |
| F1 macro – BETO fine-tuned | **0.914** |
| F1 macro – Zero-shot (40 titulares, línea base) | 0.627 |
| F1 macro – LLM débil (Qwen 2.5-3B) | 0.877 |
| Acuerdo LLM vs. auditoría humana | 19/20 (95 %) |

---

## 1. Medio y fechas de extracción

| | |
| :--- | :--- |
| **Opción** | B – El Comercio (`elcomercio.pe`) |
| **Fecha de descarga** | 26 de octubre de 2026 |
| **Rango de publicación de las notas** | 2026-10-10 a 2026-10-26 |
| **Volumen final** | 383 noticias (de 400 crudas; 17 descartadas) |
| **Fuente** | Sitemaps de noticias por sección listados en `robots.txt` (`/sitemap/news/<seccion>/`) + `<meta name="description">` de cada nota para la bajada |
| **Secciones → categorías** | `politica/*` → `politica` · `economia/*` → `economia` · `deporte-total/*` → `deportes` · `tecnologia/*` → `ciencia_tecnologia` |

Se respetó `robots.txt` (verificado con `urllib.robotparser`), con `User-Agent` descriptivo, pausa de 1.5 s entre
solicitudes y un único reintento. El RSS oficial (`/arc/outboundfeeds/rss/...`) solo trae ~18 notas por sección, por
eso se usaron los sitemaps que el propio diario publica para robots. Las respuestas crudas quedan en `datos/raw/`.

## 2. Metodología

1. **`01_recoleccion.ipynb`** – scraping, limpieza (duplicados por URL/titular, vacíos, secciones fuera de las 4
   categorías), tabla de mapeo sección → categoría, reporte de descartes, EDA con 3 gráficos Plotly y validación de extremos.
2. **`02_clasificacion.ipynb`**
   - Línea base *zero-shot* con `Recognai/bert-base-spanish-wwm-cased-xnli` sobre 40 titulares.
   - Supervisión débil con **`Qwen/Qwen2.5-3B-Instruct`** corriendo localmente en GPU: prompt estructurado con
     definiciones + 6 ejemplos *few-shot*; la etiqueta y la `confianza` salen de la probabilidad que el LLM asigna a
     cada una de las 4 respuestas (con calibración contextual). Resultado en `datos/etiquetas_llm.csv`.
   - Auditoría humana de 20 predicciones al azar (`datos/auditoria_humana.csv`).
   - Split estratificado 70/15/15 (`random_state=42`, `datos/split.csv`).
   - *Fine-tuning* de `dccuchile/bert-base-spanish-wwm-cased` (BETO) con 🤗 `Trainer`: 5 épocas, batch 16, evaluación por
     época y selección del mejor checkpoint por F1 macro en validación.
   - Evaluación final en test (accuracy, F1 macro, matriz de confusión) y comparativa de los tres enfoques.
3. **`app.py`** – dashboard Streamlit con filtros, métricas, gráficos, tabla descargable y probador en vivo.

## 3. Hallazgos analíticos

1. **El fine-tuning gana por goleada con muy pocos datos.** Con solo 268 titulares de entrenamiento, BETO pasa de
   un F1 macro de 0.63 (zero-shot) a **0.91** en test. El zero-shot NLI tiene un sesgo fuerte hacia *política*
   (recall 100 % en política, pero solo 40 % en economía y en ciencia y tecnología): sin ejemplos, "política" funciona
   como categoría por defecto para cualquier noticia con actores públicos.
2. **Las etiquetas débiles del LLM valen casi tanto como las etiquetas reales.** BETO entrenado *solo* con las
   etiquetas de Qwen (sin mirar la sección del diario) obtiene F1 0.912 frente a 0.914, y supera al propio LLM que lo
   etiquetó (0.877): el fine-tuning promedia el ruido de las etiquetas. El desacuerdo se concentra en la frontera
   **economía ↔ ciencia y tecnología** (precios de celulares, empresas tecnológicas, El Niño), que también es donde
   falla BETO: *deportes* es la categoría más fácil (F1 0.97) y *economía* la más difícil (F1 0.87) porque es transversal.
3. *(Extra, de la Parte 1)* **El ritmo de publicación sesga las fechas:** el sitemap guarda las últimas 100 notas por
   sección, así que deportes cubre solo 4 días y ciencia y tecnología 16. El dataset no es una "foto" del mismo periodo
   para todas las categorías.

## 4. Limitaciones técnicas

1. **Muestra pequeña y de un solo periodo.** El test tiene 58 noticias (cada error mueve ~1.7 puntos de accuracy) y
   todas las notas son de octubre de 2026, dominadas por la agenda del momento (delegación de facultades, El Niño,
   Torneo Clausura). El modelo puede degradarse con otros temas o con otro medio (*concept drift*); habría que
   re-entrenar periódicamente y probar con La República.
2. **La etiqueta de referencia es ruidosa y el despliegue es pesado.** La "verdad" es la sección donde el diario
   publicó la nota, que no siempre coincide con el tema (El Niño aparece en economía y en tecnología). La confianza
   del LLM está mal calibrada (dio 1.0 a su único error de la auditoría) y el prompt se ajustó con una muestra que
   incluye algunas noticias de test, por lo que la fila del LLM puede estar levemente optimista. Por último, los pesos
   de BETO (~440 MB) no caben en GitHub: el dashboard funciona en local y para Streamlit Cloud hay que publicarlos en
   Hugging Face Hub (`MODELO_HF`).

## 5. Cómo ejecutar en local

Requisitos: Python 3.13 (probado en Windows 11). La GPU es opcional para el dashboard pero recomendable para el notebook 2.

```bash
cd tarea_1
python -m venv .venv
.venv\Scripts\activate          # en macOS/Linux: source .venv/bin/activate
pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128   # solo si hay GPU NVIDIA
pip install -r requirements.txt
```

Los pesos del modelo (`modelo/model.safetensors`, ~440 MB) **no se suben a GitHub** (`.gitignore`). Para regenerarlos
hay que ejecutar el notebook 2 (≈6 min en una RTX 5050; en CPU tarda bastante más, se puede usar Google Colab):

```bash
jupyter nbconvert --to notebook --execute --inplace 01_recoleccion.ipynb   # opcional: usa la caché de datos/raw/
jupyter nbconvert --to notebook --execute --inplace 02_clasificacion.ipynb
```

Luego se lanza el dashboard:

```bash
streamlit run app.py
```

Se abre en `http://localhost:8501`. Si los pesos se publican en Hugging Face Hub, el dashboard también puede cargarlos
con `MODELO_HF=<usuario>/<repo> streamlit run app.py` (útil para Streamlit Community Cloud).

## Estructura

```text
tarea_1/
├── 01_recoleccion.ipynb       # Scraping, limpieza y EDA
├── 02_clasificacion.ipynb     # Zero-shot, LLM, fine-tuning y evaluación
├── app.py                     # Dashboard Streamlit
├── requirements.txt
├── README.md
├── .gitignore
├── datos/
│   ├── noticias.csv           # Dataset final (7 columnas)
│   ├── etiquetas_llm.csv      # Etiquetas del LLM (titular, etiqueta_llm, confianza, modelo_llm, fecha)
│   ├── auditoria_humana.csv   # Revisión manual de 20 predicciones del LLM
│   ├── split.csv              # Partición train/val/test por URL
│   └── raw/                   # Respaldo crudo: robots.txt, sitemaps XML, bajadas.jsonl
└── modelo/
    ├── config.json, tokenizer*.json, vocab.txt   # artefactos livianos de BETO fine-tuned
    └── metricas.json                             # métricas que lee el dashboard
```

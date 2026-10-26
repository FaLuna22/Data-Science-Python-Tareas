"""Dashboard – Tarea 1: Noticias peruanas, del titular al clasificador.

Ejecutar desde la carpeta tarea_1/:
    streamlit run app.py
"""
import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

BASE = Path(__file__).parent
RUTA_MODELO = BASE / "modelo"
# Para desplegar sin los pesos locales se puede apuntar a un repo de Hugging Face Hub:
#   MODELO_HF=usuario/beto-noticias-peru streamlit run app.py
MODELO_HF = os.environ.get("MODELO_HF", "")

COLORES = {"politica": "#1f77b4", "economia": "#2ca02c", "deportes": "#ff7f0e", "ciencia_tecnologia": "#9467bd"}
NOMBRES = {"politica": "Política", "economia": "Economía", "deportes": "Deportes",
           "ciencia_tecnologia": "Ciencia y tecnología"}

st.set_page_config(page_title="Clasificador de noticias peruanas", page_icon="🗞️", layout="wide")


@st.cache_data
def cargar_datos():
    noticias = pd.read_csv(BASE / "datos" / "noticias.csv")
    llm = pd.read_csv(BASE / "datos" / "etiquetas_llm.csv")
    noticias = noticias.merge(llm[["titular", "etiqueta_llm", "confianza"]], on="titular", how="left")
    metricas = json.loads((RUTA_MODELO / "metricas.json").read_text(encoding="utf-8"))
    return noticias, metricas


@st.cache_resource
def cargar_clasificador():
    from transformers import pipeline

    if (RUTA_MODELO / "model.safetensors").exists():
        origen = str(RUTA_MODELO)
    elif MODELO_HF:
        origen = MODELO_HF
    else:
        return None
    return pipeline("text-classification", model=origen, tokenizer=origen, top_k=None)


noticias, metricas = cargar_datos()

# ---------------------------------------------------------------- encabezado
st.title("🗞️ ¿Pueden convertirse los titulares peruanos en un clasificador de noticias?")
st.markdown(
    f"""
**Metodología.** Se recolectaron **{metricas['n_noticias']} titulares de {metricas['medio']}** desde los sitemaps de
noticias por sección (política, economía, deporte-total y tecnología), respetando `robots.txt` y con pausas de 1.5 s.
La sección del diario se mapeó a 4 categorías fijas. Un LLM local (**{metricas['modelo_llm']}**) etiquetó el dataset
como supervisión débil y se auditó a mano una muestra de 20 casos. Finalmente se hizo *fine-tuning* de
**BETO** (`{metricas['modelo_base']}`) con un split estratificado 70/15/15 y se evaluó en el test reservado.
"""
)

# ---------------------------------------------------------------- barra lateral
st.sidebar.header("Filtros")
medios = sorted(noticias["medio"].unique())
sel_medios = st.sidebar.multiselect("Medio", medios, default=medios)
categorias = list(NOMBRES)
sel_categorias = st.sidebar.multiselect(
    "Categoría", categorias, default=categorias, format_func=lambda c: NOMBRES[c]
)
filtrado = noticias[noticias["medio"].isin(sel_medios) & noticias["etiqueta"].isin(sel_categorias)]
st.sidebar.caption(f"{len(filtrado)} de {len(noticias)} noticias seleccionadas")

# ---------------------------------------------------------------- métricas
c1, c2, c3, c4 = st.columns(4)
c1.metric("Noticias recolectadas", f"{len(noticias)}", f"{len(filtrado)} en el filtro", delta_color="off")
c2.metric("F1 macro en test (BETO)", f"{metricas['f1_macro_test']:.3f}",
          f"{metricas['f1_macro_test'] - metricas['f1_macro_zero_shot_40']:+.3f} vs. zero-shot")
c3.metric("Acuerdo LLM vs. auditoría humana", f"{metricas['acuerdo_llm_humano_pct']:.0%}",
          metricas["acuerdo_llm_humano"], delta_color="off")
c4.metric("F1 macro zero-shot (línea base)", f"{metricas['f1_macro_zero_shot_40']:.3f}")

# ---------------------------------------------------------------- probador en vivo
st.subheader("🔮 Probador en vivo")
clasificador = cargar_clasificador()
if clasificador is None:
    st.warning("No se encontraron los pesos del modelo en `modelo/`. Ejecuta `02_clasificacion.ipynb` "
               "o define la variable de entorno `MODELO_HF` con un repositorio de Hugging Face.")
else:
    with st.form("probador"):
        titular = st.text_area("Escribe o pega un titular nuevo",
                               "BCR mantiene su tasa de interés de referencia y prevé menor inflación", height=80)
        enviado = st.form_submit_button("Clasificar titular", type="primary")
    if enviado:
        if not titular.strip():
            st.error("Escribe un titular.")
        else:
            salida = clasificador(titular.strip())[0]
            probs = pd.DataFrame(salida).rename(columns={"label": "categoria", "score": "probabilidad"})
            probs = probs.sort_values("probabilidad", ascending=False)
            mejor = probs.iloc[0]
            col_a, col_b = st.columns([1, 2])
            col_a.success(f"**{NOMBRES[mejor.categoria]}**")
            col_a.metric("Probabilidad", f"{mejor.probabilidad:.1%}")
            if mejor.probabilidad < 0.6:
                col_a.info("Confianza baja: el titular podría pertenecer a más de una categoría.")
            fig_p = px.bar(probs, x="probabilidad", y="categoria", orientation="h", color="categoria",
                           color_discrete_map=COLORES, range_x=[0, 1], text_auto=".1%",
                           title="Probabilidad por categoría")
            fig_p.update_layout(showlegend=False, height=260, yaxis={"categoryorder": "total ascending"})
            col_b.plotly_chart(fig_p, width="stretch")

# ---------------------------------------------------------------- exploración
st.subheader("📊 Exploración del dataset")
col1, col2 = st.columns(2)
conteo = filtrado["etiqueta"].value_counts().rename_axis("etiqueta").reset_index(name="n")
fig = px.bar(conteo, x="etiqueta", y="n", color="etiqueta", text="n", color_discrete_map=COLORES,
             title="Distribución de categorías (selección actual)",
             labels={"etiqueta": "Categoría", "n": "N.º de noticias"})
fig.update_layout(showlegend=False)
col1.plotly_chart(fig, width="stretch")

cruce = filtrado.groupby(["etiqueta", "etiqueta_llm"]).size().reset_index(name="n")
fig2 = px.bar(cruce, x="etiqueta", y="n", color="etiqueta_llm", color_discrete_map=COLORES,
              title="Sección del diario vs. etiqueta asignada por el LLM",
              labels={"etiqueta": "Categoría (sección del diario)", "n": "N.º de noticias", "etiqueta_llm": "LLM"})
col2.plotly_chart(fig2, width="stretch")

st.dataframe(
    filtrado[["fecha", "etiqueta", "etiqueta_llm", "confianza", "titular", "bajada", "seccion_original", "url"]],
    width="stretch", hide_index=True,
    column_config={"url": st.column_config.LinkColumn("url"),
                   "confianza": st.column_config.NumberColumn("confianza LLM", format="%.2f")},
)
st.download_button("⬇️ Descargar selección en CSV", filtrado.to_csv(index=False).encode("utf-8"),
                   file_name="noticias_filtradas.csv", mime="text/csv")

st.caption(f"Fuente: {metricas['medio']} (elcomercio.pe). Modelo entrenado el {metricas['fecha_entrenamiento']}.")

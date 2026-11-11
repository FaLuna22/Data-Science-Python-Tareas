"""Relatoría: de la sesión pública al informe verificable.

    streamlit run app.py

Tres entradas: una sesión ya transcrita (datos/sesiones/), un audio corto que se transcribe aquí
con Whisper, o una transcripción pegada. Claude devuelve el informe con un esquema fijo y cada
cita se comprueba contra la transcripción antes de mostrarla.
"""
from __future__ import annotations

import hashlib
import html
import os
import tempfile
from pathlib import Path

import streamlit as st

from relatoria import LEMA, NOMBRE, almacen
from relatoria.esquema import InformeSesion
from relatoria.exportar import a_docx
from relatoria.informe import MODELO, SinClave, Uso, generar_informe
from relatoria.transcripcion import Sesion, bloques, desde_texto, enlace_al_minuto, hhmmss
from relatoria.verificar import Resultado, normalizar, verificar_informe

RAIZ = Path(__file__).resolve().parent
SESIONES = RAIZ / "datos" / "sesiones"
MAX_AUDIO_MB = 25            # tope del audio que se transcribe en el servidor (CPU, 1 GB de RAM)
MAX_NUEVOS_POR_VISITA = 3    # tope de informes nuevos (llamadas pagadas) por visita
WHISPER_EN_VIVO = os.environ.get("RELATORIA_WHISPER", "base")

st.set_page_config(page_title=f"{NOMBRE} · informes de sesiones", page_icon="🏛️", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 2.2rem; max-width: 1200px;}
.cita {border-left: 3px solid #c9d3e0; padding: .15rem .8rem; margin: .25rem 0 .9rem 0; color: #44505f; font-style: italic;}
.cita a {font-style: normal; font-weight: 600; text-decoration: none; white-space: nowrap;}
.sello {font-style: normal; font-size: .72rem; font-weight: 600; padding: .08rem .45rem; border-radius: 999px; margin-left: .35rem; white-space: nowrap;}
.ok {background: #e3f4ea; color: #17643f;} .corr {background: #fff1d6; color: #7a5200;} .no {background: #fde4e1; color: #a12318;}
.alta {background: #fde4e1; color: #a12318;} .media {background: #fff1d6; color: #7a5200;} .baja {background: #e8edf3; color: #44505f;}
.linea {margin: 0 0 .45rem 0; line-height: 1.45;} .linea a {font-weight: 600; text-decoration: none; margin-right: .5rem; font-variant-numeric: tabular-nums;}
mark {background: #ffe9a8; padding: 0 .1rem;}
</style>""", unsafe_allow_html=True)


# ───────────────────────────────────────────────────────── utilidades
def secreto(nombre: str) -> str:
    try:
        if nombre in st.secrets:
            return str(st.secrets[nombre])
    except Exception:  # sin archivo de secrets
        pass
    return os.environ.get(nombre, "")


@st.cache_data(show_spinner=False)
def _leer_sesion(ruta: str, version: float) -> Sesion:
    return Sesion.leer(ruta)


def sesiones_guardadas() -> dict[str, Path]:
    return {p.stem: p for p in sorted(SESIONES.glob("*.json"))}


@st.cache_resource(show_spinner=False)
def _modelo_de_voz(nombre: str):
    from relatoria.transcribir import cargar_modelo
    return cargar_modelo(nombre, "cpu")


def transcribir_subido(archivo) -> Sesion:
    from relatoria.transcribir import transcribir
    datos = archivo.getvalue()
    huella = hashlib.sha256(datos).hexdigest()[:12]
    if st.session_state.get("audio_huella") == huella:
        return st.session_state["audio_sesion"]
    barra = st.progress(0.0, text=f"Cargando Whisper ({WHISPER_EN_VIVO})…")
    _modelo_de_voz(WHISPER_EN_VIVO)
    with tempfile.NamedTemporaryFile(suffix=Path(archivo.name).suffix) as tmp:
        tmp.write(datos)
        tmp.flush()
        segs, dur = transcribir(
            tmp.name, modelo=WHISPER_EN_VIVO, dispositivo="cpu",
            al_avanzar=lambda h, t: barra.progress(min(h / max(t, 1), 1.0), text=f"Transcribiendo… {hhmmss(h)} de {hhmmss(t)}"))
    barra.empty()
    sesion = Sesion(id=f"audio-{huella}", titulo=Path(archivo.name).stem, duracion_s=round(dur),
                    modelo_asr=f"faster-whisper {WHISPER_EN_VIVO}", segmentos=segs)
    st.session_state["audio_huella"], st.session_state["audio_sesion"] = huella, sesion
    return sesion


def sello(res: Resultado | None) -> str:
    if res is None:
        return ""
    clase, texto = {"verificada": ("ok", "✓ cita verificada"), "otro_minuto": ("corr", "✓ verificada · minuto corregido"),
                    "sin_respaldo": ("no", "✗ sin respaldo en la transcripción")}[res.estado]
    return f'<span class="sello {clase}">{texto}</span>'


def evidencia(item, res: Resultado | None, sesion: Sesion):
    marca = res.marca if res else item.marca
    if res and res.segundos is not None and sesion.url:
        donde = f'<a href="{enlace_al_minuto(sesion.url, res.segundos)}" target="_blank">▶ {marca}</a>'
    else:
        donde = f"<b>{html.escape(marca)}</b>"
    st.markdown(f'<div class="cita">«{html.escape(item.cita_literal)}» {donde}{sello(res)}</div>', unsafe_allow_html=True)


# ───────────────────────────────────────────────────────── barra lateral: entrada
guardadas = sesiones_guardadas()
with st.sidebar:
    st.markdown(f"## 🏛️ {NOMBRE}")
    st.caption(LEMA)

    st.markdown("#### 1 · Sesión")
    opciones = (["Sesión pública transcrita"] if guardadas else []) + ["Subir un audio corto", "Pegar una transcripción"]
    modo = st.radio("Origen", opciones, label_visibility="collapsed")
    sesion: Sesion | None = None
    if modo == "Sesión pública transcrita":
        titulos = {k: _leer_sesion(str(p), p.stat().st_mtime) for k, p in guardadas.items()}
        elegido = st.selectbox("Sesión", list(titulos), label_visibility="collapsed",
                               format_func=lambda k: f"{titulos[k].fecha} · {titulos[k].organo or titulos[k].titulo}")
        sesion = titulos[elegido]
    elif modo == "Subir un audio corto":
        archivo = st.file_uploader("Audio de la sesión", type=["mp3", "m4a", "wav", "ogg", "opus", "mp4", "webm"],
                                   help=f"Hasta {MAX_AUDIO_MB} MB (unos 10 minutos). Las sesiones completas se "
                                        "transcriben fuera de línea con pipeline/transcribir_sesion.py.")
        organo = st.text_input("Comisión u órgano", placeholder="Comisión de Energía y Minas")
        if archivo and archivo.size > MAX_AUDIO_MB * 1e6:
            st.error(f"El archivo pesa {archivo.size / 1e6:.0f} MB; el máximo aquí es {MAX_AUDIO_MB} MB.")
        elif archivo:
            sesion = transcribir_subido(archivo)
            sesion.organo = organo
    else:
        pegado = st.text_area("Transcripción", height=180,
                              placeholder="[00:00:00] Buenos días, señores diputados…\n[00:00:35] Pasamos al primer punto…")
        organo = st.text_input("Comisión u órgano", placeholder="Comisión de Energía y Minas")
        if pegado.strip():
            segs = desde_texto(pegado)
            sesion = Sesion(id="texto-" + hashlib.sha256(pegado.encode()).hexdigest()[:12], titulo="Transcripción pegada",
                            organo=organo, duracion_s=segs[-1].fin if segs else 0, modelo_asr="texto pegado", segmentos=segs)

    st.markdown("#### 2 · Qué vigila tu cliente")
    ya = almacen.guardados(sesion.id) if sesion else []
    sugerido = ", ".join(max(ya, key=len)) if ya else ""
    temas = almacen.temas_limpios(st.text_input(
        "Temas", value=sugerido, key=f"temas-{sesion.id if sesion else ''}", label_visibility="collapsed",
        placeholder="minería, canon, Petroperú", help="Separados por comas. El informe resalta todo lo que se diga sobre ellos.",
    ).split(","))
    cliente = st.text_input("Cliente (opcional)", placeholder="Nombre que irá en el informe")

    en_cache = almacen.leer(sesion, temas) if sesion else None
    clave_api = secreto("ANTHROPIC_API_KEY")
    codigo = secreto("RELATORIA_CODIGO")
    nuevos = st.session_state.get("nuevos", 0)
    codigo_ok = True
    if sesion and not en_cache and codigo:
        codigo_ok = st.text_input("Código de acceso", type="password",
                                  help="Generar un informe nuevo consume la API; los ya generados se ven sin código.") == codigo
    generar = st.button("Ver informe" if en_cache else "Generar informe", type="primary", use_container_width=True,
                        disabled=sesion is None or not sesion.segmentos)
    if en_cache:
        st.caption("Este informe ya está generado: se abre al instante y sin costo.")
    elif sesion:
        st.caption(f"Informe nuevo con Claude ({MODELO}). Quedan {max(0, MAX_NUEVOS_POR_VISITA - nuevos)} en esta visita.")

# ───────────────────────────────────────────────────────── portada
if sesion is None:
    st.title(f"{NOMBRE}")
    st.markdown(f"#### {LEMA}")
    st.markdown(
        "Una sesión de comisión dura entre dos y cuatro horas. Alguien de la consultora tiene que verla completa para "
        "contarle al cliente qué se dijo sobre su sector. **Relatoría** transcribe la sesión con Whisper, le pide a "
        "Claude un informe con estructura fija y **comprueba cada cita contra la transcripción**: lo que aparece entre "
        "comillas lleva el enlace al minuto exacto del video, y lo que no se puede comprobar queda marcado.")
    a, b, c = st.columns(3)
    a.markdown("**1 · Elige la sesión**\n\nUna sesión pública ya transcrita, un audio corto o una transcripción pegada.")
    b.markdown("**2 · Di qué vigila tu cliente**\n\nSectores, empresas, normas o entidades, separados por comas.")
    c.markdown("**3 · Recibe el informe**\n\nResumen, acuerdos, pedidos con plazo y menciones al cliente, en pantalla y en Word.")
    st.info("Empieza en la barra de la izquierda.", icon="👈")
    st.stop()

# ───────────────────────────────────────────────────────── generar o recuperar el informe
llave = (sesion.id, almacen.clave(sesion, temas))
if generar:
    if en_cache:
        st.session_state["informe"] = (llave, *en_cache)
    elif not clave_api:
        st.error("Falta configurar `ANTHROPIC_API_KEY` en los *secrets* de la app para generar informes nuevos.")
    elif not codigo_ok:
        st.error("El código de acceso no coincide.")
    elif nuevos >= MAX_NUEVOS_POR_VISITA:
        st.error(f"Esta visita ya generó {MAX_NUEVOS_POR_VISITA} informes nuevos. Vuelve a cargar la página más tarde.")
    else:
        with st.spinner(f"Claude está leyendo {sesion.palabras:,} palabras de sesión… (entre 30 segundos y 2 minutos)"):
            try:
                inf, uso = generar_informe(sesion, temas, api_key=clave_api)
            except SinClave as e:
                st.error(str(e))
            except ValueError as e:
                st.error(str(e))
            except Exception as e:  # errores de la API: se muestran sin tumbar la app
                st.error(f"No se pudo generar el informe: {type(e).__name__}: {e}")
            else:
                st.session_state["nuevos"] = nuevos + 1
                if modo == "Sesión pública transcrita":
                    almacen.guardar(sesion, temas, inf, uso)   # las sesiones públicas se guardan; lo subido por el usuario no
                st.session_state["informe"] = (llave, inf, uso)

actual = st.session_state.get("informe")
informe: InformeSesion | None = actual[1] if actual and actual[0] == llave else None
uso: Uso | None = actual[2] if informe else None

# ───────────────────────────────────────────────────────── encabezado
st.title(sesion.organo or sesion.titulo)
st.caption(" · ".join(x for x in (sesion.titulo if sesion.organo else "", sesion.fecha, f"{hhmmss(sesion.duracion_s)} de sesión",
                                  f"{sesion.palabras:,} palabras", sesion.modelo_asr) if x))

verif = verificar_informe(informe, sesion.segmentos) if informe else None
if informe:
    r, v = verif["resumen"], verif["items"]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Citas comprobadas", f"{r['con_respaldo']} de {r['citas']}",
              "todas con respaldo" if r["sin_respaldo"] == 0 else f"{r['sin_respaldo']} sin respaldo",
              delta_color="normal" if r["sin_respaldo"] == 0 else "inverse", delta_arrow="off")
    k2.metric("Menciones a tu cliente", len(informe.menciones_cliente))
    k3.metric("Acuerdos y pedidos", len(informe.acuerdos) + len(informe.compromisos))
    k4.metric("Costo de este informe", f"US$ {uso.costo_usd:.2f}", f"{uso.tokens_entrada + uso.tokens_salida:,} tokens",
              delta_color="off", delta_arrow="off")

p_informe, p_cliente, p_trans, p_como = st.tabs(["Informe", "Para tu cliente", "Transcripción", "Cómo funciona"])

with p_informe:
    if not informe:
        st.info("Indica qué vigila tu cliente y pulsa **Generar informe** en la barra de la izquierda. "
                "La transcripción ya está disponible en su pestaña.", icon="👈")
    else:
        izq, der = st.columns([3, 2], gap="large")
        with izq:
            st.subheader("Resumen ejecutivo")
            st.write(informe.resumen_ejecutivo)
            st.subheader("Acuerdos y votaciones")
            if not informe.acuerdos:
                st.caption("La sesión no registra acuerdos ni votaciones.")
            for i, a in enumerate(informe.acuerdos):
                st.markdown(f"**{a.asunto}** · _{a.tipo}_  \n{a.resultado}")
                evidencia(a, v.get(("acuerdos", i)), sesion)
            st.subheader("Intervenciones relevantes")
            for i, x in enumerate(informe.intervenciones):
                st.markdown(f"**{x.orador}**{', ' + x.cargo if x.cargo else ''} · _{x.postura}_  \n{x.resumen}")
                evidencia(x, v.get(("intervenciones", i)), sesion)
        with der:
            st.subheader("Agenda")
            for a in informe.agenda:
                st.markdown(f"`{a.marca}` **{a.tema}**  \n{a.resumen}")
            st.subheader("Pedidos y compromisos")
            if not informe.compromisos:
                st.caption("No se registran pedidos ni compromisos.")
            for i, c in enumerate(informe.compromisos):
                st.markdown(f"**{c.responsable}** · plazo: {c.plazo}  \n{c.compromiso}")
                evidencia(c, v.get(("compromisos", i)), sesion)
            if informe.proximos_pasos:
                st.subheader("Próximos pasos")
                st.markdown("\n".join(f"- {x}" for x in informe.proximos_pasos))
            if informe.limitaciones:
                with st.expander("Limitaciones de esta transcripción"):
                    st.markdown("\n".join(f"- {x}" for x in informe.limitaciones))
        st.divider()
        nombre = f"informe_{sesion.id}.docx"
        st.download_button("Descargar informe en Word (.docx)", a_docx(informe, sesion, verif, temas, cliente), nombre,
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary")

with p_cliente:
    if not informe:
        st.info("Genera el informe para ver las menciones a los temas de tu cliente.")
    elif not temas:
        st.info("Escribe en la barra lateral los temas que vigila tu cliente y vuelve a generar el informe.")
    else:
        st.caption("Temas vigilados: " + " · ".join(temas))
        if informe.alertas:
            st.subheader("Alertas")
            for x in informe.alertas:
                st.warning(x, icon="⚠️")
        st.subheader(f"Menciones ({len(informe.menciones_cliente)})")
        if not informe.menciones_cliente:
            st.success("La sesión no tocó los temas vigilados.")
        orden = {"alta": 0, "media": 1, "baja": 2}
        for i, m in sorted(enumerate(informe.menciones_cliente), key=lambda par: orden[par[1].relevancia]):
            st.markdown(f'**{html.escape(m.tema_vigilado)}** <span class="sello {m.relevancia}">relevancia {m.relevancia}</span>'
                        f" · {html.escape(m.quien)}", unsafe_allow_html=True)
            st.write(m.que_se_dijo)
            evidencia(m, v.get(("menciones_cliente", i)), sesion)

with p_trans:
    c1, c2 = st.columns([3, 1])
    buscar = c1.text_input("Buscar en la transcripción", placeholder="canon, Petroperú, cuarto intermedio…")
    lineas = bloques(sesion.segmentos, 30)
    if buscar.strip():
        aguja = normalizar(buscar)
        lineas = [b for b in lineas if aguja in normalizar(b.texto)]
    c2.metric("Bloques", f"{len(lineas):,}")
    if sesion.url:
        st.caption("Cada marca abre el video oficial en ese minuto.")
    tope = 400
    partes = []
    for b in lineas[:tope]:
        texto = html.escape(b.texto)
        if buscar.strip():
            import re
            texto = re.sub(f"({re.escape(html.escape(buscar.strip()))})", r"<mark>\1</mark>", texto, flags=re.I)
        marca = (f'<a href="{enlace_al_minuto(sesion.url, b.inicio)}" target="_blank">{hhmmss(b.inicio)}</a>'
                 if sesion.url else f"<a>{hhmmss(b.inicio)}</a>")
        partes.append(f'<p class="linea">{marca}{texto}</p>')
    st.markdown("".join(partes) or "_Sin coincidencias._", unsafe_allow_html=True)
    if len(lineas) > tope:
        st.caption(f"Se muestran los primeros {tope} bloques de {len(lineas):,}. Usa el buscador para llegar al resto.")

with p_como:
    st.markdown(f"""
**1. Transcripción (Whisper).** El audio de la sesión pública pasa por *faster-whisper* con detector de voz, para no
transcribir silencios, y con una lista de términos parlamentarios para que no deforme nombres propios. Las sesiones
completas se transcriben fuera de línea (`pipeline/transcribir_sesion.py`); aquí se transcriben audios cortos.

**2. Informe (LLM con salida estructurada).** Claude (`{MODELO}`) lee la sesión completa y devuelve el informe en un
esquema fijo de Pydantic: agenda, intervenciones, acuerdos, compromisos y menciones al cliente. Cada hallazgo debe
traer una cita literal y su minuto.

**3. Verificación.** Un programa, no el modelo, busca cada cita en la transcripción con coincidencia aproximada.
Si la encuentra, corrige el minuto con el lugar real y enlaza el video. Si no la encuentra, la marca en rojo.

**Lo que no hace.** No identifica a quien habla por su voz: usa el nombre que se dice en la sesión. La transcripción
automática se equivoca en nombres y cifras, y por eso cada cita lleva el enlace para confirmarla en el video.

**Datos.** Solo sesiones públicas del Congreso de la República, tomadas de su canal oficial. Los audios y textos que
subes aquí no se guardan en el servidor.
""")

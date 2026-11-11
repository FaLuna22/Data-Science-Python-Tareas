import io

from docx import Document

from relatoria import almacen
from relatoria.esquema import SECCIONES_CON_CITA, InformeSesion
from relatoria.exportar import a_docx
from relatoria.informe import Uso, _mensaje
from relatoria.transcripcion import a_segundos, bloques, con_marcas, desde_texto, enlace_al_minuto, hhmmss
from relatoria.verificar import Indice, normalizar, verificar_cita, verificar_informe


# ── transcripción
def test_marcas_de_tiempo_ida_y_vuelta():
    assert hhmmss(3725.9) == "01:02:05"
    assert a_segundos("01:02:05") == 3725
    assert a_segundos("[62:05]") == 3725
    assert a_segundos("sin marca") is None


def test_bloques_unen_segmentos_sin_perder_texto(sesion):
    b = bloques(sesion.segmentos, cada=80)
    assert len(b) < len(sesion.segmentos)
    assert " ".join(x.texto for x in b) == " ".join(s.texto for s in sesion.segmentos)
    assert con_marcas(sesion.segmentos).startswith("[00:00:00] Buenos días")


def test_texto_pegado_con_y_sin_marcas():
    con = desde_texto("[00:01:00] Se abre la sesión.\n[00:02:30] Se aprueba el acta.")
    assert [s.inicio for s in con] == [60.0, 150.0] and con[0].fin == 150.0
    sin = desde_texto("Primer párrafo.\n\nSegundo párrafo.")
    assert [s.inicio for s in sin] == [0.0, 30.0]


def test_enlace_al_minuto():
    assert enlace_al_minuto("https://www.youtube.com/watch?v=abc", 185.7) == "https://www.youtube.com/watch?v=abc&t=185s"
    assert enlace_al_minuto("", 10) == ""


# ── verificación de citas
def test_normalizar_quita_tildes_y_puntuacion():
    assert normalizar("¡Señor  Presidente: aprobó!") == "senor presidente aprobo"


def test_cita_real_se_verifica_aunque_cambien_tildes_y_comas(sesion, informe):
    r = verificar_cita(informe.intervenciones[0].cita_literal, "00:01:10", Indice(sesion.segmentos))
    assert r.estado == "verificada" and r.parecido >= 95 and r.segundos == 70.0


def test_cita_real_con_minuto_equivocado_se_corrige(sesion, informe):
    r = verificar_cita(informe.acuerdos[0].cita_literal, "00:40:00", Indice(sesion.segmentos))
    assert r.estado == "otro_minuto" and r.marca == "00:03:05"


def test_cita_inventada_queda_sin_respaldo(sesion, informe):
    r = verificar_cita(informe.menciones_cliente[0].cita_literal, "00:02:00", Indice(sesion.segmentos))
    assert r.estado == "sin_respaldo" and r.segundos is None


def test_cita_demasiado_corta_no_se_acepta(sesion):
    assert verificar_cita("se va a votar", "00:02:30", Indice(sesion.segmentos)).estado == "sin_respaldo"


def test_resumen_de_verificacion(sesion, informe):
    v = verificar_informe(informe, sesion.segmentos)
    assert v["resumen"] == {"citas": 4, "con_respaldo": 3, "sin_respaldo": 1, "minuto_corregido": 1, "porcentaje": 75.0}
    assert set(s for s, _ in v["items"]) == set(SECCIONES_CON_CITA)


# ── esquema, mensaje y costo
def test_el_esquema_exige_cita_y_marca_en_cada_hallazgo():
    defs = InformeSesion.model_json_schema()["$defs"]
    for modelo in ("Intervencion", "Acuerdo", "Compromiso", "MencionCliente"):
        assert {"cita_literal", "marca"} <= set(defs[modelo]["required"])


def test_el_mensaje_lleva_temas_y_transcripcion_con_marcas(sesion):
    m = _mensaje(sesion, ["GLP", "canon"])
    assert "- GLP\n- canon" in m and "[00:01:10] Señor presidente" in m
    assert "no indicó temas" in _mensaje(sesion, [])


def test_costo_por_sesion():
    assert Uso("claude-opus-5-5", 60_000, 6_000).costo_usd == 0.36


# ── caché en disco
def test_cache_distingue_temas_y_no_el_orden(tmp_path, sesion, informe):
    uso = Uso("claude-opus-5-5", 1000, 500)
    almacen.guardar(sesion, ["GLP", " canon "], informe, uso, tmp_path)
    assert almacen.leer(sesion, ["canon", "glp"], tmp_path) == (informe, uso)
    assert almacen.leer(sesion, ["minería"], tmp_path) is None
    assert almacen.guardados("prueba", tmp_path) == [["GLP", "canon"]]


# ── exportación
def test_docx_trae_secciones_citas_y_avisa_la_que_no_tiene_respaldo(sesion, informe):
    v = verificar_informe(informe, sesion.segmentos)
    doc = Document(io.BytesIO(a_docx(informe, sesion, v, ["GLP"], cliente="Cliente de prueba")))
    texto = "\n".join(p.text for p in doc.paragraphs)
    for esperado in ("Resumen ejecutivo", "Lo que le importa al cliente", "Acuerdos y votaciones",
                     "Cliente de prueba", "CITA SIN RESPALDO", "3 de 4"):
        assert esperado in texto
    assert doc.tables[0].rows[1].cells[2].text == "15 días"
    enlaces = [r.target_ref for r in doc.part.rels.values() if "hyperlink" in r.reltype]
    assert "https://www.youtube.com/watch?v=XXXXXXXXXXX&t=185s" in enlaces

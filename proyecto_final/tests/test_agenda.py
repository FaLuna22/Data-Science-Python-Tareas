"""Agenda del canal: lectura de títulos reales, feed, catálogo y seguimiento. Sin red."""
from relatoria import agenda
from relatoria.agenda import Catalogo, Emision, agrupar_variantes, analizar_titulo, coincide, leer_rss


# ── títulos tal como los publica el canal oficial
def test_comision_con_camara_y_separador_barra():
    assert analizar_titulo("🔴EN VIVO: Comisión de Constitución, Reglamento y Relaciones Exteriores del Senado | 10/11/2026") == {
        "organo": "Comisión de Constitución, Reglamento y Relaciones Exteriores", "camara": "Senado",
        "tipo": "comision", "fecha": "2026-11-10"}


def test_separador_l_y_anio_de_dos_cifras():
    d = analizar_titulo("🔴EN VIVO: Comisión de Infraestructura, Vivienda y Transportes de la Cámara de Diputados l 10/11/26")
    assert (d["organo"], d["camara"], d["fecha"]) == ("Comisión de Infraestructura, Vivienda y Transportes", "Diputados", "2026-11-10")


def test_sin_camara_y_l_pegada_al_nombre():
    assert analizar_titulo("🔴 EN VIVO: Comisión de Economía, Banca, Finanzas e Inteligencia Financiera  11/11/2026")["camara"] == ""
    assert analizar_titulo("EN VIVO: Comisión de Modernización de la Gestión del Estado y Contraloríal 10/11/2026")["organo"] == \
        "Comisión de Modernización de la Gestión del Estado y Contraloría"


def test_pleno_con_fecha_en_letras_conserva_la_camara():
    d = analizar_titulo("🔴EN VIVO: Sesión del Pleno de la Cámara de Diputados | 10 DE NOVIEMBRE DEL 2026")
    assert d == {"organo": "Pleno de la Cámara de Diputados", "camara": "Diputados", "tipo": "pleno", "fecha": "2026-11-10"}


def test_sesion_de_la_comision_y_otros_eventos():
    assert analizar_titulo("🔴EN VIVO: Sesión de la Comisión de Salud de la Cámara de Diputados | 27/10/2026")["organo"] == "Comisión de Salud"
    d = analizar_titulo("🔴EN VIVO: Conferencia de prensa del presidente del Congreso | 10/11/2026")
    assert d["tipo"] == "otro" and d["fecha"] == "2026-11-10"


def test_titulo_en_ingles_usa_mes_dia():
    assert analizar_titulo("🔴LIVE: Working meeting with the Delegation | 11/04/2026")["fecha"] == "2026-11-04"


# ── feed RSS
RSS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
 <entry><yt:videoId>abc123def45</yt:videoId><title>🔴EN VIVO: Comisión de Energía y Minas | 10/11/2026</title>
  <published>2026-11-11T03:00:00+00:00</published></entry>
 <entry><yt:videoId>xyz987uvw65</yt:videoId><title>Mesa de trabajo sobre Petroperú</title>
  <published>2026-11-11T03:00:00+00:00</published></entry>
</feed>"""


def test_feed_rss_con_fecha_de_respaldo_en_hora_de_lima():
    a, b = leer_rss(RSS)
    assert (a.id, a.organo, a.tipo, a.fecha, a.estado) == ("abc123def45", "Comisión de Energía y Minas", "comision", "2026-11-10", "")
    assert b.fecha == "2026-11-10"          # 03:00 UTC del 11 son las 22:00 del 10 en Lima
    assert a.url == "https://www.youtube.com/watch?v=abc123def45"


# ── catálogo
def test_catalogo_suma_actualiza_y_persiste(tmp_path):
    ruta = tmp_path / "catalogo.json"
    cat = Catalogo(ruta)
    assert cat.incorporar(leer_rss(RSS)) == ["abc123def45", "xyz987uvw65"]
    assert cat.incorporar(leer_rss(RSS)) == []                     # nada nuevo la segunda vez
    assert cat.actualizar_estado("abc123def45", {"estado": "en_vivo"})
    assert not cat.actualizar_estado("abc123def45", {"estado": "en_vivo"})
    cat.incorporar([Emision.desde_titulo("abc123def45", "🔴EN VIVO: Comisión de Energía y Minas | 10/11/2026",
                                         estado="terminada", duracion_s=5320)])
    cat.guardar()
    otro = Catalogo(ruta)
    e = otro.emisiones["abc123def45"]
    assert (e.estado, e.duracion_s, e.fecha) == ("terminada", 5320, "2026-11-10")
    assert otro.organos() == ["Comisión de Energía y Minas"]


def test_catalogo_danado_no_rompe(tmp_path):
    (tmp_path / "catalogo.json").write_text("{no es json", encoding="utf-8")
    assert Catalogo(tmp_path / "catalogo.json").emisiones == {}


# ── seguimiento
def test_variantes_de_un_mismo_nombre_se_agrupan():
    c = agrupar_variantes({"Comisión de Defensa Nacional y Orden Interno": 3, "Comisión de Defensa Nacional": 1,
                           "Comisión de Salud": 4, "Comisión en asuntos de Salud, Educación, Mujer y Desarrollo Social": 2,
                           "Comisión Bicameral de Presupuesto y de la Cuenta General de la República": 1,
                           "Comisión Bicameral de Presupuesto y Cuenta General de la Republica": 1})
    assert c["Comisión de Defensa Nacional"] == "Comisión de Defensa Nacional y Orden Interno"
    assert c["Comisión en asuntos de Salud, Educación, Mujer y Desarrollo Social"] != "Comisión de Salud"
    assert c["Comisión Bicameral de Presupuesto y Cuenta General de la Republica"] == \
        "Comisión Bicameral de Presupuesto y de la Cuenta General de la República"


def test_coincide_por_comision_por_mencion_y_por_palabra():
    salud = Emision.desde_titulo("a" * 11, "🔴EN VIVO: Comisión de Salud del Senado | 10/11/2026")
    mesa = Emision.desde_titulo("b" * 11, "Mesa de trabajo de la Comisión de Salud de la Cámara de Diputados")
    petro = Emision.desde_titulo("c" * 11, "Mesa de diálogo entre el Sindicato y las autoridades de PETROPERÚ")
    corto = Emision.desde_titulo("d" * 11, "Comisión de Defensa Nacional 10/11/2026")
    assert coincide(salud, ["comision de salud"]) and coincide(mesa, ["Comisión de Salud"])
    assert not coincide(petro, ["Comisión de Salud"])
    assert coincide(petro, [], ["petroperu"])
    canon = {"Comisión de Defensa Nacional": "Comisión de Defensa Nacional y Orden Interno"}
    assert coincide(corto, ["Comisión de Defensa Nacional y Orden Interno"], canonico=canon)


def test_transcritas_lee_la_carpeta(tmp_path):
    (tmp_path / "2EIYKlqJBT8.json").write_text("{}", encoding="utf-8")
    assert agenda.transcritas(tmp_path) == {"2EIYKlqJBT8"}

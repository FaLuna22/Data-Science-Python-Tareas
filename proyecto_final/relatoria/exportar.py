"""Informe -> .docx (python-docx) y -> Markdown, con el estado de verificación de cada cita."""
from __future__ import annotations

import io
from datetime import date

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from . import NOMBRE
from .esquema import InformeSesion
from .transcripcion import Sesion, enlace_al_minuto
from .verificar import Resultado

ETIQUETA = {"verificada": "cita verificada", "otro_minuto": "cita verificada (minuto corregido)",
            "sin_respaldo": "CITA SIN RESPALDO EN LA TRANSCRIPCIÓN"}
TINTA, GRIS, ROJO, VERDE = RGBColor(0x1B, 0x2A, 0x41), RGBColor(0x5B, 0x65, 0x75), RGBColor(0xB4, 0x23, 0x18), RGBColor(0x1F, 0x7A, 0x4D)


def _enlace(parrafo, texto: str, url: str):
    """python-docx no trae hipervínculos: se arma el elemento a mano."""
    rid = parrafo.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                                 is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), rid)
    r, rpr = OxmlElement("w:r"), OxmlElement("w:rPr")
    color, sub = OxmlElement("w:color"), OxmlElement("w:u")
    color.set(qn("w:val"), "1F5FA8")
    sub.set(qn("w:val"), "single")
    rpr.append(color)
    rpr.append(sub)
    t = OxmlElement("w:t")
    t.text = texto
    r.append(rpr)
    r.append(t)
    h.append(r)
    parrafo._p.append(h)


def _evidencia(doc, item, res: Resultado | None, sesion: Sesion):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(18)
    c = p.add_run(f"«{item.cita_literal}» ")
    c.italic = True
    c.font.color.rgb = GRIS
    marca = res.marca if res else item.marca
    if res and res.segundos is not None and sesion.url:
        _enlace(p, f"[{marca}]", enlace_al_minuto(sesion.url, res.segundos))
    else:
        p.add_run(f"[{marca}]").font.color.rgb = GRIS
    if res:
        e = p.add_run(f"  · {ETIQUETA[res.estado]}")
        e.font.size = Pt(8)
        e.font.color.rgb = ROJO if res.estado == "sin_respaldo" else VERDE


def _item(doc, titulo: str, cuerpo: str):
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(titulo).bold = True
    if cuerpo:
        p.add_run(f" {cuerpo}")


def a_docx(informe: InformeSesion, sesion: Sesion, verificacion: dict | None = None,
           temas: list[str] | None = None, cliente: str = "") -> bytes:
    v = (verificacion or {}).get("items", {})
    r = (verificacion or {}).get("resumen")
    doc = Document()
    base = doc.styles["Normal"]
    base.font.name, base.font.size = "Calibri", Pt(10.5)
    for nivel in (1, 2):
        doc.styles[f"Heading {nivel}"].font.color.rgb = TINTA

    t = doc.add_heading("Informe de sesión", level=0)
    t.alignment = WD_ALIGN_PARAGRAPH.LEFT
    sub = doc.add_paragraph()
    sub.add_run(informe.organo).bold = True
    sub.add_run(f"\n{informe.tipo_sesion} · {sesion.fecha or 'fecha no indicada'}")
    if cliente:
        sub.add_run(f"\nPreparado para: {cliente}")
    if temas:
        sub.add_run(f"\nTemas vigilados: {', '.join(temas)}")
    if sesion.url:
        f = doc.add_paragraph("Fuente: ")
        _enlace(f, sesion.url, sesion.url)

    doc.add_heading("Resumen ejecutivo", level=1)
    doc.add_paragraph(informe.resumen_ejecutivo)

    if informe.menciones_cliente or informe.alertas:
        doc.add_heading("Lo que le importa al cliente", level=1)
        for a in informe.alertas:
            doc.add_paragraph(a, style="List Bullet")
        for i, m in enumerate(informe.menciones_cliente):
            _item(doc, f"{m.tema_vigilado} (relevancia {m.relevancia}) — {m.quien}:", m.que_se_dijo)
            _evidencia(doc, m, v.get(("menciones_cliente", i)), sesion)

    if informe.agenda:
        doc.add_heading("Agenda", level=1)
        for a in informe.agenda:
            _item(doc, f"[{a.marca}] {a.tema}.", a.resumen)

    if informe.acuerdos:
        doc.add_heading("Acuerdos y votaciones", level=1)
        for i, a in enumerate(informe.acuerdos):
            _item(doc, f"{a.asunto} ({a.tipo}):", a.resultado)
            _evidencia(doc, a, v.get(("acuerdos", i)), sesion)

    if informe.compromisos:
        doc.add_heading("Pedidos y compromisos", level=1)
        tabla = doc.add_table(rows=1, cols=4)
        tabla.style = "Light Grid Accent 1"
        for celda, nombre in zip(tabla.rows[0].cells, ("Responsable", "Compromiso", "Plazo", "Minuto")):
            celda.text = nombre
        for i, c in enumerate(informe.compromisos):
            res = v.get(("compromisos", i))
            fila = tabla.add_row().cells
            fila[0].text, fila[1].text, fila[2].text = c.responsable, c.compromiso, c.plazo
            fila[3].text = (res.marca if res else c.marca) + (" (sin respaldo)" if res and res.estado == "sin_respaldo" else "")

    if informe.intervenciones:
        doc.add_heading("Intervenciones relevantes", level=1)
        for i, x in enumerate(informe.intervenciones):
            quien = x.orador + (f", {x.cargo}" if x.cargo else "")
            _item(doc, f"{quien} ({x.postura}):", x.resumen)
            _evidencia(doc, x, v.get(("intervenciones", i)), sesion)

    if informe.proximos_pasos:
        doc.add_heading("Próximos pasos", level=1)
        for x in informe.proximos_pasos:
            doc.add_paragraph(x, style="List Bullet")

    doc.add_heading("Cómo leer este informe", level=1)
    if r and r["citas"]:
        doc.add_paragraph(
            f"Citas comprobadas contra la transcripción: {r['con_respaldo']} de {r['citas']} "
            f"({r['porcentaje']} %). En {r['minuto_corregido']} se corrigió el minuto. "
            f"Sin respaldo: {r['sin_respaldo']}.")
    for x in informe.limitaciones:
        doc.add_paragraph(x, style="List Bullet")
    pie = doc.add_paragraph(
        f"Generado con {NOMBRE} el {date.today():%d/%m/%Y} a partir de la transcripción automática "
        f"({sesion.modelo_asr or 'modelo no indicado'}) de una sesión pública. La transcripción puede tener "
        "errores en nombres y cifras: confirme en el video, con el enlace de cada cita, antes de citar a terceros.")
    pie.runs[0].font.size = Pt(8)
    pie.runs[0].font.color.rgb = GRIS

    salida = io.BytesIO()
    doc.save(salida)
    return salida.getvalue()

"""Datos de prueba inventados (no son de ninguna sesión real): solo ejercitan el código sin red ni clave."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from relatoria.esquema import Acuerdo, Compromiso, InformeSesion, Intervencion, MencionCliente, PuntoAgenda  # noqa: E402
from relatoria.transcripcion import Segmento, Sesion  # noqa: E402

LINEAS = [
    (0, "Buenos días, señores diputados. Con el quorum reglamentario se inicia la sesión ordinaria de la comisión."),
    (35, "Pasamos al primer punto de la agenda, el predictamen sobre el fondo de estabilización de precios."),
    (70, "Señor presidente, mi bancada considera que el fondo debe incluir al gas licuado de petróleo para las regiones del sur."),
    (110, "Pido que el Ministerio de Energía y Minas remita en quince días el informe de deuda del fondo."),
    (150, "Se va a votar el predictamen. Los que estén a favor, sírvanse levantar la mano."),
    (185, "Ha sido aprobado por mayoría. Se levanta la sesión."),
]


@pytest.fixture
def sesion() -> Sesion:
    segs = [Segmento(float(t), float(t) + 30, x) for t, x in LINEAS]
    return Sesion(id="prueba", titulo="Sesión de prueba", organo="Comisión de prueba", fecha="2026-01-01",
                  url="https://www.youtube.com/watch?v=XXXXXXXXXXX", duracion_s=215, modelo_asr="ninguno", segmentos=segs)


@pytest.fixture
def informe() -> InformeSesion:
    return InformeSesion(
        organo="Comisión de prueba", tipo_sesion="Ordinaria", resumen_ejecutivo="Se aprobó un predictamen.",
        agenda=[PuntoAgenda(tema="Predictamen del fondo", resumen="Se debatió y se votó.", marca="00:00:35")],
        intervenciones=[Intervencion(
            orador="No identificado", cargo="diputado", postura="con observaciones", resumen="Pide incluir el GLP.",
            # cita real, con tildes y puntuación distintas, y la marca correcta
            cita_literal="mi bancada considera que el fondo debe incluir al gas licuado de petroleo, para las regiones del sur",
            marca="00:01:10")],
        acuerdos=[Acuerdo(
            asunto="Predictamen del fondo", tipo="votación", resultado="Aprobado por mayoría; no se indica el conteo.",
            # cita real, pero con la marca equivocada (se dijo en 00:03:05)
            cita_literal="Ha sido aprobado por mayoría. Se levanta la sesión.", marca="00:40:00")],
        compromisos=[Compromiso(
            responsable="Ministerio de Energía y Minas", compromiso="Remitir el informe de deuda del fondo.",
            plazo="15 días",
            cita_literal="Pido que el Ministerio de Energía y Minas remita en quince días el informe de deuda del fondo.",
            marca="00:01:50")],
        menciones_cliente=[MencionCliente(
            tema_vigilado="GLP", relevancia="alta", quien="No identificado", que_se_dijo="Se anunció un impuesto nuevo.",
            # cita inventada: no está en la transcripción
            cita_literal="el gobierno creará un impuesto selectivo de veinte por ciento al gas desde enero próximo",
            marca="00:02:00")],
        alertas=["El GLP podría entrar al fondo."], proximos_pasos=["El predictamen pasa al Pleno."],
        limitaciones=["Los oradores no se identifican."],
    )

"""Esquema del informe: lo que el LLM está obligado a devolver (salida estructurada, sesión 08).

Cada hallazgo lleva una `cita_literal` copiada de la transcripción y la `marca` de tiempo donde
se dijo. Con esos dos campos, `verificar.py` comprueba que la cita exista de verdad.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MARCA = "Marca de tiempo hh:mm:ss de la línea de la transcripción donde empieza la cita."
CITA = ("Frase copiada palabra por palabra de la transcripción (entre 8 y 40 palabras), sin corregir "
        "ni resumir. Si no hay una frase que lo respalde, no incluyas el ítem.")


class PuntoAgenda(BaseModel):
    tema: str = Field(description="Punto de agenda o tema tratado, en una línea.")
    resumen: str = Field(description="Qué se discutió y en qué quedó, en 2 o 3 oraciones.")
    marca: str = Field(description=MARCA)


class Intervencion(BaseModel):
    orador: str = Field(description="Nombre de quien habla, tal como se le nombra en la sesión. "
                                    "'No identificado' si la transcripción no lo dice.")
    cargo: str = Field(description="Cargo o institución (diputado, ministro, funcionario, invitado). "
                                   "Cadena vacía si no se menciona.")
    postura: Literal["a favor", "en contra", "con observaciones", "informativa", "no clara"]
    resumen: str = Field(description="Idea central de la intervención, en 1 o 2 oraciones.")
    cita_literal: str = Field(description=CITA)
    marca: str = Field(description=MARCA)


class Acuerdo(BaseModel):
    asunto: str = Field(description="Qué se acordó o se sometió a votación.")
    tipo: Literal["votación", "acuerdo sin votación", "dispensa o trámite", "pendiente"]
    resultado: str = Field(description="Aprobado, rechazado, pasa a cuarto intermedio, etc. Incluye el conteo "
                                       "de votos solo si se dice en la sesión.")
    cita_literal: str = Field(description=CITA)
    marca: str = Field(description=MARCA)


class Compromiso(BaseModel):
    responsable: str = Field(description="Persona o institución que asume el compromiso o recibe el pedido.")
    compromiso: str = Field(description="Qué debe hacer o entregar.")
    plazo: str = Field(description="Plazo o fecha mencionada. 'Sin plazo' si no se dice.")
    cita_literal: str = Field(description=CITA)
    marca: str = Field(description=MARCA)


class MencionCliente(BaseModel):
    tema_vigilado: str = Field(description="Cuál de los temas vigilados por el cliente se toca.")
    relevancia: Literal["alta", "media", "baja"] = Field(
        description="alta: decisión, votación o anuncio que afecta al tema; media: posición o pedido "
                    "sobre el tema; baja: mención de pasada.")
    quien: str = Field(description="Quién lo dijo. 'No identificado' si no se sabe.")
    que_se_dijo: str = Field(description="Qué se dijo sobre el tema y por qué le importa al cliente, en 1 o 2 oraciones.")
    cita_literal: str = Field(description=CITA)
    marca: str = Field(description=MARCA)


class InformeSesion(BaseModel):
    organo: str = Field(description="Comisión u órgano que sesiona, según la transcripción y los datos dados.")
    tipo_sesion: str = Field(description="Ordinaria, extraordinaria, audiencia pública, etc. 'No se indica' si no se dice.")
    resumen_ejecutivo: str = Field(description="Lo esencial de la sesión en 4 a 6 oraciones, para alguien que no la vio.")
    agenda: list[PuntoAgenda]
    intervenciones: list[Intervencion] = Field(description="Las intervenciones más relevantes (máximo 12).")
    acuerdos: list[Acuerdo]
    compromisos: list[Compromiso] = Field(description="Pedidos de información, encargos y compromisos con responsable.")
    menciones_cliente: list[MencionCliente] = Field(
        description="Todo lo dicho sobre los temas vigilados por el cliente. Lista vacía si no se tocan.")
    alertas: list[str] = Field(description="Riesgos u oportunidades para el cliente que se desprenden de la sesión. "
                                           "Lista vacía si no hay temas vigilados o no se tocan.")
    proximos_pasos: list[str] = Field(description="Qué viene después: próximas sesiones, plazos, votaciones pendientes.")
    limitaciones: list[str] = Field(description="Tramos inaudibles, oradores no identificados o dudas de la transcripción "
                                                "que el lector debe conocer.")


SECCIONES_CON_CITA = ("intervenciones", "acuerdos", "compromisos", "menciones_cliente")

"""Transcripción -> informe estructurado con Claude (salidas estructuradas, sesión 08).

Una sola llamada: una sesión de 3 horas son ~60 mil tokens y cabe completa en el contexto, así
el modelo ve toda la sesión y no pierde acuerdos que se cierran una hora después de abrirse.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from .esquema import InformeSesion
from .transcripcion import Sesion, con_marcas

MODELO = os.environ.get("RELATORIA_MODELO", "claude-opus-5-5")
# USD por millón de tokens (entrada, salida). Precios de lista de noviembre de 2026.
PRECIOS = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.1, 0.5)}
MAX_PALABRAS = 120_000   # ~8 horas de sesión; por encima se rechaza en vez de recortar en silencio

SISTEMA = """Eres relator de sesiones parlamentarias del Perú. Trabajas para una consultora de asuntos \
públicos que debe informar a su cliente qué pasó en una sesión sin haberla visto.

Recibirás la transcripción automática de una sesión pública, con una marca de tiempo [hh:mm:ss] al \
inicio de cada línea. La hizo un modelo de voz: puede traer nombres mal escritos y frases cortadas.

Reglas:
- Usa solo lo que está en la transcripción. No completes con lo que sabes del Congreso, de los \
proyectos de ley o de las personas. Si algo no se dice, no lo pongas.
- Cada `cita_literal` debe copiarse palabra por palabra de la transcripción, incluso con sus errores, \
y su `marca` debe ser la de la línea donde está. Un programa buscará cada cita en la transcripción \
y marcará como «sin respaldo» las que no encuentre, así que una cita parafraseada cuenta como error.
- No inventes conteos de votos, plazos, números de proyecto ni cargos. Si no se oyen, dilo en el campo \
correspondiente ("no se indica el conteo", "Sin plazo").
- Si un nombre parece mal transcrito, escríbelo como aparece y anótalo en `limitaciones`.
- Escribe en español del Perú, en tono de informe profesional: oraciones completas, sin adjetivos de \
opinión y sin recomendar posiciones políticas.
- `menciones_cliente` y `alertas` dependen de los temas vigilados que te indiquen. Incluye también \
menciones indirectas (sinónimos, entidades o normas del mismo tema) y explica la relación. Si no se \
indican temas, o la sesión no los toca, deja ambas listas vacías."""


@dataclass
class Uso:
    modelo: str
    tokens_entrada: int
    tokens_salida: int

    @property
    def costo_usd(self) -> float:
        entrada, salida = PRECIOS.get(self.modelo, PRECIOS["claude-opus-5-5"])
        return round((self.tokens_entrada * entrada + self.tokens_salida * salida) / 1e6, 4)


class SinClave(RuntimeError):
    pass


def _mensaje(sesion: Sesion, temas: list[str]) -> str:
    vigilados = "\n".join(f"- {t}" for t in temas) if temas else "(el cliente no indicó temas)"
    return (
        f"<datos_de_la_sesion>\nTítulo publicado: {sesion.titulo}\nÓrgano: {sesion.organo or 'no indicado'}\n"
        f"Fecha: {sesion.fecha or 'no indicada'}\n</datos_de_la_sesion>\n\n"
        f"<temas_vigilados_por_el_cliente>\n{vigilados}\n</temas_vigilados_por_el_cliente>\n\n"
        f"<transcripcion>\n{con_marcas(sesion.segmentos)}\n</transcripcion>\n\n"
        "Redacta el informe de esta sesión."
    )


def generar_informe(sesion: Sesion, temas: list[str] | None = None, api_key: str | None = None,
                    modelo: str = MODELO) -> tuple[InformeSesion, Uso]:
    import anthropic

    if sesion.palabras > MAX_PALABRAS:
        raise ValueError(f"La transcripción tiene {sesion.palabras:,} palabras; el máximo es {MAX_PALABRAS:,}. "
                         "Divide la sesión en dos partes.")
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SinClave("Falta ANTHROPIC_API_KEY (variable de entorno o secrets de Streamlit).")

    cliente = anthropic.Anthropic(api_key=api_key, max_retries=2)
    # En streaming: la entrada es larga y así no se corta por tiempo de espera.
    with cliente.beta.messages.stream(
        model=modelo,
        max_tokens=32000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        system=SISTEMA,
        messages=[{"role": "user", "content": _mensaje(sesion, temas or [])}],
        output_format=InformeSesion,
        # Si un filtro de seguridad rechaza la sesión, la API reintenta sola con otro modelo.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    ) as flujo:
        respuesta = flujo.get_final_message()

    if respuesta.stop_reason == "refusal":
        raise RuntimeError("El modelo declinó procesar esta transcripción.")
    if respuesta.stop_reason == "max_tokens" or respuesta.parsed_output is None:
        raise RuntimeError("El informe salió incompleto (se alcanzó el límite de salida). Vuelve a intentarlo.")
    uso = Uso(respuesta.model, respuesta.usage.input_tokens, respuesta.usage.output_tokens)
    return respuesta.parsed_output, uso

"""Verificación de citas: ¿lo que el informe pone entre comillas se dijo de verdad?

El LLM devuelve, para cada hallazgo, una `cita_literal` y una `marca` de tiempo. Aquí se busca esa
cita en la transcripción con coincidencia aproximada (rapidfuzz) y se corrige la marca con el
lugar donde realmente aparece. Lo que no se encuentra queda marcado como «sin respaldo».
"""
from __future__ import annotations

import bisect
import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz

from .esquema import SECCIONES_CON_CITA, InformeSesion
from .transcripcion import Segmento, a_segundos, hhmmss

UMBRAL = 85.0          # parecido mínimo (0-100) para dar la cita por verificada
TOLERANCIA_S = 120     # diferencia aceptada entre la marca del LLM y el lugar real
MIN_PALABRAS = 5       # una cita más corta coincide con cualquier cosa: no se acepta


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes (la ñ queda como n) ni puntuación, espacios simples."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", t)).strip()


class Indice:
    """Transcripción normalizada en una sola cadena, con la posición donde empieza cada segmento."""

    def __init__(self, segmentos: list[Segmento]):
        self.inicios_car: list[int] = []
        self.tiempos: list[float] = []
        partes, pos = [], 0
        for s in segmentos:
            n = normalizar(s.texto)
            if not n:
                continue
            self.inicios_car.append(pos)
            self.tiempos.append(s.inicio)
            partes.append(n)
            pos += len(n) + 1
        self.texto = " ".join(partes)

    def tiempo_en(self, posicion: int) -> float:
        i = bisect.bisect_right(self.inicios_car, posicion) - 1
        return self.tiempos[max(i, 0)] if self.tiempos else 0.0


@dataclass
class Resultado:
    estado: str            # 'verificada' | 'otro_minuto' | 'sin_respaldo'
    parecido: float
    segundos: float | None  # dónde aparece realmente la cita
    marca: str              # marca corregida (o la original si no se encontró)


def verificar_cita(cita: str, marca: str, indice: Indice) -> Resultado:
    aguja = normalizar(cita)
    if len(aguja.split()) < MIN_PALABRAS or not indice.texto:
        return Resultado("sin_respaldo", 0.0, None, marca)
    a = fuzz.partial_ratio_alignment(aguja, indice.texto)
    if a is None or a.score < UMBRAL:
        return Resultado("sin_respaldo", round(a.score if a else 0.0, 1), None, marca)
    real = indice.tiempo_en(a.dest_start)
    dicho = a_segundos(marca)
    cerca = dicho is not None and abs(dicho - real) <= TOLERANCIA_S
    return Resultado("verificada" if cerca else "otro_minuto", round(a.score, 1), real, hhmmss(real))


def verificar_informe(informe: InformeSesion, segmentos: list[Segmento]) -> dict:
    """Devuelve {'items': {(seccion, i): Resultado}, 'resumen': {...}} para todo el informe."""
    indice = Indice(segmentos)
    items: dict[tuple[str, int], Resultado] = {}
    for seccion in SECCIONES_CON_CITA:
        for i, item in enumerate(getattr(informe, seccion)):
            items[(seccion, i)] = verificar_cita(item.cita_literal, item.marca, indice)
    total = len(items)
    con_respaldo = sum(r.estado != "sin_respaldo" for r in items.values())
    return {
        "items": items,
        "resumen": {
            "citas": total,
            "con_respaldo": con_respaldo,
            "sin_respaldo": total - con_respaldo,
            "minuto_corregido": sum(r.estado == "otro_minuto" for r in items.values()),
            "porcentaje": round(100 * con_respaldo / total, 1) if total else None,
        },
    }

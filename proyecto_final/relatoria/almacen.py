"""Informes ya generados, guardados en disco: la misma sesión con los mismos temas no se paga dos veces."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .esquema import InformeSesion
from .informe import Uso
from .transcripcion import Sesion

CARPETA = Path(__file__).resolve().parents[1] / "datos" / "informes"


def temas_limpios(temas: list[str]) -> list[str]:
    vistos, salida = set(), []
    for t in temas:
        t = " ".join(t.split())
        if t and t.lower() not in vistos:
            vistos.add(t.lower())
            salida.append(t)
    return salida


def clave(sesion: Sesion, temas: list[str]) -> str:
    """Huella del contenido: cambia si cambia la transcripción o la lista de temas."""
    h = hashlib.sha256()
    h.update("\n".join(s.texto for s in sesion.segmentos).encode())
    h.update("|".join(sorted(t.lower() for t in temas_limpios(temas))).encode())
    return h.hexdigest()[:16]


def leer(sesion: Sesion, temas: list[str], carpeta: Path = CARPETA) -> tuple[InformeSesion, Uso] | None:
    ruta = carpeta / f"{clave(sesion, temas)}.json"
    if not ruta.exists():
        return None
    d = json.loads(ruta.read_text(encoding="utf-8"))
    return InformeSesion.model_validate(d["informe"]), Uso(**d["uso"])


def guardar(sesion: Sesion, temas: list[str], informe: InformeSesion, uso: Uso, carpeta: Path = CARPETA) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{clave(sesion, temas)}.json"
    ruta.write_text(json.dumps({"sesion": sesion.id, "temas": temas_limpios(temas), "uso": asdict(uso),
                                "informe": informe.model_dump()}, ensure_ascii=False, indent=1), encoding="utf-8")
    return ruta


def sesiones_con_informe(carpeta: Path = CARPETA) -> set[str]:
    """Id de las sesiones que tienen al menos un informe guardado."""
    salida = set()
    for ruta in carpeta.glob("*.json"):
        try:
            salida.add(json.loads(ruta.read_text(encoding="utf-8")).get("sesion", ""))
        except ValueError:
            continue
    return salida - {""}


def guardados(sesion_id: str, carpeta: Path = CARPETA) -> list[list[str]]:
    """Listas de temas para las que ya hay informe de esta sesión."""
    salida = []
    for ruta in sorted(carpeta.glob("*.json")):
        d = json.loads(ruta.read_text(encoding="utf-8"))
        if d.get("sesion") == sesion_id:
            salida.append(d.get("temas", []))
    return salida

"""Transcripción con tiempos: el formato común entre Whisper, el LLM y la app."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Segmento:
    inicio: float
    fin: float
    texto: str


@dataclass
class Sesion:
    id: str
    titulo: str
    organo: str = ""
    fecha: str = ""
    url: str = ""
    duracion_s: float = 0.0
    modelo_asr: str = ""
    segmentos: list[Segmento] = field(default_factory=list)

    @classmethod
    def leer(cls, ruta: str | Path) -> "Sesion":
        d = json.loads(Path(ruta).read_text(encoding="utf-8"))
        d["segmentos"] = [Segmento(**s) for s in d.get("segmentos", [])]
        return cls(**d)

    def guardar(self, ruta: str | Path) -> None:
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        Path(ruta).write_text(json.dumps(asdict(self), ensure_ascii=False, indent=1), encoding="utf-8")

    @property
    def palabras(self) -> int:
        return sum(len(s.texto.split()) for s in self.segmentos)


def hhmmss(t: float) -> str:
    t = int(max(0, t))
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def a_segundos(marca: str) -> int | None:
    """'01:02:03', '62:03' o '[00:05:10]' -> segundos. None si no es una marca."""
    partes = re.findall(r"\d+", marca or "")
    if not 2 <= len(partes) <= 3:
        return None
    n = [int(p) for p in partes]
    return n[0] * 3600 + n[1] * 60 + n[2] if len(n) == 3 else n[0] * 60 + n[1]


def bloques(segmentos: list[Segmento], cada: float = 30.0) -> list[Segmento]:
    """Une los segmentos de Whisper en bloques de ~`cada` segundos: menos líneas (y menos tokens)
    para el LLM, sin perder la referencia al minuto."""
    salida: list[Segmento] = []
    for s in segmentos:
        if salida and s.fin - salida[-1].inicio <= cada:
            salida[-1] = Segmento(salida[-1].inicio, s.fin, f"{salida[-1].texto} {s.texto}".strip())
        else:
            salida.append(Segmento(s.inicio, s.fin, s.texto.strip()))
    return salida


def con_marcas(segmentos: list[Segmento], cada: float = 30.0) -> str:
    """Texto que lee el LLM: una línea por bloque, con su marca [hh:mm:ss]."""
    return "\n".join(f"[{hhmmss(b.inicio)}] {b.texto}" for b in bloques(segmentos, cada))


def desde_texto(texto: str) -> list[Segmento]:
    """Transcripción pegada a mano. Respeta marcas [hh:mm:ss] o hh:mm:ss al inicio de línea si las
    hay; si no, numera los párrafos de 30 en 30 segundos solo para poder ubicarlos."""
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    patron = re.compile(r"^\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?[\s\-–:]*(.*)$")
    con = [patron.match(l) for l in lineas]
    if lineas and sum(m is not None for m in con) >= len(lineas) * 0.6:
        segs = []
        for l, m in zip(lineas, con):
            if m and m.group(2):
                segs.append(Segmento(float(a_segundos(m.group(1)) or 0), 0.0, m.group(2)))
            elif segs:
                segs[-1].texto += " " + l
        for a, b in zip(segs, segs[1:]):
            a.fin = b.inicio
        if segs:
            segs[-1].fin = segs[-1].inicio + 30
        return segs
    return [Segmento(i * 30.0, (i + 1) * 30.0, l) for i, l in enumerate(lineas)]


def enlace_al_minuto(url: str, segundos: float) -> str:
    if not url:
        return ""
    return f"{url}{'&' if '?' in url else '?'}t={int(max(0, segundos))}s"

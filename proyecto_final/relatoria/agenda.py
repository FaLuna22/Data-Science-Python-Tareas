"""Agenda del canal oficial del Congreso: qué sesiones hubo, de qué comisión y cuáles ya están transcritas.

Fuentes públicas, sin clave ni costo:
- el feed RSS del canal (las 15 emisiones más recientes; la app lo consulta cada pocos minutos);
- el listado de transmisiones con yt-dlp (más historia; lo usa pipeline/vigilar.py);
- la página de cada video, para saber si sigue en vivo, cuándo empezó y cuánto duró.

Todo se acumula en datos/catalogo.json: la lista crece aunque el feed solo muestre lo último.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .verificar import normalizar

CANAL = "UC9HLcODpEZuBRLSKXZx5igw"   # Congreso de la República del Perú, canal oficial
FEED = f"https://www.youtube.com/feeds/videos.xml?channel_id={CANAL}"
TRANSMISIONES = f"https://www.youtube.com/channel/{CANAL}/streams"
RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = RAIZ / "datos" / "catalogo.json"
SESIONES = RAIZ / "datos" / "sesiones"
LIMA = timezone(timedelta(hours=-5))
MAX_CATALOGO = 1500
_CABECERAS = {"User-Agent": "Mozilla/5.0 (Relatoria)", "Accept-Language": "es"}

MESES = {m: i for i, m in enumerate(("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                     "septiembre", "octubre", "noviembre", "diciembre"), 1)} | {"setiembre": 9}
ESTADOS_YTDLP = {"is_live": "en_vivo", "is_upcoming": "programada", "was_live": "terminada",
                 "post_live": "terminada", "not_live": "terminada"}


class AgendaNoDisponible(RuntimeError):
    """El canal no respondió (sin conexión, bloqueo temporal, formato cambiado)."""


@dataclass
class Emision:
    id: str
    titulo: str
    organo: str = ""
    camara: str = ""        # "Diputados", "Senado" o "" si el título no lo dice
    tipo: str = "otro"      # "comision", "pleno" u "otro"
    fecha: str = ""         # AAAA-MM-DD, hora del Perú
    estado: str = ""        # "en_vivo", "programada", "terminada" o "" (aún no consultado)
    duracion_s: int = 0
    visto: str = ""         # cuándo entró al catálogo (ISO, UTC)

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.id}"

    @property
    def titulo_limpio(self) -> str:
        """El título sin el '🔴 EN VIVO:' que el canal deja aun cuando la transmisión ya terminó."""
        return _PREFIJO.sub("", re.sub(r"^[^\w¿¡\"]+", "", self.titulo)).strip() or self.titulo

    @property
    def clave(self) -> str:
        """Lo que identifica al órgano para seguirlo: el nombre sin tildes ni mayúsculas."""
        return normalizar(self.organo)

    @classmethod
    def desde_titulo(cls, id: str, titulo: str, fecha_respaldo: str = "", **extra) -> "Emision":
        d = analizar_titulo(titulo)
        d["fecha"] = d["fecha"] or fecha_respaldo
        return cls(id=id, titulo=" ".join(titulo.split()), visto=extra.pop("visto", "") or _ahora(), **d, **extra)


# ───────────────────────────────────────────────────────── títulos
_PREFIJO = re.compile(r"^\W*(?:en\s+vivo|en\s+directo|live)\b\W*", re.I)
_SEPARADOR = re.compile(r"\s+[|l–—-]\s+|\s*\|\s*")
_FECHA_NUM = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})\b")
_FECHA_TXT = re.compile(r"\b(\d{1,2})\s+de\s+([a-záéíóú]+)\s+(?:del?\s+)?(\d{4})\b", re.I)
_CAMARAS = [
    (re.compile(r",?\s*(?:\(\s*senado\s*\)|\bdel\s+senado(?:\s+de\s+la\s+rep[uú]blica)?)\s*$", re.I), "Senado"),
    (re.compile(r",?\s*(?:\(\s*diputados\s*\)|\bde\s+la\s+c[aá]mara\s+de\s+diputados)\s*$", re.I), "Diputados"),
]


def analizar_titulo(titulo: str) -> dict:
    """'🔴EN VIVO: Comisión de Salud del Senado | 10/11/2026' ->
    {'organo': 'Comisión de Salud', 'camara': 'Senado', 'tipo': 'comision', 'fecha': '2026-11-10'}"""
    t = " ".join(re.sub(r"[^\w\s,.;:()/|–—\-'\"]", " ", titulo).split())   # fuera emojis
    ingles = bool(re.match(r"^live\b", t, re.I))                            # títulos en inglés: mm/dd/aaaa
    t = _PREFIJO.sub("", t)
    t = re.sub(r"(í[ao])l(?=\s+\d)", r"\1", t)   # 'Contraloríal 10/11/2026': la 'l' era el separador
    fecha = _fecha(t, ingles)

    nombre = _SEPARADOR.split(t)[0]
    nombre = _FECHA_TXT.sub("", _FECHA_NUM.sub("", nombre)).strip(" ,.;:-–|")
    # 'Sesión del Pleno…', '3ra sesión ordinaria de la Comisión…' -> desde 'Pleno' o 'Comisión'
    m = re.search(r"\b(comisi[oó]n|pleno)\b", nombre, re.I)
    if m and re.match(r"^(?:\d+\w*\s+)?sesi[oó]n\b", nombre, re.I):
        nombre = nombre[m.start():]
    nombre = nombre[:1].upper() + nombre[1:]
    tipo = ("comision" if re.match(r"comisi[oó]n\b", nombre, re.I)
            else "pleno" if re.match(r"pleno\b", nombre, re.I) else "otro")

    camara = ""
    for patron, nombre_camara in _CAMARAS:
        if patron.search(nombre):
            camara = nombre_camara
            if tipo == "comision":           # el Pleno conserva la cámara en el nombre
                nombre = patron.sub("", nombre).strip(" ,")
            break
    return {"organo": nombre, "camara": camara, "tipo": tipo, "fecha": fecha}


def _fecha(t: str, ingles: bool = False) -> str:
    m = _FECHA_NUM.search(t)
    if m:
        a, b, y = (int(x) for x in m.groups())
        y += 2000 if y < 100 else 0
        for dia, mes in ([(b, a), (a, b)] if ingles else [(a, b), (b, a)]):
            try:
                return date(y, mes, dia).isoformat()
            except ValueError:
                pass
    m = _FECHA_TXT.search(t)
    if m and normalizar(m.group(2)) in MESES:
        try:
            return date(int(m.group(3)), MESES[normalizar(m.group(2))], int(m.group(1))).isoformat()
        except ValueError:
            pass
    return ""


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hoy_en_lima() -> date:
    return datetime.now(LIMA).date()


def _en_lima(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(LIMA).date().isoformat()
    except ValueError:
        return ""


def _descargar(url: str, tiempo: float = 15) -> bytes:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=_CABECERAS), timeout=tiempo) as r:
            return r.read()
    except OSError as e:
        raise AgendaNoDisponible(f"No se pudo consultar el canal del Congreso ({e}).") from e


# ───────────────────────────────────────────────────────── fuentes
def leer_rss(xml: bytes | str | None = None) -> list[Emision]:
    """Las 15 emisiones más recientes del canal. `xml` sirve para probar sin red."""
    crudo = xml if xml is not None else _descargar(FEED)
    try:
        raiz = ET.fromstring(crudo)
    except ET.ParseError as e:
        raise AgendaNoDisponible("El feed del canal llegó con un formato inesperado.") from e
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    salida = []
    for e in raiz.findall("a:entry", ns):
        vid, titulo = e.findtext("yt:videoId", "", ns), e.findtext("a:title", "", ns)
        if vid and titulo:
            salida.append(Emision.desde_titulo(vid, titulo, _en_lima(e.findtext("a:published", "", ns))))
    return salida


def listar_transmisiones(cuantas: int = 60) -> list[Emision]:
    """Más historia que el feed, con estado y duración. Necesita yt-dlp (requirements-dev.txt)."""
    import yt_dlp
    # sin "lang", YouTube devuelve los títulos traducidos al inglés y no se reconoce la comisión
    with yt_dlp.YoutubeDL({"extract_flat": "in_playlist", "playlistend": cuantas, "quiet": True, "no_warnings": True,
                           "extractor_args": {"youtube": {"lang": ["es"]}},
                           "http_headers": {"Accept-Language": "es"}}) as y:
        info = y.extract_info(TRANSMISIONES, download=False)
    salida = []
    for e in info.get("entries") or []:
        if e.get("id") and e.get("title"):
            salida.append(Emision.desde_titulo(e["id"], e["title"], estado=ESTADOS_YTDLP.get(e.get("live_status"), ""),
                                               duracion_s=int(e.get("duration") or 0)))
    return salida


def consultar_estado(video_id: str) -> dict:
    """¿Sigue en vivo? ¿Cuándo empezó y cuánto duró? Lee la página pública del video.
    Devuelve solo lo que pudo averiguar (puede ser {})."""
    try:
        h = _descargar(f"https://www.youtube.com/watch?v={video_id}", 12).decode("utf-8", "ignore")
    except AgendaNoDisponible:
        return {}
    d: dict = {}
    if '"isLiveNow":true' in h:
        d["estado"] = "en_vivo"
    elif '"isUpcoming":true' in h:
        d["estado"] = "programada"
    elif '"isLiveNow":false' in h or '"lengthSeconds"' in h:
        d["estado"] = "terminada"
    if (m := re.search(r'"lengthSeconds":"(\d+)"', h)) and int(m.group(1)):
        d["duracion_s"] = int(m.group(1))
    if m := re.search(r'"startTimestamp":"([^"]+)"', h):
        d["inicio"] = m.group(1)
    return d


def transcritas(carpeta: Path = SESIONES) -> set[str]:
    return {p.stem for p in carpeta.glob("*.json")}


# ───────────────────────────────────────────────────────── seguimiento
def agrupar_variantes(conteo: dict[str, int]) -> dict[str, str]:
    """El canal titula la misma comisión de varias formas ('Defensa Nacional' y 'Defensa Nacional y Orden
    Interno', 'Contraloría' y 'Contraloríal'). Devuelve {variante: nombre canónico}; el canónico es la
    variante más usada. Une dos nombres si son casi iguales o si uno es el comienzo del otro."""
    from rapidfuzz import fuzz
    grupos: list[list[str]] = []
    tildes = lambda n: sum(c in "áéíóúÁÉÍÓÚñÑ" for c in n)   # noqa: E731  'República' antes que 'Republica'
    for n in sorted(conteo, key=lambda n: (-conteo[n], -tildes(n), -len(n), n)):
        k = normalizar(n)
        for g in grupos:
            r = normalizar(g[0])
            corto = min(k, r, key=len)
            if fuzz.ratio(k, r) >= 92 or ((k.startswith(r) or r.startswith(k)) and len(corto.split()) >= 3):
                g.append(n)
                break
        else:
            grupos.append([n])
    return {n: g[0] for g in grupos for n in g}


def coincide(e: Emision, seguidas: set[str] | list[str], palabras: list[str] | None = None,
             canonico: dict[str, str] | None = None) -> bool:
    """¿La emisión es de un órgano que se sigue (o lo menciona, como una mesa de trabajo de esa
    comisión), o su título dice alguna de las palabras vigiladas?"""
    claves = {normalizar(s) for s in seguidas if s}
    texto = normalizar(e.titulo)
    organo = normalizar((canonico or {}).get(e.organo, e.organo))
    if organo in claves or any(c in texto for c in claves):
        return True
    return any(p and p in texto for p in (normalizar(x) for x in palabras or []))


# ───────────────────────────────────────────────────────── catálogo en disco
class Catalogo:
    def __init__(self, ruta: str | Path = CATALOGO):
        self.ruta = Path(ruta)
        self.emisiones: dict[str, Emision] = {}
        if self.ruta.exists():
            try:
                validos = {f.name for f in fields(Emision)}
                for d in json.loads(self.ruta.read_text(encoding="utf-8")):
                    e = Emision(**{k: v for k, v in d.items() if k in validos})
                    # el título se vuelve a leer: las mejoras del lector valen también para lo ya guardado
                    a = analizar_titulo(e.titulo)
                    e.organo, e.camara, e.tipo, e.fecha = a["organo"], a["camara"], a["tipo"], a["fecha"] or e.fecha
                    self.emisiones[e.id] = e
            except (ValueError, TypeError):
                self.emisiones = {}       # archivo dañado: se reconstruye con la próxima consulta

    def incorporar(self, nuevas: list[Emision]) -> list[str]:
        """Suma emisiones; actualiza estado y duración de las que ya estaban. Devuelve los id nuevos."""
        agregados = []
        for n in nuevas:
            viejo = self.emisiones.get(n.id)
            if viejo is None:
                self.emisiones[n.id] = n
                agregados.append(n.id)
                continue
            if n.titulo != viejo.titulo:          # el canal a veces corrige el título
                viejo.titulo, viejo.organo, viejo.camara, viejo.tipo = n.titulo, n.organo, n.camara, n.tipo
            viejo.fecha = viejo.fecha or n.fecha
            viejo.estado = n.estado or viejo.estado
            viejo.duracion_s = n.duracion_s or viejo.duracion_s
        return agregados

    def actualizar_estado(self, video_id: str, info: dict) -> bool:
        e = self.emisiones.get(video_id)
        if e is None or not info:
            return False
        antes = (e.estado, e.duracion_s, e.fecha)
        e.estado = info.get("estado", e.estado)
        e.duracion_s = info.get("duracion_s", e.duracion_s)
        if not e.fecha and info.get("inicio"):
            e.fecha = _en_lima(info["inicio"])
        return antes != (e.estado, e.duracion_s, e.fecha)

    def recientes(self) -> list[Emision]:
        return sorted(self.emisiones.values(), key=lambda e: (e.fecha, e.visto), reverse=True)

    def canonico(self, tipos: tuple[str, ...] = ("comision", "pleno")) -> dict[str, str]:
        """{nombre tal como vino en el título: nombre canónico del órgano}."""
        conteo: dict[str, int] = {}
        for e in self.emisiones.values():
            if e.tipo in tipos and e.organo:
                conteo[e.organo] = conteo.get(e.organo, 0) + 1
        return agrupar_variantes(conteo)

    def organos(self, tipos: tuple[str, ...] = ("comision", "pleno")) -> list[str]:
        """Órganos conocidos, una sola vez cada uno, ordenados alfabéticamente."""
        return sorted(set(self.canonico(tipos).values()), key=normalizar)

    def guardar(self) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        datos = [asdict(e) for e in self.recientes()[:MAX_CATALOGO]]
        tmp = self.ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.ruta)

"""Sesión pública -> datos/sesiones/<id>.json (transcripción con tiempos).

    # desde un enlace público (descarga solo el audio con yt-dlp):
    python pipeline/transcribir_sesion.py "https://www.youtube.com/watch?v=LvsY8hVx-ec" \
        --organo "Comisión de Economía, Banca, Finanzas e Inteligencia Financiera (Diputados)"

    # desde un audio o video que ya tienes:
    python pipeline/transcribir_sesion.py grabacion.mp3 --id economia-2026-10-28 --fecha 2026-10-28 \
        --titulo "Sesión de la Comisión de Economía" --organo "Comisión de Economía"

Con GPU, una sesión de 1 hora toma unos 2 minutos con large-v3-turbo; en CPU, cerca de 20.
Requiere: pip install -r requirements.txt yt-dlp
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from relatoria.transcribir import transcribir  # noqa: E402
from relatoria.transcripcion import Sesion, hhmmss  # noqa: E402


def descargar(url: str, carpeta: Path) -> tuple[Path, dict]:
    """Baja solo el audio de un video público y devuelve (ruta, metadatos)."""
    import yt_dlp
    carpeta.mkdir(parents=True, exist_ok=True)
    opciones = {"format": "bestaudio/best", "outtmpl": str(carpeta / "%(id)s.%(ext)s"), "quiet": True,
                "noprogress": True}
    with yt_dlp.YoutubeDL(opciones) as y:
        info = y.extract_info(url, download=True)
        return Path(y.prepare_filename(info)), info


def fecha_en_lima(info: dict) -> str:
    """Fecha de la transmisión en hora del Perú. `upload_date` viene en UTC y, para una sesión que
    se sube de noche, cae al día siguiente; por eso se usa la hora de inicio de la transmisión."""
    from datetime import datetime, timedelta, timezone
    t = info.get("release_timestamp") or info.get("timestamp")
    if t:
        return datetime.fromtimestamp(t, timezone(timedelta(hours=-5))).strftime("%Y-%m-%d")
    f = info.get("upload_date") or ""
    return f"{f[:4]}-{f[4:6]}-{f[6:]}" if len(f) == 8 else ""


def transcribir_fuente(fuente: str, id: str | None = None, titulo: str | None = None, organo: str = "",
                       fecha: str = "", modelo: str = "large-v3-turbo", dispositivo: str = "auto",
                       borrar_audio: bool = False) -> Sesion:
    """Enlace público o archivo -> datos/sesiones/<id>.json. Devuelve la sesión guardada."""
    url = ""
    if re.match(r"https?://", fuente):
        url = fuente
        ruta, info = descargar(url, RAIZ / "datos" / "audio")
        id = id or info["id"]
        titulo = titulo or re.sub(r"^\W*(EN VIVO|LIVE)\W*", "", info.get("title", ""), flags=re.I).strip()
        fecha = fecha or fecha_en_lima(info)
        url = info.get("webpage_url", url)
    else:
        ruta = Path(fuente)
        id = id or ruta.stem
        titulo = titulo or ruta.stem

    t0 = time.perf_counter()
    ultimo = [0.0]

    def avance(hecho, total):
        if hecho - ultimo[0] >= 300:
            ultimo[0] = hecho
            print(f"  {hhmmss(hecho)} / {hhmmss(total)}", flush=True)

    print(f"Transcribiendo {ruta.name} con {modelo}...", flush=True)
    segmentos, duracion = transcribir(str(ruta), modelo=modelo, dispositivo=dispositivo, al_avanzar=avance)
    sesion = Sesion(id=id, titulo=titulo, organo=organo, fecha=fecha, url=url, duracion_s=round(duracion),
                    modelo_asr=f"faster-whisper {modelo}", segmentos=segmentos)
    salida = RAIZ / "datos" / "sesiones" / f"{id}.json"
    sesion.guardar(salida)
    if borrar_audio and url:
        ruta.unlink(missing_ok=True)
    seg = time.perf_counter() - t0
    print(f"Listo: {salida.relative_to(RAIZ)} · {hhmmss(duracion)} de audio, {sesion.palabras:,} palabras, "
          f"{seg / 60:.1f} min ({duracion / seg:.1f}x tiempo real)")
    return sesion


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fuente", help="Enlace público o ruta de un audio/video")
    p.add_argument("--id")
    p.add_argument("--titulo")
    p.add_argument("--organo", default="")
    p.add_argument("--fecha", default="", help="AAAA-MM-DD")
    p.add_argument("--modelo", default="large-v3-turbo")
    p.add_argument("--dispositivo", default="auto", choices=["auto", "cuda", "cpu"])
    a = p.parse_args()
    transcribir_fuente(a.fuente, a.id, a.titulo, a.organo, a.fecha, a.modelo, a.dispositivo)


if __name__ == "__main__":
    main()

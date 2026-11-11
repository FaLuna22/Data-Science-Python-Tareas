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

    url = ""
    if re.match(r"https?://", a.fuente):
        url = a.fuente
        ruta, info = descargar(url, RAIZ / "datos" / "audio")
        a.id = a.id or info["id"]
        a.titulo = a.titulo or re.sub(r"^\W*(EN VIVO|LIVE)\W*", "", info.get("title", ""), flags=re.I).strip()
        f = info.get("upload_date") or ""
        a.fecha = a.fecha or (f"{f[:4]}-{f[4:6]}-{f[6:]}" if len(f) == 8 else "")
        url = info.get("webpage_url", url)
    else:
        ruta = Path(a.fuente)
        a.id = a.id or ruta.stem
        a.titulo = a.titulo or ruta.stem

    t0 = time.perf_counter()
    ultimo = [0.0]

    def avance(hecho, total):
        if hecho - ultimo[0] >= 300:
            ultimo[0] = hecho
            print(f"  {hhmmss(hecho)} / {hhmmss(total)}", flush=True)

    print(f"Transcribiendo {ruta.name} con {a.modelo}...", flush=True)
    segmentos, duracion = transcribir(str(ruta), modelo=a.modelo, dispositivo=a.dispositivo, al_avanzar=avance)
    sesion = Sesion(id=a.id, titulo=a.titulo, organo=a.organo, fecha=a.fecha, url=url, duracion_s=round(duracion),
                    modelo_asr=f"faster-whisper {a.modelo}", segmentos=segmentos)
    salida = RAIZ / "datos" / "sesiones" / f"{a.id}.json"
    sesion.guardar(salida)
    seg = time.perf_counter() - t0
    print(f"Listo: {salida.relative_to(RAIZ)} · {hhmmss(duracion)} de audio, {sesion.palabras:,} palabras, "
          f"{seg / 60:.1f} min ({duracion / seg:.1f}x tiempo real)")


if __name__ == "__main__":
    main()

"""Audio -> transcripción con tiempos, con faster-whisper (sesión 13 del curso).

Misma receta que `Transcriptor("faster-whisper").segmentos()` de `voz.py` de la sesión 13:
detector de voz (VAD) para no mandarle silencio al modelo, y un `initial_prompt` con nombres
propios para que no los deforme. Aquí se usa faster-whisper directamente, sin PyTorch, para que
el mismo código corra en una laptop con GPU y en Streamlit Cloud (1 GB de RAM, solo CPU).
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Callable

from .transcripcion import Segmento

# Whisper acierta más los nombres propios si los ve escritos antes de empezar
CONTEXTO = (
    "Sesión de comisión del Congreso de la República del Perú. Cámara de Diputados, Senado, "
    "señor presidente, señora diputada, cuestión previa, cuarto intermedio, predictamen, dictamen, "
    "proyecto de ley, quorum, Mesa Directiva, MEF, SUNAT, BCRP, Osinergmin, Minem, Petroperú, "
    "Contraloría, canon, regalías, Reinfo."
)


def _registrar_dll_cuda() -> None:
    """En Windows, ctranslate2 busca cuBLAS y cuDNN en el PATH. Si se instalaron con pip
    (`nvidia-cublas-cu12`, `nvidia-cudnn-cu12`) quedan en site-packages/nvidia/*/bin, fuera del PATH."""
    if os.name != "nt":
        return
    import sysconfig
    from pathlib import Path
    for carpeta in (Path(sysconfig.get_paths()["purelib"]) / "nvidia").glob("*/bin"):
        if str(carpeta) not in os.environ["PATH"]:
            os.environ["PATH"] = f"{carpeta}{os.pathsep}{os.environ['PATH']}"
            os.add_dll_directory(str(carpeta))


@lru_cache(maxsize=2)
def cargar_modelo(nombre: str = "large-v3-turbo", dispositivo: str = "auto"):
    _registrar_dll_cuda()
    from faster_whisper import WhisperModel
    if dispositivo == "auto":
        try:
            import ctranslate2
            dispositivo = "cuda" if ctranslate2.get_cuda_device_count() else "cpu"
        except Exception:
            dispositivo = "cpu"
    return WhisperModel(nombre, device=dispositivo,
                        compute_type="float16" if dispositivo == "cuda" else "int8",
                        cpu_threads=min(8, os.cpu_count() or 4))


def transcribir(audio, modelo: str = "large-v3-turbo", idioma: str = "es", contexto: str = CONTEXTO,
                dispositivo: str = "auto", al_avanzar: Callable[[float, float], None] | None = None,
                ) -> tuple[list[Segmento], float]:
    """`audio`: ruta o archivo abierto (mp3, m4a, opus, wav, mp4...). Devuelve (segmentos, duración).

    `al_avanzar(segundos_hechos, duración)` se llama después de cada segmento, para la barra de progreso.
    """
    m = cargar_modelo(modelo, dispositivo)
    segs, info = m.transcribe(
        audio, language=idioma, beam_size=5, vad_filter=True, initial_prompt=contexto,
        vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=False,   # evita que un error se arrastre durante horas de audio
    )
    salida: list[Segmento] = []
    for s in segs:
        texto = s.text.strip()
        if texto:
            salida.append(Segmento(round(s.start, 2), round(s.end, 2), texto))
        if al_avanzar:
            al_avanzar(s.end, info.duration)
    return salida, float(info.duration)

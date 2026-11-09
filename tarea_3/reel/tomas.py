"""Varias tomas por escena con Qwen3-TTS, generando cada oración por separado.

Las oraciones cortas salen con mejor entonación que una escena entera de una sola vez, y cada generación es distinta,
así que se escoge la mejor toma de cada escena (como en un doblaje).

Uso:  python tomas.py [n_tomas] [escenas...]
      python tomas.py 3                 -> todas las escenas
      python tomas.py 4 fijo fuera      -> solo esas escenas (las tomas nuevas se numeran después de las existentes)
      python tomas.py 3 rehacer=gancho  -> rehace esa escena desde toma1 (por ejemplo, tras cambiar su texto)
Salida: muestras/tomas/<n>_<id>_toma<k>.wav y muestras/tomas/resumen.json (WER de cada toma según Whisper)
"""
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

import voz_sesion15 as V

AQUI = Path(__file__).parent
OUT = AQUI / "muestras" / "tomas"
OUT.mkdir(parents=True, exist_ok=True)
REF = AQUI / "recursos" / "voz_referencia_20s.wav"
PAUSA_FRASE = 0.28  # silencio entre oraciones de una misma escena
INICIO_SESION = time.time()


def oraciones(frase):
    """Corta en punto, dos puntos y punto y coma; conserva la puntuación para la entonación."""
    partes = re.split(r"(?<=[.:;?!])\s+", frase.strip())
    return [p for p in partes if p]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    elegir = {a for a in sys.argv[2:] if not a.startswith("rehacer=")}
    # rehacer=gancho: las tomas viejas de esa escena (texto anterior) se reemplazan, numerando desde 1
    rehacer = {x for a in sys.argv[2:] if a.startswith("rehacer=") for x in a[8:].split(",")}
    guion = json.loads((AQUI / "guion.json").read_text(encoding="utf-8"))
    escenas = [(i, e) for i, e in enumerate(guion["escenas"], 1) if not elegir or e["id"] in elegir]
    t0 = time.time()
    # bfloat16 en vez de float32: la mitad de memoria (~3.4 GB), para no agotar la RAM de la laptop
    import torch
    from qwen_tts import Qwen3TTSModel
    _cargar = Qwen3TTSModel.from_pretrained
    Qwen3TTSModel.from_pretrained = lambda *a, **kw: _cargar(*a, **{**kw, "dtype": torch.bfloat16})
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"  # RTX 5050: torch 2.14.1+cu130
    voz = V.Voz(str(REF), modelo="Qwen/Qwen3-TTS-12Hz-1.7B-Base", device=dispositivo)
    print(f"Qwen3-TTS en {dispositivo}", flush=True)
    resumen_ruta = OUT / "resumen.json"
    resumen = json.loads(resumen_ruta.read_text(encoding="utf-8")) if resumen_ruta.exists() else {}
    for k in range(1, n + 1):
        for i, e in escenas:
            # una escena por llamada: menos memoria que todas las oraciones juntas
            previas = sorted(OUT.glob(f"{i}_{e['id']}_toma*.wav"))
            if e["id"] in rehacer:
                previas = [x for x in previas if x.stat().st_mtime > INICIO_SESION]
            num = len(previas) + 1
            wavs = voz.decir(oraciones(e["frase"]))
            partes = []
            for w in wavs:
                partes += [np.asarray(w, np.float32), np.zeros(int(PAUSA_FRASE * voz.sr), np.float32)]
            audio = np.concatenate(partes[:-1])
            nombre = f"{i}_{e['id']}_toma{num}"
            sf.write(OUT / f"{nombre}.wav", audio, voz.sr)
            wer = V._wer(e["frase"], V._a16k(audio, voz.sr))
            resumen[nombre] = {"escena": e["id"], "toma": num, "segundos": round(len(audio) / voz.sr, 1), "wer": round(wer, 3),
                               "texto": e["frase"]}
            print(f"[{time.time() - t0:5.0f}s] {nombre}: {len(audio) / voz.sr:.1f} s, WER {wer:.2f}", flush=True)
            resumen_ruta.write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    print("listo: muestras/tomas/")


if __name__ == "__main__":
    main()

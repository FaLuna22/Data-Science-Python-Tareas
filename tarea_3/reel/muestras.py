"""Muestras A/B de la voz clonada para elegir el motor y el estilo antes del reel final.

Genera en muestras/ (ignorado por git) las escenas "gancho" y "movil" con:
  A  Qwen3-TTS 1.7B, velocidad natural (sin atempo)
  B  VoxCPM2 sin estilo
  C  VoxCPM2 con estilo conversacional
  D  VoxCPM2 con estilo conversacional y el gancho reescrito en tono hablado
Uso:  python muestras.py recursos/voz_referencia_20s.wav
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

import voz_sesion15 as V

AQUI = Path(__file__).parent
OUT = AQUI / "muestras"
OUT.mkdir(exist_ok=True)
ref = sys.argv[1] if len(sys.argv) > 1 else str(AQUI / "recursos" / "voz_referencia_20s.wav")
SUFIJO = sys.argv[2] if len(sys.argv) > 2 else ""
guion = json.loads((AQUI / "guion.json").read_text(encoding="utf-8"))
esc = {e["id"]: e["frase"] for e in guion["escenas"]}
textos = [esc["gancho"], esc["movil"]]
hablado = ["¿Sabes cuántos peruanos del campo usaban internet en dos mil quince? Solo once de cada cien. Hoy… son sesenta y uno.",
           esc["movil"]]
ESTILO = "warm, relaxed, conversational, like explaining something to a friend, natural pauses"

t0 = time.time()


def guardar(nombre, wavs, sr):
    pausa = np.zeros(int(0.5 * sr), np.float32)
    audio = np.concatenate([np.concatenate([np.asarray(w, np.float32), pausa]) for w in wavs])
    sf.write(OUT / f"{nombre}{SUFIJO}.wav", 0.9 * audio / np.abs(audio).max(), sr)
    wer = [V._wer(t, V._a16k(w, sr)) for t, w in zip(textos if nombre != "D_voxcpm_estilo_hablado" else hablado, wavs)]
    print(f"[{time.time() - t0:5.0f}s] {nombre}: {len(audio) / sr:.1f} s, {sr} Hz, WER {', '.join(f'{x:.2f}' for x in wer)}", flush=True)


if "solo_vox" not in sys.argv:
    q = V.Voz(ref, modelo="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    guardar("A_qwen_natural", q.decir(textos), q.sr)
    del q

# VoxCPM2 desde una carpeta local (en Windows la caché de Hugging Face falla sin permiso de enlaces simbólicos)
import voxcpm  # noqa: E402

LOCAL = Path.home() / ".cache" / "modelos" / "VoxCPM2"
_original = voxcpm.VoxCPM.from_pretrained
voxcpm.VoxCPM.from_pretrained = lambda repo, **kw: _original(str(LOCAL) if LOCAL.exists() else repo, **kw)

vx = V.VozExpresiva(ref, con_estilo=True)
vx.con_estilo = False
guardar("B_voxcpm", vx.decir(textos), vx.sr)
vx.con_estilo = True
guardar("C_voxcpm_estilo", vx.decir(textos, [ESTILO] * 2), vx.sr)
guardar("D_voxcpm_estilo_hablado", vx.decir(hablado, [ESTILO] * 2), vx.sr)
print("listo: muestras/")

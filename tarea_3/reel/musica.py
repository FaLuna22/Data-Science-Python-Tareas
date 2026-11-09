"""Genera una pista de fondo original (sin derechos de terceros) para el reel.

Progresión La menor - Fa - Do - Sol a 84 pulsos por minuto: un colchón de acordes suave y un arpegio tipo campana.
Uso:  python musica.py [segundos]   ->  recursos/musica.wav (48 kHz, mono)
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 48000
BPM = 84
AQUI = Path(__file__).parent


def nota(n):  # número MIDI -> Hz
    return 440.0 * 2 ** ((n - 69) / 12)


ACORDES = [[57, 60, 64], [53, 57, 60], [48, 55, 60, 64], [55, 59, 62]]  # Am, F, C, G


def envolvente(n, ataque, caida):
    e = np.ones(n)
    a, c = int(ataque * SR), int(caida * SR)
    e[:a] = np.linspace(0, 1, a)
    e[-c:] *= np.linspace(1, 0, c)
    return e


def pad(freqs, dur):
    t = np.arange(int(dur * SR)) / SR
    s = np.zeros_like(t)
    for f in freqs:
        for det in (-0.12, 0.0, 0.12):  # leve desafinación = coro
            fd = f * 2 ** (det / 12)
            s += np.sin(2 * np.pi * fd * t) + 0.18 * np.sin(2 * np.pi * 2 * fd * t)
    s *= envolvente(len(t), 1.2, 1.4)
    return s / (len(freqs) * 3)


def campana(f, dur=1.6):
    t = np.arange(int(dur * SR)) / SR
    s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2.01 * f * t)) * np.exp(-t * 3.2)
    return s * envolvente(len(t), 0.005, 0.3)


def pasa_bajos(x, corte=2200):
    a = np.exp(-2 * np.pi * corte / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):  # filtro de un polo
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def main(segundos=90):
    compas = 4 * 60 / BPM            # segundos por compás
    total = np.zeros(int((segundos + 3) * SR))
    t, i = 0.0, 0
    while t < segundos:
        acorde = ACORDES[i % 4]
        dur = 2 * compas            # cada acorde dura dos compases
        ini = int(t * SR)
        p = pad([nota(n) for n in acorde] + [nota(acorde[0] - 12)], dur + 1.4)
        total[ini:ini + len(p)] += 0.55 * p[: len(total) - ini]
        # arpegio en corcheas, una octava arriba
        corchea = 60 / BPM / 2
        patron = [0, 1, 2, 1, 2, 1, 0, 2] * 2
        for k, idx in enumerate(patron):
            ti = int((t + k * corchea) * SR)
            c = campana(nota(acorde[idx % len(acorde)] + 12)) * (0.16 if k % 2 == 0 else 0.10)
            fin = min(len(total), ti + len(c))
            total[ti:fin] += c[: fin - ti]
        t += dur
        i += 1
    total = total[: int(segundos * SR)]
    total = pasa_bajos(total)
    total *= envolvente(len(total), 2.0, 3.0)
    total = 0.5 * total / np.max(np.abs(total))
    (AQUI / "recursos").mkdir(exist_ok=True)
    sf.write(AQUI / "recursos" / "musica.wav", total.astype(np.float32), SR)
    print(f"recursos/musica.wav: {segundos} s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 90)

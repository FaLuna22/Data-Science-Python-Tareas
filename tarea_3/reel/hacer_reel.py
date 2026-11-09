"""Reel vertical 1080x1920 de la brecha digital: voz clonada + gráficos animados + subtítulos + música.

Pasos
  1. Voz:        voz_sesion15.py (Sesión 15 del curso) clona la voz con Qwen3-TTS y narra cada escena de guion.json;
                 Whisper revisa cada escena (WER) y da los tiempos palabra por palabra para los subtítulos.
  2. Visuales:   cada escena tiene su animación hecha con matplotlib a partir de datos/procesados/indicadores.csv
                 (mapa, líneas, cuadrícula de 100 hogares, barras y recorrido por el dashboard).
  3. Montaje:    ffmpeg une los cuadros con la narración y la música de fondo (musica.py), más baja que la voz.

Uso (desde tarea_3/reel, con el entorno .venv de esta carpeta):
  python hacer_reel.py --preview                       # sin voz: tiempos estimados, para revisar los visuales
  python hacer_reel.py --voz recursos/voz_referencia.m4a --url https://...   # reel final
  python hacer_reel.py --reusar --url https://...      # vuelve a montar el video con la narración ya generada
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import textwrap
import time
from pathlib import Path

import imageio_ffmpeg
import matplotlib
import numpy as np
import pandas as pd
import soundfile as sf

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle  # noqa: E402

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
REC = AQUI / "recursos"
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1080, 1920, 30
COLA = 3.2  # segundos finales con créditos

BG, PANEL, TXT, TXT2, MUTED, GRID = "#0f1115", "#181b21", "#f2f1ec", "#c3c2b7", "#8d8b85", "#2a2d33"
AZUL, NARANJA, GRIS = "#3987e5", "#eb6834", "#5b5e66"
AZUL_CLARO = "#9ec5f4"
CMAP = LinearSegmentedColormap.from_list("azules", ["#0d2a52", "#184f95", "#2a78d6", "#6da7ec", "#cde2fb"])

for archivo in ["segoeui.ttf", "segoeuib.ttf", "seguisb.ttf"]:
    ruta = Path("C:/Windows/Fonts") / archivo
    if ruta.exists():
        font_manager.fontManager.addfont(str(ruta))
plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "text.color": TXT, "axes.edgecolor": GRID,
                     "axes.labelcolor": TXT2, "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": BG,
                     "figure.facecolor": BG, "savefig.facecolor": BG})

# ---------------------------------------------------------------- datos
TABLA = pd.read_csv(RAIZ / "datos" / "procesados" / "indicadores.csv")
_IDX = TABLA.set_index(["indicador", "anio", "ambito", "geo", "dimension", "grupo"])["p"].to_dict()


def v(ind, anio, amb="Total", geo="Perú", dim="nacional", grupo="Total"):
    p = _IDX.get((ind, anio, amb, geo, dim, grupo))
    return None if p is None or (isinstance(p, float) and math.isnan(p)) else 100 * p


GEO = json.loads((RAIZ / "web" / "data" / "peru_departamentos.geojson").read_text(encoding="utf-8"))


def anillos(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [np.array(p[0]) for p in polys]


DEPTOS = [(f["properties"]["nombre"], anillos(f["geometry"])) for f in GEO["features"]]


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- escenas
def escena_mapa(ax, p):
    anio = 2015 + min(10, int(p / 0.8 * 11))
    for nombre, rings in DEPTOS:
        val = v("usa_internet", anio, "Rural", nombre)
        color = GRIS if val is None else CMAP(min(1, val / 90))
        for r in rings:
            ax.add_patch(Polygon(r, closed=True, facecolor=color, edgecolor=BG, linewidth=1.2))
    ax.set_xlim(-82.0, -62.5)
    ax.set_ylim(-18.6, 0.2)
    ax.set_aspect(1 / math.cos(math.radians(9)))
    ax.axis("off")
    ax.text(0.98, 0.97, str(anio), transform=ax.transAxes, ha="right", va="top", fontsize=86, weight="bold", color=TXT)
    nac = v("usa_internet", anio, "Rural")
    ax.text(0.98, 0.80, f"Perú rural: {nac:.0f} %", transform=ax.transAxes, ha="right", va="top", fontsize=30, color=TXT2)
    # escala
    for i in range(30):
        ax.add_patch(Rectangle((0.72 + i * 0.0087, 0.50), 0.0087, 0.022, transform=ax.transAxes, color=CMAP(i / 29), lw=0))
    for x, t in [(0.72, "0 %"), (0.85, "45 %"), (0.98, "90 %")]:
        ax.text(x, 0.535, t, transform=ax.transAxes, fontsize=20, color=MUTED, ha="center")
    ax.text(0.98, 0.58, "Uso de internet en el campo", transform=ax.transAxes, fontsize=24, color=TXT2, ha="right")


def escena_lineas(ax, p):
    anios = np.arange(2015, 2026)
    hasta = 2015 + ease(p / 0.85) * 10
    series = [("Urbano", "Urbano", AZUL, "-"), ("Rural", "Rural", NARANJA, "-"), ("Total", "Perú", TXT, (0, (2, 2)))]
    ax.axvspan(2019.5, 2020.5, color="#ffffff", alpha=0.06, lw=0)
    ax.text(2020, 98, "pandemia", ha="center", va="top", fontsize=22, color=MUTED)
    for amb, nombre, color, estilo in series:
        ys = np.array([v("usa_internet", int(a), amb) for a in anios])
        xs = anios[anios <= hasta].astype(float)
        yy = ys[: len(xs)]
        if len(xs) and xs[-1] < hasta and len(xs) < len(anios):  # tramo parcial
            f = hasta - xs[-1]
            xs = np.append(xs, hasta)
            yy = np.append(yy, ys[len(yy) - 1] + f * (ys[len(yy)] - ys[len(yy) - 1]))
        ax.plot(xs, yy, color=color, lw=6 if amb != "Total" else 4, ls=estilo, solid_capstyle="round")
        if len(xs):
            ax.scatter([xs[-1]], [yy[-1]], s=160, color=color, zorder=5, edgecolor=BG, linewidth=3)
            ax.text(xs[-1] + 0.25, yy[-1], f"{nombre} {yy[-1]:.0f} %", va="center", fontsize=26, color=color if amb != "Total" else TXT,
                    weight="bold")
    ax.set_xlim(2014.6, 2028.2)
    ax.set_ylim(0, 100)
    ax.set_xticks([2015, 2017, 2019, 2021, 2023, 2025])
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0", "25", "50", "75", "100 %"])
    ax.tick_params(labelsize=22, length=0)
    ax.grid(axis="y", color=GRID, lw=1)
    for s in ax.spines.values():
        s.set_visible(False)


def escena_waffle(ax, p):
    fijo = v("internet_fijo", 2025)
    movil = v("internet_solo_movil", 2025)
    cuentas = [round(fijo), round(movil)]
    cuentas.append(100 - sum(cuentas))
    colores = [AZUL] * cuentas[0] + [NARANJA] * cuentas[1] + [GRIS] * cuentas[2]
    visibles = int(ease(p / 0.65) * 100)
    for i in range(100):
        fila, col = divmod(i, 10)
        c = colores[i] if i < visibles else "#20232a"
        ax.add_patch(FancyBboxPatch((col + 0.08, 9 - fila + 0.08), 0.84, 0.84, boxstyle="round,pad=0,rounding_size=0.18",
                                    facecolor=c, edgecolor="none"))
    ax.set_xlim(-0.2, 10.2)
    ax.set_ylim(-4.6, 11.0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.text(5, 10.6, "100 hogares del Perú, 2025", ha="center", fontsize=28, color=TXT2)
    leyenda = [(AZUL, f"{cuentas[0]} con internet fijo"), (NARANJA, f"{cuentas[1]} solo con internet móvil"),
               (GRIS, f"{cuentas[2]} sin internet")]
    for k, (c, t) in enumerate(leyenda):
        y = -0.9 - k * 0.95
        ax.add_patch(FancyBboxPatch((0.1, y - 0.3), 0.6, 0.6, boxstyle="round,pad=0,rounding_size=0.12", facecolor=c, edgecolor="none"))
        ax.text(1.0, y, t, va="center", fontsize=28, color=TXT)
    if p > 0.55:
        rural = v("internet_solo_movil", 2025, "Rural")
        ax.text(0.1, -4.1, f"En el campo: {rural:.0f} de cada 100", ha="left", va="center", fontsize=26, color=NARANJA,
                weight="bold", alpha=ease((p - 0.55) / 0.15))


def escena_quintiles(ax, p):
    grupos = ["Q1", "Q2", "Q3", "Q4", "Q5"]
    etiquetas = ["20 % más pobre", "Q2", "Q3", "Q4", "20 % más rico"]
    vals = [v("internet_fijo", 2025, dim="quintil", grupo=g) for g in grupos]
    colores = [NARANJA, "#3a5f8f", "#3a5f8f", "#3a5f8f", AZUL]
    k = ease(p / 0.6)
    y = np.arange(5)[::-1]
    ax.barh(y, [x * k for x in vals], color=colores, height=0.62)
    for yi, val, et in zip(y, vals, etiquetas):
        ax.text(-1.5, yi, et, ha="right", va="center", fontsize=28, color=TXT if et.startswith("20") else TXT2,
                weight="bold" if et.startswith("20") else "normal")
        ax.text(val * k + 1.5, yi, f"{val * k:.0f} %", va="center", fontsize=34, weight="bold", color=TXT)
    ax.set_xlim(-24, 62)
    ax.set_ylim(-0.8, 4.6)
    ax.axis("off")
    ax.figure.canvas.draw_idle()


def escena_deptos(ax, p):
    deptos = [d for d, _ in DEPTOS]
    vals = {d: v("usa_internet", 2025, geo=d) for d in deptos}
    bajos = sorted(deptos, key=lambda d: vals[d])[:5]
    lista = ["Ica", "Lima"] + bajos[::-1]
    lista = lista[::-1]  # de abajo hacia arriba en el gráfico
    resaltar = {"Cusco", "Cajamarca", "Puno"}
    k = ease(p / 0.55)
    y = np.arange(len(lista))
    colores = [NARANJA if d in resaltar else AZUL if d in ("Lima", "Ica") else "#3a3d45" for d in lista]
    ax.barh(y, [vals[d] * k for d in lista], color=colores, height=0.62)
    for yi, d in zip(y, lista):
        ax.text(-2, yi, d, ha="right", va="center", fontsize=28, color=TXT if d in resaltar | {"Lima", "Ica"} else TXT2)
        ax.text(vals[d] * k + 1.5, yi, f"{vals[d] * k:.0f} %", va="center", fontsize=28, weight="bold", color=TXT)
    nac = v("usa_internet", 2025)
    ax.axvline(nac, color=TXT, lw=2, ls=(0, (3, 3)), alpha=0.7)
    ax.text(nac, len(lista) - 0.1, f"Perú {nac:.0f} %", ha="center", fontsize=22, color=TXT2)
    ax.set_xlim(-24, 100)
    ax.set_ylim(-1.4, len(lista) + 0.9)
    ax.axis("off")
    ax.text(-24, len(lista) + 0.45, "Uso de internet por departamento, 2025", fontsize=26, color=TXT2)
    # dato de edad
    if p > 0.5:
        ax.text(-24, -1.2, f"Adultos mayores rurales (65+): {v('usa_internet', 2025, 'Rural', dim='grupo_edad', grupo='65+'):.0f} %",
                ha="left", fontsize=24, color=NARANJA, alpha=ease((p - 0.5) / 0.15))


_CAPTURAS = None


def escena_dashboard(ax, p):
    global _CAPTURAS
    if _CAPTURAS is None:
        _CAPTURAS = [plt.imread(RAIZ / "web" / "assets" / "img" / n) for n in ("captura_mapa.jpg", "captura_series.jpg")]
    img = _CAPTURAS[0] if p < 0.5 else _CAPTURAS[1]
    q = (p % 0.5) / 0.5
    h, w = img.shape[:2]
    ventana = int(h * 1.12)
    x0 = int((w - ventana) * (0.15 + 0.7 * q))
    ax.imshow(img[:, x0:x0 + ventana])
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, transform=ax.transAxes, boxstyle="round,pad=0,rounding_size=0.03",
                                facecolor="none", edgecolor=GRID, lw=3))


ESCENAS = {"gancho": escena_mapa, "duplico": escena_lineas, "movil": escena_waffle, "fijo": escena_quintiles,
           "fuera": escena_deptos, "cierre": escena_dashboard}


# ---------------------------------------------------------------- cuadro
def bloques(palabras, max_palabras=4, max_letras=24):
    out, actual = [], []
    for pal in palabras:
        actual.append(pal)
        if len(actual) >= max_palabras or sum(len(x[2]) + 1 for x in actual) >= max_letras or pal[2][-1] in ".,;:?!":
            out.append(actual)
            actual = []
    if actual:
        out.append(actual)
    # no dejar una palabra corta sola ("sesenta y" / "uno."): se pega al bloque anterior
    pegado = []
    for b in out:
        if pegado and len(b) == 1 and len(b[0][2]) <= 6 and pegado[-1][-1][2][-1] not in ".,;:?!":
            pegado[-1] = pegado[-1] + b
        else:
            pegado.append(b)
    return pegado


def a_srt(palabras, ruta):
    def hms(t):
        return f"{int(t // 3600):02}:{int(t % 3600 // 60):02}:{int(t % 60):02},{int(t % 1 * 1000):03}"
    lineas = []
    for i, b in enumerate(bloques(palabras), 1):
        lineas += [str(i), f"{hms(b[0][0])} --> {hms(b[-1][1])}", " ".join(p[2] for p in b), ""]
    Path(ruta).write_text(chr(10).join(lineas), encoding="utf-8")


class Render:
    def __init__(self, guion, tiempos, palabras, url, duracion):
        self.g, self.tiempos, self.url, self.dur = guion, tiempos, url, duracion
        self.bloques = bloques(palabras)
        self.fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)

    def escena_en(self, t):
        idx = 0
        for i, (ini, _) in enumerate(self.tiempos):
            if t >= ini - 0.15:
                idx = i
        return idx

    def subtitulo(self, t):
        for b in self.bloques:
            if b[0][0] - 0.05 <= t <= b[-1][1] + 0.25:
                return " ".join(x[2] for x in b)
        return ""

    def cuadro(self, t):
        fig = self.fig
        fig.clf()
        fin_narr = self.tiempos[-1][1]
        if t > fin_narr + 0.9:
            self.creditos(t - fin_narr - 0.9)
        else:
            i = self.escena_en(t)
            e = self.g["escenas"][i]
            ini = self.tiempos[i][0]
            fin = self.tiempos[i + 1][0] if i + 1 < len(self.tiempos) else fin_narr + 0.9
            p = (t - ini) / max(0.1, fin - ini)
            a = ease((t - ini + 0.15) / 0.45)
            fig.text(0.075, 0.953, "LA BRECHA DIGITAL EN EL PERÚ", fontsize=24, weight="bold", color=AZUL)
            for k in range(len(self.g["escenas"])):
                fig.patches.append(matplotlib.patches.Circle((0.80 + k * 0.025, 0.9565), 0.0055, transform=fig.transFigure,
                                                             color=TXT if k == i else GRID))
            cifra = e["cifra"] or "Explora el tablero"
            fig.text(0.075, 0.905, cifra, fontsize=92 if e["cifra"] else 66, weight="bold", color=TXT, va="top", alpha=a)
            etiqueta = self.url if e["id"] == "cierre" and self.url else e["etiqueta"]
            fig.text(0.075, 0.835, "\n".join(textwrap.wrap(etiqueta, 40)), fontsize=30, color=TXT2, va="top", alpha=a)
            ax = fig.add_axes([0.075, 0.29, 0.85, 0.46])
            ESCENAS[e["id"]](ax, max(0.0, p))
        # subtítulos
        s = self.subtitulo(t)
        if s:
            fig.text(0.5, 0.20, s, ha="center", va="center", fontsize=50, weight="bold", color=TXT,
                     bbox=dict(boxstyle="round,pad=0.45,rounding_size=0.5", facecolor="#000000", edgecolor="none", alpha=0.72))
        # pie: fuente y aviso de IA
        fig.text(0.075, 0.075, f"Fuente: {self.g['fuente']} · elaboración propia", fontsize=22, color=MUTED)
        fig.text(0.075, 0.048, "VOZ IA", fontsize=19, weight="bold", color=BG,
                 bbox=dict(boxstyle="round,pad=0.35", facecolor=NARANJA, edgecolor="none"))
        fig.text(0.175, 0.048, "Voz generada con IA a partir de mi propia voz", fontsize=22, color=TXT2)
        fig.canvas.draw()
        return np.asarray(fig.canvas.buffer_rgba()).tobytes()

    def creditos(self, t):
        a = ease(t / 0.5)
        fig = self.fig
        fig.text(0.075, 0.80, "La brecha digital\nen el Perú", fontsize=72, weight="bold", color=TXT, va="top", alpha=a)
        if self.url:
            fig.text(0.075, 0.64, "Dashboard interactivo:", fontsize=28, color=TXT2, alpha=a)
            fig.text(0.075, 0.61, "\n".join(textwrap.wrap(self.url, 44)), fontsize=28, color=AZUL, va="top", alpha=a)
        y = 0.50
        for c in self.g["creditos"] + [self.g["aviso_ia"]]:
            for linea in textwrap.wrap(c, 52):
                fig.text(0.075, y, linea, fontsize=24, color=TXT2, alpha=a)
                y -= 0.022
            y -= 0.012


# ---------------------------------------------------------------- audio
def preparar_audio(narracion, dur, salida):
    """Narración + música de fondo (unos 18 dB por debajo de la voz), a 48 kHz estéreo."""
    musica_ruta = REC / "musica.wav"
    if not musica_ruta.exists():
        import musica
        musica.main(int(dur) + 4)
    m, srm = sf.read(musica_ruta, dtype="float32")
    n = int(dur * srm)
    m = np.pad(m, (0, max(0, n - len(m))))[:n]
    if narracion is not None:
        voz, srv = narracion
        voz = np.interp(np.arange(0, len(voz), srv / srm), np.arange(len(voz)), voz).astype(np.float32)
        voz = np.pad(voz, (0, max(0, n - len(voz))))[:n]
        voz = 0.89 * voz / (np.max(np.abs(voz)) + 1e-9)
        # la música baja cuando hay voz (ducking simple con envolvente de la voz)
        env = np.convolve(np.abs(voz), np.ones(srm // 5) / (srm // 5), mode="same")
        duck = 1 - 0.55 * np.clip(env / (env.max() + 1e-9) * 4, 0, 1)
        mezcla = voz + 0.16 * m * duck
    else:
        mezcla = 0.35 * m
    fade = int(1.5 * srm)
    mezcla[-fade:] *= np.linspace(1, 0, fade)
    sf.write(salida, np.clip(mezcla, -1, 1), srm)


# ---------------------------------------------------------------- principal
def tiempos_estimados(guion):
    t, out = 0.3, []
    palabras = []
    for e in guion["escenas"]:
        ws = e["frase"].split()
        d = len(ws) / 2.6
        for k, wrd in enumerate(ws):
            palabras.append((t + k * d / len(ws), t + (k + 1) * d / len(ws), wrd))
        out.append((t, t + d))
        t += d + 0.35
    return out, palabras


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voz", help="tu grabación de 15 a 25 s (wav, m4a, ogg, mp3)")
    ap.add_argument("--preview", action="store_true", help="sin voz, con tiempos estimados")
    ap.add_argument("--reusar", action="store_true", help="usa recursos/narracion.wav y salidas previas")
    ap.add_argument("--url", default="", help="enlace público del dashboard")
    ap.add_argument("--tts", default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    ap.add_argument("--device", default="cuda" if __import__("torch").cuda.is_available() else "cpu")
    ap.add_argument("--velocidad", type=float, default=1.0, help="1.0 = sin atempo; estirar el audio lo vuelve metálico")
    ap.add_argument("--tomas", help="toma elegida por escena de muestras/tomas, p. ej. 2,1,3,1,2,1")
    ap.add_argument("--salida", default=str(AQUI / "reel.mp4"))
    args = ap.parse_args()
    t0 = time.time()
    guion = json.loads((AQUI / "guion.json").read_text(encoding="utf-8"))
    narr = None
    if args.preview:
        tiempos, palabras = tiempos_estimados(guion)
        dur = tiempos[-1][1] + 0.8 + COLA
    elif args.reusar:
        d = json.loads((AQUI / "tiempos.json").read_text(encoding="utf-8"))
        tiempos, palabras = d["escenas"], d["palabras"]
        audio, sr = sf.read(REC / "narracion.wav", dtype="float32")
        narr = (audio, sr)
        dur = len(audio) / sr + COLA
    else:
        import voz_sesion15 as V
        if args.tomas:
            # narración armada con la toma elegida de cada escena (tomas.py), sin volver a generar la voz
            elegidas = [int(x) for x in args.tomas.split(",")]
            assert len(elegidas) == len(guion["escenas"]), "una toma por escena"
            wavs, sr = [], None
            for i, (e, k) in enumerate(zip(guion["escenas"], elegidas), 1):
                w, sr = sf.read(AQUI / "muestras" / "tomas" / f"{i}_{e['id']}_toma{k}.wav", dtype="float32")
                wavs.append(w)
                e["toma"] = k
                e["wer"] = V._wer(e["frase"], V._a16k(w, sr))
            partes, tiempos_esc, t = [np.zeros(int(V.INICIO * sr), np.float32)], [], V.INICIO
            for w in wavs:
                tiempos_esc.append((t, t + len(w) / sr))
                partes += [w, np.zeros(int(V.PAUSA * sr), np.float32)]
                t += len(w) / sr + V.PAUSA
            partes.append(np.zeros(int(V.FINAL * sr), np.float32))
            n = V.Narracion(np.concatenate(partes), sr, tiempos_esc)
        else:
            voz = V.Voz(args.voz, modelo=args.tts, device=args.device)
            print(f"[{time.time() - t0:5.0f}s] voz de referencia: «{voz.texto_ref}»", flush=True)
            n = V.narrar(voz, guion, velocidad=args.velocidad)
        print(f"[{time.time() - t0:5.0f}s] narración de {n.duracion:.1f} s; WER por escena: "
              + ", ".join(f"{e['wer']:.2f}" for e in guion["escenas"]), flush=True)
        palabras = V.subtitulos(n, guion)
        a_srt(palabras, AQUI / "subtitulos.srt")
        sf.write(REC / "narracion.wav", n.audio, n.sr)
        tiempos = n.escenas
        (AQUI / "tiempos.json").write_text(json.dumps({"escenas": tiempos, "palabras": palabras, "wer": [e["wer"] for e in guion["escenas"]]},
                                                      ensure_ascii=False, indent=1), encoding="utf-8")
        narr = (n.audio, n.sr)
        dur = n.duracion + COLA
    audio_tmp = AQUI / "tmp_audio.wav"
    preparar_audio(narr, dur, audio_tmp)
    r = Render(guion, tiempos, palabras, args.url, dur)
    frames = int(dur * FPS)
    cmd = [FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(audio_tmp), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", args.salida]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(frames):
        proc.stdin.write(r.cuadro(k / FPS))
        if k % (FPS * 5) == 0:
            print(f"[{time.time() - t0:5.0f}s] cuadro {k}/{frames}", flush=True)
    proc.stdin.close()
    proc.wait()
    audio_tmp.unlink(missing_ok=True)
    # portada para LinkedIn (cuadro de la escena 2)
    t_port = (tiempos[1][0] + tiempos[1][1]) / 2
    Path(AQUI / "portada.png").write_bytes(b"")
    plt.imsave(AQUI / "portada.png", np.frombuffer(r.cuadro(t_port), np.uint8).reshape(H, W, 4))
    print(f"[{time.time() - t0:5.0f}s] listo: {args.salida} ({dur:.1f} s)")


if __name__ == "__main__":
    main()

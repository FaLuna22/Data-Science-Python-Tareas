"""Vigila el canal oficial del Congreso y transcribe solas las sesiones nuevas de las comisiones que sigues.

Cada ronda: actualiza datos/catalogo.json con las últimas transmisiones, busca las sesiones terminadas
de tus comisiones que aún no tienen transcripción, las transcribe con Whisper y, si das `--temas`,
genera su informe con Claude. Las que siguen en vivo se dejan para la ronda siguiente.

    # ver qué haría, sin descargar nada:
    python pipeline/vigilar.py --comisiones "Comisión de Energía y Minas" "Comisión de Salud" --simular

    # una ronda (para el Programador de tareas de Windows o cron):
    python pipeline/vigilar.py --comisiones "Comisión de Energía y Minas" --palabras minería Petroperú

    # sin parar, revisando cada 10 minutos, con informe y subiendo el resultado al repositorio:
    python pipeline/vigilar.py --comisiones "Comisión de Energía y Minas" --temas minería canon \\
        --cada 600 --publicar

    # solo actualizar el catálogo:
    python pipeline/vigilar.py --solo-catalogo

Requiere: pip install -r requirements-dev.txt (yt-dlp) y, para --temas, ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "pipeline"))

from relatoria import agenda, almacen  # noqa: E402


def _hora() -> str:
    return datetime.now(agenda.LIMA).strftime("%H:%M")


def actualizar_catalogo(profundidad: int) -> agenda.Catalogo:
    cat = agenda.Catalogo()
    try:
        nuevas = agenda.listar_transmisiones(profundidad)
    except Exception as e:  # yt-dlp falla o no está instalado: el feed basta para lo reciente
        print(f"[{_hora()}] listado con yt-dlp no disponible ({e.__class__.__name__}); uso el feed RSS", flush=True)
        nuevas = agenda.leer_rss()
    agregadas = cat.incorporar(nuevas)
    for e in cat.recientes():                     # completa fecha o estado donde falten
        if (not e.fecha or e.estado in ("", "en_vivo", "programada")) and e.visto >= _hace(3):
            cat.actualizar_estado(e.id, agenda.consultar_estado(e.id))
    cat.guardar()
    print(f"[{_hora()}] catálogo: {len(cat.emisiones)} emisiones ({len(agregadas)} nuevas)", flush=True)
    return cat


def _hace(dias: int) -> str:
    """Mismo formato que Emision.visto (ISO en UTC), para poder compararlos como texto."""
    return (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(timespec="seconds")


def pendientes(cat: agenda.Catalogo, comisiones: list[str], palabras: list[str], todas: bool,
               dias: int) -> tuple[list[agenda.Emision], list[agenda.Emision]]:
    """(listas para transcribir, las que siguen en vivo o programadas)."""
    canon = cat.canonico()
    hechas = agenda.transcritas()
    desde = (agenda.hoy_en_lima() - timedelta(days=dias)).isoformat()
    # lo que sigues por nombre o palabra entra aunque sea una mesa de trabajo; --todas, solo comisiones y plenos
    elegidas = [e for e in cat.recientes()
                if e.fecha >= desde and e.id not in hechas
                and (agenda.coincide(e, comisiones, palabras, canon) or (todas and e.tipo in ("comision", "pleno")))]
    listas = [e for e in elegidas if e.estado == "terminada"]
    en_curso = [e for e in elegidas if e.estado in ("en_vivo", "programada", "")]
    return listas, en_curso


def publicar(ids: list[str]) -> None:
    """git add/commit/push de lo nuevo en datos/. Streamlit Cloud redespliega la app al recibir el push."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True)
    git("add", "datos/sesiones", "datos/informes", "datos/catalogo.json")
    r = git("commit", "-m", f"datos: {len(ids)} sesión(es) transcrita(s) por el vigilante ({', '.join(ids)})")
    if r.returncode != 0:
        print(f"[{_hora()}] nada que publicar: {r.stdout.strip() or r.stderr.strip()}", flush=True)
        return
    r = git("push")
    print(f"[{_hora()}] publicado" if r.returncode == 0 else f"[{_hora()}] git push falló: {r.stderr.strip()}",
          flush=True)


def ronda(a) -> None:
    cat = actualizar_catalogo(a.profundidad)
    if a.solo_catalogo:
        return
    listas, en_curso = pendientes(cat, a.comisiones, a.palabras, a.todas, a.dias)
    canon = cat.canonico()
    for e in en_curso:
        print(f"  · en espera ({e.estado or 'sin estado'}): {e.fecha} {canon.get(e.organo, e.organo)}", flush=True)
    if not listas:
        print(f"[{_hora()}] no hay sesiones nuevas por transcribir", flush=True)
        return
    for e in listas:
        print(f"  · por transcribir: {e.fecha} {canon.get(e.organo, e.organo)} ({e.url})", flush=True)
    if a.simular:
        return

    from transcribir_sesion import transcribir_fuente
    hechas = []
    for e in listas[:a.max]:
        organo = canon.get(e.organo, e.organo) + (f" ({e.camara})" if e.camara and e.tipo == "comision" else "")
        try:
            sesion = transcribir_fuente(e.url, id=e.id, organo=organo, fecha=e.fecha, modelo=a.modelo,
                                        dispositivo=a.dispositivo, borrar_audio=True)
        except Exception as err:  # un video que no baja no detiene a los demás
            print(f"[{_hora()}] no se pudo transcribir {e.id}: {err}", flush=True)
            continue
        hechas.append(e.id)
        if a.temas and os.environ.get("ANTHROPIC_API_KEY"):
            from relatoria.informe import generar_informe
            try:
                informe, uso = generar_informe(sesion, a.temas)
                almacen.guardar(sesion, a.temas, informe, uso)
                print(f"[{_hora()}] informe de {e.id}: US$ {uso.costo_usd:.2f}", flush=True)
            except Exception as err:
                print(f"[{_hora()}] informe de {e.id} falló: {err}", flush=True)
        elif a.temas:
            print(f"[{_hora()}] sin ANTHROPIC_API_KEY: transcrito, pero sin informe", flush=True)
    if hechas and a.publicar:
        publicar(hechas)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--comisiones", nargs="*", default=[], help="Nombres como aparecen en la agenda de la app")
    p.add_argument("--palabras", nargs="*", default=[], help="Palabras que deben aparecer en el título")
    p.add_argument("--todas", action="store_true", help="Todas las comisiones y plenos")
    p.add_argument("--temas", nargs="*", default=[], help="Si se dan, genera el informe con estos temas")
    p.add_argument("--dias", type=int, default=7, help="Solo sesiones de los últimos N días (7)")
    p.add_argument("--max", type=int, default=3, help="Máximo de sesiones a transcribir por ronda (3)")
    p.add_argument("--cada", type=int, default=0, help="Segundos entre rondas; 0 = una sola ronda")
    p.add_argument("--profundidad", type=int, default=60, help="Transmisiones a revisar en el canal (60)")
    p.add_argument("--modelo", default="large-v3-turbo")
    p.add_argument("--dispositivo", default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--publicar", action="store_true", help="git commit y push de lo nuevo en datos/")
    p.add_argument("--simular", action="store_true", help="Solo mostrar qué se transcribiría")
    p.add_argument("--solo-catalogo", action="store_true")
    a = p.parse_args()
    if not (a.comisiones or a.palabras or a.todas or a.solo_catalogo):
        p.error("indica --comisiones, --palabras, --todas o --solo-catalogo")

    while True:
        try:
            ronda(a)
        except agenda.AgendaNoDisponible as e:
            print(f"[{_hora()}] {e}", flush=True)
        if not a.cada:
            break
        time.sleep(a.cada)


if __name__ == "__main__":
    main()

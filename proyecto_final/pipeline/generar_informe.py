"""Transcripción guardada -> informe guardado en datos/informes/ (para que el demo responda al instante).

    export ANTHROPIC_API_KEY=...
    python pipeline/generar_informe.py LvsY8hVx-ec --temas "sistema financiero" "AFP" "tasas de interés"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from relatoria import almacen  # noqa: E402
from relatoria.informe import generar_informe  # noqa: E402
from relatoria.transcripcion import Sesion  # noqa: E402
from relatoria.verificar import verificar_informe  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("id")
    p.add_argument("--temas", nargs="*", default=[])
    a = p.parse_args()
    sesion = Sesion.leer(RAIZ / "datos" / "sesiones" / f"{a.id}.json")
    informe, uso = generar_informe(sesion, a.temas)
    ruta = almacen.guardar(sesion, a.temas, informe, uso)
    r = verificar_informe(informe, sesion.segmentos)["resumen"]
    print(f"{ruta.relative_to(RAIZ)} · {uso.tokens_entrada:,} tokens de entrada, {uso.tokens_salida:,} de salida, "
          f"US$ {uso.costo_usd:.2f} · citas con respaldo: {r['con_respaldo']}/{r['citas']}")


if __name__ == "__main__":
    main()

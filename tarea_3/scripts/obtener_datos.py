"""Descarga los microdatos de la ENAHO (INEI) y el GeoJSON departamental.

Módulos:
  01  Características de la vivienda y del hogar (internet, celular, teléfono fijo, TV cable)
  03  Educación (uso de internet de cada persona de 6 años a más)
  34  Sumaria (pobreza, gasto, factor de expansión del hogar)

Uso:  python scripts/obtener_datos.py          (desde tarea_3/)
Los archivos quedan en datos/originales/ (ignorado por git).
"""
from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/{codigo}-Modulo{modulo}.zip"
GEOJSON = ("https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/"
           "sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson")

# Código de encuesta del INEI para la ENAHO anual (metodología actualizada, enero-diciembre)
CODIGOS = {2015: 498, 2016: 546, 2017: 603, 2018: 634, 2019: 687,
           2020: 737, 2021: 759, 2022: 784, 2023: 906, 2024: 966, 2025: 1031}
MODULOS = ["01", "03", "34"]

DESTINO = Path(__file__).resolve().parents[1] / "datos" / "originales"


def bajar(url: str, ruta: Path, intentos: int = 4) -> None:
    if ruta.exists() and ruta.stat().st_size > 0:
        print(f"  ya existe {ruta.name}")
        return
    for i in range(1, intentos + 1):
        try:
            tmp = ruta.with_suffix(ruta.suffix + ".part")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (tarea_3 ENAHO)"})
            with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
                while bloque := r.read(1 << 20):
                    f.write(bloque)
            tmp.replace(ruta)
            print(f"  ok {ruta.name} ({ruta.stat().st_size / 1e6:.1f} MB)")
            return
        except Exception as e:  # noqa: BLE001
            print(f"  intento {i} falló para {ruta.name}: {e}")
            time.sleep(5 * i)
    sys.exit(f"No se pudo descargar {url}")


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    bajar(GEOJSON, DESTINO / "peru_departamental_simple.geojson")
    for anio, codigo in CODIGOS.items():
        print(f"ENAHO {anio} (código {codigo})")
        for m in MODULOS:
            bajar(BASE.format(codigo=codigo, modulo=m), DESTINO / f"enaho_{anio}_mod{m}.zip")


if __name__ == "__main__":
    main()

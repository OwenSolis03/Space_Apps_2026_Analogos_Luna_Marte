#!/usr/bin/env python3
"""Descarga productos MODIS de NASA Earthdata para la máscara árida y el contraste térmico.

Requiere una cuenta de Earthdata (https://urs.earthdata.nasa.gov) y un ~/.netrc en Yuca:
    machine urs.earthdata.nasa.gov login <usuario> password <contraseña>
con permisos 600. Este script nunca lee ni imprime esas credenciales: earthaccess las toma del .netrc.

Productos (grilla global CMG de 0.05°, un archivo por mes):
    MOD13C2 v061  NDVI mensual          -> máscara de vegetación (NDVI máximo anual)
    MOD11C3 v061  Temperatura superficial mensual (día/noche) -> amplitud térmica terrestre
"""
import argparse
import os
import sys

import earthaccess

PRODUCTS = {
    "MOD13C2": "ndvi",
    "MOD11C3": "lst",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True, help="p. ej. /lustre/proyectos/p089/data/raw/earth/modis")
    p.add_argument("--year", type=int, default=2023)
    args = p.parse_args()

    auth = earthaccess.login(strategy="netrc")
    if not auth or not auth.authenticated:
        sys.exit("[ERROR] No se pudo autenticar con ~/.netrc (urs.earthdata.nasa.gov).")

    for short_name, sub in PRODUCTS.items():
        out = os.path.join(args.out_dir, sub)
        os.makedirs(out, exist_ok=True)
        results = earthaccess.search_data(
            short_name=short_name,
            version="061",
            temporal=(f"{args.year}-01-01", f"{args.year}-12-31"),
        )
        print(f"[*] {short_name}: {len(results)} granulos para {args.year}")
        files = earthaccess.download(results, local_path=out)
        print(f"[OK] {short_name}: {len(files)} archivos en {out}")


if __name__ == "__main__":
    main()

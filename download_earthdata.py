#!/usr/bin/env python3
"""Download NASA Earthdata MODIS products for aridity masking and thermal contrast.

Requires an Earthdata account (https://urs.earthdata.nasa.gov) and a ~/.netrc configuration:
    machine urs.earthdata.nasa.gov login <username> password <password>
with permissions 600. Credentials are handled securely by earthaccess and are never
read or printed directly.

Products (global 0.05° CMG grid, one file per month):
    MOD13C2 v061  Monthly NDVI                  -> vegetation mask (annual maximum NDVI)
    MOD11C3 v061  Monthly Land Surface Temp     -> diurnal thermal amplitude
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
    p = argparse.ArgumentParser(
        description="Download monthly MODIS products from NASA Earthdata (MOD13C2 NDVI, MOD11C3 LST)."
    )
    p.add_argument(
        "--out-dir",
        required=True,
        help="Destination directory (e.g. /lustre/proyectos/p089/data/raw/earth/modis)",
    )
    p.add_argument("--year", type=int, default=2023, help="Acquisition year to download (default: 2023).")
    args = p.parse_args()

    auth = earthaccess.login(strategy="netrc")
    if not auth or not auth.authenticated:
        sys.exit("[ERROR] Could not authenticate via ~/.netrc (urs.earthdata.nasa.gov).")

    for short_name, sub in PRODUCTS.items():
        out = os.path.join(args.out_dir, sub)
        os.makedirs(out, exist_ok=True)
        results = earthaccess.search_data(
            short_name=short_name,
            version="061",
            temporal=(f"{args.year}-01-01", f"{args.year}-12-31"),
        )
        print(f"[*] {short_name}: {len(results)} granules found for {args.year}")
        files = earthaccess.download(results, local_path=out)
        print(f"[OK] {short_name}: {len(files)} files downloaded to {out}")


if __name__ == "__main__":
    main()

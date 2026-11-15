#!/usr/bin/env python3
"""Download the EMIT L3 aggregated mineral abundance granule (EMITL3ASA v002, one 22 MB netCDF).

Needs the Earthdata account in ``~/.netrc`` (``machine urs.earthdata.nasa.gov``), the same one that
``download_earthdata.py`` uses. earthaccess reads the credentials itself; this script never prints them.

    python tools/download_emit.py --out-dir /lustre/proyectos/p089/data/raw/earth/emit/l3asa
"""
import argparse
import sys
from pathlib import Path

import earthaccess


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()

    auth = earthaccess.login(strategy="netrc")
    if not auth or not auth.authenticated:
        sys.exit("[ERROR] Could not authenticate with ~/.netrc (urs.earthdata.nasa.gov).")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    results = earthaccess.search_data(short_name="EMITL3ASA", version="002")
    print(f"[*] EMITL3ASA v002: {len(results)} granule(s)")
    if not results:
        sys.exit("[ERROR] No EMITL3ASA v002 granule found.")
    files = earthaccess.download(results, str(args.out_dir))
    print(f"[OK] {len(files)} file(s) in {args.out_dir}")


if __name__ == "__main__":
    main()

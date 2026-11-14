#!/usr/bin/env python3
"""Download NASA Earthdata MOD08_M3 v061 monthly aerosol files for T13.

Requires an Earthdata account (https://urs.earthdata.nasa.gov) and a ~/.netrc
file with permissions 600. Uses earthaccess so credentials are never read or
printed by this script.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import earthaccess


def _count_valid_hdf(out_dir: Path) -> list[Path]:
    return sorted(p for p in out_dir.glob("*.hdf") if p.is_file() and p.stat().st_size > 0)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Download MODIS Terra MOD08_M3 v061 monthly granules (Earth AOD)."
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Destination directory (e.g. /lustre/proyectos/p089/data/raw/earth/modis/aod)",
    )
    parser.add_argument("--start", type=str, default="2019-01-01")
    parser.add_argument("--end", type=str, default="2023-12-31")
    parser.add_argument("--expected-min", type=int, default=60)
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    existing = _count_valid_hdf(args.out_dir)
    if len(existing) >= args.expected_min:
        print(
            f"[SKIP] Found {len(existing)} existing non-empty .hdf files in {args.out_dir} "
            f"(>= expected_min={args.expected_min})."
        )
        return

    auth = earthaccess.login(strategy="netrc")
    if not auth or not auth.authenticated:
        sys.exit("[ERROR] Failed to authenticate with Earthdata via ~/.netrc.")

    results = earthaccess.search_data(
        short_name="MOD08_M3",
        version="061",
        temporal=(args.start, args.end),
    )
    print(f"[*] MOD08_M3 v061 ({args.start} to {args.end}): found {len(results)} granules.")
    if len(results) < args.expected_min:
        sys.exit(
            f"[ERROR] Expected at least {args.expected_min} MOD08_M3 granules, "
            f"but search returned {len(results)}."
        )

    files = earthaccess.download(results, local_path=str(args.out_dir))
    print(f"[*] earthaccess.download returned {len(files)} paths.")

    final_hdf = _count_valid_hdf(args.out_dir)
    print(f"[OK] Verified {len(final_hdf)} non-empty .hdf files in {args.out_dir}.")
    if len(final_hdf) < args.expected_min:
        sys.exit(
            f"[ERROR] Only {len(final_hdf)} non-empty .hdf files present after download "
            f"(expected >= {args.expected_min})."
        )


if __name__ == "__main__":
    main()

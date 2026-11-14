"""Download and probe script for mineral datasets (EMIT, OMEGA, TES).

Part of experimental Mars-only mineral dimension (Option B, docs/plan_mineral_dimension.md).
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import subprocess
import sys

logger = logging.getLogger(__name__)

# Remote URLs
OMEGA_BASE_URL = (
    "https://archives.esac.esa.int/psa/ftp/MARS-EXPRESS/OMEGA/MEX-M-OMEGA-5-DDR-GLOBAL-MAPS-V1.0"
)
OMEGA_FILES = [
    ("EXTRAS/FERRIC/FERRIC_BD530_EQU_MAP.TIF", "FERRIC_BD530_EQU_MAP.TIF"),
    ("DATA/FERRIC/FERRIC_BD530_EQU_MAP.LBL", "FERRIC_BD530_EQU_MAP.LBL"),
    ("EXTRAS/FERRIC/FERRIC_NNPHS_EQU_MAP.TIF", "FERRIC_NNPHS_EQU_MAP.TIF"),
    ("DATA/FERRIC/FERRIC_NNPHS_EQU_MAP.LBL", "FERRIC_NNPHS_EQU_MAP.LBL"),
]

TES_BASE_URL = "http://tes.mars.asu.edu/data"
TES_FILES = [
    ("tes_minmap.img", 53913600),
    ("tes_minmap.hdr", 1024),
]


def download_file_curl(url: str, dest: Path, auth_required: bool = False) -> None:
    """Download a file with curl, checking for COSMOS 401 errors if auth_required."""
    if dest.exists() and dest.stat().st_size > 0:
        logger.info("File already exists: %s (%d bytes)", dest, dest.stat().st_size)
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["curl", "--fail", "-L", "-sS", "-o", str(dest)]
    if auth_required:
        cmd.append("--netrc")
    cmd.append(url)

    logger.info("Downloading %s -> %s", url, dest)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        if auth_required and ("401" in res.stderr or "401" in res.stdout or res.returncode == 22):
            logger.error("COSMOS credentials missing or invalid in ~/.netrc (machine archives.esac.esa.int)")
            sys.exit(
                "COSMOS credentials missing in ~/.netrc (machine archives.esac.esa.int). "
                "Please register an ESA COSMOS account and add it to ~/.netrc."
            )
        raise RuntimeError(f"curl failed for {url}: {res.stderr}")


def download_omega(target_dir: Path) -> list[Path]:
    """Download OMEGA global maps from ESA PSA."""
    target_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for rel_path, local_name in OMEGA_FILES:
        url = f"{OMEGA_BASE_URL}/{rel_path}"
        dest = target_dir / local_name
        download_file_curl(url, dest, auth_required=True)
        downloaded.append(dest)
    return downloaded


def download_tes(target_dir: Path) -> list[Path]:
    """Download TES 4 ppd mineral map from ASU."""
    target_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for fname, _ in TES_FILES:
        url = f"{TES_BASE_URL}/{fname}"
        dest = target_dir / fname
        download_file_curl(url, dest, auth_required=False)
        downloaded.append(dest)
    return downloaded


def download_emit(target_dir: Path) -> list[Path]:
    """Download EMIT L3 ASA V002 granule via earthaccess."""
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        import earthaccess
    except ImportError:
        logger.warning("earthaccess not installed; skipping automated EMIT download.")
        return []

    logger.info("Searching EMIT L3 ASA granule (short_name='EMITL3ASA', version='002')...")
    results = earthaccess.search_data(
        short_name="EMITL3ASA",
        version="002",
        count=1,
    )
    if not results:
        logger.warning("No EMIT granules found via earthaccess.")
        return []

    downloaded = earthaccess.download(results, str(target_dir))
    return [Path(p) for p in downloaded]


def generate_probe(
    omega_dir: Path,
    tes_dir: Path,
    emit_dir: Path,
    out_json: Path,
) -> dict[str, object]:
    """Generate diagnostic mineral_probe.json inspect report."""
    probe: dict[str, object] = {
        "omega": {},
        "tes": {},
        "emit": {},
    }

    # Probe OMEGA
    bd530_tif = omega_dir / "FERRIC_BD530_EQU_MAP.TIF"
    bd530_lbl = omega_dir / "FERRIC_BD530_EQU_MAP.LBL"
    if bd530_lbl.exists():
        probe["omega"]["bd530_lbl_text"] = bd530_lbl.read_text(encoding="latin1")[:1000]
    if bd530_tif.exists():
        try:
            import rasterio

            with rasterio.open(bd530_tif) as src:
                probe["omega"]["bd530_meta"] = {
                    "crs": str(src.crs),
                    "transform": [float(x) for x in src.transform],
                    "width": src.width,
                    "height": src.height,
                    "dtype": str(src.dtypes[0]),
                    "nodata": src.nodata,
                }
        except Exception as e:
            probe["omega"]["bd530_error"] = str(e)

    # Probe TES
    tes_hdr = tes_dir / "tes_minmap.hdr"
    if tes_hdr.exists():
        probe["tes"]["hdr_text"] = tes_hdr.read_text(encoding="latin1")
    tes_img = tes_dir / "tes_minmap.img"
    if tes_img.exists():
        probe["tes"]["img_size_bytes"] = tes_img.stat().st_size

    # Probe EMIT
    emit_files = list(emit_dir.glob("*.nc"))
    if emit_files:
        probe["emit"]["file"] = emit_files[0].name
        try:
            import xarray as xr

            with xr.open_dataset(emit_files[0]) as ds:
                probe["emit"]["vars"] = list(ds.data_vars.keys())
                probe["emit"]["coords"] = list(ds.coords.keys())
        except Exception as e:
            probe["emit"]["error"] = str(e)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(probe, indent=2), encoding="utf-8")
    logger.info("Probe report written to %s", out_json)
    return probe


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path("/lustre/proyectos/p089"))
    parser.add_argument("--probe-out", type=Path, default=Path("mineral_probe.json"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    raw_dir = args.project_dir / "data" / "raw"
    omega_dir = raw_dir / "mars" / "omega_global"
    tes_dir = raw_dir / "mars" / "tes_minmap"
    emit_dir = raw_dir / "earth" / "emit" / "l3asa"

    logger.info("Starting minerals download...")
    download_tes(tes_dir)
    download_omega(omega_dir)
    download_emit(emit_dir)

    generate_probe(omega_dir, tes_dir, emit_dir, args.probe_out)
    logger.info("Minerals download and probe completed successfully.")


if __name__ == "__main__":
    main()

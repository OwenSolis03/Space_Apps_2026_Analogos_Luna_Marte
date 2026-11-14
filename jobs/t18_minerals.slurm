#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-t18-minerals
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH -o /lustre/proyectos/p089/output/t18_minerals_%j.log
#SBATCH -e /lustre/proyectos/p089/output/t18_minerals_%j.log

# T18 mineralogy context (display only, nothing is scored).
# Adds the EMIT mineral values of every Earth analog to analogs_universe.json. The Moon (Kaguya) and Mars (TES)
# blocks are already in the committed JSON, so this job only needs the EMIT file; a source that is not given
# leaves the blocks the input already has.
#
# Run from the clone:   cd /lustre/proyectos/p089/code && git pull && sbatch jobs/t18_minerals.slurm
# Optional variables:   UNIVERSE=<input json>   EMIT_FILE=<EMIT_L3_ASA_002.nc>   EMIT_SCALE=<factor, default 100>
# EMIT_SCALE: the EMIT file has no units attribute and its values are fractions (0 to 1), so they are x100 to show percent.
# Output:               runs/<JOBID>/analogs_universe.json and runs/<JOBID>/mineral_report.md
# Reads data only; nothing under data/ is modified, except that the EMIT file is downloaded if it is missing.

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
CODE_DIR="${CODE_DIR:-${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code}}"
UNIVERSE="${UNIVERSE:-$CODE_DIR/app/public/data/analogs_universe.json}"
OUT_DIR="$PROJECT_DIR/runs/${SLURM_JOB_ID:-manual}"
mkdir -p "$OUT_DIR"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026
cd "$CODE_DIR"

echo "job=${SLURM_JOB_ID:-local} node=$(hostname) start=$(date -Is) commit=$(git -C "$CODE_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"
echo "universe=$UNIVERSE"

# EMIT file: given, or already downloaded (by T18 or by the option-B experiment), or download it now.
if [ -z "${EMIT_FILE:-}" ]; then
  EMIT_FILE="$(ls "$PROJECT_DIR"/data/raw/earth/emit/l3asa/*.nc "$PROJECT_DIR"/data/raw/earth/emit/*.nc 2>/dev/null | head -1 || true)"
fi
if [ -z "$EMIT_FILE" ]; then
  echo "[*] No EMIT file found, downloading EMITL3ASA v002 (needs ~/.netrc)"
  python tools/download_emit.py --out-dir "$PROJECT_DIR/data/raw/earth/emit/l3asa"
  EMIT_FILE="$(ls "$PROJECT_DIR"/data/raw/earth/emit/l3asa/*.nc | head -1)"
fi
ls -l "$EMIT_FILE"

# Which readers this environment has (the module tries GDAL first, then xarray).
python - <<'EOF'
import rasterio
with rasterio.Env() as env:
    print("GDAL netCDF driver:", "netCDF" in env.drivers())
try:
    import xarray, h5netcdf  # noqa: F401
    print("xarray + h5netcdf: yes")
except Exception as exc:
    print("xarray + h5netcdf:", type(exc).__name__, exc)
EOF

python -m pipeline.minerals \
  --universe "$UNIVERSE" \
  --out "$OUT_DIR/analogs_universe.json" \
  --emit-file "$EMIT_FILE" \
  --report "$OUT_DIR/mineral_report.md"

echo "=== report"
cat "$OUT_DIR/mineral_report.md"
ls -l "$OUT_DIR/analogs_universe.json"
echo "end=$(date -Is)"

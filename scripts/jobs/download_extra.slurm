#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-descargas-extra
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=06:00:00
#SBATCH -o /lustre/proyectos/p089/output/descargas_extra_%j.log
#SBATCH -e /lustre/proyectos/p089/output/descargas_extra_%j.log

# Additional Earth layers (official challenge resources):
#   1. Natural Earth: roads and airports (logistics)            ~10 MB
#   2. NASA Earthdata MODIS: NDVI (MOD13C2) and LST (MOD11C3) 2023   ~4-5 GB
# Step 2 requires ~/.netrc with Earthdata account; skipped if missing.

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
# Repo clone (the submission directory); the downloader is scripts/tools/download_earthdata.py.
CODE_DIR="${CODE_DIR:-${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code}}"
RAW_EARTH="$PROJECT_DIR/data/raw/earth"
mkdir -p "$RAW_EARTH/naturalearth" "$RAW_EARTH/modis"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026

echo "job=${SLURM_JOB_ID:-local} node=$(hostname) start=$(date -Is)"

echo "[1/2] Natural Earth 10m: roads, airports, and countries"
for layer in ne_10m_roads ne_10m_airports ne_10m_admin_0_countries; do
  aria2c -c --auto-file-renaming=false --max-tries=5 -d "$RAW_EARTH/naturalearth" -o "$layer.zip" \
    "https://naciscdn.org/naturalearth/10m/cultural/$layer.zip" || echo "[WARN] $layer failed"
  if [ -f "$RAW_EARTH/naturalearth/$layer.zip" ] && [ ! -d "$RAW_EARTH/naturalearth/$layer" ]; then
    unzip -q -n "$RAW_EARTH/naturalearth/$layer.zip" -d "$RAW_EARTH/naturalearth/$layer"
  fi
done

echo "[2/2] MODIS NDVI and LST (Earthdata)"
if [ -f "$HOME/.netrc" ]; then
  python -c "import earthaccess" 2>/dev/null || pip install --quiet earthaccess
  python "$CODE_DIR/scripts/tools/download_earthdata.py" --out-dir "$RAW_EARTH/modis" --year 2023 || echo "[WARN] MODIS failed"
else
  echo "[SKIP] ~/.netrc not found; configure Earthdata credentials in ~/.netrc and resubmit."
fi

echo "=== Verification"
ls -R "$RAW_EARTH/naturalearth" | head -20
find "$RAW_EARTH/modis" -name '*.hdf' | wc -l
du -sh "$RAW_EARTH/naturalearth" "$RAW_EARTH/modis"
echo "end=$(date -Is)"

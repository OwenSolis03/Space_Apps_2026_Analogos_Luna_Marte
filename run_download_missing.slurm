#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-descargas
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=23:00:00
#SBATCH -o /lustre/proyectos/p089/output/descargas_%j.log
#SBATCH -e /lustre/proyectos/p089/output/descargas_%j.log

# Download missing or incomplete datasets:
#   1. THEMIS IR Night (60N-60S mosaic)
#   2. Lunar true reflectance layer (LROC WAC)
#   3. Lunar polar ice favorability index (both poles)
#   4. Remaining Copernicus GLO-90 tiles (resumes partial downloads)
# Idempotent: aria2c -c resumes or skips already completed files.

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
RAW_EARTH="$PROJECT_DIR/data/raw/earth"
RAW_MOON="$PROJECT_DIR/data/raw/moon"
RAW_MARS="$PROJECT_DIR/data/raw/mars"
USGS="https://planetarymaps.usgs.gov/mosaic"
mkdir -p "$RAW_EARTH/copernicus_90m" "$RAW_MOON" "$RAW_MARS"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026

echo "job=${SLURM_JOB_ID:-local} node=$(hostname) start=$(date -Is)"
lfs quota -h -g p089 /lustre || true

ARIA_BASE=(-c --auto-file-renaming=false --allow-overwrite=false
           --max-tries=5 --retry-wait=15 --console-log-level=warn --summary-interval=300)

echo "[1/4] THEMIS IR Night 60N-60S (15.2 GB)"
aria2c "${ARIA_BASE[@]}" -x 4 -s 4 -d "$RAW_MARS" \
  -o "Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif" \
  "$USGS/Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif" || echo "[WARN] THEMIS Night failed"

echo "[2/4] LROC WAC global 100 m (6.0 GB)"
aria2c "${ARIA_BASE[@]}" -x 4 -s 4 -d "$RAW_MOON" \
  -o "Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif" \
  "$USGS/Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif" || echo "[WARN] WAC failed"

echo "[3/4] Ice favorability index (polar regions, ~8 MB)"
for pole in 90S000E 90N000E; do
  aria2c "${ARIA_BASE[@]}" -d "$RAW_MOON" -o "Moon_IceFavorabilityIndex_${pole}_591mp.tif" \
    "$USGS/Lunar_Research/IceFavorabilityIndex/Moon_IceFavorabilityIndex_${pole}_591mp.tif" \
    || echo "[WARN] ice $pole failed"
done

echo "[4/4] Copernicus GLO-90: remaining tiles"
TILE_LIST="$RAW_EARTH/copernicus_90m_tileList.txt"
URL_LIST="$RAW_EARTH/copernicus_90m_urls_${SLURM_JOB_ID:-local}.txt"
FAILED="$RAW_EARTH/copernicus_90m_failed_${SLURM_JOB_ID:-local}.txt"
# Strip \r from tileList:
tr -d '\r' < "$TILE_LIST" | awk 'NF {
    name=$0; sub(/\.tif$/, "", name);
    print "https://copernicus-dem-90m.s3.amazonaws.com/" name "/" name ".tif"
}' > "$URL_LIST"
echo "    URLs: $(wc -l < "$URL_LIST")"
aria2c "${ARIA_BASE[@]}" -j 16 -x 1 -s 1 -d "$RAW_EARTH/copernicus_90m" \
  -i "$URL_LIST" --save-session="$FAILED" || echo "[WARN] some tiles failed; see $FAILED"

echo "=== Verification"
n_tif=$(find "$RAW_EARTH/copernicus_90m" -maxdepth 1 -name '*.tif' | wc -l)
n_part=$(find "$RAW_EARTH/copernicus_90m" -maxdepth 1 -name '*.aria2' | wc -l)
echo "Copernicus: $n_tif tif, $n_part incomplete (.aria2), of $(wc -l < "$URL_LIST") in list"
echo "Failed saved to $FAILED: $(grep -c '^http' "$FAILED" 2>/dev/null || echo 0)"
ls -lh "$RAW_MARS" "$RAW_MOON"
du -sh "$RAW_EARTH/copernicus_90m" "$RAW_MARS" "$RAW_MOON"
lfs quota -h -g p089 /lustre || true
echo "fin=$(date -Is)"

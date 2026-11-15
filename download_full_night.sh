#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
RAW_EARTH="$PROJECT_DIR/data/raw/earth"
RAW_MOON="$PROJECT_DIR/data/raw/moon"
RAW_MARS="$PROJECT_DIR/data/raw/mars"
mkdir -p "$RAW_EARTH/copernicus_90m" "$RAW_EARTH/masks" "$RAW_MOON" "$RAW_MARS"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026

echo "[1/3] Verifying auxiliary layers for Moon and Mars..."
aria2c -c -x 2 -s 2 -d "$RAW_MOON" -o "Lunar_LRO_LOLA_Albedo_Global_128ppd.tif" \
  "https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_ClrShade_Global_128ppd_v04.tif" || true

aria2c -c -x 2 -s 2 -d "$RAW_MARS" -o "Mars_ODY_THEMIS_IR_Night_Mosaic_100m.tif" \
  "https://planetarymaps.usgs.gov/mosaic/Mars_MO_THEMIS-IR-Night_mosaic_global_100m_v14.tif" || true

echo "[2/3] Generating clean URL list for Copernicus DEM 90m..."
if [ ! -f "$RAW_EARTH/copernicus_90m_tileList.txt" ]; then
    aws s3 cp --no-sign-request s3://copernicus-dem-90m/tileList.txt "$RAW_EARTH/copernicus_90m_tileList.txt"
fi

URL_LIST="$RAW_EARTH/copernicus_90m_urls.txt"
tr -d '\r' < "$RAW_EARTH/copernicus_90m_tileList.txt" | awk 'NF {
    name=$0; sub(/\.tif$/, "", name);
    print "https://copernicus-dem-90m.s3.amazonaws.com/" name "/" name ".tif"
}' > "$URL_LIST"

echo "[3/3] Downloading $(wc -l < "$URL_LIST") Earth tiles (10 threads)..."
aria2c -c -j 10 -x 1 -s 1 --auto-file-renaming=false \
  --console-log-level=warn --summary-interval=60 \
  -d "$RAW_EARTH/copernicus_90m" -i "$URL_LIST"

echo "[OK] GLOBAL DOWNLOAD COMPLETED: $(date)"
du -sh "$PROJECT_DIR/data/raw/"*

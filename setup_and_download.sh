#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
RAW_EARTH="$PROJECT_DIR/data/raw/earth"
RAW_MOON="$PROJECT_DIR/data/raw/moon"
RAW_MARS="$PROJECT_DIR/data/raw/mars"
mkdir -p "$RAW_EARTH" "$RAW_MOON" "$RAW_MARS" "$PROJECT_DIR/output"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026

echo "[1/3] Descargando DEM global de Marte (MOLA 463m)..."
aria2c -c -x 2 -s 2 -d "$RAW_MARS" -o "Mars_MGS_MOLA_DEM_mosaic_global_463m.tif" \
  "https://planetarymaps.usgs.gov/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif"

echo "[2/3] Descargando mosaico térmico THEMIS de Marte (100m)..."
aria2c -c -x 2 -s 2 -d "$RAW_MARS" -o "Mars_ODY_THEMIS_IR_Day_Mosaic_100m.tif" \
  "https://planetarymaps.usgs.gov/mosaic/Mars_MO_THEMIS-IR-Day_mosaic_global_100m_v12.tif"

echo "[3/3] Descargando índice Copernicus DEM GLO-90..."
aws s3 cp --no-sign-request s3://copernicus-dem-90m/tileList.txt "$RAW_EARTH/copernicus_90m_tileList.txt"

echo "[OK] Todas las descargas base finalizaron."
ls -lh "$RAW_MOON" "$RAW_MARS" "$RAW_EARTH"

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

# Capas terrestres adicionales (recursos oficiales del challenge):
#   1. Natural Earth: carreteras y aeropuertos (logística)            ~10 MB
#   2. NASA Earthdata MODIS: NDVI (MOD13C2) y LST (MOD11C3) de 2023   ~4-5 GB
# El paso 2 necesita ~/.netrc con la cuenta de Earthdata; si no existe, se salta.

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
# Carpeta donde está download_earthdata.py: la carpeta desde la que se hizo sbatch (el clon del repo).
CODE_DIR="${CODE_DIR:-${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code}}"
RAW_EARTH="$PROJECT_DIR/data/raw/earth"
mkdir -p "$RAW_EARTH/naturalearth" "$RAW_EARTH/modis"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026

echo "job=${SLURM_JOB_ID:-local} nodo=$(hostname) inicio=$(date -Is)"

echo "[1/2] Natural Earth 10m: carreteras, aeropuertos y países"
for layer in ne_10m_roads ne_10m_airports ne_10m_admin_0_countries; do
  aria2c -c --auto-file-renaming=false --max-tries=5 -d "$RAW_EARTH/naturalearth" -o "$layer.zip" \
    "https://naciscdn.org/naturalearth/10m/cultural/$layer.zip" || echo "[WARN] $layer falló"
  if [ -f "$RAW_EARTH/naturalearth/$layer.zip" ] && [ ! -d "$RAW_EARTH/naturalearth/$layer" ]; then
    unzip -q -n "$RAW_EARTH/naturalearth/$layer.zip" -d "$RAW_EARTH/naturalearth/$layer"
  fi
done

echo "[2/2] MODIS NDVI y LST (Earthdata)"
if [ -f "$HOME/.netrc" ]; then
  python -c "import earthaccess" 2>/dev/null || pip install --quiet earthaccess
  python "$CODE_DIR/download_earthdata.py" --out-dir "$RAW_EARTH/modis" --year 2023 || echo "[WARN] MODIS falló"
else
  echo "[SKIP] No existe ~/.netrc; crea la cuenta de Earthdata y el .netrc, y vuelve a enviar este job."
fi

echo "=== Verificación"
ls -R "$RAW_EARTH/naturalearth" | head -20
find "$RAW_EARTH/modis" -name '*.hdf' | wc -l
du -sh "$RAW_EARTH/naturalearth" "$RAW_EARTH/modis"
echo "fin=$(date -Is)"

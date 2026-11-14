#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-dl-t12-t14
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH -o /lustre/proyectos/p089/output/download_t12_t14_%j.log
#SBATCH -e /lustre/proyectos/p089/output/download_t12_t14_%j.log

# Download and unpack raw datasets for T14 (geology), T13 (dust) and T12 (ice).
# Submit from /lustre/proyectos/p089/code:  sbatch jobs/download_t12_t14.slurm

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
CODE_DIR="${CODE_DIR:-${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code}}"
if [[ ! -d "$CODE_DIR/pipeline" ]]; then
  CODE_DIR="$PROJECT_DIR/code"
fi
RAW_DIR="$PROJECT_DIR/data/raw"

mkdir -p "$PROJECT_DIR/output"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026
cd "$CODE_DIR"

echo "job=${SLURM_JOB_ID:-local} node=$(hostname) start=$(date -Is) commit=$(git -C "$CODE_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"

fetch_url() {
  local url="$1"
  local dest="$2"
  mkdir -p "$(dirname "$dest")"
  if [[ -s "$dest" ]]; then
    echo "[SKIP] $dest already exists ($(stat -c '%s' "$dest") bytes)"
    return 0
  fi
  local tmp="${dest}.part"
  rm -f "$tmp"
  echo "[*] Downloading $url -> $dest"
  curl -L --fail --retry 3 --retry-delay 10 -o "$tmp" "$url"
  mv "$tmp" "$dest"
  echo "[OK] Downloaded $dest ($(stat -c '%s' "$dest") bytes)"
}

# 1. Earth GLiM 0.5 deg lithology
GLIM_DIR="$RAW_DIR/geology/earth_glim"
GLIM_ZIP="$GLIM_DIR/glim_0p5deg.zip"
fetch_url "https://hdl.handle.net/10013/epic.39939.d001" "$GLIM_ZIP"
if [[ ! -s "$GLIM_DIR/glim_wgs84_0point5deg.txt.asc" ]]; then
  echo "[*] Unzipping $GLIM_ZIP in $GLIM_DIR"
  unzip -oq "$GLIM_ZIP" -d "$GLIM_DIR"
else
  echo "[SKIP] GLiM ASCII grid already extracted in $GLIM_DIR"
fi

# 2. Mars USGS SIM 3292 geology
MARS_GEO_DIR="$RAW_DIR/geology/mars_sim3292"
MARS_GEO_ZIP="$MARS_GEO_DIR/sim3292_database.zip"
fetch_url "https://pubs.usgs.gov/sim/3292/downloads/sim3292_database.zip" "$MARS_GEO_ZIP"
fetch_url "https://pubs.usgs.gov/sim/3292/downloads/sim3292_readme.txt" "$MARS_GEO_DIR/sim3292_readme.txt"
if ! find "$MARS_GEO_DIR" -maxdepth 3 \( -name "*.shp" -o -name "*.gdb" \) | grep -q .; then
  echo "[*] Unzipping $MARS_GEO_ZIP in $MARS_GEO_DIR"
  unzip -oq "$MARS_GEO_ZIP" -d "$MARS_GEO_DIR"
else
  echo "[SKIP] Mars SIM 3292 GIS data already extracted in $MARS_GEO_DIR"
fi

# 3. Moon USGS Unified Geologic Map 1:5M (2020)
MOON_GEO_DIR="$RAW_DIR/geology/moon_unified"
MOON_GEO_ZIP="$MOON_GEO_DIR/Unified_Geologic_Map_of_the_Moon_GIS_v2.zip"
fetch_url "https://asc-astropedia.s3.us-west-2.amazonaws.com/Moon/Geology/Unified_Geologic_Map_of_the_Moon_GIS_v2.zip" "$MOON_GEO_ZIP"
if ! find "$MOON_GEO_DIR" -maxdepth 3 \( -name "*.shp" -o -name "*.gdb" \) | grep -q .; then
  echo "[*] Unzipping $MOON_GEO_ZIP in $MOON_GEO_DIR"
  unzip -oq "$MOON_GEO_ZIP" -d "$MOON_GEO_DIR"
else
  echo "[SKIP] Moon unified GIS data already extracted in $MOON_GEO_DIR"
fi

# 4. Mars dust climatology (Montabone et al. kriged CDOD v2, MY24-MY36)
MARS_DUST_DIR="$RAW_DIR/mars/dust_montabone"
MARS_DUST_TGZ="$MARS_DUST_DIR/krigedcdod_v2.tar.gz"
fetch_url "https://www-mars.lmd.jussieu.fr/mars/dust_climatology/dataset_v2/krigedcdod_v2.tar.gz" "$MARS_DUST_TGZ"
if ! find "$MARS_DUST_DIR" -maxdepth 3 -name "*.nc" | grep -q .; then
  echo "[*] Extracting $MARS_DUST_TGZ in $MARS_DUST_DIR"
  tar -xzf "$MARS_DUST_TGZ" -C "$MARS_DUST_DIR"
else
  echo "[SKIP] Montabone NetCDF files already extracted in $MARS_DUST_DIR"
fi

# 5. Earth MODIS MOD08_M3 monthly AOD (2019-2023, 60 granules)
AOD_DIR="$RAW_DIR/earth/modis/aod"
python "$CODE_DIR/download_aod.py" \
  --out-dir "$AOD_DIR" \
  --start "2019-01-01" \
  --end "2023-12-31" \
  --expected-min 60

echo "=== File sizes and SHA-256 checksums ==="
for d in "$GLIM_DIR" "$MARS_GEO_DIR" "$MOON_GEO_DIR" "$MARS_DUST_DIR" "$AOD_DIR"; do
  echo "--- Directory: $d ---"
  while IFS= read -r -d '' f; do
    size_bytes=$(stat -c '%s' "$f")
    digest=$(sha256sum "$f" | awk '{print $1}')
    printf "%14s  %s  %s\n" "$size_bytes" "$digest" "$f"
  done < <(find "$d" -type f -print0 | sort -z)
done

echo "end=$(date -Is)"

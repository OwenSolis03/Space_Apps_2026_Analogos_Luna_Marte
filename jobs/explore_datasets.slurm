#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-exploracion
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH -o /lustre/proyectos/p089/output/exploracion_%j.log
#SBATCH -e /lustre/proyectos/p089/output/exploracion_%j.log

# Reporte de exploración de todos los datasets descargados.
# Enviar desde /lustre/proyectos/p089/code:   sbatch jobs/explore_datasets.slurm
# Para explorar solo una parte:               sbatch jobs/explore_datasets.slurm --only planets
# Salida: /lustre/proyectos/p089/runs/<JOBID>/exploracion/{index.html,resumen.md,resumen.json}
# Solo lee datos; no modifica nada en data/.

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
CODE_DIR="${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code}"
OUT="$PROJECT_DIR/runs/${SLURM_JOB_ID:?}/exploracion"
mkdir -p "$OUT"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026

export GDAL_CACHEMAX=4096
export OMP_NUM_THREADS=1

echo "job=$SLURM_JOB_ID nodo=$(hostname) inicio=$(date -Is) commit=$(git -C "$CODE_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"

# MODIS viene en HDF4: si GDAL no lo soporta, el script usa pyhdf.
python -c "import pyhdf" 2>/dev/null || pip install --quiet pyhdf || echo "[WARN] no se pudo instalar pyhdf; MODIS puede quedar sin leer"

python "$CODE_DIR/tools/explore_datasets.py" \
  --data-root "$PROJECT_DIR/data/raw" \
  --out-dir "$OUT" \
  --workers "$SLURM_CPUS_PER_TASK" "$@"

echo "fin=$(date -Is)"
echo "Reporte: $OUT/index.html"

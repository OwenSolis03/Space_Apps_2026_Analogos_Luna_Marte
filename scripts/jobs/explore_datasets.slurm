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

# Exploration report for all downloaded datasets.
# Submit from /lustre/proyectos/p089/code:   sbatch scripts/jobs/explore_datasets.slurm
# To explore only a subset:                  sbatch scripts/jobs/explore_datasets.slurm --only planets
# Output: /lustre/proyectos/p089/runs/<JOBID>/exploration/{index.html,summary.md,summary.json}
# Read-only; does not modify data/.

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
CODE_DIR="${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code}"
OUT="$PROJECT_DIR/runs/${SLURM_JOB_ID:?}/exploracion"
mkdir -p "$OUT"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026

export GDAL_CACHEMAX=4096
export OMP_NUM_THREADS=1

echo "job=$SLURM_JOB_ID node=$(hostname) start=$(date -Is) commit=$(git -C "$CODE_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"

# MODIS comes in HDF4: if GDAL lacks the driver, the script uses pyhdf.
python -c "import pyhdf" 2>/dev/null || pip install --quiet pyhdf || echo "[WARN] could not install pyhdf; MODIS may remain unread"

python "$CODE_DIR/scripts/tools/explore_datasets.py" \
  --data-root "$PROJECT_DIR/data/raw" \
  --out-dir "$OUT" \
  --workers "$SLURM_CPUS_PER_TASK" "$@"

echo "end=$(date -Is)"
echo "Report: $OUT/index.html"

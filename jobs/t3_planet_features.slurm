#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-t3-planets
#SBATCH -p cpu
#SBATCH --array=0-15
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH -o /lustre/proyectos/p089/output/t3_planet_features_%A_%a.log
#SBATCH -e /lustre/proyectos/p089/output/t3_planet_features_%A_%a.log

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
CODE_DIR="${CODE_DIR:-${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code}}"
RUN_ID="${SLURM_ARRAY_JOB_ID:-${SLURM_JOB_ID:-manual}}"
OUT_DIR="${OUT_DIR:-$PROJECT_DIR/runs/$RUN_ID}"

mkdir -p "$OUT_DIR" "$PROJECT_DIR/output"

export GDAL_CACHEMAX="${GDAL_CACHEMAX:-256}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026

cd "$CODE_DIR"
echo "job=${SLURM_JOB_ID:-local} array_job=${SLURM_ARRAY_JOB_ID:-none} task=${SLURM_ARRAY_TASK_ID:-0} out_dir=$OUT_DIR nodo=$(hostname) inicio=$(date -Is) commit=$(git -C "$CODE_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"

python -c "import pandas, pyarrow, scipy, matplotlib" 2>/dev/null || pip install --quiet -r "$CODE_DIR/pipeline/requirements.txt"

python -m pipeline.planet_features \
  --project-dir "$PROJECT_DIR" \
  --out-dir "$OUT_DIR" \
  --body all \
  --stripe-idx "${SLURM_ARRAY_TASK_ID:-0}" \
  --num-stripes "${SLURM_ARRAY_TASK_COUNT:-16}" \
  --workers "${SLURM_CPUS_PER_TASK:-8}" \
  "$@"

echo "fin=$(date -Is)"

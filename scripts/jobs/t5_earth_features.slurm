#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-t5-earth
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --array=0-31%30
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH -o /lustre/proyectos/p089/output/t5_earth_%A_%a.log
#SBATCH -e /lustre/proyectos/p089/output/t5_earth_%A_%a.log

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
CODE_DIR="${CODE_DIR:-${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code}}"
if [[ ! -d "$CODE_DIR/pipeline" ]]; then
  CODE_DIR="$PROJECT_DIR/code"
fi
: "${RUN_DIR:?RUN_DIR es requerido}"
mkdir -p "$RUN_DIR" "$PROJECT_DIR/output"

export GDAL_CACHEMAX="${GDAL_CACHEMAX:-256}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026
cd "$CODE_DIR"
export PYTHONPATH="$CODE_DIR/scripts${PYTHONPATH:+:$PYTHONPATH}"

echo "job=${SLURM_JOB_ID:-local} array=${SLURM_ARRAY_JOB_ID:-none}_${SLURM_ARRAY_TASK_ID:-0} cpus=${SLURM_CPUS_PER_TASK:-1} nodo=$(hostname) inicio=$(date -Is) commit=$(git -C "$CODE_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"

python -m pipeline.earth_features extract \
  --project-dir "$PROJECT_DIR" \
  --run-dir "$RUN_DIR" \
  --stripe-idx "${SLURM_ARRAY_TASK_ID:-0}" \
  --num-stripes "${NUM_STRIPES:-32}" \
  --workers "${SLURM_CPUS_PER_TASK:-16}"

echo "fin=$(date -Is) run_dir=$RUN_DIR"

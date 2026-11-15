#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-t5-prepare
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=01:30:00
#SBATCH -o /lustre/proyectos/p089/output/t5_prepare_%j.log
#SBATCH -e /lustre/proyectos/p089/output/t5_prepare_%j.log

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
CODE_DIR="${CODE_DIR:-${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code}}"
if [[ ! -d "$CODE_DIR/pipeline" ]]; then
  CODE_DIR="$PROJECT_DIR/code"
fi
RUN_DIR="${RUN_DIR:-$PROJECT_DIR/runs/${SLURM_JOB_ID:-manual}}"
mkdir -p "$RUN_DIR" "$PROJECT_DIR/output"

export GDAL_CACHEMAX="${GDAL_CACHEMAX:-256}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026
cd "$CODE_DIR"
export PYTHONPATH="$CODE_DIR/scripts${PYTHONPATH:+:$PYTHONPATH}"

echo "job=${SLURM_JOB_ID:-local} nodos=${SLURM_JOB_NUM_NODES:-1} cpus=${SLURM_CPUS_PER_TASK:-1} nodo=$(hostname) inicio=$(date -Is) commit=$(git -C "$CODE_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"

python -m pipeline.earth_features prepare --project-dir "$PROJECT_DIR" --run-dir "$RUN_DIR" "$@"

echo "fin=$(date -Is) run_dir=$RUN_DIR"

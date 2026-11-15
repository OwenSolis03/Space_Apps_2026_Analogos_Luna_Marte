#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-t6-earth-layers
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH -o /lustre/proyectos/p089/output/t6_earth_layers_%j.log
#SBATCH -e /lustre/proyectos/p089/output/t6_earth_layers_%j.log

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
CODE_DIR="${CODE_DIR:-${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code}}"
if [[ ! -d "$CODE_DIR/pipeline" ]]; then
  CODE_DIR="$PROJECT_DIR/code"
fi
OUT_DIR="${OUT_DIR:-$PROJECT_DIR/runs/${SLURM_JOB_ID:-manual}}"
mkdir -p "$OUT_DIR" "$PROJECT_DIR/output"

export GDAL_CACHEMAX="${GDAL_CACHEMAX:-256}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026
cd "$CODE_DIR"
export PYTHONPATH="$CODE_DIR/scripts${PYTHONPATH:+:$PYTHONPATH}"

echo "job=${SLURM_JOB_ID:-local} nodes=${SLURM_JOB_NUM_NODES:-1} cpus=${SLURM_CPUS_PER_TASK:-1} node=$(hostname) start=$(date -Is) commit=$(git -C "$CODE_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"

python -c "import pyhdf" || { echo "Missing pyhdf in spaceapps_2026"; exit 2; }
python -m pipeline.earth_layers --project-dir "$PROJECT_DIR" --out-dir "$OUT_DIR" --build --check "$@"

echo "end=$(date -Is) out_dir=$OUT_DIR"

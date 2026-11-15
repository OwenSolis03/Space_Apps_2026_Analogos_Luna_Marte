#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-t4-targets
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:45:00
#SBATCH -o /lustre/proyectos/p089/output/t4_targets_%j.log
#SBATCH -e /lustre/proyectos/p089/output/t4_targets_%j.log

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
CODE_DIR="${CODE_DIR:-${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code}}"
T3_DIR="${T3_DIR:-$PROJECT_DIR/runs/2242278}"
OUT_DIR="${OUT_DIR:-$PROJECT_DIR/runs/${SLURM_JOB_ID:-manual}}"

mkdir -p "$OUT_DIR" "$PROJECT_DIR/output"

export GDAL_CACHEMAX="${GDAL_CACHEMAX:-256}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026

cd "$CODE_DIR"
export PYTHONPATH="$CODE_DIR/scripts${PYTHONPATH:+:$PYTHONPATH}"
echo "job=${SLURM_JOB_ID:-local} t3_dir=$T3_DIR out_dir=$OUT_DIR nodo=$(hostname) inicio=$(date -Is) commit=$(git -C "$CODE_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"

python -c "import pandas, pyarrow, scipy, sklearn, geopandas, matplotlib" 2>/dev/null || pip install --quiet -r "$CODE_DIR/scripts/pipeline/requirements.txt"

python -m pipeline.targets \
  --project-dir "$PROJECT_DIR" \
  --t3-dir "$T3_DIR" \
  --out-dir "$OUT_DIR" \
  --body all \
  "$@"

echo "fin=$(date -Is)"

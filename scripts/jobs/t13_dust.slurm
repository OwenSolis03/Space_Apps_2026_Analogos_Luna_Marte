#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-t13-dust
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:45:00
#SBATCH -o /lustre/proyectos/p089/output/t13_dust_%j.log
#SBATCH -e /lustre/proyectos/p089/output/t13_dust_%j.log

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
CODE_DIR="${CODE_DIR:-${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code}}"
if [[ ! -d "$CODE_DIR/pipeline" ]]; then
  CODE_DIR="$PROJECT_DIR/code"
fi
T3_DIR="${T3_DIR:-$PROJECT_DIR/runs/2242278}"
T4_DIR="${T4_DIR:-$PROJECT_DIR/runs/2242423}"
T5_DIR="${T5_DIR:-$PROJECT_DIR/runs/2242438}"
OUT_DIR="${OUT_DIR:-$PROJECT_DIR/runs/${SLURM_JOB_ID:-manual}}"

mkdir -p "$OUT_DIR" "$PROJECT_DIR/output"

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026
cd "$CODE_DIR"
export PYTHONPATH="$CODE_DIR/scripts${PYTHONPATH:+:$PYTHONPATH}"

echo "job=${SLURM_JOB_ID:-local} t3_dir=$T3_DIR t4_dir=$T4_DIR t5_dir=$T5_DIR out_dir=$OUT_DIR node=$(hostname) start=$(date -Is) commit=$(git -C "$CODE_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"

python -m pipeline.dust \
  --project-dir "$PROJECT_DIR" \
  --t3-dir "$T3_DIR" \
  --t4-dir "$T4_DIR" \
  --t5-dir "$T5_DIR" \
  --out-dir "$OUT_DIR" \
  "$@"

echo "end=$(date -Is)"

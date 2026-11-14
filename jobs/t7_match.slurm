#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-t7-match
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH -o /lustre/proyectos/p089/output/t7_match_%j.log
#SBATCH -e /lustre/proyectos/p089/output/t7_match_%j.log

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
CODE_DIR="${CODE_DIR:-${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code}}"
T3_DIR="${T3_DIR:-$PROJECT_DIR/runs/2242278}"
T4_DIR="${T4_DIR:-$PROJECT_DIR/runs/2242423}"
T5_DIR="${T5_DIR:?set T5_DIR to the T5 run directory}"
T12_DIR="${T12_DIR:?set T12_DIR to the T12 ice run directory}"
T13_DIR="${T13_DIR:?set T13_DIR to the T13 dust run directory}"
T14_DIR="${T14_DIR:?set T14_DIR to the T14 geology run directory}"
OUT_DIR="${OUT_DIR:-$PROJECT_DIR/runs/${SLURM_JOB_ID:-manual}}"

mkdir -p "$OUT_DIR" "$PROJECT_DIR/output"

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026

cd "$CODE_DIR"
echo "job=${SLURM_JOB_ID:-local} t3_dir=$T3_DIR t4_dir=$T4_DIR t5_dir=$T5_DIR t12_dir=$T12_DIR t13_dir=$T13_DIR t14_dir=$T14_DIR out_dir=$OUT_DIR node=$(hostname) start=$(date -Is) commit=$(git -C "$CODE_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"

python -m pipeline.match \
  --t3-dir "$T3_DIR" \
  --t4-dir "$T4_DIR" \
  --t5-dir "$T5_DIR" \
  --t12-dir "$T12_DIR" \
  --t13-dir "$T13_DIR" \
  --t14-dir "$T14_DIR" \
  --out-dir "$OUT_DIR" \
  "$@"

python -m pipeline.export \
  --t3-dir "$T3_DIR" \
  --t4-dir "$T4_DIR" \
  --t5-dir "$T5_DIR" \
  --t12-dir "$T12_DIR" \
  --t13-dir "$T13_DIR" \
  --t14-dir "$T14_DIR" \
  --out-dir "$OUT_DIR"

echo "end=$(date -Is)"

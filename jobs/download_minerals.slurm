#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-download-minerals
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH -o /lustre/proyectos/p089/output/download_minerals_%j.log
#SBATCH -e /lustre/proyectos/p089/output/download_minerals_%j.log

set -euo pipefail

PROJECT_DIR="/lustre/proyectos/p089"
CODE_DIR="${CODE_DIR:-${SLURM_SUBMIT_DIR:-$PROJECT_DIR/code_exp_mineral}}"
if [[ ! -d "$CODE_DIR/pipeline" ]]; then
  CODE_DIR="$PROJECT_DIR/code"
fi

mkdir -p "$PROJECT_DIR/output"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026
cd "$CODE_DIR"

echo "job=${SLURM_JOB_ID:-local} node=$(hostname) start=$(date -Is) commit=$(git -C "$CODE_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"

python -m pipeline.minerals_download \
  --project-dir "$PROJECT_DIR" \
  --probe-out "$PROJECT_DIR/output/mineral_probe.json"

echo "end=$(date -Is)"

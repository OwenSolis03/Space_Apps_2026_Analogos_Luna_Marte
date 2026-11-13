#!/usr/bin/env bash
#SBATCH --job-name=spaceapps_analogs
#SBATCH --partition=cpu
#SBATCH --account=p089
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G
#SBATCH --time=04:00:00
#SBATCH --output=/lustre/proyectos/p089/output/spaceapps_%j.log

PROJECT_DIR="${1:-/lustre/proyectos/p089}"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK

echo "[*] Ejecutando pipeline en $(hostname) | Proyecto: $PROJECT_DIR"
python3 "$PROJECT_DIR/process_analogs.py" --project-dir "$PROJECT_DIR" --n-clusters 40

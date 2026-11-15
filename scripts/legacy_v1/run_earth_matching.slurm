#!/usr/bin/env bash
#SBATCH --job-name=earth_analogs
#SBATCH --account=p089
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/lustre/proyectos/p089/output/earth_match_%j.log

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

python /lustre/proyectos/p089/match_earth_analogs.py \
  --project-dir /lustre/proyectos/p089 \
  --workers 32 \
  --top-k 5

#!/usr/bin/env bash
# Uso: bash jobs/t5_submit.sh            (corrida completa, 32 franjas)
#      bash jobs/t5_submit.sh --limit 500 (prueba: 1 franja)
set -euo pipefail
cd "$(dirname "$0")/.."
LIMIT_ARGS=(); NUM_STRIPES=32; ARRAY="0-31%30"
if [[ "${1:-}" == "--limit" ]]; then LIMIT_ARGS=(--limit "$2"); NUM_STRIPES=1; ARRAY="0-0"; fi
PREP=$(sbatch --parsable jobs/t5_prepare.slurm "${LIMIT_ARGS[@]}")
RUN_DIR=/lustre/proyectos/p089/runs/$PREP
ARR=$(sbatch --parsable --dependency=afterok:$PREP --array="$ARRAY" \
      --export=ALL,RUN_DIR=$RUN_DIR,NUM_STRIPES=$NUM_STRIPES jobs/t5_earth_features.slurm)
MRG=$(sbatch --parsable --dependency=afterok:$ARR \
      --export=ALL,RUN_DIR=$RUN_DIR,NUM_STRIPES=$NUM_STRIPES jobs/t5_merge.slurm)
echo "prepare=$PREP array=$ARR merge=$MRG run_dir=$RUN_DIR"

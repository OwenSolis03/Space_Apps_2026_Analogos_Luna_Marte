#!/usr/bin/env bash
#SBATCH -A p089
#SBATCH -J p089-diviner
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=01:00:00
#SBATCH -o /lustre/proyectos/p089/output/diviner_%j.log
#SBATCH -e /lustre/proyectos/p089/output/diviner_%j.log

# LRO Diviner Polar Resource Product (PDS3 LRO-L-DLRE-5-PRP-V2.0, PDS4 urn:nasa:pds:lro_diviner_derived1:data_derived_prp).
# ASCII table: one triangle of polar mesh (80-90°) per row, with annual mean and maximum temperatures
# and ice stability depth. South pole only (used by Artemis targets).
# Submit from /lustre/proyectos/p089/code:   sbatch jobs/download_diviner.slurm

set -euo pipefail

OUT="/lustre/proyectos/p089/data/raw/moon/diviner"
BASE="https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp"
mkdir -p "$OUT"

source /apps/miniconda3/etc/profile.d/conda.sh
conda activate spaceapps_2026

echo "job=${SLURM_JOB_ID:-local} node=$(hostname) start=$(date -Is)"

for f in dlre_prp_south.lbl dlre_prp_south.xml dlre_prp_south.tab; do
  aria2c -c --auto-file-renaming=false --allow-overwrite=false --max-tries=5 --retry-wait=15 \
    --console-log-level=warn --summary-interval=60 -x 4 -s 4 -d "$OUT" "$BASE/$f" || echo "[WARN] $f failed"
done

echo "=== Verification (expected size of .tab: 604800210 bytes)"
ls -l "$OUT"
head -n 5 "$OUT/dlre_prp_south.tab" || true
echo "end=$(date -Is)"

"""Before/after comparison tool for experimental Mars mineral dimension (Option B).

Evaluates matches.parquet between geology_and_materials and geology_and_materials_mineral_exp.
Generates mineral_comparison.md and mineral_comparison.csv in the run directory.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

logger = logging.getLogger(__name__)

BASE_PRESET = "geology_and_materials"
EXP_PRESET = "geology_and_materials_mineral_exp"


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard index between two sets."""
    union = set_a.union(set_b)
    if not union:
        return 1.0
    return float(len(set_a.intersection(set_b))) / float(len(union))


def run_comparison(run_dir: Path) -> None:
    matches_file = run_dir / "matches.parquet"
    if not matches_file.exists():
        sys.exit(f"matches.parquet not found in {run_dir}")

    meta_file = run_dir / "matches_meta.json"
    logger.info("Loading matches from %s", matches_file)
    df = pd.read_parquet(matches_file)

    rank_base_col = f"rank_{BASE_PRESET}"
    rank_exp_col = f"rank_{EXP_PRESET}"
    msi_base_col = f"msi_{BASE_PRESET}"
    msi_exp_col = f"msi_{EXP_PRESET}"

    for col in (rank_base_col, rank_exp_col, msi_base_col, msi_exp_col):
        if col not in df.columns:
            sys.exit(f"Required preset column {col!r} not found in matches.parquet")

    # Safety check: refuse to run if S_mineral is completely absent or all NaN for Mars
    if "S_mineral" not in df.columns:
        sys.exit("Refusing to run: S_mineral column is missing from matches.parquet.")

    target_ids = df["target_id"].unique()
    results: list[dict[str, object]] = []

    for tid in target_ids:
        sub = df[df["target_id"] == tid].copy()
        # Filter for top 30 under each preset
        top30_base = sub[sub[rank_base_col].notna() & (sub[rank_base_col] <= 30)]
        top30_exp = sub[sub[rank_exp_col].notna() & (sub[rank_exp_col] <= 30)]

        if top30_exp.empty:
            continue

        base_ids = set(top30_base["earth_id"])
        exp_ids = set(top30_exp["earth_id"])
        jaccard = jaccard_similarity(base_ids, exp_ids)

        # Top 10 turnover
        top10_base = set(sub[sub[rank_base_col].notna() & (sub[rank_base_col] <= 10)]["earth_id"])
        top10_exp = set(sub[sub[rank_exp_col].notna() & (sub[rank_exp_col] <= 10)]["earth_id"])
        turnover_in = len(top10_exp - top10_base)
        turnover_out = len(top10_base - top10_exp)

        # Union for Spearman rho
        union_ids = base_ids.union(exp_ids)
        union_sub = sub[sub["earth_id"].isin(union_ids)]
        if len(union_sub) >= 3:
            rho, _ = spearmanr(union_sub[msi_base_col], union_sub[msi_exp_col])
        else:
            rho = np.nan

        # Mean S_mineral of top 10 under each preset
        s_min_base = float(sub[sub["earth_id"].isin(top10_base)]["S_mineral"].mean())
        s_min_exp = float(sub[sub["earth_id"].isin(top10_exp)]["S_mineral"].mean())

        # Share of top-30 analogs with missing Earth mineral data (case C)
        missing_c_share = (
            float(top30_exp["earth_missing_dims"].str.contains("mineral", na=False).sum())
            / max(1, len(top30_exp))
        )

        results.append(
            {
                "target_id": tid,
                "jaccard_top30": round(jaccard, 3),
                "spearman_rho": round(float(rho), 3) if np.isfinite(rho) else np.nan,
                "top10_turnover_in": turnover_in,
                "top10_turnover_out": turnover_out,
                "mean_s_mineral_top10_base": round(s_min_base, 3) if np.isfinite(s_min_base) else np.nan,
                "mean_s_mineral_top10_exp": round(s_min_exp, 3) if np.isfinite(s_min_exp) else np.nan,
                "missing_mineral_top30_share": round(missing_c_share, 3),
            }
        )

    res_df = pd.DataFrame(results)
    csv_out = run_dir / "mineral_comparison.csv"
    res_df.to_csv(csv_out, index=False)
    logger.info("Wrote %s (%d rows)", csv_out, len(res_df))

    # Generate Markdown summary report
    md_lines = [
        "# Mars Mineral Dimension Comparison Report (Option B)",
        "",
        f"Run directory: `{run_dir}`",
        f"Presets compared: `{BASE_PRESET}` vs `{EXP_PRESET}`",
        "",
        "## Overall Summary",
        "",
        f"- **Median Top-30 Jaccard Overlap:** {res_df['jaccard_top30'].median():.3f}",
        f"- **Median Spearman rho (MSI):** {res_df['spearman_rho'].median():.3f}",
        f"- **Mean Top-10 Turnover:** {res_df['top10_turnover_in'].mean():.1f} analogs",
        f"- **Mean Case C (Missing EMIT) Share in Top-30:** {res_df['missing_mineral_top30_share'].mean() * 100.0:.1f}%",
        "",
        "## Top 5 Targets with Largest Divergence (Lowest Jaccard)",
        "",
        "| Target ID | Jaccard Top-30 | Spearman rho | Top-10 In | Case-C Share |",
        "| --- | --- | --- | --- | --- |",
    ]
    sorted_diff = res_df.sort_values("jaccard_top30", ascending=True).head(5)
    for _, row in sorted_diff.iterrows():
        md_lines.append(
            f"| {row['target_id']} | {row['jaccard_top30']} | {row['spearman_rho']} | {row['top10_turnover_in']} | {row['missing_mineral_top30_share']*100:.1f}% |"
        )

    md_out = run_dir / "mineral_comparison.md"
    md_out.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    logger.info("Wrote %s", md_out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="T7 run directory containing matches.parquet")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_comparison(args.run_dir)


if __name__ == "__main__":
    main()

# Detailed plan T7 + T8: matching, scoring and export

Full specification of T7 (`pipeline/match.py`) and T8 (`pipeline/export.py`). It expands sections T7 and T8 of [implementation_plan.md](implementation_plan.md). Where they disagree, **this document wins**. Written by Claude on 2026-11-13 on `main` at `a2b2073`, using the real outputs of T3 (`runs/2242278`), T4 (`runs/2242423`) and the T5 smoke test (`runs/2242432`).

This is the first plan written in English. Code comments, docstrings, log messages and commit messages for T7/T8 are in **English**, and so is the bitácora entry.

**Inputs:**

| Run | File | Rows |
| --- | --- | --- |
| T3 | `runs/2242278/features_{mars,moon}.parquet` | 140,916 Mars, 36,741 Moon |
| T4 | `runs/2242423/targets.parquet` | 76 targets: 16 curated, 60 clusters |
| T5 | `runs/2242438/features_earth.parquet` | 40,244 (12,125 in Antarctica, 1,843 in Greenland) |

T5 full run: `runs/2242438` (jobs 2242438–2242440). The smoke-test output `runs/2242432` (445 rows) is still handy for quick tests.

**Outputs:**

- `runs/<JOBID>/matches.parquet`
- `runs/<JOBID>/analogs_universe.json`
- `runs/<JOBID>/t7_checks.json` and `t7_report.md`

---

## 0. Summary

| What | Where |
| --- | --- |
| Normalisation, RBF scores, MSI, candidate search, diversity, mismatches | `pipeline/match.py` |
| JSON for the app | `pipeline/export.py` |
| Physical limits per body (T11 content; this plan only defines the format and a fallback) | `pipeline/data/limits.json` |
| One job running match and export | `jobs/t7_match.slurm` |
| Tests | `tests/test_match.py`, `tests/test_export.py` |

Commit: `T7/T8: RBF matching, MSI presets and app export`. Commit and push **before** submitting the job, so the log records the right commit.

---

## 1. Facts measured on the real data (2026-11-13)

**Earth vs. the targets at the 32 km / 500 m scale.** These are medians of `mean_slope_deg`:

| Set | Median slope | Source |
| --- | --- | --- |
| Earth candidates | 0.50° | T5 smoke test |
| Earth outside Antarctica | 0.69° | T5 smoke test |
| Mars | 1.16° | T3 |
| Moon | 6.8° | T3 |
| Lunar curated targets | 8.1–14.3° | T4 |
| Mars landing plains | 0.25–0.54° | T4 |
| Jezero | 2.55° | T4 |
| Gale | 5.85° | T4 |

Arid Earth is smooth at this scale. Earth's p95 slope is 6.9° and its maximum 23°, so lunar south-pole terrain sits in the far tail of Earth's distribution. Expect low absolute similarity for lunar targets (see §2.3).

**Ice sheets.**

- 139 of the 445 smoke-test patches (31 %) are in Antarctica. They pass the T5 prefilter because MOD13C2 has no NDVI there.
- Their median slope is 0.30°, their relief 90 m and their daytime LST −39.6 °C. They are very flat, and they would flood the rankings of flat Mars targets (InSight, Arcadia, Zhurong).
- Our data cannot tell bare ground from ice. The McMurdo Dry Valleys are ice-free and also very cold.
- Greenland's ice sheet has NDVI ≈ 0, so it also passes the prefilter.

**Earth columns available in T5:**

- the 7 terrain features and `valid_frac`;
- `ndvi_max`, `lst_day_c`, `lst_night_c`, `lst_amplitude_c`;
- `dist_road_km`, `dist_airport_km`, `nearest_airport_iata`, `nearest_airport_name`;
- `country`, `known_region`, `classification`, `ndvi_missing`.

**App contract:** `app/src/lib/types.ts`. It reads `metadata`, `mission_presets`, `limits` (keyed `Moon`/`Mars`), and `targets[]` with nested `analogs[]`. `app/public/data/sample.json` already contains provisional English limits for both bodies.

---

## 2. Design decisions (and why)

### 2.1 Features and dimensions

| Dimension `k` | Earth side | Target side | Why |
| --- | --- | --- | --- |
| `topography` | `mean_slope_deg`, `p90_slope_deg`, `relief_m`, `hypsometric_integral` | Same features | Landing-scale shape of the terrain |
| `roughness` | `detrended_std_m`, `tri_m` | Same features | Surface irregularity at 500 m |
| `environment` | `ndvi_max` (aridity) | None: the targets are airless or arid | Vegetation breaks a planetary analog |
| `thermal` (Mars only) | `lst_amplitude_c`, ranked within Earth | `themis_delta`, ranked within Mars | Relative thermal contrast. The units are not comparable, so it is compared by rank |

`mean_elev_m` is never compared, because datums differ between bodies. It is still exported for display.

### 2.2 Normalisation (robust z in "Earth units")

1. Apply `log1p` to `relief_m`, `detrended_std_m` and `tri_m` on every row (Earth patches and targets). **Why:** these features have long tails.
2. For each feature, `z = (x − median_E) / (1.4826 · MAD_E)`. The median and MAD are computed **on the Earth candidate patches only**. **Why:** one unit means one typical Earth deviation, so distances read as "how unusual this would be on Earth".
3. **Floor:** if `MAD_E == 0`, use `1e-6` and log a warning.
4. **Thermal:**
   - Earth: `zt_E = rank_pct(lst_amplitude_c)` over the Earth candidates.
   - Mars: `zt_M = rank_pct(themis_delta)` over the **T3 Mars** patches. Use `scipy.stats.rankdata(..., 'average') / n`.
   - The thermal distance is `|zt_E − zt_M| / 0.15`. **Why:** 0.15 percentile points then counts as one unit, the same scale as the other dimensions.

### 2.3 Similarity per dimension

- **Geomorphic dimensions:**
  - `d_k = ||z_E − z_T|| / sqrt(n_k)` over the dimension's features;
  - `S_k = exp(−d_k² / (2 σ_k²))`.
- **Environment:**
  - `S_env = exp(−max(0, ndvi_max − 0.10)² / (2 · 0.10²))`.
  - If `ndvi_max` is NaN (`ndvi_missing`, Antarctica), `S_env = 1.0`, because the surface is unvegetated. The flag goes into the JSON so the app can say "no NDVI data".
- **Thermal:**
  - `S_thermal = exp(−d_t² / 2)` with `d_t` from §2.2.
  - `S_thermal = null` for every Moon target, for any Mars target whose `themis_delta` is NaN, and for any Earth patch whose `lst_amplitude_c` is NaN.
- **σ:** default `σ_topography = σ_roughness = 1.0` in Earth units. The CLI option `--sigma-scale s` multiplies both.
  - **Why keep 1.0:** a low score for lunar targets is a real finding. Earth has almost no arid terrain as rugged as the lunar south pole at 32 km scale, and the app should show that honestly rather than inflate it.
  - The report (§5) prints the score distribution so the team can decide after the first run whether to use `--sigma-scale`. Changing σ is a one-flag re-run, not a code change.

### 2.4 MSI and presets

`MSI = Σ w_k · S_k / Σ w_k` over the dimensions where `S_k` is not null. Moon targets therefore drop `thermal` automatically.

| Preset key | English label | topography | roughness | environment | thermal |
| --- | --- | --- | --- | --- | --- |
| `mobility_and_traction` | Rover mobility and traction | 0.45 | 0.40 | 0.15 | 0.00 |
| `construction_and_base` | Base construction and landing | 0.55 | 0.25 | 0.10 | 0.10 |
| `dust_and_thermal` | Dust and thermal environment | 0.15 | 0.15 | 0.40 | 0.30 |

These are the same weights as `implementation_plan.md` and the app sample. The logistics adjustment `MSI_log = MSI · (1 − λ + λ · exp(−dist_road_km / 100))` happens **in the app**; T7 only exports `dist_road_km`.

### 2.5 Candidate search, diversity and the ice cap

For each target:

1. **Candidate pool.** Build `sklearn.neighbors.NearestNeighbors` once on the Earth matrix `[z_topo / sqrt(4), z_rough / sqrt(2)]` (6 columns) and query `k = min(2000, n_earth)` neighbours.
   - **Why:** Euclidean distance in this space equals `sqrt(d_topo² + d_rough²)`, the part of the score that varies most. Computing everything only on the pool keeps the run fast.
2. **Scoring.** Compute every `S_k` and the 3 preset MSIs on the pool.
3. **Selection per preset.** Sort the pool by that preset's MSI (descending). Walk the list and accept a patch only if:
   - it is **≥ 150 km** (haversine, Earth radius 6371 km) from every patch already accepted **for that preset**;
   - accepting it keeps **≤ 3 "polar cold" patches** (`lst_day_c < −10 °C`) among the accepted ones.

   Stop at **30**.
   - **Why 150 km:** the results should not be 30 neighbouring patches of the same plateau.
   - **Why the polar cap:** our data cannot tell an ice sheet from bare ground, and flat ice would otherwise fill the flat Mars rankings. Three slots keep places like the Dry Valleys visible.
   - If fewer than 30 are accepted, re-query once with `k = 8000` and log it.
4. **Union.** The union of the three presets' selections, at most 90 per target, goes to the JSON with all sub-scores. Each analog records which presets selected it (`selected_by`), so the app can re-rank them with any weights.
5. **Earth patch id:** `earth-{lat:+08.4f}{lon:+09.4f}`, for example `earth+31.8480-113.3900`. It is stable across runs.

### 2.6 Where the analogy breaks (mismatches)

For every exported (target, analog) pair, and for every feature in topography and roughness:

- if `|z_E − z_T| > 1.5`, append `{feature, earth, target, z_diff}`;
- `earth` and `target` are in **physical units** (degrees, metres, unitless HI), rounded to 2 decimals;
- `z_diff = z_E − z_T`, rounded to 2.

Add a thermal mismatch for Mars when `|zt_E − zt_M| > 0.30` (two thermal units), with `feature = "thermal_rank"`. **Why:** the challenge explicitly asks where the analogy fails, per site, with data.

Fixed body limits (gravity, atmosphere, radiation, …) come from `limits.json` (§4.2), not from T7.

---

## 3. `pipeline/match.py`

```python
TOPO = ["mean_slope_deg", "p90_slope_deg", "relief_m", "hypsometric_integral"]
ROUGH = ["detrended_std_m", "tri_m"]
LOG_FEATURES = ["relief_m", "detrended_std_m", "tri_m"]
MATCH_FEATURES = TOPO + ROUGH
PRESETS = {...}                       # §2.4, with English labels
NDVI_FREE, NDVI_SCALE = 0.10, 0.10
THERMAL_UNIT = 0.15
POLAR_COLD_LST_C = -10.0
MAX_POLAR_PER_PRESET = 3
TOP_N, MIN_SEP_KM = 30, 150.0
POOL_K, POOL_K_RETRY = 2000, 8000
MISMATCH_Z = 1.5
MISMATCH_THERMAL = 0.30

@dataclass
class Normalizer:
    median: dict[str, float]; scale: dict[str, float]          # scale = 1.4826 * MAD (floored)
    @classmethod
    def fit_earth(cls, earth: pd.DataFrame) -> "Normalizer": ...
    def transform(self, df: pd.DataFrame) -> np.ndarray: ...     # (n, 6) z matrix, log1p applied first
    def to_dict(self) -> dict: ...                               # exported to JSON metadata

def thermal_ranks(earth: pd.DataFrame, mars_t3: pd.DataFrame, targets: pd.DataFrame
                  ) -> tuple[np.ndarray, np.ndarray]: ...        # zt_E per Earth row, zt_T per target (NaN for Moon)

def dimension_scores(z_e: np.ndarray, z_t: np.ndarray, ndvi: np.ndarray, zt_e: np.ndarray,
                     zt_t: float, sigma_scale: float = 1.0) -> dict[str, np.ndarray]:
    """Vectorised over Earth rows for ONE target -> {'topography','roughness','environment','thermal'}.
    Thermal is all-NaN when zt_t is NaN. NaN means null downstream."""

def msi(scores: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    """Σ w·S / Σ w over non-NaN dimensions, row by row; NaN if every weighted dimension is NaN."""

def haversine_km(lat1, lon1, lat2, lon2) -> np.ndarray: ...

def select_diverse(order: np.ndarray, lat: np.ndarray, lon: np.ndarray, polar: np.ndarray,
                   n: int = TOP_N, min_sep_km: float = MIN_SEP_KM,
                   max_polar: int = MAX_POLAR_PER_PRESET) -> list[int]:
    """Greedy walk over `order` applying the 150 km rule and the polar cap."""

def mismatches(e_row: pd.Series, t_row: pd.Series, z_e: np.ndarray, z_t: np.ndarray,
               zt_e: float, zt_t: float) -> list[dict]: ...

def match_all(earth: pd.DataFrame, targets: pd.DataFrame, mars_t3: pd.DataFrame,
              sigma_scale: float = 1.0) -> pd.DataFrame:
    """Returns matches.parquet rows: target_id, earth_id, lat, lon, rank_<preset> (1..30 or NA),
    selected_by (comma-separated preset keys), S_topography, S_roughness, S_environment,
    S_thermal, msi_<preset> for all 3 presets, polar_cold, mismatches_json (JSON string)."""

def main(argv=None): ...   # --t3-dir, --t4-dir, --t5-dir, --out-dir, --sigma-scale (1.0),
                           # --targets (optional comma list of target ids, for quick tests)
```

**Status filter:** targets with `status != "ok"` are skipped and logged. Today all 76 are ok.

---

## 4. `pipeline/export.py` and limits

### 4.1 `analogs_universe.json`

It follows `app/src/lib/types.ts`. Fields marked *new* are additions that the app may ignore at first.

```json
{
  "metadata": {
    "version": "2.0.0",
    "generated_at": "ISO-8601 UTC",
    "source": "pipeline v2 (T3 2242278, T4 2242423, T5 <run>, T7 <jobid>)",
    "slurm_job_id": "<T7 jobid>",
    "commit": "<short sha>",
    "patch": { "size_km": 32, "res_m": 500, "projection": "local azimuthal equidistant" },
    "earth_patches_evaluated": 0,
    "sigma": { "topography": 1.0, "roughness": 1.0 },
    "normalization": { "median": {...}, "scale": {...}, "log1p": ["relief_m", "detrended_std_m", "tri_m"] },
    "selection": { "top_n": 30, "min_sep_km": 150, "max_polar_cold_per_preset": 3 },
    "datasets": [ { "name": "...", "source": "...", "url": "..." } ]
  },
  "mission_presets": { "<key>": { "label": "...", "weights": { "topography": 0.45, "roughness": 0.4, "environment": 0.15, "thermal": 0 } } },
  "limits": { "Moon": [ ... ], "Mars": [ ... ] },
  "targets": [
    {
      "id": "...", "type": "CURATED|CLUSTER", "body": "Moon|Mars", "name": "...",
      "lat": 0, "lon": 0, "category": "...", "why": "...", "source_url": "...",
      "coord_source_url": "... (new)", "anchor_note": "... (new)", "iau_label": "...",
      "features": { "<6 match features>": 0, "mean_elev_m": 0 },
      "aux": { "themis_day": 0, "...": null },
      "analogs": [
        {
          "id": "earth+31.8480-113.3900", "lat": 0, "lon": 0, "country": "Mexico",
          "classification": "NEW_CANDIDATE", "known_region": null,
          "sub_scores": { "topography": 0, "roughness": 0, "environment": 0, "thermal": null },
          "msi_by_preset": { "mobility_and_traction": 0, "construction_and_base": 0, "dust_and_thermal": 0 },
          "selected_by": ["mobility_and_traction"],
          "features": { "<6 match features>": 0, "mean_elev_m": 0 },
          "earth_env": { "ndvi_max": 0, "lst_day_c": 0, "lst_night_c": 0, "lst_amplitude_c": 0, "ndvi_missing": false },
          "logistics": { "dist_road_km": 0, "dist_airport_km": 0, "nearest_airport_iata": "HMO", "nearest_airport_name": "..." },
          "polar_cold": false,
          "mismatches": [ { "feature": "relief_m", "earth": 0, "target": 0, "z_diff": 0 } ]
        }
      ]
    }
  ]
}
```

**Rules:**

- **Rounding:** 4 decimals for coordinates, 3 for scores and MSI, 2 for physical values.
- **Nulls:** NaN becomes `null`. Never write `NaN` or `Infinity` (`json.dump(..., allow_nan=False)` must pass).
- **Order:**
  - analogs sorted by `msi_by_preset.mobility_and_traction`, descending;
  - targets ordered curated first (Moon, then Mars, in the `targets.json` order), then clusters by body and rank.
- **Datasets list.** Each entry carries a name, source and URL; take the URLs from `docs/pipeline.md` and `implementation_plan.md` §2. Entries:
  - MGS MOLA DEM;
  - THEMIS IR Day/Night;
  - LRO LOLA LDEM;
  - LROC WAC;
  - LRO Diviner PRP;
  - USGS lunar ice favorability;
  - Copernicus GLO-90;
  - MODIS MOD13C2 and MOD11C3;
  - Natural Earth;
  - USGS Gazetteer of Planetary Nomenclature.

  Any URL not already in the docs is `null` with `TODO(verify)`.
- **Size:** if the file is > 20 MB, write `analogs_moon.json` and `analogs_mars.json` instead, plus a small `analogs_universe.json` without `targets` that lists them, and log it. The estimate is 76 × ≤ 90 analogs × ~1 KB ≈ 7 MB, so one file is expected.
- **Where it is written:** only to `runs/<JOBID>/`. Copying into `app/public/data/` is a separate, explicit step (§6), so a job never edits the git working tree.

### 4.2 `pipeline/data/limits.json` (T11)

```json
{ "version": "...", "Moon": [ { "factor": "gravity", "earth": "1 g", "target": "0.166 g", "consequence": "...", "source": "https://..." } ], "Mars": [ ... ] }
```

- **Who writes it:** T11 is content written by the team (P3), with a minimum of 6 factors per body (`implementation_plan.md` §T11).
- **Fallback:** if `limits.json` does not exist, `export.py` copies `limits` from `app/public/data/sample.json`, sets `metadata.limits_source = "provisional (sample.json)"` and logs a warning. If it exists, `export.py` validates that every entry has the 5 keys and a non-empty `source`.

---

## 5. Checks and report (`t7_checks.json`, `t7_report.md`)

**Hard checks** (the job exits with code 1 if one fails):

| # | Check | Criterion |
| --- | --- | --- |
| 1 | Coverage | Every `ok` target has ≥ 20 analogs for each preset. Fewer only if the 8000 retry was used, and that is logged |
| 2 | Diversity | No two analogs selected for the same (target, preset) are < 150 km apart |
| 3 | Polar cap | ≤ 3 `polar_cold` per (target, preset) |
| 4 | Scores | Every non-null `S_k` and MSI is in [0, 1]. `S_thermal` is null for all Moon targets |
| 5 | JSON | `json.load` round-trip works with `allow_nan=False`; size < 20 MB or split; every analog has the keys of `types.ts` |

**Report** (soft; printed and written to `t7_report.md` for review by Claude and Owen):

1. **Score distribution per body.** Median and p90 of the best and the 30th MSI (`mobility_and_traction`) over the curated targets. This is the input to the σ decision.
2. **Top 5 per curated target** for `mobility_and_traction`: `earth_id`, country, `known_region`, MSI, sub-scores and mismatch count.
3. **Olympus Mons sanity check** (from the general plan):
   - take the T3 Mars patch nearest to (18.65 N, −133.80 E) as a temporary check-only target (not exported);
   - print its top 10 with country and `known_region`;
   - a shield or large volcano among them (Hawaii, Galápagos, Iceland, Tibesti, Andean volcanoes) is expected, but coastal islands may be removed by the T5 sea mask;
   - this is a **review item, not a hard check**.
4. **Counts:**
   - `KNOWN_ANALOG` vs `NEW_CANDIDATE` among exported analogs;
   - top 15 countries;
   - number of `polar_cold` and `ndvi_missing` analogs.
5. **Runtime** of match and export.

---

## 6. Job and commands

`jobs/t7_match.slurm`, same shape as `jobs/t4_targets.slurm`, with:

```bash
#SBATCH -J p089-t7-match
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH -o /lustre/proyectos/p089/output/t7_match_%j.log
#SBATCH -e /lustre/proyectos/p089/output/t7_match_%j.log
T3_DIR=${T3_DIR:-$PROJECT_DIR/runs/2242278}
T4_DIR=${T4_DIR:-$PROJECT_DIR/runs/2242423}
T5_DIR=${T5_DIR:?set T5_DIR to the T5 run directory}
OUT_DIR=${OUT_DIR:-$PROJECT_DIR/runs/$SLURM_JOB_ID}
python -m pipeline.match  --t3-dir "$T3_DIR" --t4-dir "$T4_DIR" --t5-dir "$T5_DIR" --out-dir "$OUT_DIR" "$@"
python -m pipeline.export --t3-dir "$T3_DIR" --t4-dir "$T4_DIR" --t5-dir "$T5_DIR" --out-dir "$OUT_DIR"
```

There is no `pip install` in the job: everything needed is already in `spaceapps_2026`.

**Commands for Owen** (SSH or the Open OnDemand shell, from `/lustre/proyectos/p089/code`):

```bash
cd /lustre/proyectos/p089/code && git pull
```

```bash
sbatch -A p089 -p cpu --time=00:15:00 --mem=4G -o /lustre/proyectos/p089/output/tests_t7_%j.log --wrap 'bash -c "source /apps/miniconda3/etc/profile.d/conda.sh && conda activate spaceapps_2026 && cd /lustre/proyectos/p089/code && pytest -q tests"'
```

Smoke test against the T5 smoke run (445 Earth patches). Coverage check #1 may fail here because the pool is tiny. Everything else must pass.

```bash
sbatch --export=ALL,T5_DIR=/lustre/proyectos/p089/runs/2242432 jobs/t7_match.slurm
```

Real run, after the full T5 run:

```bash
sbatch --export=ALL,T5_DIR=/lustre/proyectos/p089/runs/2242438 jobs/t7_match.slurm
```

**Publishing to the app** is a separate step, after Claude or Owen review `t7_report.md`:

```bash
cp /lustre/proyectos/p089/runs/<T7_JOBID>/analogs_universe.json app/public/data/analogs_universe.json && git add app/public/data/analogs_universe.json && git commit -m "Data: analogs_universe.json from T7 run <T7_JOBID>" && git push
```

Then the app switches `DATA_URL` in `app/src/App.tsx` from `sample.json` to `analogs_universe.json`; that part is T10.

---

## 7. Tests (synthetic only)

**`tests/test_match.py`:**

1. **`test_identical_target_scores_one`:** an Earth row identical to the target gives `S_topography = S_roughness = 1`, and `S_env = 1` when NDVI ≤ 0.10.
2. **`test_normalizer_uses_earth_only`:** the median and MAD come from the Earth rows. Adding an extreme target does not change them.
3. **`test_log1p_applied`:** for `relief_m = e − 1`, the transformed value before z is 1.
4. **`test_env_score`:**
   - NDVI 0.10 gives 1;
   - NDVI 0.20 gives `exp(−0.5)`;
   - NaN gives 1.
5. **`test_thermal_null_for_moon`:** `S_thermal` is all NaN when `zt_t` is NaN.
6. **`test_msi_skips_null`:** `msi({'topography': 1, 'thermal': NaN}, {'topography': 0.5, 'thermal': 0.5})` gives 1.
7. **`test_select_diverse_150km`:** with points 100 km apart along a meridian, every other point is skipped; with points 200 km apart, all are kept.
8. **`test_select_diverse_polar_cap`:** with 10 high-ranked polar points and 10 others, at most 3 polar points are selected.
9. **`test_mismatches_threshold`:** a 1.4 z difference gives no mismatch; 1.6 gives one, with physical values.
10. **`test_earth_id_format`:** `(31.848, -113.39)` gives `"earth+31.8480-113.3900"`.

**`tests/test_export.py`:**

11. **`test_json_no_nan_and_schema`:** a tiny synthetic match set produces JSON that passes `allow_nan=False`, has the `types.ts` keys, and uses null for NaN.
12. **`test_limits_fallback`:** without `limits.json`, the limits come from a synthetic `sample.json` and `limits_source` says provisional.

---

## 8. Documentation (same commit, then update after the run)

- **`docs/logbook.md`:** new entry **in English** with what was done and why, the job ids, the hard check table, and the score distribution from the report.
- **`docs/HISTORY.md`:** add a "T7/T8" section with the decisions of §2 and their reasons.
- **`docs/pipeline.md`:** add the run.
- **`docs/handoff.md`:** mark T7/T8 as done, with the path of the JSON.

## 9. What NOT to do

- Do not compare `mean_elev_m` or absolute temperatures across bodies.
- Do not tune σ, thresholds or caps inside the code after looking at results. They are CLI flags or constants listed here; changing a value needs a note in the bitácora with the reason.
- Do not write into `app/` from the job.
- Do not drop the polar cap, and do not filter Antarctica out entirely. The Dry Valleys must stay possible.
- Do not invent dataset URLs.

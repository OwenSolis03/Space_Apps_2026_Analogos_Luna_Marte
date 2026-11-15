# Handoff: v2 progress

Continuity document for whoever picks up the work, human or agent. The code lives on Yuca at `/lustre/proyectos/p089/code` (branch `main`), cloned from GitHub.

| Need | Document |
| --- | --- |
| Source-of-truth specification | [implementation_plan.md](implementation_plan.md), plus the per-task plans `plan_t4.md`, `plan_t5.md`, `plan_t6.md`, `plan_t7_t8.md` |
| Data, scales and runs on Yuca | [pipeline.md](pipeline.md) and [logbook.md](logbook.md) |
| Why each decision was made | [HISTORY.md](HISTORY.md) |
| Working rules for the coding agent (MODE A with SSH, MODE B without) | [gemini_prompt.md](gemini_prompt.md) |
| Submission rules and timeline (NASA Space Apps Sonora, Tec de Monterrey) | [submission.md](submission.md) |
| Working without SSH at the venue | [working_without_ssh.md](working_without_ssh.md) |

At the venue, Yuca stays reachable through Open OnDemand (HTTPS): the agent works locally and pushes, and Owen runs `git pull` and `sbatch` in the OOD shell and passes the logs back.

---

## 1. Status per task

| Task | Main files | Status | Evidence |
| --- | --- | --- | --- |
| **T0** data | `jobs/download_missing.slurm`, `jobs/download_extra.slurm`, `jobs/download_diviner.slurm` | **Done** | See below |
| **T1** patch extraction | `pipeline/config.py`, `pipeline/geo.py`, `tests/test_geo.py` | **Done** (`ac743ce`, adjusted in `920f812`, `bcf10de`; polar branch in `115e0c3`) | Local AEQD 64 × 64 patch at 500 m/px; `scale`/`offset` applied after masking nodata |
| **T2** features | `pipeline/features.py`, `tests/test_features.py` | **Done** (`a661bb7`, `920f812`) | 7 float32 features |
| **T3** Mars and Moon sweep | `pipeline/planet_features.py`, `jobs/t3_planet_features.slurm` | **Done and run** (`19e3899`…`57f4f36`) | Jobs 2242278 (array 0–15) and 2242279 (merge): 140,916 Mars patches and 36,741 Moon patches. Visual check passed |
| **T4** targets | `pipeline/targets.py`, `pipeline/iau.py`, `pipeline/data/targets.json`, `jobs/t4_targets.slurm` | **Done and run** (`115e0c3`) | Job 2242423: 76 targets (16 curated, all ok; 60 clusters) |
| **T6** Earth layers | `pipeline/earth_layers.py`, `pipeline/data/known_analogs.json`, `jobs/t6_earth_layers.slurm` | **Done and run** (`29fbb88`, `84888cd`) | Jobs 2242426 (cache) and 2242430 (checks): 8/8 hard, 5/5 soft |
| **T5** Earth sweep | `pipeline/earth_features.py`, `jobs/t5_*.slurm`, `jobs/t5_submit.sh` | **Done and run** (`52bf3d7`) | Jobs 2242438 (prepare), 2242439 (array 0–31), 2242440 (merge): 44,375 candidates, 40,244 valid patches (90.69 %), 6/6 hard checks, 4/5 soft checks (`runs/2242438/features_earth.parquet`, kit `t5_2242438.tar.gz`) |
| **T7/T8/T15** matching and export | `pipeline/match.py`, `pipeline/export.py`, `jobs/t7_match.slurm` | **Done and run; report ready for review** (`bda0acf`) | Job `2242489`: 7 dimensions, 5 presets, 5,010 pairs across 76 targets, `7/7` hard checks, `4/4` soft checks, `/lustre/proyectos/p089/runs/2242489/analogs_universe.json` (6.23 MB) + `t7_report.md` (pending Claude review before copy to `app/`) |
| **T9** tests | `tests/` | Ongoing | 81 synthetic tests pass (job `2242488`) |
| **T10** app | `app/`, `tools/v1_to_sample.py` | **Skeleton on `main`** (`9325dea`, PR #2) | Runs on `app/public/data/sample.json` (v1 converted) |
| **T12–T15** geology, dust and seasons, water and ice | `pipeline/geology.py`, `geology_rules.py`, `pipeline/data/geology_overrides.json`, `dust.py`, `ice.py`, `pipeline/data/ice_hints.json` | **Done and run** (`bda0acf`) | Downloads `2242481` (60 `MOD08_M3` v6.1 + GLiM/SIM3292/Moon/Montabone); `T14=runs/2242486` (overrides applied, 0.0% null/default, 6/6 hard, 2/3 soft), `T13=runs/2242484` (cdod610 + Deep Blue AOD, all parquets + 4 PNGs), `T12=runs/2242487` (ice parquets, 1/1 hard, 3/3 soft); feed into T15 `runs/2242489` |
| **T11** limits | `pipeline/data/limits.json` | **Done** (`e24162e`) | 6 sourced limits per body; used by the final export (job 2242490) |

**T0 data verified on Yuca:**

- MOLA, THEMIS Day/Night, LOLA, LROC WAC, the ice favorability index and Diviner PRP.
- Copernicus GLO-90 complete: 26,475 tiles, and the failure list of job 2242198 is empty.
- MODIS 2023 and Natural Earth, countries included.

---

## 2. What is implemented (`main`)

**`pipeline/config.py`**

- Patch constants: `PATCH_SIZE_KM = 32.0`, `PATCH_RES_M = 500.0`, `PATCH_PIXELS = 64`, `MIN_VALID_FRAC = 0.90`, `MAX_ABS_ELEV_M = 1e5`, `WINDOW_MARGIN_PX = 2`.
- Radii: Earth 6,371,000 m, Moon 1,737,400 m, Mars 3,396,190 m. `FEATURE_NAMES`.
- Yuca paths, raw file maps per body (`MARS_RAW_FILES`, `MOON_RAW_FILES`, `EARTH_RAW_FILES`) and derived files.

**`pipeline/geo.py`** — `extract_patch(src, lat, lon, body, size_km=32, res_m=500)` returns a 64 × 64 float32 array or `None`. It:

1. Checks the body radius against the CRS.
2. Skips and counts patches crossing ±180°.
3. Reads a reduced window on fine rasters.
4. Cleans the data: masks non-finite values and sentinels > 1e5, masks `nodata`, then applies `scale`/`offset`.
5. Reprojects to local AEQD.
6. Requires ≥ 90 % valid pixels.

Patches that contain a pole read a full latitude band; Shackleton is the only one that needs it.

**`pipeline/features.py`** — `compute_features(z, res_m)` returns mean and p90 slope, relief (p95−p5), hypsometric integral, detrended roughness, Riley TRI and mean elevation.

**`pipeline/planet_features.py`**

- Near equal-area global grid (−88° to 88°), latitude stripes, `--limit` for tests and `--merge`.
- Diviner PRP cached once and queried per polar patch with a KD-tree in south polar stereographic (`ice_depth = -999` becomes NaN).
- `[META]` lines with dtype, nodata, scale and offset of every raster.
- LROC WAC compared as a percentile within the Moon.
- `resolve_body_paths()` and `PointSampler` reuse the exact T3 point computation for T4.

**`pipeline/iau.py`, `pipeline/targets.py`, `pipeline/data/targets.json`**

- **Gazetteer:** loaded with geopandas; longitudes converted from 0–360 to −180..180.
- **16 curated targets:**
  - 8 on the Moon: the Artemis III regions anchored on IAU features, plus the rim of Shackleton.
  - 8 on Mars: landing sites plus the SWIM shallow-ice region of Arcadia.
- **Sampling:** each curated target averages either a `point` anchor (5 patches, at least 3 valid) or a `rim` anchor (8 patches, at least 5 valid).
- **Clusters:** 30 k-means clusters per body.

**`pipeline/earth_layers.py`**

- **MODIS with `pyhdf`** (GDAL has no HDF4 driver): NDVI is `raw / 10000` and LST is `raw × 0.02` K. The cache is `data/derived/ndvi_max_2023.tif` and `lst_2023.tif`.
- **Logistics:** roads without ferries, densified to 0.02°; non-military airports; country.
- **Known analog regions:** 12.
- **`EarthLayers`:** the façade used by T5.

**`pipeline/earth_features.py`**

- **Mosaic:** a Copernicus VRT with `-srcnodata 0 -vrtnodata -9999`, so the sea is masked.
- **Three stages:** prepare (prefilter and Earth layers), a 32-stripe array, and merge with checks.
- **Prefilter:** NDVI > 0.25 is dropped; NaN NDVI passes only if LST exists.

**`pipeline/match.py` and `pipeline/export.py`**

- **Normalization & scores:** Earth-only `log1p` + median/`1.4826 * MAD` normalization, Mars-only percentile thermal ranks (`themis_delta` vs `lst_amplitude_c`), 7 similarity dimensions (`topography`, `roughness`, `environment`, `thermal`, `geology`, `dust`, `ice`), and 5 weighted mission presets (`mobility_and_traction`, `construction_and_base`, `geology_and_materials`, `dust_and_seasons`, `isru_and_ice`).
- **Selection:** Whole Earth table (`40,244` patches) evaluated per target (candidate pool dropped) -> greedy top-30 per preset with `>= 150 km` separation and `<= 3` `ice_surface` (GLiM `ig`) analogs (exempt on `isru_and_ice`), plus physical (`|z_diff| > 1.5`), thermal (`> 0.30`), and layer mismatches (`geo_class`, `dust_level_rank`, `dust_seasonality_rank`, `dust_peak_phase_deg`, `cold_rank`).
- **Export & checks:** writes `analogs_universe.json` matching `types.ts` (falling back to provisional `sample.json` limits while `pipeline/data/limits.json` is absent), runs 7 hard checks and 4 soft checks (`t7_checks.json`), and emits `t7_report.md` (with Olympus Mons sanity check, Mars plains spread, dust top 5, and ISRU ice top 5).

---

## 3. Verified outputs on Yuca

| Run | Outputs |
| --- | --- |
| T3, `runs/2242278/` | `features_mars.parquet` (140,916 rows, 99.61 % of candidates), `features_moon.parquet` (36,741, 99.26 %), slope maps. Diviner cache in `data/derived/diviner_prp_south.parquet` (2,880,000 triangles) |
| T4, `runs/2242423/` | `targets.parquet`, `targets.json`, `targets_patches.parquet`, `clusters_{mars,moon}.parquet`, `map_targets_{mars,moon}.png` |
| T6, `runs/2242430/` | `t6_checks.json` and the control maps; cache in `data/derived/` |
| T5 smoke, `runs/2242432/` | `candidates.parquet` (500), `prefilter_stats.json` (44,375 candidates worldwide), `features_earth.parquet` (445), `t5_checks.json`, maps |
| T5 full, `runs/2242438/` | `features_earth.parquet` (40,244 valid patches of 44,375 candidates, 3.3 MB), `prefilter_stats.json`, `t5_checks.json` (6/6 hard, 4/5 soft), `map_earth_*.png`; kit `kit/t5_2242438.tar.gz` (3.7 MB) |
| T14, `runs/2242486/` | `geology_earth.parquet` (40,244), `geology_targets.parquet` (76), `geology_mapping_review.md` (12 overrides applied, 0.0% null/default share on Moon & Mars), `t14_checks.json` (6/6 hard, 2/3 soft) |
| T13, `runs/2242484/` | `dust_earth.parquet` (40,244), `dust_mars.parquet` (140,916), `dust_targets.parquet` (76), 4 PNG maps (`map_dust_level_*`, `map_dust_peak_phase_*`), `t13_checks.json` |
| T12, `runs/2242487/` | `ice_earth.parquet` (40,244), `ice_targets.parquet` (76), `t12_checks.json` (1/1 hard, 3/3 soft) |
| T7/T8 smoke, `runs/2242473/` | `matches.parquet` (3,342 rows), `analogs_universe.json` (2.99 MB), `t7_checks.json` (5/5 hard), `t7_report.md` |
| T7/T8 full, `runs/2242474/` | `matches.parquet` (3,908 rows across 76 targets), `analogs_universe.json` (3.18 MB), `t7_checks.json` (5/5 hard), `t7_report.md` |
| T15 full, `runs/2242489/` | `matches.parquet` (5,010 pairs across 76 targets), `analogs_universe.json` (6.23 MB), `t7_checks.json` (7/7 hard, 4/4 soft), `t7_report.md` |

**Raster scales** (checked with rasterio on the real files; more in [pipeline.md](pipeline.md)):

- **LOLA** stores half-metres (`scale = 0.5`). v1 and the first v2 test had every lunar vertical metric doubled. After the fix (job 2242231), the median lunar slope went from 13.24° to 6.93°.
- **LROC WAC** is relative brightness (uint8, scale 1.00395, offset −0.00395).
- **THEMIS** mosaics are raw grey levels.
- **The ice index** has nodata −3.4e38.
- **MOLA** is int16 metres.

---

## 4. Operational notes

1. **`sbatch --wrap` runs under `/bin/sh`,** where `conda activate spaceapps_2026` fails with exit code 2. Use `.slurm` scripts with `#!/usr/bin/env bash`, or `--wrap 'bash -c "..."'`.
2. **Do not touch or import the v1 scripts** in `legacy_v1/` (`process_analogs.py`, `match_earth_analogs.py`, `enrich_nomenclature.py`). They have no `__main__` guard.
3. **Cluster rules:**
   - `-A p089`, `-p cpu`, `--time`, `--mem`;
   - logs in `/lustre/proyectos/p089/output/`;
   - outputs in a new `runs/<jobid>/`;
   - group limit of 500 CPUs and 4 GPUs (use `%30` on 16-CPU arrays);
   - never `rm -rf` (move to `_to_delete/`) and never disable TLS.
4. **Commit before submitting a job,** so its log records the right commit.

---

## 5. Next steps

**The analog model is complete.** Final run: job 2242490, `runs/2242490/analogs_universe.json`, published to `app/public/data/analogs_universe.json`. It has 7 dimensions, 5 presets, 76 targets and 5,010 pairs, and passed 7/7 hard and 4/4 soft checks.

1. **App (T10, app developer):** switch `DATA_URL`, support 7 dimensions from `metadata.dimensions`, and deploy.
2. **Submission items** in [submission.md](submission.md).
3. **Optional:** translate the code comments to English; the refinements listed in [HISTORY.md](HISTORY.md) "Next".

---

## Queue of pending cluster commands

Commands waiting to be run on Yuca, in order. Whoever works without SSH (MODE B) adds here what they leave ready. Owen runs them top to bottom, over SSH or in the Open OnDemand shell, checks each log against the stated criterion, and strikes the line.

| # | Command (from `/lustre/proyectos/p089/code`, after `git pull`) | Check in the log |
| --- | --- | --- |
| 1 | ~~Tests~~ (job 2242421) | 31 passed |
| 2 | ~~T4 smoke: `sbatch jobs/t4_targets.slurm --k 5 --body Moon`~~ (job 2242422) | 8/8 lunar targets ok |
| 3 | ~~T4 full: `sbatch jobs/t4_targets.slurm`~~ (job 2242423) | 76 targets |
| 4 | ~~T6: `sbatch jobs/t6_earth_layers.slurm`~~ (jobs 2242426, 2242430) | 8/8 hard checks |
| 5 | ~~T5 smoke: `bash jobs/t5_submit.sh --limit 500`~~ (jobs 2242432–2242434) | 5/5 hard checks |
| 6 | ~~T5 full: `bash jobs/t5_submit.sh`~~ (jobs 2242438–2242440) | 40,244 valid patches, 6/6 hard checks |
| 7 | ~~T7/T8 smoke: `sbatch --export=ALL,T5_DIR=/lustre/proyectos/p089/runs/2242432 jobs/t7_match.slurm`~~ (job 2242473) | 3,342 pairs, 5/5 hard checks |
| 8 | ~~T7/T8 real: `sbatch --export=ALL,T5_DIR=/lustre/proyectos/p089/runs/2242438 jobs/t7_match.slurm`~~ (job 2242474) | 3,908 pairs, 5/5 hard checks |

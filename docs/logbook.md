# Logbook

A record of what happens in the project, newest first. It also feeds the use-of-AI description of the submission. Until the evening of 2026-11-13 the entries were written in Spanish; they were translated to English on 2026-11-13, and new entries are written in English. The reasoning behind each decision is summarised in [HISTORY.md](HISTORY.md).

## 2026-11-14: T16.5 — app mirrors the missing-data policy

**What was done and why** (code written by Gemini per `docs/plan_t16_missing_data.md` §7):

- Updated `app/src/lib/types.ts`: added `available_dims` and `preset_status` to `Target`, `earth_missing_dims` to `Analog`, `applies_to` to `Preset`, `scoring_policy` and `preset_status_summary` to `Universe.metadata`.
- Updated `app/src/lib/msi.ts`:
  - Defined `DIMENSION_BODIES`.
  - Updated `msi()` and `msiLog()` to accept `targetDims` and `earthMissing` (defaults to 0), scoring Case C missing Earth dimensions as 0 rather than dropping them.
  - Updated `rankTargets()` to compute preset coverage per target against active weights; targets with coverage < `min_preset_coverage` (0.6) are unranked and returned in `unranked: UnrankedTarget[]`.
- Updated `app/src/components/ScenarioPanel.tsx`: added `body` prop and filtered mission preset chips to only display presets whose `applies_to` includes the current planetary body.
- Updated `app/src/components/RankList.tsx`: added `unranked` prop to render an unranked targets explanatory footer note below the list.
- Updated `app/src/components/Radar.tsx`: added `availableDims` and `earthMissingDims` props; missing Earth data dimensions are plotted at r=0 with a hollow marker and flagged with "no Earth data" in the axis label.
- Updated `app/src/components/Dossier.tsx`: passed `available_dims` and `earth_missing_dims` to `Radar`, formatted `no_earth_data:<dim>` mismatches as "no Earth data for <dim>", and added rows in the feature comparison table for missing Earth dimensions with status `differs` (scored 0).
- Updated `app/src/App.tsx`: wired `body` into `ScenarioPanel`, wired `unranked` into `RankList`, added automatic preset switching on body change if the active preset is inapplicable to the new body, and rendered `metadata.scoring_policy.rules` under Dimensions in the Methodology section.
- Verified: `npm --prefix app run build` (`tsc -b && vite build`) passed with 0 errors. Full test suite: 88 passed, 2 skipped.

## 2026-11-14: T16.4 — tests for the missing-data policy

**What was done and why** (tests written by Gemini per `docs/plan_t16_missing_data.md` §6):

- Added 8 unit tests in `tests/test_match.py`:
  1. `test_msi_case_c_counts_zero`: Verifies Case C scores 0.0 for Earth-missing dimensions.
  2. `test_msi_case_b_skips_target_missing`: Verifies Case B drops dimensions missing on target.
  3. `test_msi_legacy_when_target_dims_none`: Verifies legacy behavior when `target_dims=None`.
  4. `test_msi_scalar_branch_matches_vector_branch`: Verifies scalar and vector branches match for cases B and C.
  5. `test_available_dims_rules`: Tests target dimensions across bodies, thermal, dust, geology, and ice rules.
  6. `test_preset_status`: Tests status evaluation (`ok`, `not_applicable_body`, `insufficient_target_data`).
  7. `test_select_by_preset_skips_not_ok`: Verifies non-ok presets yield all-NaN MSI and empty selection.
  8. `test_dust_preset_does_not_reward_missing_earth_dust`: Reproduces the dust bug and documents the fix.
- Added 1 unit test in `tests/test_export.py`:
  9. `test_export_preset_status_and_missing_dims`: Verifies preset status dictionary, Moon dust applicability, and analog `earth_missing_dims`.
- Verified on local test suite: **88 passed, 2 skipped** in 4.86s.

## 2026-11-14: T16.3 — hard checks 12-14 and soft checks 15-17

**What was done and why** (code written by Gemini per `docs/plan_t16_missing_data.md` §5):

- Added hard checks 12–14 and soft checks 15–17 to `run_t7_checks()` in `pipeline/export.py`:
  - **Check 12 (hard):** Recomputed MSI from raw `sub_scores`, preset weights, `available_dims`, and `earth_missing_score = 0.0` matches `msi_by_preset` within 0.002 for all `ok` presets.
  - **Check 13 (hard):** For every preset with status ≠ `ok`: no analog of that target lists the preset in `selected_by`, and `msi_by_preset[pkey]` is null.
  - **Check 14 (hard):** No Moon target has status `ok` for `dust_and_seasons`.
  - **Check 15 (soft):** Counts targets whose 1st-ranked analog has the preset's highest-weight dimension in `earth_missing_dims` (expected 0).
  - **Check 16 (soft):** Counts Mars targets whose top-1 analog is in Antarctica under `dust_and_seasons` (expected ≤ 5).
  - **Check 17 (soft):** Reports targets with status `ok` for `isru_and_ice` per body (expected Mars 1, Moon 8).
- Extended `build_t7_report()` with section 6 detailing T16 missing-data check results.
- Updated `tests/test_export.py` to assert 10 hard checks passed and 17 total checks evaluated.
- Verified on local test suite: 79 passed, 2 skipped.

## 2026-11-14: T16.2 — export available_dims, preset_status and earth_missing_dims

**What was done and why** (code written by Gemini per `docs/plan_t16_missing_data.md` §4):

- Added `"available_dims"` and `"preset_status"` to `REQUIRED_TARGET_KEYS`, and `"earth_missing_dims"` to `REQUIRED_ANALOG_KEYS` in `pipeline/export.py`.
- Updated `build_universe_dict()`:
  - Per target: exports `available_dims` (sorted list of available dimensions) and `preset_status` (dict mapping each preset key to `{"status": ..., "coverage": ..., "missing_dims": [...]}`). Derived from `matches_meta["preset_status"]` or computed via `available_dims()` and `preset_status()`.
  - Per analog: exports `earth_missing_dims` (list of dimensions available on target but missing on Earth) and sets `msi_by_preset[pkey] = None` when the target's preset status is not `"ok"`.
  - Added `metadata.scoring_policy` detailing `earth_missing_score = 0.0`, `min_preset_coverage = 0.6`, and the 4 scoring policy rules.
  - Added `metadata.preset_status_summary` counting targets per status across bodies and presets.
  - Updated `run_t7_checks` check 1 (`coverage`) to check coverage >= 20 only for presets where `preset_status == "ok"`.
- Updated Universe schema docstring in `pipeline/export.py`.
- Verified on local test suite: 79 passed, 2 skipped.

## 2026-11-14: T16.1 — missing-data policy in MSI and preset selection

**What was done and why** (code written by Gemini per `docs/plan_t16_missing_data.md` §3):

- Defined `EARTH_MISSING_SCORE = 0.0`, `MIN_PRESET_COVERAGE = 0.6`, and `DIMENSION_BODIES` in `pipeline/match.py`.
- Added pure functions `available_dims(tv: TargetVec)` and `preset_status(weights, body, applies_to, available)` to identify applicable/available dimensions per target and evaluate coverage per preset.
- Updated `msi()` to implement Case C: when `target_dims` is provided, non-finite Earth scores for dimensions in `target_dims` receive `earth_missing_score = 0.0` rather than being dropped; dimensions not in `target_dims` (cases A and B) are skipped. Preserved legacy behaviour when `target_dims is None`.
- Updated `select_by_preset()` to evaluate `preset_status`: when status is not `"ok"`, the preset's MSI array is filled with NaN and no candidates are selected. Returns `(msi_by_preset, selected, status_by_preset)`.
- Updated `match_all()` to pass `available_dims` to `select_by_preset()`, attach `earth_missing_dims` and case-C `no_earth_data:<dim>` mismatches to exported analog records, collect `all_preset_status` in `meta_out["preset_status"]`, and write `target_presets.csv` in `main()`.
- Verified on `tests/test_match.py`: 20/20 passed.

## 2026-11-14: T16 specification, missing data was a free pass in the MSI

**What was found** (by Owen in the app, diagnosed by Claude on run 2242490):

- With the dust preset, Mars targets landed in Antarctica; with the ice preset, in the Sahara.
- Cause: `msi()` drops a null sub-score and renormalises the rest, so missing data acts as a free pass. MODIS Deep Blue AOD has no values over ice and snow (1,057 of 2,908 Mars analogs have no dust score, 739 in Antarctica). All 17 Mars targets whose top dust-preset analog is Antarctic had dust null. For ice, only 1 of 38 Mars targets and 8 of 38 Moon targets have ice data, so the preset's 50% ice weight vanished for the rest and terrain plus aridity decided (deserts). The pipeline and the app share the formula, so both were affected.

**What was decided** ([plan_t16_missing_data.md](plan_t16_missing_data.md), for the coding agent):

- Three cases: not applicable to the body (ignored; presets only for the bodies in `applies_to`), missing on the target (ignored, but if less than 60% of the preset weight is left the target is not ranked for that preset), missing on the Earth patch while the target has it (scores 0: no evidence, no credit).
- Missing NDVI on snow and ice keeps counting as bare ground.
- Expected after the re-run: no Mars dust-preset winner without dust data; ice preset ranks 1 Mars target (Arcadia) and 8 Moon targets; no dust preset on the Moon; mobility, construction and geology presets unchanged.
- Nothing is implemented yet. The app part goes on top of `feat/app-seven-dimensions`.

## 2026-11-14: app reads the final export and scores all seven dimensions

**What was done and why** (code written by Claude, branch `feat/app-seven-dimensions`):

- The app still loaded `sample.json` (v1 data converted for the T10 skeleton) and only knew four dimensions, so geology, dust and ice were ignored: the `isru_and_ice` preset put 50% of its weight on a dimension the browser dropped, and most targets scored 99.x.
- `App.tsx` now loads `app/public/data/analogs_universe.json` (run 2242490). Types, MSI, sliders and radar cover the seven dimensions; dimensions that do not apply to a body (thermal and dust on the Moon) are disabled with "not modelled for the Moon".
- MSI in the browser (`Σ w·S / Σ w` over non-null sub-scores) reproduces the pipeline's `msi_by_preset` for all 25,050 analog-preset pairs (max error 0.0009). Spot checks in the running app: Haworth rim with `isru_and_ice` 55.2, Shackleton rim with `mobility_and_traction` 73.0, mars-cluster-29 with `isru_and_ice` 68.8, all equal to the export.
- New controls: road-distance factor λ (0 to 0.3, `MSI · (1 − λ + λ·exp(−road_km/100))`) and "only new candidates" (hides `KNOWN_ANALOG` sites).
- Site sheet: mission context of the target (category, why, geology unit, source), Earth logistics (road, airport), NDVI and day-night ΔT, rows for rock class, dust ranks, cold-trap rank and any other mismatch, non-numeric mismatches (rock class) shown as "differs", pipeline site notes (lava-tube terrain, polar cold), and a source link per physical limit.
- Removed v1 leftovers: "best v1 similarity", "road distance arrives with T6", the T11 "provisional" notes and the `sample.json` error message. The header now shows mission sites and new Earth candidate sites; Methodology lists the dimensions, what is not modelled, datasets and references from the export metadata. Footer venue updated to NASA Space Apps Sonora.
- Checked with `tsc -b`, `npm run build` and in the browser (Mars and Moon, all presets, λ, no console errors).

## 2026-11-14 (morning): T15 matching and export complete (7 dimensions, 5 presets), following Claude's §5.8 review

**What was done and why** (code written by Gemini from Claude's approval in [`docs/plan_t12_t15.md`](plan_t12_t15.md) §5.8, commits `d3a255f`, `bda0acf`):

1. **T14 geology re-run (`job 2242486`, `COMPLETED 0:0`, 8 s, output `/lustre/proyectos/p089/runs/2242486/`):**
   - Applied `pipeline/data/geology_overrides.json` from Claude's review.
   - All 12 target units (`Nt`, `pNt`, `Ioho`, `INt`, `It`, `Iif`, `Iohs`, `Iork`, `Iia`, `Iom`, `Itd`, `lApd`) recorded `rule=override` in `geology_mapping_review.md`.
   - `default_or_null_area_share` dropped to **0.0% for Moon** and **0.0% for Mars**.
   - Checks: **6/6 hard passed, 2/3 soft passed** (only soft warning: `arcadia_swim` is `VOLCANIC_BASIC` while `utopia_zhurong` is `SEDIMENTARY`, handled via shallow ice in T12).
2. **T12 water & ice re-run (`job 2242487`, `COMPLETED 0:0`, 4 s, `T14_DIR=runs/2242486`, output `/lustre/proyectos/p089/runs/2242487/`):**
   - Rebuilt `ice_earth.parquet` (`40,244` rows) and `ice_targets.parquet` (`76` rows) using the new geology run.
   - Checks: **1/1 hard, 3/3 soft passed**.
3. **T13 check update and tropical amendment:**
   - Updated check 5 in `pipeline/dust.py` to `earth_bodele_dust_source` (hard: Bodélé rank > 0.9; Taklimakan reported only); dropped check 7 (`mars_hellas_gt_tharsis`).
   - Implemented §5.8 tropical amendment in `S_dust`: when `|lat| < 15.0°` for either Earth patch or target, drop the seasonal phase term and use denominator `4.0` (`2 * 2`).
4. **T15 matching and export implementation (`pipeline/match.py`, `pipeline/export.py`, `jobs/t7_match.slurm`):**
   - Expanded matching across 7 dimensions (`topography`, `roughness`, `environment`, `thermal`, `geology`, `dust`, `ice`) and 5 mission presets (`mobility_and_traction`, `construction_and_base`, `geology_and_materials`, `dust_and_seasons`, `isru_and_ice`).
   - Vectorized scoring across the entire Earth table (`40,244` patches) per target, dropping the k-NN candidate pool.
   - Enforced ice cap rule: `<= 3` `ice_surface` (GLiM `ig`) analogs per (target, preset), except for `isru_and_ice` which is exempt.
   - Added layer mismatches (`geo_class`, `dust_level_rank`, `dust_seasonality_rank`, `dust_peak_phase_deg`, `cold_rank`).
   - Extended target and analog schemas with rich layer objects, citations, `not_modelled`, and pipeline run metadata.
5. **Unit tests (`job 2242488`, `COMPLETED 0:0`, 5 s):**
   - **`81 passed, 73 warnings in 4.00s`** across all unit test suites.
6. **T15 production run (`job 2242489`, `COMPLETED 0:0`, 11 s, output `/lustre/proyectos/p089/runs/2242489/`):**
   - Matches: `5,010` analog pairs across `76` targets.
   - Universe JSON: `6.23 MB` (under 20 MB ceiling, single file, 0 NaN/Inf values).
   - Lava tube terrain: `684` pairs with `subsurface_note = "Basaltic volcanic terrain: lava tubes are possible here (not mapped)"`.
   - Checks: **7/7 hard passed, 4/4 soft passed** in [`t7_checks.json`](file:///lustre/proyectos/p089/runs/2242489/t7_checks.json):
     - #1 `coverage`: 76 targets checked, 0 below 20 analogs.
     - #2 `diversity`: min pair distance `150.001 km`, 0 violations.
     - #3 `ice_cap`: max 3 `ice_surface` per preset, exempt for `isru_and_ice`, 0 violations.
     - #4 `scores`: all `S_k` and `MSI` in `[0, 1]`, `S_thermal` null for Moon, 0 errors.
     - #5 `json_contract`: valid JSON, 6.23 MB, required keys present.
     - #6 `layer_scores`: non-null geology 4,814, dust 1,851, ice 732, 0 errors.
     - #7 `olympus_mons_geology`: **10 / 10** `VOLCANIC_BASIC` (`vb`) Earth patches in the top 10 under `geology_and_materials` (Chad/Tibesti, Djibouti/Afar, Argentina/Puna, Antarctic/Greenland basaltic nunataks).
     - #8 `mars_plains_spread`: median spread `0.059 > 0.012`.
     - #9 `dust_and_seasons_mars_top5`: Yemen, Algeria, Sudan, Oman identified for Jezero and Meridiani.
     - #10 `isru_and_ice_moon_top5`: Antarctica ice and cold-trap analogs for Haworth, Slater Plain, Shackleton.
     - #11 `geo_class_shares`: Crystalline 39.7%, Sedimentary 35.6%, Volcanic Basic 13.6%, Ice 5.2%, Volcanic Other 1.7%, Evaporite 0.1%, Pyroclastic 0.2%, Null 3.9%.

## 2026-11-14 (early morning): T14 geology, T13 dust & seasons, T12 water & ice (runs before T15 review stop)

**What was done and why** (code written by Gemini from Claude's [`docs/plan_t12_t15.md`](plan_t12_t15.md) §1–§4 and §7, stopping at §5.6 before T15)

- **Downloads (`download_aod.py`, `jobs/download_t12_t14.slurm`):**
  - Initial `MOD08_M3` search failed on `version="061"` (`job 2242480`); updated `download_aod.py` to LAADS CMR `version="6.1"` and filtered granules to `2019–2023` (`commit c0f88f5`, excluding Dec 2018 overlap `A2018335`).
  - **`job 2242481` (`COMPLETED`, exit `0:0`, `00:04:42`, `/lustre/proyectos/p089/output/download_t12_t14_2242481.log`):** verified GLiM 0.5° (`earth_glim/glim_wgs84_0point5deg.txt.asc`, `1,235,039` B), Mars SIM 3292 (`sim3292_database.zip`, `808,910,442` B + extracted `.gdb`/shapefiles), Moon Unified Geologic Map v2 (`Unified_Geologic_Map_of_the_Moon_GIS_v2.zip`, `224,413,040` B), Montabone kriged CDOD v2 (`krigedcdod_v2.tar.gz`, `618,852,694` B + 13 `MY24`–`MY36` NetCDF3 files), and **60 non-empty `MOD08_M3` v6.1 `.hdf` granules** (`2019–2023`), printing byte sizes and SHA-256 digests.
- **Unit tests (`tests/test_geology.py`, `tests/test_dust.py`, `tests/test_ice.py`):**
  - Initial run (`job 2242476`) had 1 synthetic failure from overlapping 3×3 neighborhoods on a 4×4 grid; updated `test_glim_at_corners_and_coast_fallback` to 6×6 (`commit e81cccb`).
  - **`job 2242478` (`COMPLETED`, exit `0:0`, `00:00:05`, `pytest -q tests`):** **`70 passed, 73 warnings in 3.63s`** (0 failures, 0 warnings from T12–T14).
- **T14 Geology (`pipeline/geology_rules.py`, `pipeline/geology.py`, `jobs/t14_geology.slurm`):**
  - Implemented the 8 `GEO_CLASSES`, symmetric `GEO_SIMILARITY`, word-boundary Moon/Mars rules (`\b<kw>(?:s|es)?\b` so `"edifice"` does not match `"ice"`), vectorised GLiM `glim_at` with 3×3 coast fallback, layer priority excluding boundary/clip/annotation layers (`commit 25f2e7e`), and `geology_mapping_review.md` / CSV unit summaries.
  - **`job 2242482` (`COMPLETED`, exit `0:0`, runtime `7.501 s`, commit `25f2e7e`, output `/lustre/proyectos/p089/runs/2242482/`):**
    - Earth GLiM over `40,244` T5 patches: `SEDIMENTARY=22,123`, `ICE=12,742`, `CRYSTALLINE=3,631`, `VOLCANIC_BASIC=739`, `VOLCANIC_OTHER=630`, `EVAPORITE=181`, `<NA>=138`, `PYROCLASTIC=60` (`lava_tube_terrain=739`, `ice_surface=12,742`).
    - Moon read from `Shapefiles/GeoUnits.shp` (`12,247` polygons, `49` units, joined with `Unified_Geologic_Map_of_the_Moon_DOMU_descriptions.csv` because `Global_Geology_of_the_Moon_5M_03-02-2020.gdb` uses ESRI CDF compression unhandled by OpenFileGDB). Mars read from `SIM3292_geodatabase.gdb / SIM3292_Global_Geology` (`1,311` polygons, `44` units, joined with `Unit_Description`).
    - Checks (**`6/6` hard, `2/3` soft** in [`t14_checks.json`](file:///lustre/proyectos/p089/runs/2242482/t14_checks.json)):
      - Hard PASS: `earth_pinacate_tibesti` (`vb -> VOLCANIC_BASIC`), `earth_dry_valleys` (`sm -> SEDIMENTARY`), `earth_ice_interiors` (`ig -> ICE`), `moon_maria` (`Im2 -> VOLCANIC_BASIC`), `mars_tharsis_volcanoes` (`Ave -> VOLCANIC_BASIC`), `mars_north_polar_cap` (`lApc -> ICE`).
      - Soft PASS: `moon_shackleton_rim` (`IMPACT`), `default_or_null_area_share` (Moon `7.34%` across 5 `[REVIEW]` units: `Ioho` `3.78%`, `Iif` `1.37%`, `Iohs` `0.93%`, `Iork` `0.73%`, `Iia` `0.54%`; Mars `0.00%`).
      - Soft FAIL: `mars_arcadia_utopia` (`arcadia_swim: VOLCANIC_BASIC`, `utopia_zhurong: SEDIMENTARY`).
  - **Post-run review commit `16db5db`:** Claude reviewed `runs/2242482/geology_mapping_review.md` and added [`pipeline/data/geology_overrides.json`](../pipeline/data/geology_overrides.json) (Moon: `Nt, pNt, INt, It -> CRYSTALLINE`, `Ioho, Iohs, Iif, Iork, Iia, Iom -> IMPACT`, `Itd -> VOLCANIC_OTHER`; Mars: `lApd -> SEDIMENTARY`; `arcadia_swim` kept on `lAv` with shallow ice handled via `ice_hints.json`). A clean re-run of `jobs/t14_geology.slurm` on `16db5db`+ awaits §5.6 sign-off together with T13.
- **T13 Dust & Seasons (`pipeline/dust.py`, `jobs/t13_dust.slurm`):**
  - First run (`job 2242483`) printed Montabone & MOD08 metadata and exited on `NameError: name 'math' is not defined`; fixed by adding `import math` (`commit c834727`, merged before `16db5db`).
  - **`job 2242484` (`FAILED`, exit `1:0` at final hard-check guard after writing all parquets, maps and checks, runtime `13.638 s`, commit `16db5db`, output `/lustre/proyectos/p089/runs/2242484/`):**
    - Printed Montabone NetCDF3 metadata (`669 × 60 × 120` across 13 files `MY24`–`MY36`): selected `cdod610` (`IR absorption CDOD normalized to the reference pressure of 610 Pa`, `units='Pa/Pa'`), `Ls` (`Solar longitude`, `degrees`), `Time` (`sol`).
    - Printed `MOD08_M3` HDF4 metadata (60 files): selected `Deep_Blue_Aerosol_Optical_Depth_550_Land_Mean_Mean` (`_FillValue=-9999`, `scale_factor=0.0010000000474974513`, `add_offset=0.0`, `valid_range=[0, 5000]`, grid `180 × 360` from `89.5°N` to `-89.5°S`, `-179.5°W` to `179.5°E`); summer Sahara mean AOD = `0.4546`.
    - Wrote `dust_mars.parquet` (`140,916` rows), `dust_earth.parquet` (`40,244` rows, `24,998` with valid dust), `dust_targets.parquet` (`76` rows), and the 4 maps (`map_dust_level_{earth,mars}.png`, `map_dust_peak_phase_{earth,mars}.png`).
    - Checks (**`3/4` hard, `3/4` soft** in [`t13_checks.json`](file:///lustre/proyectos/p089/runs/2242484/t13_checks.json)):

| # | Check | Kind | Status | Observed |
| --- | --- | --- | --- | --- |
| 1 | `mars_variables_identified` | Hard | PASS | `cdod610` (`Pa/Pa`), `Ls`, `Time` (`latitude`, `longitude`) |
| 2 | `earth_sds_and_scaling` | Hard | PASS | `Deep_Blue_Aerosol_Optical_Depth_550_Land_Mean_Mean`, Sahara summer AOD `0.4546` |
| 3 | `mars_storm_years_top3` | Soft | PASS | Top 3: `MY25` (`0.27759`), `MY34` (`0.25284`), `MY28` (`0.18932`) |
| 4 | `mars_global_curve_perihelion_peak` | Hard | PASS | Peak bin `7` (`Ls=225.0°`, mean `0.26039`) |
| 5 | `earth_known_dust_sources` | Hard | FAIL | Bodélé `(17, 18)` AOD `0.513`, rank `0.9847`; Taklimakan `(39, 83)` AOD `0.2903`, rank `0.7281` (`< 0.9`) |
| 6 | `earth_atacama_clean_air` | Soft | PASS | Atacama `(-24.5, -69.3)` AOD `0.0475`, rank `0.1615` |
| 7 | `mars_hellas_gt_tharsis` | Soft | FAIL | Hellas `(-42, 70)` `0.1695` (rank `0.5954`) vs Tharsis `(0, -110)` `0.1718` (rank `0.6269`) |
| 8 | `dust_maps_written` | Soft | PASS | All 4 PNG maps written |

    - **What was learned:**
      - Mars local peak phase shows physically coherent perihelion dust timing (`Ls=225°` global peak, hemispheric solstice separation in `map_dust_peak_phase_mars.png`), and Earth local peak phase captures spring Asian/Saharan vs boreal summer aerosol maxima (`map_dust_peak_phase_earth.png`).
      - Hard check #5 failed at Taklimakan `(39, 83)` because `MOD08_M3` Deep Blue 550 nm **annual** mean across the `24,998` valid Earth patches is highest over the Indo-Gangetic Plain (`0.6–0.9+`), Sahel/Sahara (`0.4–0.6`), Eastern China (`0.4–0.7`) and Arabia, whereas Taklimakan has strong spring dust storms and low winter AOD (yielding annual mean `0.2903`, rank `0.7281`). Similarly, median MY24–MY36 equatorial CDOD610 over Tharsis (`0.1718`) slightly exceeds mid-latitude Hellas (`0.1695` at `-42°`). Left untouched for §5.6 review.
- **T12 Water & Ice (`pipeline/data/ice_hints.json`, `pipeline/ice.py`, `jobs/t12_ice.slurm`):**
  - **`job 2242485` (`COMPLETED`, exit `0:0`, runtime `0.094 s`, commit `16db5db`, `T14_DIR=runs/2242482`, output `/lustre/proyectos/p089/runs/2242485/`):**
    - `ice_earth.parquet` (`40,244` rows: `ice_E=1.0 -> 12,742`, `ice_E=0.5 -> 2,161`, `ice_E=0.0 -> 25,341`); `375` Moon T3 patches with finite `diviner_tavg_k`.
    - Checks (**`1/1` hard, `3/3` soft** in [`t12_checks.json`](file:///lustre/proyectos/p089/runs/2242485/t12_checks.json)):
      - Soft PASS #1 (`coldest_1pct_earth_polar`): `403/403` coldest 1% Earth patches in Antarctica (`outside_ant_grl_count=0`).
      - Hard PASS #2 (`moon_haworth_slater_cold_rank`): `moon-a3-haworth=0.9734`, `moon-a3-slater-plain=0.9574` (`> 0.9`).
      - Soft PASS #3 (`dry_valleys_ice_e_05`): `9` patches, `frac_eq_0_5=1.0`.
      - Soft PASS #4 (`mars_ice_targets_list`): `[mars-arcadia-swim (ice_T=1.0, ice_source=ice_hint)]`.

**What is left (§5.6 review stop before T15)**

- Send `geology_mapping_review.md` / `geology_units_{moon,mars}.csv` (`2242482`), `t13_checks.json` + the 4 dust PNG maps (`2242484`), and `t12_checks.json` (`2242485`) to Owen/Claude.
- Re-run `jobs/t14_geology.slurm` (to apply `pipeline/data/geology_overrides.json` from `16db5db`) and re-run `jobs/t13_dust.slurm` (and `t12_ice.slurm` if `T14_DIR` changes) once §5.6 decisions are confirmed, then implement and run T15 (`pipeline/match.py`, `pipeline/export.py`).

## 2026-11-13 (night): T7/T8 — RBF matching, MSI presets and universe JSON export

**What was done and why** (code written by Gemini from Claude's [`docs/plan_t7_t8.md`](plan_t7_t8.md))

- **Matching (`pipeline/match.py`):** implemented `Normalizer` (Earth-only median and `1.4826 * MAD` after `log1p` on `relief_m`, `detrended_std_m` and `tri_m`), Mars/Earth percentile `thermal_ranks`, vectorized RBF `dimension_scores` (`σ_scale = 1.0`), `msi` across the three mission presets (`mobility_and_traction`, `construction_and_base`, `dust_and_thermal`), `NearestNeighbors` candidate pooling (`k = 2000`, retry `k = 8000` if `< 30` accepted), greedy `select_diverse` enforcing `>= 150 km` separation and `<= 3` `polar_cold` (`lst_day_c < -10 °C`) analogs per preset, and `mismatches` (`|z_diff| > 1.5` or `|zt_e - zt_m| > 0.30`). Kept Antarctica (`Dry Valleys`) reachable while preventing Antarctic ice sheets from dominating flat Mars rankings.
- **Export, checks and report (`pipeline/export.py`, `jobs/t7_match.slurm`):** assembled `analogs_universe.json` matching `app/src/lib/types.ts` (NaNs serialized as `null`, rounding 4/3/2, verified URLs only or `null` with `TODO(verify)`), used provisional `limits` from `app/public/data/sample.json` with warning log (since `pipeline/data/limits.json` does not exist yet), added the 5 hard checks (`t7_checks.json`) and generated `t7_report.md` including the Olympus Mons sanity check.
- **Unit tests (`tests/test_match.py`, `tests/test_export.py`):** 12 synthetic tests covering Earth-only normalization, `log1p`, NDVI/NaN environment scoring, Moon null thermal, `msi` null-skipping, 150 km & polar-cap greedy diversity, mismatch threshold, `earth_id` format, strict JSON schema (`allow_nan=False`), and provisional `sample.json` limits fallback.

**Verification on Yuca** (via Slurm, env `spaceapps_2026`)

- **Unit test suite** (`job 2242472`, commit `997a0c0`, `pytest -q tests`): **`61 passed, 73 warnings in 4.24s`** (0 skipped, 0 warnings in T7/T8).
- **Smoke test against T5 smoke run** (`T5_DIR=runs/2242432`, `job 2242473`, commit `c8c080f`, runtime `0.29 s` match): `3,342` union pairs across `76` targets, `analogs_universe.json` `2.99 MB`, **`5/5` hard checks PASS** (`coverage` 0 below 20, `min_pair_km=150.305`, `max_polar_per_preset=3`, `scores` ok, `json_contract` ok).
- **Full run against T5 global run** (`T5_DIR=runs/2242438`, `job 2242474`, commit `c8c080f`, output `/lustre/proyectos/p089/runs/2242474/`):
  - Runtime: `match = 0.511 s`, `export = 0.854 s`; `0` targets required the `8000` retry.
  - Exported **`3,908` pairs across `76` targets** (`KNOWN_ANALOG=213`, `NEW_CANDIDATE=3,695`; `polar_cold=286`, `ndvi_missing=185`) into `/lustre/proyectos/p089/runs/2242474/analogs_universe.json` (`3.18 MB`).

| # | Check | Status | Observed | Expected |
| --- | --- | --- | --- | --- |
| 1 | `coverage` | PASS | `76` targets checked, `below_20_no_retry=0`, `below_20_with_retry=0` | `>= 20` per preset (or `8000` retry) |
| 2 | `diversity` | PASS | `min_pair_km = 150.238`, `violations = []` | `>= 150.0 km` within `(target, preset)` |
| 3 | `polar_cap` | PASS | `max_polar_per_preset = 3`, `violations = []` | `<= 3 polar_cold` per `(target, preset)` |
| 4 | `scores` | PASS | `error_count = 0` | All `S_k`, `MSI` in `[0, 1]`; `S_thermal` null for Moon |
| 5 | `json_contract` | PASS | `analogs_universe.json` (`3.183 MB`), `76` targets parsed, `errors = []` | Valid JSON (`allow_nan=False`), `< 20 MB`, `types.ts` keys |

- **Curated score distribution (`mobility_and_traction`, `σ_scale=1.0`):**

| Body | Curated targets | 1st MSI median | 1st MSI p90 | 30th MSI median | 30th MSI p90 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Moon | 8 | `0.932` | `0.965` | `0.778` | `0.861` |
| Mars | 8 | `0.998` | `0.999` | `0.986` | `0.993` |

- **Olympus Mons sanity check (`18.3523°N, -133.6437°E`):** top 10 analogs at `0.803–0.957` MSI across steep relief massifs (Antarctica, China/Tian Shan–Kunlun, Afghanistan, Baja California/Mexico at `0.807`, Iran); island shield volcanoes (`Hawaii`, `Lanzarote`) remain filtered by coastal sea pixels in the Copernicus VRT mask as anticipated.

**What is left**

- Review of [`runs/2242474/t7_report.md`](file:///lustre/proyectos/p089/runs/2242474/t7_report.md) (score distribution and Olympus Mons check) by Claude/Owen before copying `analogs_universe.json` to `app/public/data/`, completing T11 (`pipeline/data/limits.json`), and switching `DATA_URL` in T10.

## 2026-11-13 (night): T5 — Earth global sweep (Copernicus GLO-90 + T6 layers)

**What was done and why** (code written by Gemini from Claude's [`docs/plan_t5.md`](plan_t5.md))

- **Code:**
  - Copernicus settings (`copernicus_dir`, `copernicus_vrt`) in `pipeline/config.py`;
  - `pipeline/earth_features.py`;
  - Slurm jobs `jobs/t5_prepare.slurm`, `jobs/t5_earth_features.slurm` and `jobs/t5_merge.slurm`, with the launcher `jobs/t5_submit.sh`;
  - 7 synthetic unit tests in `tests/test_earth_features.py`, covering `gdalbuildvrt` sea masking and latitude-varying tile widths.
- **Same scale as Mars and the Moon:** `pipeline/geo.py` (T1) and `pipeline/features.py` (T2) were reused unmodified, so Earth patches are exactly the same 64 × 64 (500 m/px) AEQD patches.
- **Prefilter:** the `plan_t5.md` §2.5.3 rule (`ndvi_max <= 0.25`, keeping `ndvi_max == NaN` only when `lst_day_c` is finite). It retains the ice-covered regions that MOD13C2 omits south of −59.45°S, including Antarctica and the McMurdo Dry Valleys.

**Verification on Yuca** (via Slurm, env `spaceapps_2026`, commit `52bf3d7`)

- **Unit test suite** (`job 2242431`, `pytest -q tests`): **`49 passed, 73 warnings in 4.08s`** (0 skipped, 0 warnings from T5/T6 modules).
- **Smoke test** (`bash jobs/t5_submit.sh --limit 500`; jobs `2242432` prepare / `2242433` array / `2242434` merge; `/lustre/proyectos/p089/runs/2242432/`):
  - built `/lustre/proyectos/p089/data/derived/copernicus_90m.vrt` (`13M`, `432004×208800`, `res=(0.0008333333333333334, 0.0008333333333333334)`, `26,475` tiles, in `00:04:35`);
  - prefiltered `44,375` candidates from `497,818` grid points (`179,663` with tiles);
  - stripe `0/1` yielded `445/500` valid patches (`89.0%`) in `5.0s`, with `mean_elev_m ∈ [-28.00, 5244.27]` and median slope `0.504°`;
  - checks: `5/5` hard, `4/5` soft.
- **Full 32-stripe run** (`bash jobs/t5_submit.sh`; jobs `2242438` prepare / `2242439` array `0-31%30` / `2242440` merge; shared run directory `/lustre/proyectos/p089/runs/2242438/`):
  - Reused the existing `/lustre/proyectos/p089/data/derived/copernicus_90m.vrt`; loaded `1,650,450` road vertices.
  - **`prefilter_stats.json`:**

    | Count | Value | By latitude |
    | --- | --- | --- |
    | `grid` | 497,818 | |
    | `no_tile` | 318,155 (`with_tile=179,663`) | |
    | `vegetated` | 113,935 | |
    | `no_land_data` | 21,353 | south of −60: 1,878; −60 to 60: 17,573; north of 60: 1,902 |
    | `ndvi_missing` | 14,130 | south of −60: 13,081; −60 to 60: 837; north of 60: 212 |
    | `kept` | 44,375 (`NEW_CANDIDATE=43,596`, `KNOWN_ANALOG=779`) | |

  - **Merge (`32/32` stripes):** `/lustre/proyectos/p089/runs/2242438/features_earth.parquet` (`3.3M`), **`40,244` valid patches** (`90.69%`), `elev_min_m=-112.91`, `elev_max_m=5922.13`, `slope_median_deg=0.464`.
  - **Visual map inspection:** `/lustre/proyectos/p089/runs/2242438/map_earth_mean_slope_deg.png` (`572K`) shows the expected topographic contrast across the Andes, Himalaya/Tibet, the flat Sahara and the Antarctic plateau. `map_earth_classification.png` (`204K`) cleanly separates `ndvi_missing`, `KNOWN_ANALOG` and `NEW_CANDIDATE`.
  - **Offline kit packaged:** `/lustre/proyectos/p089/kit/t5_2242438.tar.gz` (`3.7M`, `sha256: 8396d59ab029c2dab1059326791f84f86c46f97fa23eb917a6a08ee934e0b76f`).

| # | Type | Check | Observed | Expected | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Hard | `valid_patch_count` | `40244` | `[30000, 80000]` | PASS |
| 2 | Hard | `amazon_le_5` | `0` | `<= 5` | PASS |
| 3 | Hard | `congo_le_5` | `0` | `<= 5` | PASS |
| 4 | Hard | `indonesia_le_5` | `0` | `<= 5` | PASS |
| 5 | Hard | `arid_regions_present` | `atacama=324, sahara=6542, sonora=78, central_australia=508, mcmurdo-dry-valleys=14` | `>= 1` in all regions | PASS |
| 6 | Hard | `join_and_t6_columns` | `orphan_rows=0, all_nan_t6_cols=[]` | No orphan rows or all-NaN T6 column | PASS |
| 7 | Soft | `known_region_counts` | `atacama=324, mojave=76, pilbara=49, devon-island=42, svalbard=27, iceland=26, mcmurdo-dry-valleys=14, utah-mdrs=9, meteor-crater=4`; `0` in `hawaii-big-island`, `rio-tinto`, `lanzarote` | Informative count (12 regions) | PASS |
| 8 | Soft | `new_candidate_ratio` | `0.9858` (`NEW_CANDIDATE=39673`, `KNOWN_ANALOG=571`) | `> 0.95 NEW_CANDIDATE` | PASS |
| 9 | Soft | `top15_countries` | `Antarctica=12125, China=2816, Algeria=2158, Australia=1945, Greenland=1843, Saudi Arabia=1805, Libya=1552, Iran=1158, Sudan=1138, Egypt=905, Niger=898, Mauritania=859, Argentina=790, Kazakhstan=776, Mali=745` (`Mexico` outside top 15; Sonora contributes `78` in #5) | `Mexico` in top 15 | FAIL (soft) |
| 10 | Soft | `ndvi_missing_valid_count` | `12412` | Valid count with `ndvi_missing` | PASS |
| 11 | Soft | `control_maps_written` | `map_earth_mean_slope_deg.png`, `map_earth_classification.png` | Both PNGs written | PASS |

**What is left**

- Implement and run T7/T8 (`pipeline/match.py`, `pipeline/export.py`, `jobs/t7_match.slurm`) against `runs/2242438/features_earth.parquet`.
- Author the T11 content (`pipeline/data/limits.json`).
- Publish `app/public/data/analogs_universe.json`.
- Complete the English code cleanup.

## 2026-11-13 (night): documentation in English

- Claude translated every document to English and renamed the files:

  | Old name | New name |
  | --- | --- |
  | `bitacora` | `logbook` |
  | `plan_implementacion` | `implementation_plan` |
  | `prompt_gemini` | `gemini_prompt` |
  | `progreso_handoff` | `handoff` |
  | `propuesta_de_valor` | `value_proposition` |
  | `operacion_sin_ssh` | `working_without_ssh` |
  | `entrega` | `submission` |

  The master plan and the idea log moved into `docs/`.
- The README was rewritten in English to describe the project.
- [HISTORY.md](HISTORY.md) tells the whole history in English, with the reason for every decision.
- **Rules from now on:** commit messages, new documentation and new code comments are in English. Old commits are not rewritten, because their hashes are cited in the docs and in the Slurm logs. Gemini will translate the code comments in a later session ([gemini_prompt.md](gemini_prompt.md)).
- Claude also wrote the detailed T7/T8 plan in English ([plan_t7_t8.md](plan_t7_t8.md)), using the real T3, T4 and T5 outputs.
  - **Scale gap:** Earth's arid land is much smoother than the lunar south pole at 32 km scale, so lunar scores will be low.
  - **Ice sheets:** about 30 % of the Earth candidates are flat ice sheets that the data cannot tell from bare ground, so they are capped at 3 per ranking.

## 2026-11-13 (night): T6 — Earth layers (NDVI, LST, logistics, country and known analogs)

**What was done** (code written by Gemini from Claude's `docs/plan_t6.md`)

- **Configuration and dependencies** (`pipeline/config.py`, `pipeline/requirements.txt`): `EARTH_RAW_FILES`, `EARTH_DERIVED_FILES` (`ndvi_max_2023.tif`, `lst_2023.tif`) and `MODIS_CMG_RES_DEG = 0.05`, plus `pyhdf>=0.10`, used only to build the caches on Yuca.
- **Known regions** (`pipeline/data/known_analogs.json`): 12 curated approximate bboxes (`atacama`, `mcmurdo-dry-valleys`, `iceland`, `hawaii-big-island`, `devon-island`, `utah-mdrs`, `rio-tinto`, `svalbard`, `pilbara`, `meteor-crater`, `lanzarote`, `mojave`), validated on load (unique `id`, valid bboxes, non-empty `source_url`).
- **`pipeline/earth_layers.py` and `jobs/t6_earth_layers.slurm`:**
  - **Pure functions** on the 0.05° CMG grid:
    - `ndvi_from_raw`: `/ 10000.0`, fill `-3000`;
    - `lst_c_from_raw`: `* 0.02 - 273.15`, fill `0`, `< 7500 -> NaN`;
    - annual accumulators: `running_nanmax`, `running_sum_count`, `finalize_mean(..., min_count=3)`;
    - patch window: `cell_index`, and `patch_window_stat` with antimeridian wrapping.
  - **Cache builders** on Yuca (`build_ndvi_max`, `build_lst`, `ensure_cache`): `pyhdf` imported lazily, atomic writes (`.tmp.tif` + `os.replace`), existing files never overwritten.
  - **Spatial indexes:**
    - `Logistics`: a haversine `BallTree` on `ne_10m_roads` densified every `0.02°` without `Ferry` (`1,650,450` vertices), and on civil airports (military airports and spaceports excluded);
    - `Countries`: `within`, then `sjoin_nearest` in `EPSG:4087` up to `25 km`;
    - `KnownRegions`;
    - the `EarthLayers` façade (~420 MB), meant to be created once before `fork` in T5.
- **Unit tests** (`tests/test_earth_layers.py`): 11 synthetic tests, without `pyhdf`.

**Verification on Yuca** (via Slurm)

- **Unit suite** (`job 2242425`, `pytest -q tests`): **`42 passed` in 3.79s** (31 previous + 11 from T6; 0 warnings from the T6 module).
- **Cache build and first check** (`job 2242426`, commit `29fbb88`):
  - Built `/lustre/proyectos/p089/data/derived/ndvi_max_2023.tif` (18 MB, 2 `float32` bands, `3600×7200`, `EPSG:4326`) and `/lustre/proyectos/p089/data/derived/lst_2023.tif` (56 MB, 3 `float32` bands, `3600×7200`, `EPSG:4326`).
  - Passed `5/5` soft and `6/8` hard. Two hard checks failed:
    - **#2:** Egypt `(24.0, 28.0)` gave `0.1028`, with pixel reliability `0` in all 12 months;
    - **#8:** the unweighted finite fraction was `0.2438`, because MOD13C2 has no data south of `-59.45°S` and omits Antarctica.
  - Claude approved, in `plan_t6.md` §6.2.1, changing #2 to `< 0.12` and #8 to a `cos(lat)`-weighted fraction `> 0.25`.
- **Re-check after the adjustment** (`job 2242430`, commit `84888cd`, reusing the existing caches; outputs in `/lustre/proyectos/p089/runs/2242430/`): **`8/8` hard and `5/5` soft (PASS)**. The 3 PNGs were reviewed visually (`map_ndvi_max.png`, `map_lst_amplitude.png`, and `map_known_analogs.png` with the 12 bboxes on their regions):

| # | Type | Check | Observed | Expected | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Hard | `cache_metadata` | `ndvi` 2 bands, `lst` 3 bands, `3600×7200`, `EPSG:4326` | `3600×7200 EPSG:4326` | PASS |
| 2 | Hard | `ndvi_sahara` | `dz=0.0919`, `eg=0.1028` | `< 0.12` in both | PASS |
| 3 | Hard | `ndvi_atacama` | `0.0760` | `< 0.10` | PASS |
| 4 | Hard | `ndvi_tropical_forests` | `amazonia=0.8684`, `congo=0.8650` | `> 0.70` in both | PASS |
| 5 | Hard | `dist_road_hermosillo` | `0.596 km` | `< 5 km` | PASS |
| 6 | Hard | `countries_lookup` | `Mexico` / `Chile` / `Algeria` | `Mexico` / `Chile` / `Algeria` | PASS |
| 7 | Hard | `known_region_lookup` | `utah-mdrs` / `None` | `utah-mdrs` / `None` | PASS |
| 8 | Hard | `ndvi_finite_land_frac` | `cos_weighted=0.2696` (`unweighted=0.2438`) | `> 0.25` (weighted by `cos(lat)`) | PASS |
| 9 | Soft | `lst_day_dry_valleys` | `-28.18 °C` | `< 0 °C` | PASS |
| 10 | Soft | `lst_amp_sahara_vs_amazonia` | Sahara `21.30 °C` vs Amazon `4.16 °C` | Sahara `> 15 °C` and `>` Amazon | PASS |
| 11 | Soft | `dist_road_dry_valleys` | `3447.74 km` | `> 1000 km` | PASS |
| 12 | Soft | `ndvi_prefilter_pass_frac` | `grid=0.0543` (`land=0.2228`) | Informative | PASS |
| 13 | Soft | `sample_10k_runtime_s` | `1.216 s` | `< 30 s` | PASS |

- **Prefilter rule for T5:** Claude then estimated the T5 prefilter on the real cache. 20,524 of the 35,483 tile centres with NaN NDVI are over the sea (coastal tiles, atolls), not in Antarctica. The T5 plan was changed so that a NaN NDVI passes only where LST exists (`plan_t5.md` §2.5.3).

**What was left:** T5, T7, T8 and T11.

## 2026-11-13 (night): the real venue and its submission rules

- The team is registered at **NASA Space Apps Sonora 2026** (Tec de Monterrey, Campus Sonora Norte), not at the UTH venue the README used to show.
- Claude reviewed [spaceappssonora.org](https://spaceappssonora.org/) and its [pitch guide](https://spaceappssonora.org/pitches):
  - hackathon on Saturday the 14th from 9:00 to 21:00; pitches on Sunday the 15th from 9:00 to 14:00;
  - a 3-minute pitch in Canva, with the team number on the first slide;
  - documentation and a 30-second video in English;
  - a deployed app;
  - judging criteria: innovation, social impact, documentation and scalability.
- The README was updated with the venue, schedule and rules. [submission.md](submission.md) was created with the deliverables, a timeline fitted to a single working day, the checklist and plan B. The 48-hour timeline in `implementation_plan.md` was marked as superseded.

## 2026-11-13: T4 — curated targets, T4.0 polar support and global clusters

**What was done** (code written by Gemini from Claude's `docs/plan_t4.md`)

- **T4.0** (`pipeline/geo.py`, `tests/test_geo.py`): added `_patch_contains_pole()` and the polar branch in `extract_patch()`, which reads a full latitude band when a patch contains the pole (Shackleton, at `lat = -89.67°`). Patches away from the poles and the antimeridian count are untouched, so T3 (`|lat| <= 88°`) does not change.
- **Sampling refactor** (`pipeline/planet_features.py`): `resolve_body_paths()` was extracted, and `PointSampler` samples single points reusing T3's `_process_point()` exactly.
- **IAU nomenclature** (`pipeline/iau.py`, `tests/test_iau.py`):
  - a clean module with no import side effects;
  - it loads `MARS_nomenclature_center_pts.shp` and `MOON_nomenclature_center_pts.shp` with `geopandas`;
  - it normalises `center_lon` (`0–360 -> -180..180`) and makes the links `https://`;
  - it implements `haversine_km`, `iau_label` and `find_feature`.
- **Curated targets and clusters** (`pipeline/data/targets.json`, `pipeline/targets.py`, `jobs/t4_targets.slurm`, `tests/test_targets.py`):
  - `targets.json` holds **16 curated targets**, using `point` anchors (5 patches) and `rim` anchors (8 patches):
    - 8 lunar: 7 Artemis III regions anchored on their IAU features, because no official centres are published, plus the Shackleton rim;
    - 8 Martian: Jezero, Gale, Gusev, Meridiani Planum, Utopia Planitia, Elysium/InSight, Oxia Planum and the Arcadia Planitia SWIM region.
  - `wac_percentile` is computed per patch against `runs/2242278/features_moon.parquet`, and `ice_stable_frac` from Diviner, both before averaging.
  - **k-means clustering:** `k = 30`, `seed = 42`, `log1p` on `relief_m`, `detrended_std_m` and `tri_m`, and a per-body `StandardScaler`, on `runs/2242278/features_{mars,moon}.parquet`. Each cluster is represented by the real patch closest to its centroid, named with `iau_label`.

**Verification on Yuca** (via Slurm)

- **Unit suite** (job `2242421`, `pytest -q tests`): **`31 passed` in 3.76s** (17 previous + 3 in `test_geo.py` + 3 in `test_iau.py` + 8 in `test_targets.py`).
- **Lunar smoke test** (job `2242422`, `jobs/t4_targets.slurm --k 5 --body Moon`, 17 s): `8/8` lunar curated targets `ok`, Shackleton included, and 5 clusters.
- **Full T4 run** (job `2242423`, `jobs/t4_targets.slurm`, 32 s, outputs in `/lustre/proyectos/p089/runs/2242423/`):
  - **Outputs:** **`76` targets** (`16` curated + `60` clusters) in `targets.parquet` and `targets.json`, plus `targets_patches.parquet`, `clusters_{mars,moon}.parquet`, `map_targets_mars.png` and `map_targets_moon.png`. No curated target dropped out (`0 insufficient_coverage`).
  - **Moon (`8/8 ok`):**
    - every anchor matches its `anchor.iau_feature` exactly (`d = 0.0 km`);
    - all have finite `diviner_tavg_k` (`64.9–133.3 K`), `ice_favorability`, `ice_depth_m` (`ice_stable_frac = 1.0`) and `wac_percentile`;
    - `moon-shackleton-rim` completed `8/8` patches (`mean_slope = 14.27°`, `relief = 3616 m`);
    - the 30 clusters add up to `36,741` patches (`min/median/max = 518/1040/2332`).
  - **Mars (`8/8 ok`):** all with `5/5` patches and finite `themis_day`, `themis_night` and `themis_delta`. The 30 clusters add up to `140,916` patches (`min/median/max = 494/4715/8933`).
- **Sanity review** (`plan_t4.md` §10):
  - **Mars** (global median `mean_slope_deg = 1.16°`): the five landing plains are all well below the global median. InSight is the flattest (`0.25°`, `relief = 71.6 m`), followed by Arcadia SWIM (`0.30°`, `39.1 m`), Zhurong/Utopia (`0.42°`, `126.9 m`), Spirit/Gusev (`0.49°`, `80.4 m`) and Opportunity/Meridiani (`0.54°`, `132.5 m`).
    - The strict top 3 is InSight, Arcadia SWIM and Zhurong, so Opportunity comes 5th, inside the flat block below `0.55°`.
    - Gale has `relief_m = 2793.1 m`, against `71.6 m` for InSight (`~39×`).
  - **Moon** (global median `mean_slope_deg = 6.78°`): the 8 polar targets range from `8.09°` (Mons Mouton) to `14.27°` (Shackleton rim), all above the global lunar median.
  - **Maps** (`map_targets_mars.png`, `map_targets_moon.png`): the curated targets fall in their expected regions, and Tharsis and Valles Marineris separate from the northern plains.
- **Claude's review:** accepted. The Opportunity criterion was too strict in the plan, and the result is correct. The explanation Gemini first gave (that its 16 km neighbours "touch" the rim of Victoria crater) does not hold: Victoria is ~750 m across, far too small to move a 32 km patch. The job log records commit `0e1e43c` because the job ran before the commit; the code was unchanged between the run and `115e0c3`. Rule since then: commit before running.

**What was left:** T6, T5, T7, T8 and T11.

## 2026-11-13 (night): T4 plan, Gemini 4 prompt and working without SSH

**What was done** (documents written by Claude, in a session directly on Yuca)

- **Real state on Yuca:**
  - Copernicus GLO-90 is complete: 26,475 tiles, and the failure list of job 2242198 is empty;
  - the T3 maps (`runs/2242278/`) pass the visual check: Valles Marineris, Olympus Mons, Hellas and Argyre on Mars; maria against highlands, Crisium and Orientale on the Moon.
- **[plan_t4.md](plan_t4.md),** the full T4 specification:
  - NASA publishes only the names of the 9 Artemis III regions, without coordinates, so each is anchored on the IAU feature of the same name. Rim regions are measured with 8 patches on the crater rim.
  - Nobile Rim 1 and 2 are merged into one target, and so are Mons Mouton and its plateau.
  - Landing coordinates were verified for the 8 Mars sites; `TODO(verify)` remains on Spirit, Oxia and Arcadia.
  - Support for patches that contain the pole (Shackleton) is added without changing T3.
  - k-means clusters (30 per body) are built on the T3 features.
- **[gemini_prompt.md](gemini_prompt.md)** was rewritten for Gemini 4 in Antigravity's Orchestrator (Argon) mode, which by then had access to Yuca.
  - MODE A is with SSH, MODE B without.
  - Reinforced rules: no `pytest` on the login node, and never import the v1 scripts.
- **[working_without_ssh.md](working_without_ssh.md):** the venue network blocks SSH on 14 and 15 November, but Open OnDemand (HTTPS) works; that is how the team worked on the 13th.
  - **Workflow:** Gemini works locally and pushes to GitHub; Owen runs `git pull`/`sbatch` in the OOD shell and passes the logs back.
  - **Also covered:** the checklist for that night, the offline kit, what can move forward on each side, and plan B.
  - **Offline kit:** `/lustre/proyectos/p089/kit/offline_kit_2026-11-13.tar.gz`, 88 MB, with the T3 parquet files, the IAU gazetteer, Natural Earth and the Diviner cache.
- **[handoff.md](handoff.md)** was updated and now has a queue of pending cluster commands.
- **Incident without damage:** while inspecting the gazetteer, Claude imported `enrich_nomenclature.py`, which ran and rewrote `/lustre/proyectos/p089/output/planetary_baselines.json`. The content came out identical to the repository copy.

**What was left**

- Gemini implements T4 from `plan_t4.md`, and it runs on Yuca, ideally the same night.
- Download the offline kit to the laptop and set up the local environment for the tests.
- Detailed plans for T6, T5 and T7/T8 (Claude).

## 2026-11-13: T10, first app skeleton (branch `feat/app-t10-esqueleto`)

**What was done** (code written by Claude, from the mockup published as an artifact)

- **`app/`:** React 18, Vite 5, TypeScript and Tailwind 4, with an English interface. Sections:
  - a Mars / Moon selector;
  - a thesis with figures;
  - the explorer: mission presets, weight sliders, minimum MSI, dual maps and ranking;
  - the site card: target-vs-Earth table with match / no match, a 4-dimension radar, suggested use, and "Where the analogy breaks";
  - methodology with the sources.
- **MSI in the browser:** recomputed as `MSI = Σ w·S / Σ w`, only over the dimensions that have a `sub_score` (`app/src/lib/msi.ts`). Environment and thermal are shown as disabled, labelled with the task that brings them (T5/T6, T7).
- **Maps:** Leaflet for all three bodies.
  - Mars with Trek's MOLA, and the Moon with Trek's LROC WAC, both in EPSG:4326; Earth with GIBS Blue Marble in Web Mercator.
  - The plan asked for MapLibre for Earth; Leaflet was kept so the skeleton has a single library. For the same reason the radar is drawn in custom SVG instead of Recharts.
- **Sample data:** `tools/v1_to_sample.py` converts `output/analogs.json` (v1) to the v2 schema of section 5, and writes `app/public/data/sample.json` (80 targets, 400 analogs, 260 KB).
  - **The `sub_scores` are provisional:** an RBF kernel per feature, with σ = 35 % of the target's value and an absolute minimum (1.5° and 2.5° for the slopes, 30 m and 25 m for the elevation σ and TRI).
  - **`mismatches`** flags features more than 1.5 σ away (the standard deviation of the set, per body): 67 of the 400 analogs have at least one.
  - **Presets and physical limits** have provisional English text, which T11 replaces.
- **Design:** tokens in `app/src/index.css` (one layer of CSS variables; light and dark themes through `prefers-color-scheme`; a rust accent for Mars and blue-grey for the Moon).
- **Verified:**
  - `npm run build` passes without errors.
  - In the browser, the Trek and GIBS tiles load with no console errors, and the preset, the body switch and the target/analog selection all update the ranking, the maps and the card.
  - There is no horizontal scroll at 320 or 414 px.
  - Design-kit gates: no emoji, no hard-coded values, no native `<select>`.
  - AA contrast was measured on the token pairs of both themes; the light `--faint` was darkened to `#5c6370` because it failed on `--surface-2`.
  - The kit's render gates were not run, because they expect a standalone HTML file and the app needs a server to read the JSON.
- **Dev setup:** `.claude/launch.json` with the `app` configuration (port 5173), to start it from Claude Code.

**What was left**

- Connect the real `analogs_universe.json` once T8 exists (changing `DATA_URL` in `app/src/App.tsx` is enough).
- A "Compare" view for two sites, card export (JSON / Markdown) and a print view.
- A "new candidates only" filter and the logistics priority (λ), once T6 brings `dist_road_km`.
- A notice and a polar view for the lunar south pole (the equirectangular projection distorts heavily).
- Measure the 50 ms slider criterion, and review the app at 1366 × 768 and on a projector.

To run it: `cd app && npm install && npm run dev`.

## 2026-11-13: T1/T3 — `scales`/`offsets` in `geo.py`, WAC by lunar percentile and raster metadata

**What was done** (code written by Gemini)

- **First T3 test run recorded** (`--limit 500`, job `2242227`, 1 min 18 s):
  - Mars: `498/500` valid (`mean_slope_deg` median `1.08°`, p95 `4.63°`, max `17.15°`);
  - Diviner PRP cached (`2,880,000` triangles in `data/derived/diviner_prp_south.parquet`);
  - Moon: `494/500` valid (`mean_slope_deg` median `13.24°`, p95 `21.50°`, max `27.68°`).
- **LOLA and the full scale table, confirmed on Yuca** (`docs/pipeline.md`):
  - **LOLA:** `Lunar_LRO_LOLA_Global_LDEM_118m.tif` is `int16` with `scales=(0.5,)`, `offsets=(0.0,)` and `nodata=-32768`. Because `scale=0.5` was not applied, **both v1 and the first test `2242227` had every lunar vertical metric doubled** (`mean_elev_m`, `relief_m`, `roughness_std_m`, `tri` and `tan(slope)`). The earlier note about the v1 elevation range is withdrawn.
  - **Only LOLA and WAC** have a scale other than `(1.0, 0.0)` among all the mosaics checked on Yuca. LOLA has `scale=0.5`, `offset=0.0`; LROC WAC is `uint8` with `scale=1.00395`, `offset=-0.00395`, `nodata=0`.
  - **WAC** gives relative brightness (`≈ 1–256`), not absolute physical reflectance, so it must be compared by percentile within the Moon.
  - **The ice index:** `Moon_IceFavorabilityIndex_{90N,90S}000E_591mp.tif` is `float32` with `nodata=-3.4e38`.
- **`pipeline/geo.py`** (`extract_patch` and `_clean_nodata`):
  - reads with `out_dtype="float32"`, including the `out_shape` branch;
  - filters non-finite values and `|z| > 1e5` sentinels first, which avoids `float32` overflow with `nodata=-3.4e38`;
  - masks `src.nodata`;
  - applies `src.scales[0]` / `src.offsets[0]` before reprojecting.
- **`pipeline/features.py`:** `np.gradient(z_clean, res, res)` is now explicit for both axes.
- **`pipeline/planet_features.py`:**
  - `_log_raster_meta` prints, at the start, the `dtype`, `nodata`, `scales`, `offsets` and `res` of every raster used (`DEM`, `themis_day`, `themis_night`, `wac_reflectance`, `ice_south`, `ice_north`);
  - a summary (`min`, median, `p95`, `max`) of `mean_slope_deg`, `relief_m`, `mean_elev_m` and `wac_reflectance`;
  - `compute_lunar_wac_percentile`, which turns WAC brightness into a `[0, 1]` percentile within the Moon.
- **Tests** in `tests/test_geo.py` and `tests/test_planet_features.py`:
  - scaled `int16` (`scale=0.5`, `offset=100.0`, `nodata=-32768`);
  - scaled `uint8` WAC at `100 m/px`;
  - filtering `nodata=-3.4e38` without warnings;
  - `compute_lunar_wac_percentile`.
- **Verification on Yuca** (commit `bcf10de`):
  - `pytest -q tests` (`tests_v2`): **`17 passed` in 3.30s** in `spaceapps_2026`.
  - **`--limit 500` test AFTER the fix** (job `2242231_0`, 22 s on `amdcpu-hpc-23`), compared with job `2242227` (BEFORE, same set of `494/500` valid lunar patches):

    | Moon metric | Min | Median | p95 | Max |
    | --- | --- | --- | --- | --- |
    | `mean_slope_deg` | `0.33° -> 0.17°` | `13.24° -> 6.93°` | `21.50° -> 11.51°` | `27.68° -> 16.04°` |
    | `relief_m` (exactly half) | `67.92 -> 33.96 m` | `3229.80 -> 1614.90 m` | `7460.09 -> 3730.05 m` | `11210.04 -> 5605.02 m` |
    | `mean_elev_m` (exactly half, now inside the physical lunar range of `-9.1` to `+10.8 km`) | `-10630.40 -> -5315.20 m` | `-1424.61 -> -712.31 m` | `8225.56 -> 4112.78 m` | `14751.13 -> 7375.57 m` |

    - `wac_reflectance` (Moon; relative `uint8` brightness with `scale=1.00395, offset=-0.00395, nodata=0`): min `1.00`, median `67.26`, p95 `93.85`, max `136.71` (`n=494`).
    - `ice_south` / `ice_north` (`float32`, `nodata=-3.4028226550889045e+38`): read without warnings, and polar Diviner coverage on 5 patches of the `--limit 500` sample.
    - Mars in `2242231_0` (`498/500` valid, `scale=1.0`):

      | Mars metric | Min | Median | p95 | Max |
      | --- | --- | --- | --- | --- |
      | `mean_slope_deg` | `0.04°` | `1.08°` | `4.63°` | `17.15°` |
      | `relief_m` | `6.04 m` | `239.32 m` | `1476.28 m` | `5310.49 m` |
      | `mean_elev_m` | `-6864.79 m` | `-282.06 m` | `4256.35 m` | `9031.45 m` |

  - **Full global T3 run** (jobs `2242278` `0..15` + merge `2242279`):
    - Mars: 16 stripes -> **`140,916` valid patches** (of `141,472`, `99.61 %`; meets `~141k ± 10 %`) in `/lustre/proyectos/p089/runs/2242278/features_mars.parquet`, with the map `/lustre/proyectos/p089/runs/2242278/map_mars_mean_slope_deg.png`.
    - Moon: 16 stripes -> **`36,741` valid patches** (of `37,014`, `99.26 %`; meets `~37k ± 10 %`) in `/lustre/proyectos/p089/runs/2242278/features_moon.parquet`, with the map `/lustre/proyectos/p089/runs/2242278/map_moon_mean_slope_deg.png`.

**What was left**

- A quick visual check of `map_mars_mean_slope_deg.png` and `map_moon_mean_slope_deg.png` in `runs/2242278/` (Valles Marineris and Olympus Mons on Mars; highlands against maria on the Moon). Claude did it later the same day: passed.
- Implement **T4** (`pipeline/targets.py` + `pipeline/data/targets.json` + tests): curated targets (Artemis III + Shackleton, Mars landing sites with verified coordinates) and 30 clusters per body on the T3 parquet files (`2242278`); then T6, T5, T7 and T8.

## 2026-11-13: T3 — global Mars and Moon sweep (`pipeline/planet_features.py`)

**What was done** (code written by Gemini)

- **T1 + T2 suite on Yuca:** passed (job `2242225`, `spaceapps_2026`: `9 passed in 1.16s`).
- **Configuration:** `pipeline/config.py` and `pipeline/requirements.txt` updated (`matplotlib>=3.7`, planetary raster and Diviner PRP paths).
- **`pipeline/planet_features.py` and `jobs/t3_planet_features.slurm`:**
  - a global `32 km` grid (`-88°` to `88°`; ~141k centres on Mars and ~37k on the Moon);
  - parallel extraction by stripes (`--array=0-15`, `8 CPUs`);
  - auxiliary layers: `themis_day`, `themis_night` and `themis_delta` on Mars; `wac_reflectance` and polar `ice_favorability` on the Moon;
  - Diviner: `dlre_prp_south.tab` is read and cached into `data/derived/diviner_prp_south.parquet`, then queried per polar patch with a `cKDTree` for `diviner_tmax_k`, `diviner_tavg_k` and `ice_depth_m`, ignoring `-999`;
  - `--limit` for tests, and `--merge` to combine the stripes and draw `mean_slope_deg` scatter maps.
- **Tests:** synthetic unit tests in `tests/test_planet_features.py` (`14 passed` in total, locally).

**What was left**

- Run T3 on Yuca, first in test mode (`--limit 500`), review the log and PNG, then the full array (`0-15`) + `--merge`.
- Continue with T4 (`pipeline/targets.py` + `pipeline/data/targets.json`) and T5–T11.

## 2026-11-13: Diviner download

- **Where it is:** the Diviner Polar Resource Product was found in the PDS4 bundle `lro_diviner_derived1`, collection `data_derived_prp`. Yuca can reach PDS Geosciences; the laptop cannot.
- **New `jobs/download_diviner.slurm`:** downloads `dlre_prp_south.tab` (604,800,210 bytes), `.lbl` and `.xml` into `data/raw/moon/diviner/`. The north pole file (same size) is not downloaded, because the targets are in the south.
- **Downloaded and verified on Yuca:** the `.tab` is exactly 604,800,210 bytes, with no `.aria2`. It was submitted twice by mistake, but the second job (2242221) only found the files already complete.
- **Real format** (CSV with a header):
  - `tri1_x..tri3_z`: mesh vertices, in km;
  - `tri_clon`, `tri_clat`: triangle centre, in degrees;
  - `tri_calt`;
  - `temp_avg` and `temp_max`: in K;
  - `ice_depth`: in m; `-999` means no stable ice.

  The mesh is a square centred on the pole, so at its corners it reaches ~75.9°S.

## 2026-11-13: dataset explorer

- **The tool:** Claude wrote `tools/explore_datasets.py` and `jobs/explore_datasets.slurm`. They build a self-contained HTML report with:
  - for every raster: a thumbnail, metadata (CRS, resolution, nodata, body radius), statistics, a histogram and the values at known sites;
  - coverage and validation of the Copernicus tiles (each tile is opened);
  - MODIS NDVI and temperature maps;
  - roads, airports and countries;
  - the IAU nomenclature.

  It also writes `resumen.md` and `resumen.json`.
- **Dependencies:** only numpy, rasterio and pyproj; the images are generated without matplotlib. MODIS is read with GDAL or, if it has no HDF4, with pyhdf (the job installs it if missing).
- **Tested** on the laptop with synthetic data (equirectangular rasters, valid tiles plus a broken one, a shapefile and a dbf). It still had to be run on Yuca with the real data.

## 2026-11-13: checking the downloaded mosaics (job 2242198)

- THEMIS IR Night 60N-60S: 15,179,427,309 bytes, the same as on S3, with no `.aria2`.
- LROC WAC 100 m: 5,959,263,751 bytes, the same as on S3, with no `.aria2`.
- Ice favorability index, both poles: 4,003,661 bytes each.
- Copernicus: still downloading (17,293 tiles at 18:06, then in Antarctica); the end of the log and the failure list still had to be checked. Later the same day: complete, 26,475 tiles and 0 failures.

## 2026-11-13: T2 — patch terrain features (`pipeline/features.py`)

**What was done** (code written by Gemini)

- **`compute_features`** (alias `extract_features`) in `pipeline/features.py`, for `64 × 64` patches at `500 m/px`. It fills any remaining `NaN` with the patch median, and returns 7 features as `float32`:
  - `mean_slope_deg`, `p90_slope_deg`;
  - `relief_m`, `hypsometric_integral`;
  - `detrended_std_m`;
  - `tri_m` (Riley's TRI over 8 neighbours on interior pixels);
  - `mean_elev_m`.
- **Synthetic tests** in `tests/test_features.py`: a 10° tilted plane, a horizontal plane, a synthetic cone with hypsometric integral ≈ 1/3, `NaN` filling, and `float32` types.
- **Local check:** the full suite passed, 9/9 with `pytest -q tests`.

**What was left**

- Install `pipeline/requirements.txt` if anything is missing in the `spaceapps_2026` environment on Yuca, and run `pytest -q tests` there.
- Next tasks: T3 (`pipeline/planet_features.py` + `jobs/t3_planet_features.slurm`) and T4 (`pipeline/targets.py` + `pipeline/data/targets.json`), and finish the T0 downloads.

## 2026-11-13: T1 — distortion-free patch extraction (`pipeline/geo.py`)

**What was done** (code written by Gemini)

- **Package base:** `pipeline/` was created (`__init__.py`, `config.py`, `requirements.txt`).
- **`extract_patch`** in `pipeline/geo.py`. It extracts `32 × 32 km` patches at `500 m/px` (`64 × 64 px`) in a local AEQD projection centred on `(lat, lon)`, and:
  - checks the body radius (`WGS84` for Earth, `1737400 m` for the Moon, `3396190 m` for Mars);
  - reduces the read with `out_shape` on fine rasters;
  - skips and counts patches crossing `±180°`;
  - turns `nodata` and `|z| > 1e5` into `NaN`;
  - requires at least 90 % valid pixels.
- **Synthetic tests** in `tests/__init__.py` and `tests/test_geo.py`: 5/5 pass with `pytest`. They cover:
  - slope invariance between lat 0° and 70° on the Moon;
  - a seam between tiles in an Earth VRT, with no holes;
  - dropping ocean/nodata;
  - antimeridian crossing;
  - radius validation.

**What was left**

- T2 (`pipeline/features.py` + `tests/test_features.py`) and tasks T3–T11.
- Run `pytest -q tests` on Yuca and check the T0 download coverage.

## 2026-11-13: missing data

- Gemini started on the plan.
- `ne_10m_admin_0_countries` (Natural Earth, 5 MB) was added to `run_download_extra.slurm`, to fill in each analog's country. The job has to be resubmitted; files already downloaded are skipped.
- **Still pending:** finish Copernicus (job 2242198) and check the sizes, and Diviner PRP (manual).

## 2026-11-13: working prompt for Gemini

- Claude wrote [gemini_prompt.md](gemini_prompt.md): instructions for Gemini to implement the plan task by task. It covers:
  - what to read first;
  - the commit and logbook rules;
  - the Yuca rules;
  - the answer format;
  - the suggested order of sessions.

## 2026-11-13: downloads submitted on Yuca

- **Clone:** the repository was cloned into `/lustre/proyectos/p089/code`, and jobs are submitted from there. The old copies of the scripts in the root of `p089/` are no longer used.
- **Earthdata credentials:** the `~/.netrc` was created on Yuca by hand, by Owen.
- **Jobs submitted:** `2242198` (`run_download_missing.slurm`) and `2242199` (`run_download_extra.slurm`).
  - `2242199` downloaded Natural Earth, but MODIS failed because of invalid Earthdata credentials.
  - After the `.netrc` was fixed, `2242203` downloaded all of MODIS: 12 MOD13C2 files (NDVI) in `data/raw/earth/modis/ndvi` and 12 MOD11C3 files (LST) in `data/raw/earth/modis/lst`, all from 2023.
  - `2242194` was a duplicate submission of `run_download_missing.slurm` (17:49) that ran for a few minutes alongside `2242198`; it was cancelled.
- **Pending:** two downloads wrote at the same time, so at the end check that:
  - the mosaics have the S3 sizes (THEMIS Night 15,179,427,309 bytes, WAC 5,959,263,751 bytes);
  - no `.aria2` files are left next to them;
  - every Copernicus tile opens with rasterio (T5 does this when it logs failing tiles).

## 2026-11-13: v2 implementation plan and official resources

**What was done**

- **The challenge's Resources tab was reviewed.** PDS, LRO (LOLA, LROC WAC) and Copernicus were already in use. Diviner (polar temperatures) and NASA Earthdata (MODIS) were missing. CSA RADARSAT, the ESA Open Science Catalog and JAXA G-Portal are out of scope.
- **[implementation_plan.md](implementation_plan.md):** Claude wrote tasks T0–T11 with files, formulas, acceptance criteria, the v2 JSON contract and a timeline. Gemini implements the code from that plan.
- **Key decisions of the plan:**
  - 32 × 32 km patches at 500 m/px, in a local AEQD projection, for all three bodies;
  - a MODIS NDVI mask;
  - curated targets (Artemis III, Mars landing sites) plus clusters;
  - an RBF score per dimension;
  - a known-analog label.
- **New job `run_download_extra.slurm`** with `download_earthdata.py`: Natural Earth (roads, airports), and MODIS NDVI (MOD13C2) and LST (MOD11C3) for 2023, through `earthaccess`.
- **App base layers:** the NASA GIBS (Earth) and NASA Trek (Moon and Mars) tile URLs were verified.

**Pending**

- The Diviner Polar Resource Product (`LRO-L-DLRE-5-PRP-V2.0`): its exact URL could not be verified from the laptop's network; download it by hand.
- Create an Earthdata account and a `~/.netrc` on Yuca before submitting `run_download_extra.slurm`.

## 2026-11-13: job to re-download what was missing

**What was done**

- **The USGS bucket** (`asc-pds-services`, prefix `mosaic/`) was checked for the real file names:
  - THEMIS Night only exists as `Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif` (15.2 GB, 60°N–60°S). That is why the global URL returned 404.
  - For the Moon, `Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif` (6.0 GB, a real reflectance mosaic) was chosen instead of the ClrShade.
  - `Moon_IceFavorabilityIndex_{90S,90N}000E_591mp.tif` (~4 MB each) was added; it is useful for a permanent base at the pole.
- **New job `run_download_missing.slurm`:**
  - downloads the files above;
  - resumes Copernicus GLO-90 with the list cleaned of `\r`;
  - saves the failures to `copernicus_90m_fallidos_<job>.txt`;
  - checks counts and quota at the end.

  It runs with `sbatch`, not with `nohup` on the login node.
- **`process_analogs.py`** now reads THEMIS Night and WAC with their new names (`wac_reflectance` replaces `lola_albedo_shade`).

**Pending**

- SSH to Yuca was blocked from the network in use at the time, so the job was ready but had not run.
- The `p089` quota was checked: 78.9 GB used of 18.63 TB (15,839 files). There is plenty of room for the ~75–80 GB estimated.
- After the download, move to `_to_delete/` the `Lunar_LRO_LOLA_Albedo_Global_128ppd.tif` (it is ClrShade) and the failed attempt `Mars_ODY_THEMIS_IR_Night_Mosaic_100m.tif`, if it is still there.

## 2026-11-13: value proposition

- **The document:** Claude drafted [value_proposition.md](value_proposition.md) for the pitch and video team. It covers:
  - the problem and the value proposition;
  - what the project adds to what NASA asks;
  - the differentiators against other teams;
  - Mexican candidates from the prototype.
- **Limits:** it lists what must not be claimed yet, because of the prototype's limitations.
- **A hypothesis:** the differentiator against other teams cannot be checked, since their projects are not visible before submission.
- **Shared copy:** the same content was uploaded to a Claude doc for the team, [Propuesta de valor: Planetary Analog Finder](https://claude.ai/artifact/563rMStp47364hAEc9pCmV). It stays private until it is shared.

## 2026-11-13: review of the prototype and the repository

**What was done**

- The scripts, logs and `output.zip` (without the rasters) were downloaded from Yuca.
- Claude reviewed the scripts, logs and outputs.
- The folder was organised: logs in `logs/`, output JSON in `output/`, documentation in `docs/`.
- The GitHub repository was created (private), and the team was invited with write access: Javier033x, FernyBoy, EmiB-05, FlorMMF and verdielias.

**State of the prototype**

The pipeline runs end to end: the Mars and Moon DEMs, then 40 archetypes per body with IAU names, then the top 5 terrestrial analogs. `output/analogs.json` can already feed the app.

**Points to improve, by priority**

1. **Scale.** The windows are ~118 km on Mars (256 px × 463 m), ~30 km on the Moon (256 × 118 m) and ~46 km on Earth (512 × 90 m). Slope and roughness depend on resolution, so everything must be resampled to a common resolution, with windows of the same extent in km.
2. **Arid mask.** There is no vegetation filter (`masks/` is empty), so many lunar analogs land in the Himalaya, Tibet and the Colombian Andes.
3. **Lunar layer.** The file called "Albedo" was downloaded from the `ClrShade` URL (colour-shaded relief). The URL must point to a real albedo or roughness layer.
4. **Earth coverage.** Only 6,983 of 26,475 tiles, so the analogs fall between 0.4° and 45.8° N. The overnight download stopped, and 976 tiles failed because of a `\r` in the URLs, which is already fixed in the script.
5. **THEMIS Night.** The `..._v14.tif` URL returns 404; the right one is still to be found.
6. **Targets.** The k-means is global; the challenge's real targets (lunar south pole / Artemis, Mars landing sites) are missing.
7. **Score.** Move from `100/(1+0.35d)` to the master plan's RBF with a σ per dimension.
8. **Minor:**
   - `tri` is really the absolute deviation from the median;
   - `themis_ir_day` holds raw values;
   - lunar IAU labels are often satellite craters;
   - `analyze_earth_tile` ignores errors silently.

## 2026-11-12: downloads and first runs on Yuca

- Download of MOLA, THEMIS Day and LOLA LDEM (`logs/descargas/download.log`).
- Overnight Copernicus GLO-90 download; it stopped halfway (`logs/descargas/night_download.log`).
- Clustering runs (jobs 2241770, 2241771, 2241773) and matching runs (2241781, 2241782, 2241783). Details in [pipeline.md](pipeline.md).

## Before 12 November

- The team's ideas and their evaluation: [ideas.md](ideas.md).
- Master plan: [master_plan.md](master_plan.md).

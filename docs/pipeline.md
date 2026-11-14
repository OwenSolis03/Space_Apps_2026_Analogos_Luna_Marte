# Pipeline: data, scales and runs

How the pipeline that runs on Yuca (project `p089`) works today. This document describes the real state of the code, data and runs, not the master plan. The reasoning behind each design decision is in [HISTORY.md](HISTORY.md).

## Flow

### v2 (`pipeline/`)

```text
T3: pipeline/planet_features.py ─► runs/2242278/features_{mars,moon}.parquet
                                          │
T4: pipeline/targets.py + targets.json ───┴─► runs/2242423/targets.parquet (16 curated + 60 clusters)

T6: pipeline/earth_layers.py + known_analogs.json ─► data/derived/{ndvi_max_2023,lst_2023}.tif (checks: runs/2242430/)
                                          │
T5: pipeline/earth_features.py ───────────┴─► runs/2242438/features_earth.parquet (40,244 valid patches; smoke: runs/2242432/)
                                          │
T14: pipeline/geology.py + overrides ────────► runs/2242486/geology_{earth,moon,mars,targets}.parquet (overrides applied)
T13: pipeline/dust.py ───────────────────────► runs/2242484/dust_{earth,mars,targets}.parquet + 4 PNGs
T12: pipeline/ice.py + ice_hints.json ───────► runs/2242487/ice_{earth,targets}.parquet (uses T14_DIR=runs/2242486)
                                          │
T7/T8/T15/T16: match.py, export.py ───┴─► runs/2242506/analogs_universe.json (6.35 MB, 7 dims, 5 presets, missing-data policy)
```

**Run directories:** each run writes to a new `runs/<jobid>/`. The one exception is T5: its three stages (prepare, array, merge) share the directory of the prepare job (e.g., jobs `2242438`–`2242440` write into `runs/2242438/`, `plan_t5.md` §2).

### v1 prototype (repo root, kept as reference)

```text
setup_and_download.sh ──┐
download_full_night.sh ─┴─> /lustre/proyectos/p089/data/raw/{moon,mars,earth}
                                   │
            run_clustering.slurm ──┤  process_analogs.py
                                   ▼
                    output/planetary_baselines.json   (40 archetypes per body)
                                   │
                                   │  enrich_nomenclature.py  (IAU names)
                                   ▼
                    output/planetary_baselines.json   (with iau_nomenclature)
                                   │
        run_earth_matching.slurm ──┤  match_earth_analogs.py
                                   ▼
                    output/analogs.json               (top-5 Earth analogs per archetype)
```

## Data

Paths on Yuca, under `/lustre/proyectos/p089/data/raw/`.

| Body | File | Source | Status |
| --- | --- | --- | --- |
| Mars | `mars/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif` (2 GB) | USGS Astrogeology | OK |
| Mars | `mars/Mars_ODY_THEMIS_IR_Day_Mosaic_100m.tif` (22 GB) | USGS Astrogeology | OK |
| Mars | `mars/Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif` (15.2 GB) | USGS Astrogeology | OK (checked in job 2242231) |
| Moon | `moon/Lunar_LRO_LOLA_Global_LDEM_118m.tif` (8 GB) | USGS Astrogeology | OK |
| Moon | `moon/Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif` (6.0 GB) | USGS Astrogeology | OK (checked in job 2242231) |
| Moon | `moon/Moon_IceFavorabilityIndex_{90S,90N}000E_591mp.tif` | USGS Astrogeology | OK (checked in job 2242231) |
| Moon | `moon/Lunar_LRO_LOLA_Albedo_Global_128ppd.tif` | USGS Astrogeology | Obsolete: it is actually the colour-shaded relief; not used |
| Moon | `moon/diviner/dlre_prp_south.{tab,lbl,xml}` (577 MB, ASCII triangular mesh, 80–90°S) | NASA PDS Geosciences (LRO Diviner PRP) | OK (`jobs/download_diviner.slurm`) |
| Earth | `earth/copernicus_90m/*.tif` | Copernicus GLO-90 (AWS, unsigned) | Complete: 26,475 tiles (checked 2026-11-13) |
| Earth | `earth/modis/ndvi/*.hdf` (MOD13C2 v061, 12 months of 2023) | NASA Earthdata (LP DAAC) | OK (cache in `data/derived/ndvi_max_2023.tif`) |
| Earth | `earth/modis/lst/*.hdf` (MOD11C3 v061, 12 months of 2023) | NASA Earthdata (LP DAAC) | OK (cache in `data/derived/lst_2023.tif`) |
| Earth | `earth/naturalearth/ne_10m_{roads,airports,admin_0_countries}` | Natural Earth | OK (1,650,450 road vertices after densifying to 0.02°) |
| Earth | `geology/earth_glim/glim_wgs84_0point5deg.txt.asc` (1.2 MB) | GLiM 0.5° (Hartmann & Moosdorf 2012, PANGAEA) | OK (`2242481`) |
| Mars | `geology/mars_sim3292/SIM3292_MarsGlobalGeologicGIS_20M/` (`SIM3292_geodatabase.gdb`) | USGS SIM 3292 1:20M (Tanaka et al. 2014) | OK (`2242481`, `1,311` polygons, `44` units) |
| Moon | `geology/moon_unified/Unified_Geologic_Map_of_the_Moon_GIS/Lunar_GIS/Shapefiles/GeoUnits.shp` + `DOMU_descriptions.csv` | USGS Unified Geologic Map v2 1:5M (Fortezzo et al. 2020) | OK (`2242481`, `12,247` polygons, `49` units; `.gdb` skipped due to ESRI CDF) |
| Mars | `mars/dust_montabone/dustscenario_MY{24..36}_v2-*.nc` (13 files, ~58 MB each) | Montabone et al. 2015/2020 kriged CDOD v2 | OK (`2242481`, NetCDF3 `scipy`) |
| Earth | `earth/modis/aod/MOD08_M3.A{2019..2023}*.hdf` (60 granules) | NASA Earthdata (LAADS CMR v6.1 via `earthaccess`) | OK (`2242481`) |
| Moon, Mars | `nomenclature/MARS*.dbf`, `nomenclature/MOON*.dbf` | USGS/IAU Gazetteer | OK (download not recorded in the scripts) |

**Derived files** in `/lustre/proyectos/p089/data/derived/`:

| File | Size | Content |
| --- | --- | --- |
| `diviner_prp_south.parquet` | 61 MB | Diviner PRP south cache |
| `ndvi_max_2023.tif` | 18 MB | 2 float32 bands: `ndvi_max`, `n_months` |
| `lst_2023.tif` | 56 MB | 3 float32 bands: `lst_day_c`, `lst_night_c`, `lst_amplitude_c` |
| `copernicus_90m.vrt` | 13 MB | `432004×208800` mosaic of 26,475 Copernicus tiles (`-srcnodata 0 -vrtnodata -9999`, T5) |

**The GDAL build in `spaceapps_2026` has no HDF4 driver**, so the original MODIS `.hdf` files are read with `pyhdf`. Rasters are not committed to the repository (see `.gitignore`).

### Type, scale and nodata of every file

Checked on Yuca on 2026-11-13 with rasterio. **Always apply `value = raw · scale + offset`**, because `rasterio.read()` does not do it.

| File | dtype | scale | offset | nodata | Note |
| --- | --- | --- | --- | --- | --- |
| `Mars_MGS_MOLA_DEM_mosaic_global_463m.tif` | int16 | 1.0 | 0.0 | −32768 | Metres |
| `Mars_ODY_THEMIS_IR_Day_Mosaic_100m.tif` | uint8 | 1.0 | 0.0 | 0 | Grey level, not kelvin |
| `Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif` | uint8 | 1.0 | 0.0 | 0 | Grey level, not kelvin |
| `Lunar_LRO_LOLA_Global_LDEM_118m.tif` | int16 | **0.5** | 0.0 | −32768 | **Half-metres.** v1 did not apply the scale, so every lunar vertical metric came out doubled |
| `Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif` | uint8 | 1.00395 | −0.00395 | 0 | Relative brightness (≈ 1–256), not absolute reflectance; compared by percentile within the Moon |
| `Moon_IceFavorabilityIndex_{90N,90S}000E_591mp.tif` | float32 | 1.0 | 0.0 | −3.4e38 | Filter the huge nodata value |
| `Lunar_LRO_LOLA_Albedo_Global_128ppd.tif` | uint8 × 3 | 1.0 | 0.0 | 0 | Obsolete (colour-shaded RGB); move to `_to_delete/` |
| `MOD13C2.A2023*.hdf` (`CMG 0.05 Deg Monthly NDVI`) | int16 | **÷ 10000** | 0.0 | −3000 | **Opposite MODIS VI convention:** divide by 10000, do not multiply. `valid_range = [-2000, 10000]`; values below −0.3 become NaN. No data south of 59.45°S (Antarctica missing). Read with `pyhdf` |
| `MOD11C3.A2023*.hdf` (`LST_Day_CMG`, `LST_Night_CMG`) | uint16 | **× 0.02** | −273.15 (to °C) | 0 | **Here it is multiplied:** `°C = raw × 0.02 − 273.15` (`valid_range = [7500, 65535]`, at least 3 valid months). Covers Antarctica. Read with `pyhdf` |
| `MOD08_M3.A2019..2023*.hdf` (`Deep_Blue_Aerosol_Optical_Depth_550_Land_Mean_Mean`) | int16 | **× 0.001** (`0.0010000000474974513`) | 0.0 | −9999 | `(raw − add_offset) × scale_factor`, `valid_range = [0, 5000]`. Grid 180 × 360 (`89.5°N` to `-89.5°S`, `-179.5°W` to `179.5°E`); no retrievals over snow/ice (NaN). Read with `pyhdf` |
| `dustscenario_MY{24..36}_v2-*.nc` (`cdod610`, `Ls`, `Time`) | float32 | 1.0 (`cdod610`) | 0.0 | — | NetCDF3 classic read via `xarray` `engine="scipy"`; `cdod610` is IR absorption CDOD normalized to 610 Pa (`units='Pa/Pa'`), grid 669 × 60 × 120 (`88.5` to `-88.5`, `-180` to `177`) |
| `glim_wgs84_0point5deg.txt.asc` | int (`1..16`) | — | — | −9999 | ESRI ASCII 720 × 360 (`0.5°`); coastline cells mapped from `wb` via valid 3×3 neighborhood |
| Copernicus GLO-90 tiles | float32 | 1.0 | 0.0 | **none** | **Sea inside coastal tiles is exactly 0.0.** Tile width shrinks with latitude (1200 px below 50°, down to 120 px above 85°). The VRT treats 0 as nodata |

## v1 scripts

### `process_analogs.py`

- Walks each body's DEM in 256-px windows and keeps up to 4,500 spaced windows.
- Drops windows with less than 80 % valid pixels.
- Per window: mean elevation, standard deviation (roughness), mean slope, p90 slope, and mean absolute deviation from the median (called `tri`).
- Samples auxiliary layers (THEMIS, the lunar layer) with the median of a 32 × 32 window.
- Normalises with `StandardScaler`, clusters with `MiniBatchKMeans` (40 clusters) and keeps the window nearest each centroid as the archetype.

### `enrich_nomenclature.py`

Assigns each archetype the nearest IAU feature and the nearest major feature (≥ 30 km), with haversine distance on the body radius. Reads the `.dbf` files without external dependencies.

**Do not import it:** it has no `__main__` guard and rewrites `output/planetary_baselines.json`. Its logic lives in `pipeline/iau.py` for v2.

### `match_earth_analogs.py`

- Walks the Copernicus tiles in 512-px windows, in parallel (32 processes).
- Drops windows with < 85 % valid pixels, with > 30 % of pixels near 0 m (sea), or nearly flat.
- Compares each archetype against every Earth window with Euclidean distance over 4 normalised features: roughness, mean slope, p90 slope and `tri`. Elevation is not used.
- Keeps the best 5, at least 150 km apart.
- Score: `100 / (1 + 0.35 · d)`.

## Recorded runs

Logs in `/lustre/proyectos/p089/output/` (v2) and `logs/slurm/` (v1).

| Job | Script | Result |
| --- | --- | --- |
| 2241770 | v1 clustering | First test, no counts |
| 2241771 | v1 clustering | 4,000 windows per body, 40 archetypes |
| 2241773 | v1 clustering | 4,500 windows per body, with auxiliary layers (final v1) |
| 2241781 | v1 matching | 3,643 tiles, 66,215 sites |
| 2241782 | v1 matching | 5,175 tiles, 98,465 sites |
| 2241783 | v1 matching | 6,983 tiles, 21,906 sites (final v1, with sea and flatness filters) |
| 2242227 | `jobs/t3_planet_features.slurm --limit 500` | First v2 test; revealed the LOLA half-metre scale (lunar relief doubled) |
| 2242231 | `jobs/t3_planet_features.slurm --limit 500` | v2 test with LOLA `scale = 0.5` and WAC uint8: Mars 498/500, Moon 494/500 |
| 2242278 / 2242279 | `jobs/t3_planet_features.slurm` (array 0–15 + `--merge`) | T3 global sweep: 140,916 Mars patches and 36,741 Moon patches |
| 2242421 | `pytest -q tests` | v2 tests (T1–T4): 31 passed |
| 2242422 | `jobs/t4_targets.slurm --k 5 --body Moon` | T4 lunar smoke test: 8/8 curated ok (Shackleton included), 5 clusters |
| 2242423 | `jobs/t4_targets.slurm` | T4 full run: 76 targets (16 curated, 60 clusters) |
| 2242425 | `pytest -q tests` | v2 tests (T1–T4, T6): 42 passed |
| 2242426 | `jobs/t6_earth_layers.slurm` | T6 cache build; 6/8 hard and 5/5 soft checks before fixing #2 and #8 (`plan_t6.md` §6.2.1) |
| 2242430 | `jobs/t6_earth_layers.slurm` | T6 checks (commit `84888cd`): 8/8 hard, 5/5 soft, 3 maps; sampling 10k points takes 1.2 s |
| 2242431 | `pytest -q tests` | v2 tests (T1–T6): 49 passed |
| 2242432–2242434 | `bash jobs/t5_submit.sh --limit 500` | T5 smoke test: 44,375 candidates worldwide, 445/500 valid, 5/5 hard checks |
| 2242438–2242440 | `bash jobs/t5_submit.sh` | T5 full 32-stripe sweep (commit `52bf3d7`): 44,375 candidates, 40,244 valid patches (90.69 %), 6/6 hard and 4/5 soft checks, control maps in `runs/2242438/` |
| 2242472 | `pytest -q tests` | v2 tests (T1–T8): 61 passed |
| 2242473 | `sbatch --export=ALL,T5_DIR=runs/2242432 jobs/t7_match.slurm` | T7/T8 smoke run (445 Earth rows): 3,342 pairs, `analogs_universe.json` (2.99 MB), 5/5 hard checks |
| 2242474 | `sbatch --export=ALL,T5_DIR=runs/2242438 jobs/t7_match.slurm` | T7/T8 full run (40,244 Earth rows): 3,908 pairs across 76 targets, `analogs_universe.json` (3.18 MB), 5/5 hard checks, `t7_report.md` ready for review |
| 2242478 | `pytest -q tests` | v2 tests (T1–T8, T12–T14): `70 passed` (`commit e81cccb`) |
| 2242481 | `jobs/download_t12_t14.slurm` | Downloads & SHA-256 verification: GLiM, SIM 3292, Moon Unified v2, Montabone MY24–MY36, and `60 MOD08_M3` v6.1 HDFs (2019–2023) |
| 2242482 | `jobs/t14_geology.slurm` | T14 geology (`commit 25f2e7e`, before `16db5db` overrides): Earth GLiM (`40,244`), Moon (`49` units), Mars (`44` units), `6/6` hard and `2/3` soft checks, `geology_mapping_review.md` |
| 2242484 | `jobs/t13_dust.slurm` | T13 dust & seasons (`commit 16db5db`): `cdod610` + `MOD08_M3 Deep_Blue` (`24,998` Earth valid), all parquets + 4 PNGs + `t13_checks.json` (`3/4` hard, `3/4` soft; paused at §5.6 for check #5 Taklimakan `rank=0.7281 < 0.9`) |
| 2242485 | `sbatch --export=ALL,T14_DIR=runs/2242482 jobs/t12_ice.slurm` | T12 water & ice (`commit 16db5db`): `ice_earth` (`40,244`), `ice_targets` (`76`), `1/1` hard and `3/3` soft checks |
| 2242486 | `jobs/t14_geology.slurm` | T14 geology re-run (`commit d3a255f`): applied `geology_overrides.json`, 12 units mapped via override, default/null share 0.0% Moon & Mars, 6/6 hard, 2/3 soft |
| 2242487 | `sbatch --export=ALL,T14_DIR=runs/2242486 jobs/t12_ice.slurm` | T12 water & ice re-run: linked to T14 `2242486`, `1/1` hard and `3/3` soft checks |
| 2242488 | `pytest -q tests` | v2 tests (T1–T8, T12–T15): `81 passed, 73 warnings in 4.00s` (`commit bda0acf`) |
| 2242489 | `sbatch --export=ALL,T5_DIR=runs/2242438,T12_DIR=runs/2242487,T13_DIR=runs/2242484,T14_DIR=runs/2242486 jobs/t7_match.slurm` | T15 matching & export: 7 dims, 5 presets, 5,010 pairs across 76 targets, `analogs_universe.json` (6.23 MB), 7/7 hard checks, 4/4 soft checks, `t7_report.md` |
| 2242506 | `sbatch --export=ALL,T5_DIR=runs/2242438,T12_DIR=runs/2242487,T13_DIR=runs/2242484,T14_DIR=runs/2242486 jobs/t7_match.slurm` | T16 production run (`commit 730165a`): missing-data policy (Case C penalisation, target preset coverage filtering), 4,944 pairs across 76 targets, `analogs_universe.json` (6.35 MB), `target_presets.csv`, 10/10 hard checks, 7/7 soft checks |

### T16 Export Fields and Diagnostics

Run `2242506` outputs:
- `analogs_universe.json`: Universe export loaded by the web app. Adds:
  - Per target: `available_dims` (active dimensions per target data) and `preset_status` (mapping each preset key to status `ok`, `not_applicable_body`, or `insufficient_target_data`, plus `coverage` and `missing_dims`).
  - Per analog: `earth_missing_dims` (dimensions present on target but missing on Earth patch) and `msi_by_preset[pkey] = null` for non-ok presets.
  - In `metadata`: `scoring_policy` (earth_missing_score = 0.0, min_preset_coverage = 0.6, policy rules) and `preset_status_summary`.
- `target_presets.csv`: Tabular audit of target status across all presets (`target_id,preset,status,coverage,missing_dims,available_dims`).
- `t7_checks.json` & `t7_report.md`: Verification suite results (10 hard checks, 7 soft checks, all passed).

## Exploring the data

`jobs/explore_datasets.slurm` builds a report of everything downloaded. It only reads; it never modifies `data/`.

```bash
cd /lustre/proyectos/p089/code && git pull && sbatch jobs/explore_datasets.slurm
```

**Output** in `/lustre/proyectos/p089/runs/<JOBID>/exploracion/`: `index.html` (report with images), `resumen.md` (short table) and `resumen.json`. **One part only:** `sbatch jobs/explore_datasets.slurm --only planets` (or `copernicus`, `modis`, `vectors`).

## Yuca resources

Checked on 2026-11-13 with `sinfo` and `sacctmgr`.

| Partition | Nodes | Per node | Max time | State that day |
| --- | --- | --- | --- | --- |
| `cpu` (default) | 24 (`amdcpu-hpc-01..24`) | 64 CPUs, ~1 TB RAM | 7 days | 19 idle, 4 busy, 1 draining (`24`) |
| `gpu` | 6 (`amdgpu-hpc-01..06`) | 48 CPUs, ~1 TB RAM, 2 × AMD MI210 (ROCm, not CUDA) | 7 days | 3 idle, 2 busy, 1 down (`06`) |

**Users** of account `p089` (QOS `qos089`):

| User | Role |
| --- | --- |
| `owen` | Pipeline |
| `aborquez` | — |
| `javier` | Frontend; rarely uses the cluster |
| `vmmn` | ACARUS staff; does not run jobs |

In practice the resources belong to the team. `qos089` limits are **500 CPUs and 4 GPUs for the whole group**, and 7 days per job. There is no limit on running or queued jobs, per user or per account; the only cap is the sum of resources across the group's jobs.

## Running the v1 downloads and scripts

On Yuca, with the `spaceapps_2026` environment:

```bash
bash setup_and_download.sh
```

```bash
sbatch run_download_missing.slurm
```

`run_download_missing.slurm` replaces `download_full_night.sh`: it runs as a job (not on the login node) and uses the corrected URLs.

Project quota and usage:

```bash
lfs quota -h -g p089 /lustre
```

The v1 steps, kept for reference:

```bash
sbatch run_clustering.slurm
```

```bash
python3 enrich_nomenclature.py
```

```bash
sbatch run_earth_matching.slurm
```

The v2 commands are in each task plan and in the README.

# Implementation plan v2

Plan for version 2 of the pipeline and the app. It is written so that a coding agent (Gemini) or a team member can implement it task by task without guessing. For each task it says which file to create, what the file must do, with which formulas, and how to know it is done.

Read first: [pipeline.md](pipeline.md) (data, scales and Yuca resources) and [HISTORY.md](HISTORY.md) (what was wrong with v1 and why each decision was made).

**Detailed plans:** T4 and later tasks have their own documents: [plan_t4.md](plan_t4.md), [plan_t5.md](plan_t5.md), [plan_t6.md](plan_t6.md) and [plan_t7_t8.md](plan_t7_t8.md). Where they disagree with this document, the detailed plan wins.

---

## 0. Rules for whoever implements

1. **One task, one commit.** The message says which task it is. Until 2026-11-13 messages were in Spanish (`T3: features globales de Marte y Luna`); **since then they are in English** (`T7: RBF matching and MSI presets`). Add an entry to [logbook.md](logbook.md) in the same commit. The English history is in [HISTORY.md](HISTORY.md).
2. **Do not delete v1.** The root scripts (`process_analogs.py`, `match_earth_analogs.py`, `enrich_nomenclature.py`) stay as reference, and they must not be imported. New code goes in `pipeline/`.
3. **Nothing heavy in the repo.** Rasters, parquet files and shards stay on Yuca (`/lustre/proyectos/p089/...`). Only the final app JSON (`app/public/data/`) is committed, and only if it is under 20 MB.
4. **Yuca rules (mandatory):**
   - Anything that takes more than a minute runs with `sbatch`. Never `nohup`, `&` or long `python` on the login node.
   - Every job declares `-A p089`, `-p cpu`, `--time` and `--mem`, and writes its log to `/lustre/proyectos/p089/output/`.
   - The outputs of each run go to a new directory, `/lustre/proyectos/p089/runs/<SLURM_JOB_ID>/`. Never overwrite previous runs.
   - No `rm -rf`. To clean up, move files to `/lustre/proyectos/p089/_to_delete/`.
   - Never disable TLS verification (`curl -k`, `verify=False`, etc.).
   - Group limit: 500 CPUs and 4 GPUs in total. CPU nodes have 64 cores and ~1 TB RAM.
5. **The code lives on Yuca** in `/lustre/proyectos/p089/code/`, a clone of the repository, updated with `git pull`.
6. **Environment:** the conda environment `spaceapps_2026`. New dependencies go into `pipeline/requirements.txt`.
7. **If a fact or URL cannot be verified, do not invent it.** Leave `null` and a `TODO(verify)` with the suggested source.

---

## 1. What changes from v1

| v1 problem | v2 solution |
| --- | --- |
| Windows of different size and resolution (Mars ~118 km at 463 m, Moon ~30 km at 118 m, Earth ~46 km at 90 m) | **Every body is compared in 32 × 32 km patches resampled to 500 m/px (64 × 64 px)**, projected locally without distortion |
| The equirectangular projection stretches the X axis away from the equator, and v1 does not correct it | Each patch is reprojected to an azimuthal equidistant (AEQD) projection centred on the patch |
| No vegetation mask | Mask from MODIS annual maximum NDVI (NASA Earthdata) |
| Targets = only global clusters | The challenge's curated targets (Artemis regions near the lunar south pole, Mars landing sites) **plus** global clusters as an exploration mode |
| Score `100/(1+0.35d)` | RBF kernel per dimension and a weighted MSI that the app can recompute |
| It does not say where the analogy breaks | Every analog carries the list of features that do not match, and the body's physical limits |
| It does not distinguish famous sites | Label `KNOWN_ANALOG` / `NEW_CANDIDATE` from a list of known analog regions |
| No logistics | Distance to road and airport (Natural Earth) |

---

## 2. Official challenge resources and how we use them

Source: the challenge's Resources tab, checked on 2026-11-13.

| Official resource | Used? | Product |
| --- | --- | --- |
| NASA Planetary Data System (PDS) | Yes | MOLA DEM 463 m, THEMIS IR Day/Night 100 m, LOLA LDEM 118 m, LROC WAC 100 m (USGS Astrogeology mosaics built from PDS) |
| NASA Lunar Reconnaissance Orbiter (LRO) | Yes | LOLA (topography), LROC WAC (brightness) |
| NASA LRO Diviner Lunar Data | Yes | Diviner Polar Resource Product (PDS `LRO-L-DLRE-5-PRP-V2.0`, file `DLRE_PRP_SOUTH.TAB`): annual mean and maximum temperature, and ice stability depth, 80–90°S |
| NASA Earthdata Search | Yes | MODIS MOD13C2 (monthly NDVI) and MOD11C3 (day/night land surface temperature), 0.05° |
| NASA Worldview | In the app | NASA GIBS base layers (the technology behind Worldview) for the Earth map |
| Copernicus Data Space Ecosystem (ESA) | Yes | Copernicus DEM GLO-90 |
| ESA Open Science Catalog | No | Optional: adds nothing we do not already have |
| CSA RADARSAT / SAR tutorial | No (out of scope) | Mention as future work: centimetre-scale roughness from radar |
| JAXA G-Portal | No | Optional: precipitation or snow as an alternative to NDVI |

Also used, outside the list: the USGS lunar ice favorability index and Natural Earth (logistics).

---

## 3. v2 architecture

```text
Raw data (Yuca, /lustre/proyectos/p089/data/raw)
   │
   ├── T3  pipeline/planet_features.py   (job array)  ─► runs/<id>/features_{mars,moon}.parquet
   ├── T5  pipeline/earth_features.py    (job array)  ─► runs/<id>/features_earth.parquet
   │        └── uses T6 pipeline/earth_layers.py (NDVI, LST, logistics, known regions)
   ├── T4  pipeline/targets.py + pipeline/data/targets.json  ─► curated targets + clusters
   │
   ├── T7  pipeline/match.py   ─► runs/<id>/matches.parquet
   └── T8  pipeline/export.py  ─► runs/<id>/analogs_universe.json  ─► app/public/data/
                                                                         │
                                               T10 app/ (React + Vite) ◄─┘
```

All feature computation uses **one function** (T1 + T2) for the three bodies. That is what guarantees a fair comparison.

### Folder layout

```text
pipeline/
  __init__.py
  config.py            # constants: patch size, resolution, paths, radii
  geo.py               # T1: extract an AEQD patch from any raster
  features.py          # T2: terrain features of a patch
  planet_features.py   # T3: global Mars and Moon sweep
  iau.py               # T4: IAU gazetteer helpers
  targets.py           # T4: curated targets + clusters
  earth_layers.py      # T6: NDVI, LST, logistics, known regions
  earth_features.py    # T5: Earth sweep
  match.py             # T7: RBF, MSI, diversity, where it breaks
  export.py            # T8: JSON for the app
  data/
    targets.json       # T4: curated targets (with a source for each)
    known_analogs.json # T6: famous analog regions
    limits.json        # T11: physical limits per body (team content)
  requirements.txt
jobs/
  t3_planet_features.slurm
  t4_targets.slurm
  t5_prepare.slurm, t5_earth_features.slurm, t5_merge.slurm, t5_submit.sh
  t6_earth_layers.slurm
  t7_match.slurm
tests/
  test_geo.py, test_features.py, test_planet_features.py, test_iau.py, test_targets.py,
  test_earth_layers.py, test_earth_features.py, test_match.py, test_export.py
app/                   # T10
```

---

## 4. Tasks

### T0. Data (Owen, on Yuca, before everything else)

Commands in section 7.

| ID | What | Job | Status |
| --- | --- | --- | --- |
| T0.1 | THEMIS Night, LROC WAC, lunar ice, the rest of Copernicus | `run_download_missing.slurm` | Done (job 2242198): 26,475 tiles, 0 failures |
| T0.2 | Natural Earth (roads, airports, countries) and MODIS NDVI and LST 2023 | `run_download_extra.slurm` | Done (job 2242203) |
| T0.3 | Diviner Polar Resource Product (south): `dlre_prp_south.tab` (604,800,210 bytes) + `.lbl` + `.xml` | `jobs/download_diviner.slurm` | Done. Source: `https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/` |
| T0.4 | Copernicus virtual mosaic | Inside T5 | `data/derived/copernicus_90m.vrt`, with the sea masked ([plan_t5.md](plan_t5.md)) |

### T1. `pipeline/geo.py`: extract a patch without distortion

**Goal:** given any raster (Earth, Moon or Mars) and a point (lat, lon), return a 64 × 64 array of elevations at 500 m/px in an azimuthal equidistant projection centred on that point.

**Main function:**

```python
def extract_patch(src, lat, lon, body, size_km=32.0, res_m=500.0, resampling=Resampling.average) -> np.ndarray | None
```

**Steps:**

1. **Body radius:** Earth uses the WGS84 ellipsoid, the Moon `R = 1737400 m`, Mars `R = 3396190 m`. If the raster's CRS carries the radius, read it with `pyproj.CRS(src.crs).ellipsoid.semi_major_metre` and check that it matches.
2. **Target CRS:** `+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +units=m`, plus `+R={R}` (Moon, Mars) or `+datum=WGS84` (Earth).
3. **Target transform:** `Affine(res_m, 0, -size_km*500, 0, -res_m, size_km*500)`, shape `(64, 64)`.
4. **Source window:**
   - Compute the patch bounds in the source CRS with `rasterio.warp.transform_bounds(dst_crs, src.crs, *bounds, densify_pts=21)`, convert them to a window with `src.window(...)`, add a 2-px margin and clip to the raster.
   - **Antimeridian:** if the window crosses ±180°, skip the patch and count it.
   - **Poles:** patches that contain a pole read a full latitude band ([plan_t4.md](plan_t4.md) T4.0).
5. **Reduced read:** if the source resolution is much finer than 500 m (Copernicus 90 m, LOLA 118 m), read the window with a reduced `out_shape` (factor `floor(500 / source_res)`) and `Resampling.average`, so millions of extra pixels are not read.
6. **Reprojection:** `rasterio.warp.reproject` of the array into the target grid, with `dst_nodata = np.nan`.
7. **Validity:** return `None` if less than 90 % of the pixels are valid.

**Nodata and scale:** turn `src.nodata` and values with `|z| > 1e5` into NaN, **then** apply `value = raw · scale + offset` (LOLA stores half-metres; see [pipeline.md](pipeline.md)).

**Acceptance criteria (tests in `tests/test_geo.py`):**

- On a synthetic equirectangular Moon raster with a known tilted plane, the patch at lat 0° and at lat 70° gives the same slope (±0.2°). v1 fails this.
- An Earth patch that crosses the edge between two Copernicus tiles (through the VRT) has no holes.
- A patch over the ocean returns `None`.

### T2. `pipeline/features.py`: patch features

**Input:** a 64 × 64 array `z` (metres), with `res_m = 500`.

**Features** (all float32, with exact names, because they are used in the JSON):

| Name | Formula | Dimension |
| --- | --- | --- |
| `mean_slope_deg` | `gy, gx = np.gradient(z, res_m)`; `slope = degrees(arctan(hypot(gx, gy)))`; mean | topography |
| `p90_slope_deg` | 90th percentile of `slope` | topography |
| `relief_m` | `p95(z) − p5(z)` | topography |
| `hypsometric_integral` | `(mean(z) − min(z)) / (max(z) − min(z))`; 0.5 if `max == min` | topography |
| `detrended_std_m` | Fit a plane `z ≈ a·x + b·y + c` by least squares; standard deviation of the residual | roughness |
| `tri_m` | Riley's TRI: for each interior pixel, `sqrt(Σ (z_neighbour − z_centre)²)` over 8 neighbours; mean | roughness |
| `mean_elev_m` | Mean of `z` | Stored but **not** compared: the datums of different bodies are not comparable |

Before computing, fill the remaining NaNs with the patch median.

**Acceptance criteria (`tests/test_features.py`):**

- 10° tilted plane: `mean_slope_deg ≈ 10` (±0.1), `detrended_std_m ≈ 0`, `tri_m` constant and known.
- Horizontal plane: everything ≈ 0, and `hypsometric_integral = 0.5`.
- Synthetic cone: `hypsometric_integral ≈ 1/3` (±0.05).

### T3. `pipeline/planet_features.py` + `jobs/t3_planet_features.slurm`

**Goal:** sweep Mars and the Moon with 32 km patches and store their features.

**Grid of centres** (the same for every body, Earth included):

- Latitude step: `dlat = degrees(32000 / R)` (Mars ≈ 0.54°, Moon ≈ 1.06°, Earth ≈ 0.29°).
- Longitude step at each latitude: `dlon = dlat / cos(lat)`.
- Latitudes from −88° to 88°. AEQD works at the pole; raster coverage sets the limit.
- Mars ≈ 141 thousand patches; Moon ≈ 37 thousand.

**Auxiliary layers per patch.** Each is the median within the patch, also extracted with `extract_patch` and `Resampling.average`; NaN where there is no coverage.

- **Mars:**
  - `themis_day` and `themis_night`: raw mosaic values; document that they are not temperature;
  - `themis_delta = themis_day − themis_night`.
- **Moon:**
  - `wac_reflectance`: relative brightness, compared as a percentile within the Moon;
  - `ice_favorability`: poles only;
  - `diviner_tmax_k`, `diviner_tavg_k` and `ice_depth_m`, from the PRP table (T0.3).
- **Format of `dlre_prp_south.tab`:** CSV with a header and spaces. Columns `tri1_x, tri1_y, tri1_z, tri2_x, …, tri3_z, tri_clon, tri_clat, tri_calt, temp_avg, temp_max, ice_depth`. Use only:
  - `tri_clon`, `tri_clat`: triangle centre, in degrees;
  - `temp_avg`, `temp_max`: in K;
  - `ice_depth`: in m. `−999` means no stable ice; it becomes NaN for the median but counts as "no ice".
- **Reading it:** 2.88 million rows (577 MB). Read once with `pandas.read_csv(..., usecols=[...], skipinitialspace=True)` and cache it in `data/derived/diviner_prp_south.parquet`.
- **Sampling it:** for each polar patch, take the triangles whose centre falls inside the patch (`scipy.spatial.cKDTree` on south polar stereographic coordinates), and use the median. Coverage runs from ~76°S to 90°S.

**Parallelism:** a job array over latitude stripes (16 stripes, `--array=0-15`, 8 CPUs each, `multiprocessing.Pool`). Each task writes `runs/<id>/features_<body>_<stripe>.parquet`, and `--merge` combines them.

**Output columns:** `body, lat, lon, <T2 features>, <auxiliary layers>, valid_frac`.

**Acceptance criteria:**

- The number of valid patches per body matches the expectation (±10 %).
- A quick `mean_slope_deg` map (lat/lon scatter, PNG in `runs/<id>/`) shows recognisable features: Valles Marineris and Olympus Mons on Mars; highlands against maria on the Moon.

**Done:** runs 2242278 and 2242279.

### T4. `pipeline/targets.py` + `pipeline/data/targets.json`

**Goal:** define which Moon and Mars sites the analogs are searched against.

> **Detailed specification:** [plan_t4.md](plan_t4.md) (verified coordinates, IAU anchors, polar support, signatures, outputs and tests). It wins over this section.

**Two kinds of target:**

1. **Curated (`CURATED`),** in `targets.json`.
   - **Fields:** `id`, `body`, `name`, `lat`, `lon`, `category`, `why` (one line), `source_url`.
   - **Coordinates** come from the official source. If they cannot be found, `lat`/`lon = null` and the target is skipped.
   - **Moon, south pole:** the Artemis III candidate regions published by NASA (2024 update: Peak near Cabeus B, Haworth, Malapert Massif, Mons Mouton Plateau, Mons Mouton, Nobile Rim 1, Nobile Rim 2, de Gerlache Rim 2, Slater Plain), plus the rim of Shackleton crater. NASA does not publish centre coordinates, so they are anchored on IAU features (see plan_t4).
   - **Mars:** Jezero (Perseverance), Gale (Curiosity), Gusev (Spirit), Meridiani Planum (Opportunity), Utopia Planitia (Zhurong), Elysium Planitia (InSight), Oxia Planum (Rosalind Franklin), and a shallow-ice region from the SWIM maps (Arcadia Planitia).
2. **Clusters (`CLUSTER`):**
   - k-means on the T3 features (standardised topography and roughness features), 30 clusters per body;
   - the representative is the patch closest to the centroid;
   - its name is the nearest IAU feature.

**Target features:** extracted with exactly the same T1 + T2 functions at the target's coordinates. A curated target averages several patches (a centre and 4 neighbours at 16 km, or 8 patches on a crater rim), so it does not depend on a single patch.

**Acceptance criterion:** `targets.json` has at least 6 lunar and 6 Martian targets with `source_url`, and every one of them has valid features.

**Done:** run 2242423 (16/16 curated targets, 60 clusters).

### T5. `pipeline/earth_features.py` + Slurm jobs

**Goal:** the same as T3, but for Earth, filtering out what is useless first.

> **Detailed specification:** [plan_t5.md](plan_t5.md) (VRT with the sea masked, prefilter in a `prepare` stage, a balanced array, and a `merge` stage with checks). It wins over this section.

**Steps:**

1. Build (once, inside the job) the Copernicus VRT.
2. Generate the global grid of centres (same function as T3, with Earth's radius).
3. **Cheap prefilter** before extracting the patch, using the T6 layers at 0.05°:
   - drop if `ndvi_max > 0.25` (vegetation);
   - drop if there is no Copernicus tile in that 1° cell.
4. Extract the patch from the VRT and compute the T2 features.
5. Attach the T6 layers: `ndvi_max`, `lst_day_c`, `lst_night_c`, `lst_amplitude_c`, `dist_road_km`, `dist_airport_km`, `known_region` (name or null).

**Parallelism:** a job array over latitude stripes, `--array=0-31%30`, 16 CPUs each. The `%30` keeps the group under 500 CPUs.

**Acceptance criteria:**

- Between 30 and 80 thousand valid Earth patches. This was 40–120 thousand before measuring the real cache.
- At most 5 patches each in the Amazon, the Congo and equatorial Indonesia.
- The Atacama, the Sahara, the Sonoran desert, central Australia and the McMurdo Dry Valleys are present.

**Status:** smoke test passed (runs 2242432–2242434); the full run is pending.

### T6. `pipeline/earth_layers.py`: Earth layers

> **Detailed specification:** [plan_t6.md](plan_t6.md) (MODIS through pyhdf because GDAL has no HDF4, scale conventions, densified roads, `EarthLayers` for T5, known regions and checks). It wins over this section.

Functions that load once (in memory, per process) and answer queries by (lat, lon):

- **Annual maximum NDVI:**
  - read the 12 MOD13C2 files (subdataset `CMG 0.05 Deg Monthly NDVI`, divided by 10000; values below −0.3 or the fill value become NaN);
  - take the per-pixel maximum;
  - cache it as a GeoTIFF in `data/derived/ndvi_max_2023.tif`.
- **Land surface temperature (LST):**
  - from MOD11C3, `LST_Day_CMG` and `LST_Night_CMG` (× 0.02, kelvin → °C);
  - annual mean by day, by night, and the amplitude `day − night`;
  - cache in `data/derived/lst_2023.tif` (3 bands).
- **Logistics:** distance in km to the nearest road (Natural Earth, without ferries) and the nearest non-military airport, with `BallTree` (haversine) on the road vertices densified every ~2 km.
- **Known regions:** `pipeline/data/known_analogs.json`, with approximate bounding boxes and a source for each of 12 regions:
  - Atacama Desert, McMurdo Dry Valleys, Iceland, Hawaii (Mauna Kea / Kilauea), Devon Island (Haughton crater), Utah (MDRS, Hanksville);
  - Rio Tinto (Spain), Svalbard, Pilbara (Australia), Meteor Crater (Arizona), Lanzarote, Mojave.

  A patch inside any of them is labelled `KNOWN_ANALOG`; otherwise `NEW_CANDIDATE`.

**Acceptance criteria:**

- `ndvi_max` in the Sahara < 0.12 and in the Amazon > 0.7.
- Distance to road in Hermosillo < 5 km.

**Done:** runs 2242426 and 2242430.

### T7. `pipeline/match.py`: scoring and selection

> **Detailed specification (English):** [plan_t7_t8.md](plan_t7_t8.md). It wins over this section for T7 and T8.

**1. Common normalisation.**

- Apply `log1p` to the long-tailed features (`relief_m`, `detrended_std_m`, `tri_m`).
- For each feature, compute a robust z: `z = (x − median) / (1.4826 · MAD)`, with the median and MAD computed **on Earth**. Units are then "typical Earth deviations".

**2. Dimensions and RBF.**

| Dimension `k` | Features | Default σ |
| --- | --- | --- |
| `topography` | `mean_slope_deg`, `p90_slope_deg`, `relief_m`, `hypsometric_integral` | 1.0 |
| `roughness` | `detrended_std_m`, `tri_m` | 1.0 |
| `environment` | Aridity: `ndvi_max` of the Earth patch | See below |
| `thermal` | Mars only: rank of `lst_amplitude_c` (Earth) against rank of `themis_delta` (Mars), each within its own body | 1.0 |

- **Geomorphology:** `d_k = ||z_earth − z_target|| / sqrt(n_features_k)`, and `S_k = exp(−d_k² / (2 σ_k²))`.
- **Environment:** `S_env = exp(−max(0, ndvi_max − 0.10)² / (2 · 0.10²))`. A site without vegetation scores 1.
- **Thermal:** a comparison by rank (how extreme the amplitude is **within its own body**), not of absolute temperatures. The app says so. For the Moon, `S_thermal = null`, because there is no Earth equivalent.

**3. MSI.** `MSI = Σ w_k · S_k / Σ w_k`, over the non-null dimensions.

| Preset | topography | roughness | environment | thermal |
| --- | --- | --- | --- | --- |
| `mobility_and_traction` | 0.45 | 0.40 | 0.15 | 0 |
| `construction_and_base` | 0.55 | 0.25 | 0.10 | 0.10 |
| `dust_and_thermal` | 0.15 | 0.15 | 0.40 | 0.30 |

The app applies the logistics adjustment `MSI_log = MSI · (1 − λ + λ · exp(−dist_road_km / 100))`, with λ between 0 and 0.3.

**4. Selection with diversity.**

- For each target and each preset, sort by MSI and take the best 30 that are more than 150 km apart (haversine).
- At most 3 of them can be "polar cold" patches (see plan_t7_t8).
- The union of the three presets (at most 90 sites per target) goes into the JSON with its `sub_scores`, so the app can re-rank with any weights.
- To keep it fast with tens of thousands of patches, first compute the topography + roughness distance with `sklearn.neighbors.NearestNeighbors` (k = 2000), and apply the full MSI only to those candidates.

**5. Where the analogy breaks (per site).**

- For each feature with `|z_earth − z_target| > 1.5`, add an object `{feature, earth, target, z_diff}` to `mismatches`, with values in physical units.
- Also copy the body's fixed limits from `limits.json` (T11) into the JSON.

**Acceptance criteria (`tests/test_match.py` and review):**

- A target identical to an Earth patch gets `S_topography = S_roughness = 1`.
- No two analogs of the same target are less than 150 km apart.
- Sanity review: for a target on Olympus Mons, the top 30 should include some shield or large volcano (Hawaii, the Galápagos, Iceland). If not, check the scales before moving on.

### T8. `pipeline/export.py`: JSON for the app

- **Output:** `runs/<id>/analogs_universe.json`. Copying it to `app/public/data/analogs_universe.json` is a separate, reviewed step.
- **Schema:** section 5 below and [plan_t7_t8.md](plan_t7_t8.md) §4.
- **Rounding:** coordinates to 4 decimals and scores to 3.
- **Size:** if it is over 20 MB, split it into one file per body (`analogs_moon.json`, `analogs_mars.json`).

### T9. Tests

- **Unit tests:** `tests/` with `pytest`, synthetic data only (they never touch the rasters). They run in a short job: `sbatch --wrap 'bash -c "... pytest -q tests"'` with `-A p089 -p cpu --time=00:15:00 --mem=4G`.
- **Test runs:** before running T3 or T5 in full, run each one with `--limit 500` (an option that limits the number of patches) and review the output.

### T10. App (Javier)

**Stack:** React + Vite + TypeScript + Tailwind. Maps with **MapLibre GL** (no token needed, unlike Mapbox) for Earth and **Leaflet** for the Moon and Mars. Charts with Recharts. The current skeleton uses Leaflet for all three bodies and its own SVG radar (see [HISTORY.md](HISTORY.md) §7).

**Base layers verified on 2026-11-13:**

| Map | Tile URL |
| --- | --- |
| Earth (NASA GIBS, relief) | `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg` |
| Earth (NASA GIBS, true colour) | `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2023-07-01/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg` |
| Moon (NASA Trek, LROC WAC) | `https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/default/default028mm/{z}/{y}/{x}.jpg` |
| Moon (NASA Trek, LOLA relief) | `https://trek.nasa.gov/tiles/Moon/EQ/LRO_LOLA_ClrShade_Global_128ppd_v04/1.0.0/default/default028mm/{z}/{y}/{x}.png` |
| Mars (NASA Trek, Viking colour) | `https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg` |
| Mars (NASA Trek, MOLA relief) | `https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg` |

The Trek tiles are in geographic projection (EPSG:4326, 2 tiles in X at level 0); in Leaflet use `crs: L.CRS.EPSG4326`. Near the lunar south pole the equirectangular view distorts heavily: show a notice and, at least, centre on the region. Look for a south polar (SP) layer on trek.nasa.gov if there is time.

**Screens and components:**

1. **Scenario selector:** body (Moon / Mars), target type (curated / cluster), mission preset.
2. **Weights panel:** one slider per dimension (normalised to sum 1), a logistics priority switch (λ from 0 to 0.3), and a "new candidates only" filter.
3. **Dual view:** the target in Leaflet on the left; Earth on the right, with markers coloured by MSI. Clicking an analog centres the map.
4. **Results list:** cards ordered by the MSI recomputed in the browser (`MSI = Σ w·S / Σ w` with the JSON `sub_scores`; nothing geophysical is recomputed in the client).
5. **Site card:**
   - radar chart of the 4 dimensions;
   - table of Earth vs. target features, in physical units;
   - a **"Where the analogy breaks"** section: the site's `mismatches` plus the body's fixed limits;
   - suggested test protocol;
   - logistics (distance to road and airport);
   - `KNOWN_ANALOG` or `NEW_CANDIDATE` label;
   - links to the source datasets.
6. **Compare:** two sites side by side.
7. **Export:** the card as JSON and Markdown, and a print view with CSS.
8. **Methodology:** a short page with the T7 formulas and the resource table of section 2.

**Data:** until T8 exists, use a sample JSON that follows the section 5 schema (`app/public/data/sample.json`, converted from the v1 output by `tools/v1_to_sample.py`).

**Deployment:** GitHub Pages or Vercel from `main`. The venue requires a public link ([submission.md](submission.md)).

**Acceptance criteria:**

- Moving a slider re-orders the list in under 50 ms.
- It works without a connection to Yuca.
- It looks right on a 1366 × 768 laptop and on a projector.

### T11. Content (P1, P3, P4)

- **`pipeline/data/limits.json`:** per body, a list of `{factor, earth, target, consequence, source}` (format in [plan_t7_t8.md](plan_t7_t8.md) §4.2). Minimum:
  - Moon: gravity, vacuum, radiation, thermal cycle, polar illumination and regolith.
  - Mars: gravity, pressure, radiation, thermal cycle, dust and perchlorates.
- **Test protocols:** one short text per preset, which the app shows depending on the dimension with the largest weight.
- **Pitch, presentation and video:** see [submission.md](submission.md); base text in [value_proposition.md](value_proposition.md).
- **Use of AI:** see [HISTORY.md](HISTORY.md).

---

## 5. Data contract: `analogs_universe.json` (v2)

The detailed, current version, with every field, is in [plan_t7_t8.md](plan_t7_t8.md) §4.1. The core:

```json
{
  "metadata": {
    "version": "2.0.0",
    "generated_at": "ISO-8601",
    "slurm_job_id": "123456",
    "patch": { "size_km": 32, "res_m": 500, "projection": "local AEQD" },
    "earth_patches_evaluated": 0,
    "datasets": [ { "name": "Copernicus DEM GLO-90", "source": "ESA", "url": "..." } ]
  },
  "mission_presets": {
    "mobility_and_traction": { "label": "Rover mobility and traction", "weights": { "topography": 0.45, "roughness": 0.40, "environment": 0.15, "thermal": 0 } }
  },
  "limits": {
    "Moon": [ { "factor": "gravity", "earth": "1 g", "target": "0.166 g", "consequence": "...", "source": "..." } ],
    "Mars": [ ]
  },
  "targets": [
    {
      "id": "moon-a3-haworth",
      "type": "CURATED",
      "body": "Moon",
      "name": "Haworth rim",
      "lat": -87.45,
      "lon": -5.17,
      "category": "Artemis III candidate region",
      "why": "...",
      "source_url": "...",
      "iau_label": "...",
      "features": { "mean_slope_deg": 0, "p90_slope_deg": 0, "relief_m": 0, "hypsometric_integral": 0, "detrended_std_m": 0, "tri_m": 0 },
      "aux": { "wac_reflectance": 0, "ice_favorability": 0, "diviner_tmax_k": null },
      "analogs": [
        {
          "id": "earth+31.8480-113.3900",
          "lat": 0,
          "lon": 0,
          "country": null,
          "classification": "NEW_CANDIDATE",
          "known_region": null,
          "sub_scores": { "topography": 0, "roughness": 0, "environment": 0, "thermal": null },
          "msi_by_preset": { "mobility_and_traction": 0 },
          "features": { "mean_slope_deg": 0 },
          "earth_env": { "ndvi_max": 0, "lst_day_c": 0, "lst_night_c": 0, "lst_amplitude_c": 0 },
          "logistics": { "dist_road_km": 0, "dist_airport_km": 0 },
          "mismatches": [ { "feature": "relief_m", "earth": 0, "target": 0, "z_diff": 0 } ]
        }
      ]
    }
  ]
}
```

`country` comes from Natural Earth `ne_10m_admin_0_countries` (column `ADMIN`).

---

## 6. Order and timing

> **Superseded by [submission.md](submission.md).** The real venue (NASA Space Apps Sonora, Tec de Monterrey) gives Saturday from 9:00 to 21:00 and pitches on Sunday morning, not 48 hours. The task order still holds: T0 → T1/T2 → T3 → T4 → T6 → T5 → T7/T8, with the app (T10) and content (T11) in parallel.

**Plan B:**

- **If T5 does not finish in time,** use only the latitude stripes that did finish (`merge --allow-missing`), and say so in the app ("partial coverage: X % of the candidates").
- **If T7/T8 fail completely,** the app still works with the v1 sample converted to the new schema.

---

## 7. Download commands (Owen, on Yuca)

Everything runs **on Yuca** (`login-01`, over SSH or the Open OnDemand shell). The code arrives by cloning the public repository into `/lustre/proyectos/p089/code`; no token is needed.

First time:

```bash
git clone https://github.com/OwenSolis03/Space_Apps_2026_Analogos_Luna_Marte.git /lustre/proyectos/p089/code
```

To bring in changes:

```bash
cd /lustre/proyectos/p089/code && git pull
```

Test without queueing, then submit (always from `code/`):

```bash
cd /lustre/proyectos/p089/code && sbatch --test-only run_download_missing.slurm && sbatch --test-only run_download_extra.slurm
```

```bash
cd /lustre/proyectos/p089/code && sbatch run_download_missing.slurm && sbatch run_download_extra.slurm
```

MODIS needs a free account at https://urs.earthdata.nasa.gov and a `~/.netrc` file on Yuca created **by hand** (the password must never go through an agent):

```bash
nano ~/.netrc
```

Content: `machine urs.earthdata.nasa.gov login YOUR_USER password YOUR_PASSWORD`. Then:

```bash
chmod 600 ~/.netrc
```

Progress:

```bash
squeue -u owen
```

```bash
tail -n 30 /lustre/proyectos/p089/output/descargas_*.log
```

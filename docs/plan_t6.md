# Detailed plan T6: Earth layers (NDVI, LST, logistics, country and known analogs)

Full specification of T6. It expands section T6 of [implementation_plan.md](implementation_plan.md); where they disagree, **this document wins for T6**. Written by Claude on 2026-11-13 on `main` at `115e0c3`, after checking the Yuca data that day.

**Status:** implemented by Gemini (commits `29fbb88`, `84888cd`). The cache was built in job 2242426; the checks in job 2242430 passed 8/8 hard and 5/5 soft.

T6 does not sweep the Earth (that is T5). It delivers:

1. **Two cached derived rasters:** annual maximum NDVI and annual LST for 2023.
2. **A class** that, given many (lat, lon) points, returns **every** Earth column T5 attaches to each patch. T5 only imports that class.

---

## 0. Summary

| What | Where |
| --- | --- |
| Reading MODIS and computing the NDVI maximum and annual LST | `pipeline/earth_layers.py` |
| Known analog regions (hand-written, committed) | `pipeline/data/known_analogs.json` |
| New paths | `pipeline/config.py` |
| Job: build the cache and check it | `jobs/t6_earth_layers.slurm` |
| Tests | `tests/test_earth_layers.py` |
| Shared cache (not committed) | `data/derived/ndvi_max_2023.tif`, `data/derived/lst_2023.tif` |
| Run outputs | `runs/<JOBID>/t6_checks.json`, `map_ndvi_max.png`, `map_lst_amplitude.png`, `map_known_analogs.png` |

Commit: `T6: Earth layers (NDVI, LST, logistics, known regions)`. **Commit before submitting the job,** so the log records the right commit. In T4, the run's log recorded `0e1e43c` because the job ran before the commit.

---

## 1. Facts checked on Yuca (do not assume otherwise)

**MODIS: GDAL cannot read it.** The GDAL build in `spaceapps_2026` (3.12.3) **has no HDF4 plugin**, so neither `gdalinfo` nor `rasterio` can open the `.hdf` files. `pyhdf` **is** installed and works. Therefore:

- Read with `from pyhdf.SD import SD, SDC`, calling `SD(path, SDC.READ).select(<name>).get()`.
- Do the `import pyhdf` **inside** the functions that read HDF, not at module level. That way the tests run on a laptop without `pyhdf`.
- Do not install `libgdal-hdf4` or touch the conda environment.

**MOD13C2 (NDVI):** 12 files, one per month of 2023, in `data/raw/earth/modis/ndvi/`.

| SDS | Type | Actual attributes |
| --- | --- | --- |
| `CMG 0.05 Deg Monthly NDVI` | int16, 3600 × 7200 | `scale_factor=10000.0`, `_FillValue=-3000`, `valid_range=[-2000, 10000]` |
| `CMG 0.05 Deg Monthly pixel reliability` | int8 | `valid_range=[0, 4]`, `_FillValue=-1` |

⚠️ **MODIS VI convention: `NDVI = raw / 10000`.** You **divide** by the `scale_factor`; you do not multiply. Write the constant explicitly (`NDVI_DIVISOR = 10000.0`), and do not apply the attribute generically.

**MOD11C3 (LST):** 12 files in `data/raw/earth/modis/lst/`.

| SDS | Type | Actual attributes |
| --- | --- | --- |
| `LST_Day_CMG`, `LST_Night_CMG` | uint16, 3600 × 7200 | `scale_factor=0.02`, `_FillValue=0`, `valid_range=[7500, 65535]`, unit K |

⚠️ **Here you multiply:** `K = raw · 0.02`, then `°C = K − 273.15`. Explicit constant: `LST_SCALE = 0.02`.

**Common grid of both products** (from `StructMetadata.0`): `Projection=GCTP_GEO`, `UpperLeft=(-180, 90)`, `LowerRight=(180, -90)`, 7200 × 3600. That means:

- EPSG:4326, 0.05° cells;
- row 0 = 90°N, column 0 = 180°W;
- transform `rasterio.transform.from_origin(-180.0, 90.0, 0.05, 0.05)`.

**Natural Earth** (`data/raw/earth/naturalearth/`, EPSG:4326):

| Layer | Content |
| --- | --- |
| `ne_10m_roads` | 56,600 lines, 709,166 vertices. `featurecla` ∈ {`Road`: 56,312, `Ferry`: 288}. **Exclude `Ferry`** |
| `ne_10m_airports` | 893 points. `type` ∈ {`mid` 475, `major` 369, `mid and military` 14, `major and military` 14, `military mid` 10, `military major` 4, `spaceport` 3, `small` 2, `military` 2}. Has `name` and `iata_code` |
| `ne_10m_admin_0_countries` | 258 polygons, column `ADMIN` |

Natural Earth has no roads in Antarctica, so `dist_road_km` will be very large there. That is correct: the Dry Valleys are logistically remote.

---

## 2. `pipeline/config.py`: additions

```python
EARTH_RAW_FILES: dict[str, str] = {
    "ndvi_dir": "earth/modis/ndvi",
    "lst_dir": "earth/modis/lst",
    "roads": "earth/naturalearth/ne_10m_roads/ne_10m_roads.shp",
    "airports": "earth/naturalearth/ne_10m_airports/ne_10m_airports.shp",
    "countries": "earth/naturalearth/ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp",
}
EARTH_DERIVED_FILES: dict[str, str] = {
    "ndvi_max": "ndvi_max_2023.tif",
    "lst": "lst_2023.tif",
}
MODIS_CMG_RES_DEG: float = 0.05
```

All paths are relative to `<project_dir>/data/raw` and `<project_dir>/data/derived`. Nothing in T6 uses `/lustre/...` directly, so it works the same with the offline kit (`--project-dir ~/p089_offline`).

---

## 3. `pipeline/earth_layers.py`

### 3.1 Pure functions (no I/O; tested with synthetic arrays)

```python
NDVI_SDS = "CMG 0.05 Deg Monthly NDVI"
NDVI_FILL = -3000
NDVI_DIVISOR = 10000.0
NDVI_MIN_VALID = -0.3          # values below -> NaN (water/noise), as in the general plan
LST_DAY_SDS, LST_NIGHT_SDS = "LST_Day_CMG", "LST_Night_CMG"
LST_FILL = 0
LST_MIN_RAW = 7500
LST_SCALE = 0.02
KELVIN_0C = 273.15
MIN_MONTHS_LST = 3             # minimum valid months for the annual mean

def ndvi_from_raw(raw: np.ndarray) -> np.ndarray:
    """int16 -> float32. Fill, raw < -2000 or > 10000 -> NaN; then /10000; < -0.3 -> NaN."""

def lst_c_from_raw(raw: np.ndarray) -> np.ndarray:
    """uint16 -> float32 °C. Fill (0) or raw < 7500 -> NaN; then raw*0.02 - 273.15."""

def running_nanmax(acc: np.ndarray | None, x: np.ndarray) -> np.ndarray:
    """Running maximum ignoring NaN (np.fmax). acc=None -> copy of x."""

def running_sum_count(sum_: np.ndarray | None, cnt: np.ndarray | None, x: np.ndarray
                      ) -> tuple[np.ndarray, np.ndarray]:
    """Accumulates the sum (float64) and count (uint8) of finite values."""

def finalize_mean(sum_, cnt, min_count) -> np.ndarray:
    """sum/cnt as float32; NaN where cnt < min_count."""

def cell_index(lat: np.ndarray, lon: np.ndarray, res: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """Row and column of the CMG cell containing each point.
    row = floor((90 - lat)/res) clipped to [0, 3599]; col = floor((lon + 180)/res) clipped to [0, 7199].
    lon is normalised to [-180, 180) first."""

def patch_window_stat(grid: np.ndarray, lat: np.ndarray, lon: np.ndarray, half_km: float,
                      stat: str, res: float = 0.05) -> np.ndarray:
    """Statistic (stat ∈ {'median','mean','max'}) of the cells inside the patch square:
    latitude half-side = degrees(half_km / 6371.0); longitude half-side = that / max(cos(lat), 0.05).
    Corner cells via cell_index; in longitude wrap modulo 7200 (the antimeridian is not skipped here:
    this is a global grid). NaN is ignored; all NaN -> NaN.
    Loop per point: <= ~150k points and windows of <= ~15x40 cells."""
```

**Why the window and not the centre cell:** a 32 km patch covers ~6 × 6 cells of 0.05° at the equator. With only the centre cell, an oasis or a river could flip the whole patch's classification.

**Statistic per variable:**

| Variable | Statistic | Why |
| --- | --- | --- |
| `ndvi_max` | median | Represents the patch, not a strip of vegetation |
| `lst_day_c`, `lst_night_c`, `lst_amplitude_c` | mean | — |

### 3.2 Building the cache (in the job only)

```python
def build_ndvi_max(ndvi_dir: Path, out_tif: Path) -> Path:
    """Reads the 12 MOD13C2 files (sorted by name) one at a time with pyhdf, applies ndvi_from_raw and
    accumulates running_nanmax and the count of valid months. Writes a 2-band GeoTIFF:
      band 1 ndvi_max (float32, nodata NaN), band 2 n_months (uint8 stored as float32).
    EPSG:4326, from_origin(-180, 90, 0.05, 0.05), compress='deflate', tiled=True, BIGTIFF='IF_SAFER'.
    Write to out_tif.with_suffix('.tmp.tif') and os.replace at the end (atomic).
    ValueError if there are not exactly 12 files or an SDS is not (3600, 7200)."""

def build_lst(lst_dir: Path, out_tif: Path) -> Path:
    """Same with the 12 MOD11C3 files: annual means with finalize_mean(min_count=3), day and night.
    Writes 3 float32 bands: 1 lst_day_c, 2 lst_night_c, 3 lst_amplitude_c = day - night
    (NaN if either is missing). Same writing parameters."""

def ensure_cache(project_dir: Path, force: bool = False) -> dict[str, Path]:
    """Builds whatever is missing in data/derived/. Existing files are left alone.
    With force=True it does NOT overwrite: it fails and asks to move the old file to _to_delete/
    by hand (Yuca rule: never overwrite)."""
```

Memory: one month is processed at a time. The accumulators are 3600 × 7200 float64 (~207 MB each), so the peak stays under 2 GB.

### 3.3 Logistics, country and known regions

```python
ROAD_DENSIFY_DEG = 0.02        # ~2.2 km: max error per vertex ~1.1 km
AIRPORT_EXCLUDE_TYPES = {"military", "military mid", "military major", "spaceport"}
EARTH_RADIUS_KM = 6371.0

class Logistics:
    def __init__(self, roads_shp: Path, airports_shp: Path): ...
        # Roads: featurecla != 'Ferry'; shapely.segmentize(geom, ROAD_DENSIFY_DEG);
        # all vertices (shapely.get_coordinates); BallTree(np.radians([[lat, lon]]),
        # metric='haversine'). Print the vertex count after densifying.
        # Airports: type not in AIRPORT_EXCLUDE_TYPES; same BallTree; keep name and iata_code.
    def dist_road_km(self, lat, lon) -> np.ndarray: ...
    def nearest_airport(self, lat, lon) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(dist_km float32, iata object, name object); empty or '-' iata -> None."""

class Countries:
    def __init__(self, countries_shp: Path): ...   # geopandas + .sindex
    def lookup(self, lat, lon, max_coast_km: float = 25.0) -> np.ndarray:
        """ADMIN of the polygon that contains the point (geopandas.sjoin, predicate='within').
        If none contains it (coast, small islands), use the nearest country only if it is
        <= 25 km away (sjoin_nearest in EPSG:4087 with max_distance=25_000). Otherwise None."""

class KnownRegions:
    def __init__(self, json_path: Path = KNOWN_ANALOGS_JSON): ...  # validates (section 4)
    def lookup(self, lat, lon) -> np.ndarray:
        """id of the first region whose bbox contains the patch CENTRE, or None."""
    def name_of(self, region_id: str) -> str: ...
```

### 3.4 Façade used by T5

```python
EARTH_ENV_COLUMNS = ["ndvi_max", "lst_day_c", "lst_night_c", "lst_amplitude_c",
                     "dist_road_km", "dist_airport_km", "nearest_airport_iata",
                     "nearest_airport_name", "country", "known_region", "classification"]

class EarthLayers:
    @classmethod
    def from_project(cls, project_dir: Path, need: set[str] | None = None) -> "EarthLayers":
        """Loads into memory ndvi_max (band 1) and the 3 LST bands as float32 arrays, plus
        Logistics, Countries and KnownRegions. `need` can load only a part (e.g. {'ndvi'} for the
        prefilter). Fails with a clear message if the cache is missing:
        'Run jobs/t6_earth_layers.slurm first'."""

    def ndvi_prefilter(self, lat, lon, half_km: float = 16.0) -> np.ndarray:
        """Patch ndvi_max (window median), for the T5 prefilter (> 0.25 is dropped)."""

    def sample(self, lat, lon, half_km: float = 16.0) -> pd.DataFrame:
        """DataFrame with EARTH_ENV_COLUMNS, one row per point, in the same order.
        classification = 'KNOWN_ANALOG' if known_region is not None, else 'NEW_CANDIDATE'.
        float32 for numbers, string for texts."""
```

**Memory use in T5:** one `EarthLayers` takes ~420 MB (four 104 MB grids plus the trees). T5 creates it **once, before forking** the `Pool`, so the processes share it copy-on-write. Note this in the docstring.

### 3.5 CLI

```text
python -m pipeline.earth_layers --project-dir P --out-dir RUN_DIR [--build] [--check]
```

- `--build` calls `ensure_cache`.
- `--check` runs the checks of section 6, writes `t6_checks.json`, prints a table, and exits with code 1 if a **hard** criterion fails. It also writes the PNGs (§6.3).

---

## 4. `pipeline/data/known_analogs.json` (hand-written)

The committed file is [pipeline/data/known_analogs.json](../pipeline/data/known_analogs.json). Its bounding boxes are **approximate**: Claude drew them to contain the cited study areas, and they do not come from an official source. Each one therefore carries a `bbox_note`, and the §6 checks review them on a map. The bbox format is `[lon_min, lat_min, lon_max, lat_max]`.

**Validation** in `KnownRegions.__init__`: unique `id`, `lon_min < lon_max` and `lat_min < lat_max`, valid ranges, and a non-empty `source_url`.

| id | Name | Country | bbox | Source |
| --- | --- | --- | --- | --- |
| `atacama` | Atacama Desert | Chile | −71.5, −30.0, −68.0, −18.0 | Wikipedia: Atacama Desert |
| `mcmurdo-dry-valleys` | McMurdo Dry Valleys | Antarctica | 160.0, −78.5, 164.5, −76.5 | Wikipedia: McMurdo Dry Valleys |
| `iceland` | Iceland | Iceland | −24.6, 63.2, −13.4, 66.7 | Wikipedia: Iceland |
| `hawaii-big-island` | Hawaii (Mauna Kea / Kilauea) | United States | −156.1, 18.9, −154.8, 20.3 | Wikipedia: Mauna Kea |
| `devon-island` | Devon Island (Haughton crater) | Canada | −96.0, 74.5, −79.5, 76.8 | Wikipedia: Haughton impact crater |
| `utah-mdrs` | Utah (MDRS, Hanksville) | United States | −111.4, 37.9, −110.2, 38.9 | Wikipedia: Mars Desert Research Station |
| `rio-tinto` | Rio Tinto | Spain | −7.0, 37.1, −6.4, 37.8 | Wikipedia: Rio Tinto (river) |
| `svalbard` | Svalbard | Norway | 10.0, 76.4, 34.0, 80.9 | Wikipedia: Svalbard |
| `pilbara` | Pilbara | Australia | 116.0, −23.5, 121.5, −20.0 | Wikipedia: Pilbara |
| `meteor-crater` | Meteor Crater | United States | −111.35, 34.75, −110.70, 35.30 | Wikipedia: Meteor Crater |
| `lanzarote` | Lanzarote | Spain | −13.88, 28.83, −13.40, 29.25 | Wikipedia: Lanzarote |
| `mojave` | Mojave Desert | United States | −118.0, 34.0, −114.5, 36.5 | Wikipedia: Mojave Desert |

The file also has `analog_for`, `why` and `bbox_note` for every region. If this list comes up in the presentation, say the boxes are approximate. More precision is not needed: they only decide the label and never enter the score.

---

## 5. `tests/test_earth_layers.py` (synthetic data only, no `pyhdf`)

1. **`test_ndvi_from_raw`:** `[-3000, -2500, -2000, 0, 2500, 10000, 12000]` gives `[nan, nan, -0.2, 0.0, 0.25, 1.0, nan]`. The fill value and anything outside `valid_range` give NaN; `-2000` is valid and gives `-0.2`.
2. **`test_lst_c_from_raw`:** `0` gives NaN, `7499` gives NaN, `14658` gives `20.01 °C` (±0.01), and `65535` gives a finite value.
3. **`test_running_ops`:** three 2 × 2 "months" with NaNs scattered among them. The `nanmax` is right, the mean respects `min_count`, and a cell with 2 valid months and `min_count=3` gives NaN.
4. **`test_cell_index_edges`:** `(90, -180)` gives `(0, 0)`; `(-90, 180)` gives `(3599, 0)`, because lon 180 is normalised to −180; `(0, 0)` gives `(1800, 3600)`.
5. **`test_patch_window_stat_antimeridian`:** a grid with 1.0 in column 0 and 0.0 in column 7199. `max` at `(0, 179.99)` with `half_km = 16` gives 1.0, because the window wraps.
6. **`test_patch_window_stat_lat`:** at 60° latitude the window has ~2× the columns it has at the equator (±1).
7. **`test_logistics_densify`:** a `GeoDataFrame` with **one** 2-vertex line from `(0, 0)` to `(0, 10)` (lat 0, lon 0→10), plus a ferry line next to the point.
   - `dist_road_km(0.5, 5.0)` ≈ 55.6 km (±1.5); without densifying it would be ~556 km.
   - The ferry line is ignored.
8. **`test_airports_exclude_military`:** a `military` airport 1 km away and a `mid` one 50 km away. The result is the `mid` one, at ~50 km.
9. **`test_countries_lookup`:** a synthetic "Testland" polygon on `[0,1]×[0,1]`.
   - `(0.5, 0.5)` gives "Testland";
   - `(0.5, 1.1)`, ~11 km outside, also gives "Testland" (coast rule);
   - `(0.5, 3)` gives None.
10. **`test_known_regions_real_file`:** loads the real `pipeline/data/known_analogs.json`.
    - It has 12 regions, unique ids and valid bboxes.
    - `lookup(38.4064, -110.7919)` (MDRS) gives `utah-mdrs`.
    - `lookup(29.07, -110.96)` (Hermosillo) gives None.
11. **`test_sample_schema`:** an `EarthLayers` built by hand from synthetic grids, through a constructor `EarthLayers.from_arrays(...)` added for tests. `sample` returns exactly `EARTH_ENV_COLUMNS`, with a correct `classification`.

---

## 6. Job and checks

### 6.1 `jobs/t6_earth_layers.slurm`

Same shape as `jobs/t4_targets.slurm` (`#!/usr/bin/env bash`, `set -euo pipefail`, conda, an echo with the commit), with:

```bash
#SBATCH -J p089-t6-earth-layers
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH -o /lustre/proyectos/p089/output/t6_earth_layers_%j.log
#SBATCH -e /lustre/proyectos/p089/output/t6_earth_layers_%j.log
...
python -c "import pyhdf" || { echo "pyhdf missing in spaceapps_2026"; exit 2; }
python -m pipeline.earth_layers --project-dir "$PROJECT_DIR" --out-dir "$OUT_DIR" --build --check "$@"
```

- **No installs.** `pyhdf` is already in the environment, so the job must not install anything; if it is missing, the job fails. Add `pyhdf>=0.10` to `pipeline/requirements.txt` with the comment `# only to build the T6 cache (Yuca)`.
- **No separate test run.** The full job takes minutes, and its checks are the test. If it fails, diagnose before resubmitting.
- **No half-built cache.** It is written to `.tmp.tif` and then `os.replace`d.

### 6.2 Criteria (in `--check`, written to `t6_checks.json`)

**Hard** (the job exits with code 1 if one fails):

| # | Check | Criterion |
| --- | --- | --- |
| 1 | Cache | Both `.tif` grids are 3600 × 7200 in EPSG:4326 with `from_origin(-180, 90, 0.05, 0.05)` |
| 2 | `ndvi_max` Sahara: patches at `(26.0, 3.0)` (Algeria) and `(24.0, 28.0)` (Egypt's Western Desert) | < 0.12 (see §6.2.1) |
| 3 | `ndvi_max` Atacama `(-24.5, -69.3)` | < 0.10 |
| 4 | `ndvi_max` Amazon `(-3.5, -62.0)` and Congo `(0.5, 20.0)` | > 0.70 |
| 5 | `dist_road_km` Hermosillo `(29.07, -110.96)` | < 5 |
| 6 | `country` at Hermosillo / Atacama / Sahara `(26.0, 3.0)` | `Mexico` / `Chile` / `Algeria` |
| 7 | `known_region` at MDRS `(38.4064, -110.7919)` and at Hermosillo | `utah-mdrs` / None |
| 8 | Area-weighted (`cos(lat)`) fraction of cells with a finite `ndvi_max` | > 0.25 (land covers ~29 % of the globe; see §6.2.1) |

**Soft** (reported; they do not fail the job, but report any that fail):

| # | Check | Expected |
| --- | --- | --- |
| 9 | `lst_day_c` Dry Valleys `(-77.5, 162.0)` | < 0 °C |
| 10 | `lst_amplitude_c` Sahara `(26.0, 3.0)` vs. the Amazon | Sahara > 15 °C, and above the Amazon |
| 11 | `dist_road_km` Dry Valleys | > 1000 km (no roads in Antarctica) |
| 12 | Fraction of the grid with `ndvi_max ≤ 0.25` | Print it: it estimates how many patches pass the T5 prefilter |
| 13 | Time of `EarthLayers.sample` on 10,000 random land points | Print it; it should be < 30 s so T5 does not stall |

#### 6.2.1 Adjustments after the first run (job 2242426, decided by Claude on 2026-11-13)

The two hard checks that failed in the first run were badly specified in this plan; the code and the data were correct.

- **#2:** the Sahara threshold is now **`< 0.12`**. Bright bare soil gives NDVI of 0.05–0.12. At `(24.0, 28.0)`, all 12 months have pixel reliability 0 ("good"), and the median of the maximum is 0.103. That is still far below the prefilter cut of 0.25.
- **#8:** the fraction of cells with a finite `ndvi_max` is now **area-weighted** (`cos(lat)`) and must be `> 0.25`. The measured value is 0.2696. The unweighted version over-represents the poles, and MOD13C2 has no data south of −59.45°.
- **Consequence for T5:** a NaN NDVI passes the prefilter only where LST exists ([plan_t5.md](plan_t5.md) §2.5.3).

After these fixes, job 2242430 passed 8/8 hard and 5/5 soft.

### 6.3 PNG maps in `runs/<JOBID>/`

These are control images, not for the presentation:

- **`map_ndvi_max.png`:** the grid downsampled ×4, `cmap='YlGn'`, `vmin=0`, `vmax=0.9`, with the NDVI = 0.25 contour in red;
- **`map_lst_amplitude.png`:** the same, with `cmap='magma'`;
- **`map_known_analogs.png`:** NDVI in grey with the 12 bboxes drawn and labelled. Check by eye that each rectangle sits on its region.

---

## 7. Commands for Owen on Yuca

Over SSH or in the Open OnDemand shell, from `/lustre/proyectos/p089/code`:

```bash
cd /lustre/proyectos/p089/code && git pull
```

```bash
sbatch -A p089 -p cpu --time=00:15:00 --mem=4G -o /lustre/proyectos/p089/output/tests_t6_%j.log --wrap 'bash -c "source /apps/miniconda3/etc/profile.d/conda.sh && conda activate spaceapps_2026 && cd /lustre/proyectos/p089/code && pytest -q tests"'
```

```bash
sbatch jobs/t6_earth_layers.slurm
```

```bash
tail -n 80 /lustre/proyectos/p089/output/t6_earth_layers_<JOBID>.log
```

Then download the 3 PNGs from `runs/<JOBID>/` through OOD Files to review them. The `.tif` caches do **not** need to go into the offline kit; the laptop tests use synthetic grids.

---

## 8. Documentation (same commit, then updated after the job)

- **[logbook.md](logbook.md):** a new entry with what was done, the job id, the check table (hard and soft), and a note that Gemini wrote the code from this plan.
- **[pipeline.md](pipeline.md):**
  - the two derived caches, in the data table;
  - MOD13C2 (`/10000`, fill −3000) and MOD11C3 (`×0.02`, fill 0) in the scale table, with the opposite-convention warning;
  - the note "GDAL has no HDF4: use pyhdf";
  - the run.
- **[handoff.md](handoff.md):** T6 done, with the job id and the cache paths.

---

## 9. What NOT to do

- Do not apply the MODIS `scale_factor` generically (`value * scale_factor`): on MOD13C2 that gives NDVI × 10000.
- Do not install `libgdal-hdf4` or modify the conda environment.
- Do not overwrite the cache. To rebuild it, move the old file to `/lustre/proyectos/p089/_to_delete/`.
- Do not use `known_region` or `country` in the score: they only label.
- Do not invent new coordinates or bboxes. If a region looks wrongly drawn in `map_known_analogs.png`, report it and propose the change.
- Do not import the v1 scripts.

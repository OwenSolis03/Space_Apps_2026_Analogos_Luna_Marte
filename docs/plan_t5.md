# Detailed plan T5: Earth sweep

Full specification of T5. It expands section T5 of [implementation_plan.md](implementation_plan.md); where they disagree, **this document wins for T5**. Written by Claude on 2026-11-13 on `main` at `5b33704`, after checking the Copernicus tiles on Yuca that day.

**Status:** implemented by Gemini (commit `52bf3d7`).

| Run | Jobs | Run directory | Result |
| --- | --- | --- | --- |
| Smoke test | 2242432–2242434 | `runs/2242432` | 445/500 valid |
| Full run | 2242438–2242440 | `runs/2242438` | 44,375 candidates, **40,244 valid patches**, 6/6 hard checks |

**Depends on T6:** T5 uses `EarthLayers` and the cache in `data/derived/{ndvi_max_2023,lst_2023}.tif` ([plan_t6.md](plan_t6.md)). The T5 code can be written in parallel, but the T5 run goes **after** the T6 run.

---

## 0. Summary

| What | Where |
| --- | --- |
| Virtual mosaic, prefilter, extraction and merge | `scripts/pipeline/earth_features.py` |
| Jobs (3 chained stages) | `scripts/jobs/t5_prepare.slurm`, `scripts/jobs/t5_earth_features.slurm`, `scripts/jobs/t5_merge.slurm` |
| Submitting the 3 stages with one command | `scripts/jobs/t5_submit.sh` |
| Tests | `tests/test_earth_features.py` |
| Shared cache (not committed) | `data/derived/copernicus_90m.vrt` |
| Outputs (in `runs/<PREP_JOBID>/`) | `candidates.parquet`, `prefilter_stats.json`, `features_earth_<i>.parquet`, `features_earth.parquet`, `t5_checks.json`, `map_earth_mean_slope_deg.png`, `map_earth_classification.png` |

Commit: `T5: Earth sweep`. **Commit and push before submitting the jobs.**

---

## 1. Facts checked on Yuca (2026-11-13)

**Copernicus GLO-90 tiles:**

- 26,475 tiles in `data/raw/earth/copernicus_90m/`, all `.tif`, 67 GB.
- Name pattern: `Copernicus_DSM_COG_30_{N|S}{lat:02d}_00_{E|W}{lon:03d}_00_DEM.tif`. The lat/lon in the name is the **lower-left** corner of the 1° cell.
- EPSG:4326, float32, `scales=(1.0,)`.
- **No `nodata`.**
- **The sea inside a coastal tile is exactly `0.0`.** For example, `N29_00_W113` (Gulf of California) has 52.3 % of its pixels at 0.0, and `N29_00_W112` (inland) has 0 %.
- **Tile width shrinks with latitude.** Copernicus lowers the longitude resolution away from the equator. The height is always 1200 px (0.000833°):

| Latitude band | Width (px) |
| --- | --- |
| below 50° | 1200 |
| 50–60° | 800 |
| 60–70° | 600 |
| 70–80° | 400 (0.0025°; for example `S78_00_E162`, `N75_00_W090`) |
| 80–85° | 240 |
| 85–90° | 120 |

- Where there is no land, **there is no tile**.

**Earth grid** (`generate_grid("Earth")`, the same function as T3):

| Count | Centres |
| --- | --- |
| Total | 497,818 |
| With a tile in their 1° cell | 179,663 |
| … south of −60° (Antarctica) | 14,959 |
| … between −60° and 60° | 143,426 |
| … north of 60° | 21,278 |

**Tools:** `gdalbuildvrt` is in the environment (`~/.conda/envs/spaceapps_2026/bin/`). Outside conda it is not on the `PATH`.

---

## 2. Decisions (do not change them without asking)

1. **The sea is masked in the mosaic, not in Python.** The VRT is built with `-srcnodata 0 -vrtnodata -9999`:
   - tile zeros and areas without a tile become nodata `-9999`;
   - `extract_patch` already masks `src.nodata` and returns `None` below 90 % valid pixels;
   - so **a patch with more than 10 % sea is dropped on its own**.

   Accepted side effect: land at exactly 0.0 m is also masked. That is negligible, because the values are continuous float32.
2. **VRT resolution: `-resolution highest`** (0.000833°). High-latitude tiles are nearest-neighbour upsampled inside the VRT. That does not matter, because `extract_patch` averages down to 500 m afterwards.
3. **Three stages instead of one array:**
   - **`prepare`** (one job): builds the VRT if missing, applies the prefilter, and computes **once** every T6 Earth column for each candidate;
   - **the array** (32 tasks): only extracts DEM patches, with the same number of candidates per task;
   - **`merge`**: joins the stripes with the `prepare` columns and runs the checks.

   This way `EarthLayers` (~420 MB) is not loaded 32 times, and the stripes are balanced.
4. **Run id = the JOBID of `prepare`.** All three stages write to `runs/<PREP_JOBID>/`. It is the one exception to "each job in its own `runs/$SLURM_JOB_ID/`", and it is documented in `pipeline.md`. The logs still carry each job's own id.
5. **Prefilter,** in this order, with every drop counted in `prefilter_stats.json`:
   1. No Copernicus tile in the 1° cell of the **centre**: drop (`no_tile`).
   2. The patch's `ndvi_max` (window median, `EarthLayers.ndvi_prefilter`) **> 0.25**: drop (`vegetated`).
   3. A **NaN** `ndvi_max` passes **only if** the window's `lst_day_c` is finite (`patch_window_stat(..., 'mean')` on LST band 1).
      - That is land without NDVI, such as Antarctica, where MOD13C2 has no data south of −59.45°. It is flagged `ndvi_missing = True`.
      - If NDVI and LST are both NaN, the centre is over the sea (coastal tiles, atolls), and the patch is dropped (`no_land_data`).
      - Measured with the T6 cache (job 2242426): 35,483 centres with a tile have NaN NDVI; 14,959 of them are south of −60° and 20,524 north of it, almost all over the sea.
6. **Same functions as T3:** `extract_patch(src, lat, lon, body="Earth")` and `compute_features`. `geo.py` and `features.py` do not change. Patches crossing ±180° are skipped and counted; 140 centres with a tile have `|lon| > 179.5°`.

---

## 3. `scripts/pipeline/earth_features.py`

### 3.1 Tiles and VRT

```python
TILE_RE = re.compile(r"_(?P<ns>[NS])(?P<lat>\d{2})_00_(?P<ew>[EW])(?P<lon>\d{3})_00_DEM\.tif$")
VRT_NODATA = -9999.0

def parse_tile_cell(name: str) -> tuple[int, int]:
    """'..._S78_00_E162_00_DEM.tif' -> (-78, 162); '..._N00_00_W001_00_DEM.tif' -> (0, -1).
    ValueError if the name does not match."""

def load_tile_cells(copernicus_dir: Path) -> set[tuple[int, int]]:
    """Cells (lat_floor, lon_floor) that have a tile, from the file names (no file is opened)."""

def has_tile(lat: np.ndarray, lon: np.ndarray, cells: set[tuple[int, int]]) -> np.ndarray:
    """Per point: (floor(lat), floor(lon)) in cells. Careful with negatives: floor(-0.5) = -1."""

def build_vrt(copernicus_dir: Path, vrt_path: Path) -> Path:
    """If vrt_path exists, do nothing and return it.
    Otherwise write the tile list (sorted) to vrt_path.with_suffix('.list.txt') and run
      gdalbuildvrt -overwrite -resolution highest -srcnodata 0 -vrtnodata -9999 \
                   -input_file_list <list> <vrt_path>.tmp.vrt
    with subprocess.run(check=True), then os.replace(<tmp>, vrt_path).
    Find gdalbuildvrt with shutil.which; if missing, RuntimeError('activate spaceapps_2026').
    Then open the VRT with rasterio and check: crs EPSG:4326, nodata == -9999,
    |res| == (1/1200, 1/1200) within 1e-9; print width, height and bounds."""
```

### 3.2 `prepare` stage

```python
CANDIDATE_COLUMNS = ["lat", "lon", *EARTH_ENV_COLUMNS, "ndvi_missing"]   # EARTH_ENV_COLUMNS from T6
NDVI_PREFILTER_MAX = 0.25

def prefilter(lat, lon, cells, layers: EarthLayers) -> tuple[np.ndarray, dict]:
    """Candidate mask and counts {grid, no_tile, vegetated, no_land_data, ndvi_missing, kept}."""

def prepare_candidates(project_dir: Path, out_dir: Path, limit: int | None = None) -> Path:
    """1) build_vrt(...) into data/derived/copernicus_90m.vrt.
       2) generate_grid('Earth').
       3) prefilter. Call ndvi_prefilter only on the points that have a tile.
       4) If limit: apply_limit on the candidates AFTER filtering (the test uses real candidates).
       5) layers.sample(...) on the candidates -> T6 columns; ndvi_missing.
       6) Sort by (lat, lon) and write out_dir/candidates.parquet and prefilter_stats.json.
       Print the counts and the classification distribution."""
```

### 3.3 Extraction stage (array)

```python
EARTH_FEATURE_COLUMNS = ["lat", "lon", *FEATURE_NAMES, "valid_frac"]

def _init_earth_worker(vrt_path: str, size_km: float, res_m: float) -> None   # opens the VRT once per process
def _process_earth_point(point: tuple[float, float]) -> dict | None           # extract_patch + compute_features

def extract_stripe(run_dir: Path, stripe_idx: int, num_stripes: int, workers: int,
                   vrt_path: Path) -> Path:
    """Reads run_dir/candidates.parquet (lat and lon only), select_stripe (T3's),
    Pool(workers, initializer=_init_earth_worker), imap with a chunksize as in T3.
    Writes run_dir/features_earth_<stripe_idx>.parquet with EARTH_FEATURE_COLUMNS
    (lat/lon float64, the rest float32). Prints valid / candidates for the stripe, the time, and
    min/median/p95/max of mean_slope_deg, relief_m and mean_elev_m (as in T3)."""
```

### 3.4 `merge` stage

```python
EARTH_COLUMNS = ["body", "lat", "lon", *FEATURE_NAMES, "valid_frac",
                 *EARTH_ENV_COLUMNS, "ndvi_missing"]

def merge_earth(run_dir: Path, num_stripes: int, allow_missing: bool = False) -> Path:
    """Concatenates features_earth_<i>.parquet. If one is missing: error, unless allow_missing
    (plan B: partial coverage; print which stripes are missing and the % of candidates covered).
    Inner join with candidates.parquet on exact (lat, lon) (same grid, rounded to 6 decimals).
    Checks that no stripe row is left without a match. body = 'Earth'.
    Writes run_dir/features_earth.parquet with EARTH_COLUMNS."""

def plot_earth_maps(df: pd.DataFrame, run_dir: Path) -> None:
    """map_earth_mean_slope_deg.png (same style as T3's plot_slope_map) and
    map_earth_classification.png (NEW_CANDIDATE grey, KNOWN_ANALOG orange, ndvi_missing blue)."""

def run_checks(df: pd.DataFrame, run_dir: Path) -> bool:
    """Section 6. Writes t5_checks.json; returns False if a hard criterion fails."""
```

### 3.5 CLI

```text
python -m pipeline.earth_features prepare --project-dir P --run-dir R [--limit N]
python -m pipeline.earth_features extract --project-dir P --run-dir R --stripe-idx I --num-stripes K --workers W
python -m pipeline.earth_features merge   --run-dir R --num-stripes K [--allow-missing]
```

`merge` exits with code 1 if `run_checks` returns False.

---

## 4. Jobs

All three `.slurm` files follow the shape of `scripts/jobs/t4_targets.slurm`: `#!/usr/bin/env bash`, `set -euo pipefail`, conda, an echo with the commit, and **no `pip install`** (everything is already in the environment). `RUN_DIR` comes in through `--export`.

| Script | Resources | Command |
| --- | --- | --- |
| `t5_prepare.slurm` | `-J p089-t5-prepare`, 4 CPUs, 24G, `--time=01:30:00`, log `t5_prepare_%j.log` | `RUN_DIR=${RUN_DIR:-$PROJECT_DIR/runs/$SLURM_JOB_ID}`; `python -m pipeline.earth_features prepare ... "$@"` |
| `t5_earth_features.slurm` | `-J p089-t5-earth`, `--array=0-31%30`, 16 CPUs, 32G, `--time=03:00:00`, log `t5_earth_%A_%a.log` | `extract --stripe-idx $SLURM_ARRAY_TASK_ID --num-stripes ${NUM_STRIPES:-32} --workers $SLURM_CPUS_PER_TASK`; export `GDAL_CACHEMAX=256`, `OMP_NUM_THREADS=1` |
| `t5_merge.slurm` | `-J p089-t5-merge`, 2 CPUs, 16G, `--time=00:30:00`, log `t5_merge_%j.log` | `merge --num-stripes ${NUM_STRIPES:-32} ${ALLOW_MISSING:+--allow-missing}` |

**Group limit:** 30 simultaneous tasks × 16 CPUs = 480 CPUs, under 500. If other group jobs are running, `%30` keeps the total from going over.

**`scripts/jobs/t5_submit.sh`** runs on the login node and only calls `sbatch`. That is a short command, also allowed in the OOD shell.

```bash
#!/usr/bin/env bash
# Usage: bash scripts/jobs/t5_submit.sh            (full run, 32 stripes)
#        bash scripts/jobs/t5_submit.sh --limit 500 (test: 1 stripe)
set -euo pipefail
cd "$(dirname "$0")/.."
LIMIT_ARGS=(); NUM_STRIPES=32; ARRAY="0-31%30"
if [[ "${1:-}" == "--limit" ]]; then LIMIT_ARGS=(--limit "$2"); NUM_STRIPES=1; ARRAY="0-0"; fi
PREP=$(sbatch --parsable scripts/jobs/t5_prepare.slurm "${LIMIT_ARGS[@]}")
RUN_DIR=/lustre/proyectos/p089/runs/$PREP
ARR=$(sbatch --parsable --dependency=afterok:$PREP --array="$ARRAY" \
      --export=ALL,RUN_DIR=$RUN_DIR,NUM_STRIPES=$NUM_STRIPES scripts/jobs/t5_earth_features.slurm)
MRG=$(sbatch --parsable --dependency=afterok:$ARR \
      --export=ALL,RUN_DIR=$RUN_DIR,NUM_STRIPES=$NUM_STRIPES scripts/jobs/t5_merge.slurm)
echo "prepare=$PREP array=$ARR merge=$MRG run_dir=$RUN_DIR"
```

`--array` on the command line overrides the `#SBATCH --array` in the file.

**Plan B,** if a stripe fails and there is no time to repeat it:

```bash
sbatch --export=ALL,RUN_DIR=<run_dir>,NUM_STRIPES=32,ALLOW_MISSING=1 scripts/jobs/t5_merge.slurm
```

The app must then say "partial coverage: X % of the candidates".

---

## 5. `tests/test_earth_features.py` (synthetic)

1. **`test_parse_tile_cell`:**
   - `S78_00_E162` gives `(-78, 162)`;
   - `N00_00_W001` gives `(0, -1)`;
   - `N89_00_E179` gives `(89, 179)`;
   - an invalid name raises `ValueError`.
2. **`test_has_tile_negative_floor`:** with `cells = {(-1, -1)}`, `(-0.5, -0.5)` is True and `(0.5, -0.5)` is False.
3. **`test_build_vrt_masks_sea`** (skipped if `shutil.which('gdalbuildvrt')` is None):
   - two synthetic 1° × 1° tiles in EPSG:4326 at 1/1200° without nodata: one land tile (z = 100 + ramp) and one with its western half at 0.0 (sea);
   - in the VRT, `src.nodata == -9999` and a sea pixel reads −9999;
   - `extract_patch` over the sea gives `None`, and over land a 64 × 64 array.
4. **`test_build_vrt_mixed_widths`** (same skip):
   - a 1200 × 1200 tile at lat 69–70 and a 1200 × 400 (height × width) tile at lat 70–71;
   - the VRT builds, and a patch centred on the seam (lat 70.0) has no holes: every value is finite.
5. **`test_build_vrt_does_not_overwrite`:** if `vrt_path` already exists, `build_vrt` leaves it untouched (same modification time).
6. **`test_prefilter_counts`:** a synthetic `EarthLayers.from_arrays` (from T6) and 5 points:

   | Point | Expected |
   | --- | --- |
   | No tile | Dropped (`no_tile`) |
   | NDVI 0.4 | Dropped (`vegetated`) |
   | NDVI 0.2 | Kept |
   | NDVI NaN, LST finite (ice) | Kept, `ndvi_missing` |
   | NDVI NaN, LST NaN (sea) | Dropped (`no_land_data`) |

   - The mask is `[F, F, T, T, F]`, and `ndvi_missing` is set only on the fourth point.
   - The counts are `{grid: 5, no_tile: 1, vegetated: 1, no_land_data: 1, ndvi_missing: 1, kept: 2}`.
7. **`test_merge_join`:** `candidates.parquet` with 5 rows, and two stripes with 2 and 1 valid rows.
   - The result has 3 rows, the exact `EARTH_COLUMNS`, `body == 'Earth'`, and the T6 columns copied correctly.
   - A missing stripe makes `merge_earth` fail, unless `allow_missing=True`.

---

## 6. Acceptance criteria

### 6.1 `prepare` (log and `prefilter_stats.json`)

- `grid = 497,818` and `grid − no_tile = 179,663`, exactly.
- `kept` between 35,000 and 80,000. The estimate from the T6 cache is ~45,000: 30,245 with NDVI ≤ 0.25 plus ~15,000 in Antarctica. If it falls outside, **stop and report** before launching the array.
- Print `ndvi_missing` and `no_land_data` with their distribution by latitude. `ndvi_missing` is expected almost entirely south of −60°.

### 6.2 Test run (`bash scripts/jobs/t5_submit.sh --limit 500`)

- All three stages finish without errors.
- At least 70 % of the 500 are valid; the rest are mostly coastal patches with more than 10 % sea.
- The stripe takes under 5 minutes.
- In `features_earth.parquet`, `mean_elev_m` is between −500 and 7000 m, and the median `mean_slope_deg` is between 0.5° and 6°.

### 6.3 Full run (`merge` → `t5_checks.json`)

**Hard:**

| # | Check | Criterion |
| --- | --- | --- |
| 1 | Valid patches | Between 30,000 and 80,000. The general plan said 40–120 thousand before there was data; with the T6 cache ~45 thousand candidates are expected, minus the coastal ones the VRT drops. Under 30 thousand means checking the VRT sea mask |
| 2 | Amazon `lat ∈ [-10, 2], lon ∈ [-75, -50]` | ≤ 5 patches, listed |
| 3 | Congo `lat ∈ [-5, 5], lon ∈ [12, 30]` | ≤ 5, listed |
| 4 | Equatorial Indonesia `lat ∈ [-5, 5], lon ∈ [95, 120]` | ≤ 5, listed |
| 5 | Present (≥ 1 patch each): Atacama `known_region == 'atacama'`; Sahara `lat ∈ [15, 30], lon ∈ [-10, 30]`; Sonora `lat ∈ [28, 33], lon ∈ [-115, -110]`; central Australia `lat ∈ [-28, -20], lon ∈ [125, 138]`; Dry Valleys `known_region == 'mcmurdo-dry-valleys'` | All present |
| 6 | Join with `candidates` | No orphan rows; no T6 column entirely NaN |

The general plan asked for "no patch" in the Amazon, the Congo and Indonesia. Up to 5 are tolerated here, because the median NDVI of a patch over a clearing, a mine or a town could drop below 0.25. More than 5 means the filter is wrong.

**Soft** (print, and report anything odd):

| # | Check | Expected |
| --- | --- | --- |
| 7 | Count per `known_region` | Print all 12. Some may be 0 because of vegetation (Iceland, Hawaii, Svalbard, Rio Tinto). That is not an error, but note it in the logbook, because it affects which known analogs appear in the app |
| 8 | `NEW_CANDIDATE` vs `KNOWN_ANALOG` | Print the ratio; more than 95 % `NEW_CANDIDATE` is expected |
| 9 | By country | Print the top 15 countries by number of patches; Mexico should appear |
| 10 | `ndvi_missing` | Print how many valid patches have it |
| 11 | Map | `map_earth_mean_slope_deg.png` shows the Andes, the Himalaya and Tibet, the flat Sahara and the Antarctic plateau |

### 6.4 Outcome of the full run (2242438–2242440)

- **Prefilter:** 44,375 candidates. Of the centres with a tile, 113,935 were dropped as vegetated and 21,353 as sea; 14,130 have `ndvi_missing`.
- **Patches:** 40,244 valid (90.7 %).
- **Hard checks:** 6/6.
  - Amazon, Congo and Indonesia have 0 patches each.
  - Atacama 324, Sahara 6,542, Sonora 78, central Australia 508, Dry Valleys 14.
- **Soft checks:** 4/5. The one that failed is "Mexico in the top 15": Antarctica (12,125) and the big deserts dominate by area, and Mexico's arid land is much smaller.
- **Known regions with 0 patches:** Hawaii, Rio Tinto and Lanzarote (vegetation or sea).
- **Offline kit:** `kit/t5_2242438.tar.gz`.

---

## 7. Commands for Owen on Yuca

Over SSH or in the Open OnDemand shell, from `/lustre/proyectos/p089/code`. **Requirement:** T6 has run and its cache exists.

```bash
cd /lustre/proyectos/p089/code && git pull && ls -la /lustre/proyectos/p089/data/derived/
```

```bash
sbatch -A p089 -p cpu --time=00:15:00 --mem=4G -o /lustre/proyectos/p089/output/tests_t5_%j.log --wrap 'bash -c "source /apps/miniconda3/etc/profile.d/conda.sh && conda activate spaceapps_2026 && cd /lustre/proyectos/p089/code && pytest -q tests"'
```

```bash
bash scripts/jobs/t5_submit.sh --limit 500
```

```bash
squeue -u owen
```

Check `t5_prepare_<PREP>.log`, `t5_earth_<ARR>_0.log` and `t5_merge_<MRG>.log` in `/lustre/proyectos/p089/output/`. If everything meets §6.2:

```bash
bash scripts/jobs/t5_submit.sh
```

When it finishes, pack the output for the offline kit (a few MB), since T7 needs it to develop on the laptop:

```bash
cd /lustre/proyectos/p089 && tar -czf kit/t5_<PREP>.tar.gz runs/<PREP>/features_earth.parquet runs/<PREP>/prefilter_stats.json runs/<PREP>/t5_checks.json runs/<PREP>/map_earth_*.png
```

---

## 8. Documentation

- **[logbook.md](logbook.md):** a new entry with the prepare, array and merge job ids, `prefilter_stats` and the check table. Say the code was written by Gemini from this plan.
- **[pipeline.md](pipeline.md):**
  - the VRT among the derived data;
  - the note "Copernicus: no nodata, sea = 0.0, width varies with latitude";
  - the shared run directory exception;
  - the run.
- **[handoff.md](handoff.md):** T5 done, with `runs/<PREP>/features_earth.parquet` as the T7 input.
- **[working_without_ssh.md](working_without_ssh.md):** add the `t5_<PREP>.tar.gz` kit.

---

## 9. What NOT to do

- Do not modify `geo.py` or `features.py`: Earth uses the same functions as Mars and the Moon.
- Do not treat 0.0 as a valid elevation, and do not filter the sea in Python with thresholds; the VRT does it.
- Do not load `EarthLayers` in the array tasks.
- Do not overwrite `copernicus_90m.vrt`. To rebuild it, move the old one to `/lustre/proyectos/p089/_to_delete/`.
- Do not launch the full run without reviewing the `--limit 500` run.
- Do not resubmit the whole array if it fails. Diagnose the failed stripe from its log, then:
  1. resubmit only that stripe: `sbatch --array=<i> --export=ALL,RUN_DIR=<run_dir>,NUM_STRIPES=32 scripts/jobs/t5_earth_features.slurm`;
  2. run `merge` again with the same `--export`.

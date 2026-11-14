# Detailed plan T4: curated targets and clusters

Full specification of T4, written so it can be implemented without guessing. It expands section T4 of [implementation_plan.md](implementation_plan.md); where they disagree, **this document wins for T4**. Written by Claude on 2026-11-13 with `main` at `51678d9` and the T3 run `2242278`.

**Status:** implemented by Gemini and run on 2026-11-13 (commit `115e0c3`, run `2242423`): 16/16 curated targets and 60 clusters. See [HISTORY.md](HISTORY.md) §9.

Read first: section 0 (rules) of `implementation_plan.md`, and all of `pipeline/planet_features.py`.

---

## 0. Summary

| What | Where |
| --- | --- |
| Curated target definitions (hand-written, committed) | `pipeline/data/targets.json` |
| Extraction of patches that contain a pole (Shackleton only) | `pipeline/geo.py` (T4.0) |
| Sampling a point with the same code as T3 | `pipeline/planet_features.py` (refactor, no behaviour change) |
| Reusable IAU nomenclature | `pipeline/iau.py` (new) |
| Curated features, clusters and outputs | `pipeline/targets.py` (new) |
| Job | `jobs/t4_targets.slurm` (new) |
| Tests | `tests/test_targets.py` and `tests/test_iau.py` (new), plus 3 new tests in `tests/test_geo.py` |
| Run outputs (not committed) | `runs/<JOBID>/targets.parquet`, `targets_patches.parquet`, `targets.json`, `clusters_{mars,moon}.parquet`, `map_targets_{mars,moon}.png` |

**Suggested commits:** `T4.0: support patches that contain a pole` and `T4: curated targets and clusters`. A single `T4: ...` commit is also fine, as long as the logbook mentions both parts.

**Language:** user-facing texts (`name`, `category`, `why`) are in **English**, because the app interface is in English.

---

## 1. Decisions already made (do not change them without asking)

1. **NASA publishes no centre coordinates for the Artemis III regions.** The 2024-10-28 announcement and the LPSC 2026 abstract (NTRS 20250011660) give only names.
   - Each region is anchored on the IAU feature of the same name, from the gazetteer already on Yuca (`data/raw/nomenclature/MOON_nomenclature_center_pts.*`).
   - The JSON says so in `anchor.note`, and the app must say "approximate location".
2. **Two pairs of regions are merged.** Each pair shares an anchor, so it would give identical features, and counting it twice would mislead:
   - "Nobile Rim 1" and "Nobile Rim 2" become one target (`moon-a3-nobile-rim`);
   - "Mons Mouton" and "Mons Mouton Plateau" become one target (`moon-a3-mons-mouton`).
3. **Anchor types:**
   - `point`: a central patch plus 4 neighbours shifted 16 km at azimuths 0°, 90°, 180° and 270° (5 patches);
   - `rim`: 8 patches centred on the crater rim, at `radius_km = IAU diameter / 2` from the centre, at azimuths 0°, 45°, …, 315°. It represents a "Rim" region.
4. **Minimum valid patches:** `point` needs ≥ 3 of 5, and `rim` ≥ 5 of 8. Otherwise the target gets `status = "insufficient_coverage"`, no features, and does not go into T7.
5. **Target features** are the `nanmean` of the features of its valid patches, computed with **exactly** T3's `_process_point`. That guarantees they are comparable.
6. **Clusters:** k-means with k = 30 per body on the 6 terrain features, without `mean_elev_m`.
   - Apply `log1p` to `relief_m`, `detrended_std_m` and `tri_m`, then standardise per body. T7 uses the same transform.
   - The representative is a **real T3 patch**: the member closest to the centroid.
7. **Do not import `enrich_nomenclature.py`.** It has no `if __name__ == "__main__"` guard, so importing it runs it and rewrites `/lustre/proyectos/p089/output/planetary_baselines.json`. That happened once on 2026-11-13; the file came out identical, but it must not happen again. Its logic is **copied** into `pipeline/iau.py`.
8. **Longitudes:** the gazetteer stores `center_lon` in 0–360 °E. Always convert to −180…180 with `((lon + 180) % 360) - 180`.

---

## 2. T4.0: polar support in `pipeline/geo.py`

**Problem.** Shackleton is at −89.67°, so its 32 km patch contains the south pole. Today `extract_patch` drops it in two ways:

- `_patch_crosses_antimeridian` sees a longitude range > 180°;
- the `(right - left) > max_span` check in the source CRS fails.

Both return `None` and add to the antimeridian counter.

**Change.** Before the antimeridian check, detect whether the patch contains a pole. If it does, read a full band of rows.

```python
def _patch_contains_pole(lat: float, half_m: float, r_sphere: float) -> int:
    """-1 if the patch contains the south pole, +1 for the north pole, 0 otherwise.
    Criterion: angular distance from the centre to the pole <= angular half-diagonal of the patch."""
    half_diag_deg = math.degrees(half_m * math.sqrt(2.0) / r_sphere)
    if 90.0 - lat <= half_diag_deg:
        return 1
    if 90.0 + lat <= half_diag_deg:
        return -1
    return 0
```

**Polar branch** inside `extract_patch`, only when `has_cut` and `_patch_contains_pole(...) != 0`:

1. **Skip** `_patch_crosses_antimeridian` and the `max_span` check.
2. **Band edge latitude** (south pole): `lat_lim = -90 + (90 + lat) + half_diag_deg + 0.05`.
3. **Source window:** **all columns** (`col_off=0`, `width=src.width`), and the rows from the raster's polar edge to `lat_lim`.
   - Projected CRS: transform `(0, lat_lim)` from the body's lon/lat to the source CRS with `pyproj.Transformer` (`always_xy=True`), then use `src.index(x, y)`.
   - Geographic CRS: use `src.index(0, lat_lim)` directly.
4. **Reduced read,** with its own factors (at 89° the normal factor is too small):
   - Y: `factor_polar = max(1, floor(res_m / res_y_m))`;
   - X: `out_w = min(src.width, 8192)`.

   LOLA (≈ 92,600 columns) is then read at ~8192 columns, still finer than 500 m at −89°. Memory ≈ 8192 × (≤ 300 rows) × 4 B < 10 MB.
5. **Reproject** with the array and its `win_transform`, exactly as today. The target AEQD grid, centred on the patch, has no seam at the pole. The ±180° seam of the source array is a single line of pixels, which `Resampling.average` tolerates.
6. **Everything else** (90 % valid threshold, nodata cleaning) is unchanged.

**Why T3 does not change.** On the T3 grid (|lat| ≤ 88) no patch contains a pole, so the new branch never triggers in T3:

| Body | Half-diagonal | Contains a pole at 88°? |
| --- | --- | --- |
| Moon | 0.75° (88 + 0.75 < 90) | No |
| Mars | 0.38° | No |
| Earth | 0.20° | No |

The 17 existing tests must keep passing untouched.

**New tests in `tests/test_geo.py`:**

- **`test_polar_patch_constant`:** a synthetic equirectangular Moon raster (`+proj=eqc +R=1737400`, 0.05°/px, covering −90…−80) with constant `z = 100`. `extract_patch(lat=-89.67, lon=129.78, body="Moon")` returns a 64 × 64 array, not `None`, with every value ≈ 100 (±0.01).
- **`test_polar_patch_plane`:** the same raster with `z = y_m * tan(5°)`, a plane in projection coordinates. The result must **not** be `None`, and ≥ 90 % of its values must be finite. The slope is not checked, because a plane in eqc is not planar near the pole.
- **`test_antimeridian_count_unchanged`:** a patch at lat −60, lon 179.9 still returns `None` and adds 1 to the counter.

**Plan B,** if T4.0 takes more than an hour: leave Shackleton with `status = "insufficient_coverage"`. That still leaves 7 lunar targets, above the minimum of 6. Say so and carry on with the rest of T4.

---

## 3. Refactor in `pipeline/planet_features.py` (no behaviour change)

**Goal:** T4 computes a point's features with **the same** `_process_point` as T3, without copying code.

**1. Path resolution** moves out of `run_body_extraction` into a public function:

```python
def resolve_body_paths(body: str, raw_dir: Path, derived_dir: Path | None,
                       need_diviner: bool,
                       file_overrides: dict[str, Path] | None = None
) -> tuple[Path, dict[str, str], str | None, str | None]:
    """Returns (dem_path, aux_paths, diviner_tab_path, diviner_parquet_path).
    Same logic as today: missing auxiliary layers are skipped with [WARN], and Diviner is
    prepared only if need_diviner and body == 'Moon'."""
```

`run_body_extraction` calls it with `need_diviner = any(lat <= -75 for lat, _ in stripe_points)`, and still prints the `[META]` lines.

**2. A public point sampler:**

```python
class PointSampler:
    """Opens a body's DEM and auxiliary layers once and computes the T3 row of a point."""
    def __init__(self, body: str, raw_dir: Path, derived_dir: Path,
                 size_km: float = PATCH_SIZE_KM, res_m: float = PATCH_RES_M,
                 file_overrides: dict[str, Path] | None = None): ...
        # Calls resolve_body_paths(..., need_diviner=True) and _init_worker(...)
    def sample(self, lat: float, lon: float) -> dict[str, object] | None:
        return _process_point((lat, lon))
    def close(self) -> None: _close_worker()
    def __enter__(self): return self
    def __exit__(self, *exc): self.close()
```

`_WORKER_STATE` is global per process, so only one `PointSampler` can be open at a time in a process. Document that in the docstring, and raise `RuntimeError` if a second one is opened before the first is closed.

**3. Criterion:** `pytest -q tests` stays green, and a T3 `--limit 500` run would give the same rows. It does not need to be run: the diff of `run_body_extraction` should only move code.

---

## 4. `pipeline/iau.py` (new)

A clean copy of the logic in `enrich_nomenclature.py`, as functions, with no side effects on import.

```python
IAU_SHP: dict[str, str] = {
    "Mars": "nomenclature/MARS_nomenclature_center_pts.shp",
    "Moon": "nomenclature/MOON_nomenclature_center_pts.shp",
}

def load_gazetteer(body: str, raw_dir: Path) -> pd.DataFrame:
    """Reads the gazetteer with geopandas and returns name, type, diameter_km, lat, lon (−180..180)
    and link (https). Drops rows without a name or with non-finite coordinates."""

def haversine_km(lat1, lon1, lat2, lon2, radius_km) -> np.ndarray:  # vectorised

def iau_label(lat: float, lon: float, gaz: pd.DataFrame, radius_km: float,
              near_km: float = 80.0, major_diam_km: float = 30.0) -> dict[str, object]:
    """Same rule as v1:
    nearest = the closest feature; regional = the closest with diameter >= 30 km (any if none);
    display_label = f"{nearest} ({type})" if d_nearest < 80 km, else f"Near {regional} ({type})".
    Returns {nearest_feature, feature_type, distance_km, regional_landmark, regional_type,
    regional_distance_km, display_label, link}; distances rounded to 0.1 km.
    `link` belongs to the feature used in display_label."""

def find_feature(gaz: pd.DataFrame, name: str) -> pd.Series:
    """Exact, case-insensitive name lookup. KeyError if missing."""
```

**Details:**

- `radius_km` comes from `BODY_RADII_M[body] / 1000`.
- `link` turns `http://planetarynames.wr.usgs.gov/...` into `https://`.
- The real gazetteer columns, checked on Yuca, are `name`, `clean_name`, `diameter`, `center_lat`, `center_lon`, `type`, `link`, …

**`tests/test_iau.py`** (a synthetic DataFrame, no files):

- converting 0–360 to −180…180: `center_lon = 354.83` gives `-5.17`;
- `iau_label` 10 km from a feature returns its name in `display_label`;
- 200 km from everything it returns `"Near <regional> (<type>)"`;
- the haversine distance between (0, 0) and (0, 1°) on the Moon is ≈ 30.32 km (±0.01).

---

## 5. `pipeline/data/targets.json` (new, hand-written)

The committed file is [pipeline/data/targets.json](../pipeline/data/targets.json). Copy it **as is**:

- **Moon:** the coordinates are IAU centres from the Yuca gazetteer, already converted to −180…180.
- **Mars:** the coordinates are landing points, verified on 2026-11-13.

Do not change any number without a source.

**Validation in `load_curated`:**

- `id` is unique;
- `body` ∈ {Moon, Mars};
- `lat` ∈ [−90, 90] and `lon` ∈ [−180, 180];
- `anchor.type` ∈ {point, rim}, and `radius_km > 0` for `rim`;
- `source_url` and `coord_source_url` are not empty.

**Content (8 lunar and 8 Martian targets):**

| id | Name | Anchor | Lat, lon | Coordinate source |
| --- | --- | --- | --- | --- |
| `moon-a3-haworth` | Haworth rim | rim, IAU Haworth, r = 25.71 km | −87.45, −5.17 | IAU feature 14502 |
| `moon-a3-malapert-massif` | Malapert Massif | point, IAU Mons Malapert | −85.98, −1.67 | IAU 16338 |
| `moon-a3-mons-mouton` | Mons Mouton and Mons Mouton Plateau | point, IAU Mons Mouton | −84.6, 31.0 | IAU 16070 |
| `moon-a3-nobile-rim` | Nobile rim | rim, IAU Nobile, r = 39.64 km | −85.2752, 53.2725 | IAU 4321 |
| `moon-a3-de-gerlache-rim` | de Gerlache rim | rim, IAU de Gerlache, r = 16.35 km | −88.4849, −88.3447 | IAU 1439 |
| `moon-a3-slater-plain` | Slater Plain | point, IAU Slater | −88.0792, 111.2881 | IAU 15325 |
| `moon-a3-cabeus-b` | Peak near Cabeus B | rim, IAU Cabeus B, r = 29.81 km | −82.2587, −54.5846 | IAU 8058 |
| `moon-shackleton-rim` | Shackleton rim | rim, IAU Shackleton, r = 10.46 km (needs T4.0) | −89.67, 129.78 | IAU 5450 |
| `mars-jezero-perseverance` | Jezero crater (Perseverance) | point (Octavia E. Butler Landing) | 18.4447, 77.4508 | NASA / Wikipedia |
| `mars-gale-curiosity` | Gale crater (Curiosity) | point (Bradbury Landing) | −4.5895, 137.4417 | Wikipedia |
| `mars-gusev-spirit` | Gusev crater (Spirit) | point (Columbia Memorial Station, IAU 2000) | −14.5692, 175.4729 | JPL photojournal; primary source TODO(verify) |
| `mars-meridiani-opportunity` | Meridiani Planum (Opportunity) | point (Challenger Memorial Station) | −1.9462, −5.5266 | NASA photojournal |
| `mars-utopia-zhurong` | Utopia Planitia (Zhurong) | point | 25.066, 109.925 | Nature Astronomy; MDPI Remote Sensing |
| `mars-elysium-insight` | Elysium Planitia (InSight) | point (georeferenced lander) | 4.5024, 135.6234 | Golombek et al. 2020 |
| `mars-oxia-rosalind-franklin` | Oxia Planum (Rosalind Franklin) | point, IAU Oxia Planum centre | 17.28, −25.71 | IAU 15821; ellipse centre TODO(verify) |
| `mars-arcadia-swim` | Arcadia Planitia (shallow ice) | point, centre of the SWIM pilot-study figure | 47.25, −164.0 | SWIM; figure TODO(verify) |

**Source URLs:**

- **Artemis III regions:** `source_url` is NASA's announcement, `https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/`.
- **Shackleton:** `source_url` is NTRS 20250011660.
- **Every other target:** the full `source_url`, `coord_source_url`, `category` and `why` are in the JSON file.

---

## 6. `pipeline/targets.py` (new)

### 6.1 Constants

```python
CLUSTER_FEATURES = ["mean_slope_deg", "p90_slope_deg", "relief_m",
                    "hypsometric_integral", "detrended_std_m", "tri_m"]
LOG_FEATURES = ["relief_m", "detrended_std_m", "tri_m"]
N_CLUSTERS = 30
KMEANS_SEED = 42
NEIGHBOR_OFFSET_KM = 16.0
MIN_OK = {"point": 3, "rim": 5}
TARGETS_JSON = Path(__file__).parent / "data" / "targets.json"
AUX_COLS = {
    "Mars": ["themis_day", "themis_night", "themis_delta"],
    "Moon": ["wac_reflectance", "wac_percentile", "ice_favorability",
             "diviner_tmax_k", "diviner_tavg_k", "ice_depth_m"],
}
```

### 6.2 Functions

```python
def load_curated(path: Path = TARGETS_JSON) -> list[dict]:
    """Reads and validates targets.json (section 5). ValueError naming the failing id."""

def anchor_points(target: dict) -> list[tuple[float, float]]:
    """Patch centres, with pyproj.Geod(a=R, b=R) of the body.
    point: [centre] + fwd 16 km at azimuths 0, 90, 180, 270  -> 5 points.
    rim:   fwd radius_km at azimuths 0, 45, ..., 315          -> 8 points (no centre).
    Longitudes normalised to −180..180."""

def aggregate_patches(rows: list[dict | None], anchor_type: str, body: str) -> dict:
    """Takes the PointSampler.sample rows (None = invalid patch).
    Returns {status, n_patches, n_ok, <FEATURE_NAMES: nanmean>, <aux: nanmean>,
    mean_slope_std (std of mean_slope_deg across valid patches)}.
    status = 'ok' if n_ok >= MIN_OK[anchor_type], else 'insufficient_coverage' with NaN features.
    ice_depth_m uses nanmean (NaN = no stable ice); also returns ice_stable_frac = fraction of
    patches with finite ice_depth_m among those with Diviner data."""

def curated_features(targets: list[dict], raw_dir: Path, derived_dir: Path,
                     t3_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One PointSampler per body; samples every anchor point of its targets.
    Returns (targets_df, patches_df). patches_df has one row per attempted patch:
    target_id, k (index), lat, lon, ok (bool) and the T3 features/aux.
    Moon: wac_percentile = compute_lunar_wac_percentile(value,
    reference=features_moon.parquet['wac_reflectance']), PER PATCH, before averaging."""

def build_clusters(df: pd.DataFrame, body: str, k: int = N_CLUSTERS,
                   seed: int = KMEANS_SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """X = df[CLUSTER_FEATURES]; log1p on LOG_FEATURES; StandardScaler fitted on this body;
    KMeans(n_clusters=k, n_init=10, random_state=seed); clusters ranked by size (1..k).
    Representative = member with the smallest Euclidean distance to its centroid (scaled X).
    Returns reps_df (the representative's T3 row + cluster_rank, cluster_size, cluster_frac,
    dist_to_centroid) and summary_df (rank, size, frac, per-feature member medians in physical
    units, unscaled centroid). Can also return the per-patch labels (for the PNG)."""

def cluster_targets(reps_df: pd.DataFrame, summary_df: pd.DataFrame, body: str,
                    gaz: pd.DataFrame) -> pd.DataFrame:
    """Representatives become targets with the curated schema:
    id = f"{body.lower()}-cluster-{rank:02d}", type = "CLUSTER",
    name = iau_label(...)['display_label'], category = "Global terrain archetype (k-means)",
    why = "Archetype covering {frac:.1%} of {body}'s 32 km patches: median mean slope {s:.1f}°,
    relief {r:.0f} m, TRI {t:.0f} m." (cluster medians), source_url = IAU link of the named feature,
    anchor = {"type": "patch", ...}, status = "ok". Features and aux are the representative's T3 row."""

def plot_targets_map(t3_df, labels, targets_df, body, png_path) -> Path:
    """T3 lat/lon scatter coloured by cluster (30 colours), curated targets as black stars with
    their id, representatives as circles with their rank."""

def run(t3_dir: Path, out_dir: Path, project_dir: Path, bodies: list[str],
        k: int = N_CLUSTERS, skip_curated: bool = False) -> None: ...

def main(argv=None): ...   # --t3-dir, --out-dir (required), --project-dir, --body {Mars,Moon,all},
                           # --k (default 30), --skip-curated
```

### 6.3 Outputs in `runs/<JOBID>/`

**`targets.parquet`** has one row per target, curated and clusters, for both bodies. Columns, in order:

| Column | Type | Note |
| --- | --- | --- |
| `target_id` | string | |
| `type` | string | `CURATED` or `CLUSTER` |
| `body` | string | |
| `name`, `category`, `why` | string | English |
| `lat`, `lon` | float64 | Anchor (curated) or representative centre (cluster) |
| `anchor_type`, `anchor_note` | string | `point`, `rim` or `patch` |
| `source_url`, `coord_source_url` | string (nullable) | |
| `status` | string | `ok` or `insufficient_coverage` |
| `n_patches`, `n_ok` | int16 | |
| `mean_slope_deg` … `mean_elev_m` | float32 | The 7 `FEATURE_NAMES` |
| `mean_slope_std` | float32 | |
| `themis_day`, `themis_night`, `themis_delta` | float32 | NaN on the Moon |
| `wac_reflectance`, `wac_percentile`, `ice_favorability`, `diviner_tmax_k`, `diviner_tavg_k`, `ice_depth_m`, `ice_stable_frac` | float32 | NaN on Mars |
| `iau_label`, `iau_nearest`, `iau_distance_km`, `iau_link` | | From `iau_label()` at (lat, lon) |
| `cluster_rank`, `cluster_size`, `cluster_frac` | | Null for curated targets |

**Other outputs:**

- **`targets_patches.parquet`:** for auditing.
- **`clusters_{mars,moon}.parquet`:** the cluster summaries.
- **`targets.json`:** the same data as `{"metadata": {...}, "targets": [...]}`.
  - Floats are rounded to 4 decimals, and NaN becomes `null`.
  - Features are nested in `features` and `aux`, so T8 can copy them.
  - `metadata` carries the job id, the T3 run, `k`, the seed, the time and the commit.
- **`map_targets_{mars,moon}.png`.**

T8 reads this from `runs/`; nothing is copied into the repository.

---

## 7. Expected log

```text
[T4] t3_dir=/lustre/proyectos/p089/runs/2242278 out_dir=... commit=...
[CURADO] moon-a3-haworth  rim   8/8 ok  slope=..° relief=.. m  iau=Haworth (Crater, craters) d=.. km  div_tavg=.. K
...
[CURADO] resumen: Moon 8/8 ok, Mars 8/8 ok
[CLUSTER] Mars: N=140,916  k=30  size min/median/max = ../../..  inertia=..
...
[OK] targets.parquet: 76 targets (16 curated + 60 clusters)
```

The IAU name of each curated anchor **centre** must be its own feature. For example, if `iau_nearest` for `moon-a3-haworth` is not "Haworth", the longitude conversion is wrong.

---

## 8. `jobs/t4_targets.slurm` (new)

Same shape as `jobs/t3_planet_features.slurm` (`#!/usr/bin/env bash`, `set -euo pipefail`, conda, an echo of job, node and commit), with:

```bash
#SBATCH -A p089
#SBATCH -J p089-t4-targets
#SBATCH -p cpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:45:00
#SBATCH -o /lustre/proyectos/p089/output/t4_targets_%j.log
#SBATCH -e /lustre/proyectos/p089/output/t4_targets_%j.log
T3_DIR="${T3_DIR:-$PROJECT_DIR/runs/2242278}"
OUT_DIR="${OUT_DIR:-$PROJECT_DIR/runs/${SLURM_JOB_ID:-manual}}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"   # KMeans uses threads; allowed here
python -m pipeline.targets --project-dir "$PROJECT_DIR" --t3-dir "$T3_DIR" --out-dir "$OUT_DIR" --body all "$@"
```

It is a single job with no array, and it should take under 10 minutes. `--limit` does not apply here: use `--k 5 --body Moon` as a quick smoke test before the full run.

---

## 9. `tests/test_targets.py` (synthetic data only)

1. **`test_load_curated_real_file`:** the real `targets.json` has ≥ 6 targets per body, unique ids, every URL present, coordinates in range, and `radius_km > 0` for every `rim`.
2. **`test_load_curated_rejects_bad`:** `lat = 95` raises a `ValueError` naming the id.
3. **`test_anchor_points_point`:** 5 points; the 4 neighbours are 16.0 km (±0.01) from the centre.
4. **`test_anchor_points_rim_near_pole`:** Haworth (−87.45, −5.17, r = 25.71 km) gives 8 points, all 25.71 km (±0.01) from the centre, with every longitude in [−180, 180].
5. **`test_aggregate_min_ok`:** 4 of 8 valid gives `insufficient_coverage` and NaN features; 5 of 8 gives `ok`, the correct mean and `n_ok == 5`.
6. **`test_aggregate_ice_stable_frac`:** 4 patches with Diviner, 1 with finite ice depth, gives `ice_stable_frac == 0.25`.
7. **`test_build_clusters_blobs`:** 3 separated blobs (300 rows) with k = 3. The representatives are real rows in distinct blobs, the sizes sum to 300, the ranks are sorted by size, and the result is deterministic with the seed.
8. **`test_cluster_targets_schema`:** ids like `mars-cluster-01`, `type == "CLUSTER"`, and `why` contains the percentage.

---

## 10. Acceptance criteria

**Automatic:** every test passes (the previous 17, the 3 new ones in `test_geo.py`, and those in `test_iau.py` and `test_targets.py`).

**On the real run:**

1. At least 6 curated targets `ok` per body. The goal is 8 and 8; if Shackleton drops out, 7 and 8 is fine.
2. Every `ok` lunar curated target has finite `diviner_tavg_k`, `ice_favorability` and `wac_percentile`. All their patches lie south of 81°S, inside the Diviner and ice index coverage.
3. Every Martian curated target has finite `themis_day` and `themis_night` (all are within 60° of latitude).
4. The `iau_nearest` of each lunar anchor centre matches its `anchor.iau_feature`.
5. 30 clusters per body. Their sizes sum to 140,916 (Mars) and 36,741 (Moon), and the 60 representatives are distinct patches.
6. **Sanity review** (if it fails, report it before moving to T6):
   - InSight and Opportunity are among the 3 flattest Martian curated targets and below the Mars median slope (1.16°);
   - Gale has more relief than InSight;
   - the lunar polar targets are above the lunar median slope (6.8°).
7. **Maps:** the clusters are spatially coherent (Tharsis and Valles Marineris apart from the northern plains), and the curated stars sit where they belong.

**Outcome (run 2242423):** every criterion passed except the strict reading of 6. Opportunity ranked 5th by slope (0.54°), because Arcadia, Zhurong and Gusev turned out even flatter. All five plains are below 0.55°. The criterion was too strict; the result is correct.

---

## 11. Commands for Owen on Yuca

From `/lustre/proyectos/p089/code`. Read each log before running the next command.

```bash
cd /lustre/proyectos/p089/code && git pull
```

```bash
sbatch -A p089 -p cpu --time=00:15:00 --mem=4G -o /lustre/proyectos/p089/output/tests_t4_%j.log --wrap 'bash -c "source /apps/miniconda3/etc/profile.d/conda.sh && conda activate spaceapps_2026 && cd /lustre/proyectos/p089/code && pytest -q tests"'
```

```bash
sbatch jobs/t4_targets.slurm --k 5 --body Moon
```

```bash
sbatch jobs/t4_targets.slurm
```

```bash
tail -n 120 /lustre/proyectos/p089/output/t4_targets_<JOBID>.log
```

---

## 12. Documentation (same commit)

- **[logbook.md](logbook.md):** a new entry. It says the code is Gemini's, from this plan, and gives the job id, the counts, which targets dropped out and why, and the sanity review result.
- **[pipeline.md](pipeline.md):** add the run and the flow line.
- **[handoff.md](handoff.md):** mark T4 as done and leave the job id for T7.

## 13. What NOT to do

- Do not invent or "improve" coordinates; the `TODO(verify)` notes stay until a source is found.
- Do not recompute cluster features with another function.
- Do not use `mean_elev_m` for clustering or comparison.
- Do not import `enrich_nomenclature.py` or modify the v1 scripts.
- Do not write into `runs/2242278/`.

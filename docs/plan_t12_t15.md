# Detailed plan T12–T15: geology, dust and seasons, water and ice

Full specification of the new evidence dimensions, so the analog search goes **beyond terrain**. Written by Claude on 2026-11-14 (early morning) on `main` at `a5a1990`. The data sources were checked that night, from Yuca and the web.

| Task | Dimension | Bodies | Module |
| --- | --- | --- | --- |
| T14 | **Geology and surface materials** (+ subsurface and ice-surface labels) | Earth, Moon, Mars | `pipeline/geology.py` |
| T13 | **Processes: dust and seasons** | Earth, Mars | `pipeline/dust.py` |
| T12 | **Water and ice / cold traps** | Earth, Moon (+ Mars through geology) | `pipeline/ice.py` |
| T15 | **Integration** of the three into matching and export | all | `pipeline/match.py`, `pipeline/export.py` |

**Why these dimensions.** The challenge lists geology and surface materials, water and ice, and dust and atmospheric processes as dimensions of analogy, and asks to "think about processes as well as places". The T7 run showed the two limits of terrain alone:

- **Flat Mars plains are almost ties.** The top-1 and top-30 MSI differ by 0.012.
- **No volcano came up for Olympus Mons.** The score measures shape, not origin.

These dimensions are what separates such candidates.

**Principles (same as T7):**

- **Different units → compare by rank within each body.** Dust optical depth on Mars and aerosol optical depth on Earth are not the same quantity, but "how dusty is this place compared with the rest of its planet" is comparable.
- **Categories → compare through a shared class taxonomy** with an explicit similarity matrix.
- **No data → null, never a guess.** The MSI already skips null dimensions.
- **Every number traces to a source file and a run.**

Implementation order: **downloads → T14 and T13 (in parallel) → T12 → T15.** There is a **review stop** before T15 (§5.6).

---

## 0. Facts checked on 2026-11-13/14

**Earth lithology: GLiM** (Hartmann & Moosdorf 2012, CC-BY-3.0, [PANGAEA 10.1594/PANGAEA.788537](https://doi.pangaea.de/10.1594/PANGAEA.788537)).

- **Download:** `https://hdl.handle.net/10013/epic.39939.d001`, a 38 kB zip. Inside are `glim_wgs84_0point5deg.txt.asc` (ESRI ASCII grid, 720 × 360, 0.5°, `xllcorner -180`, `yllcorner -90`, `NODATA -9999`) and `Classnames.txt`.
- **Classes:**

  | Value | Code | Class |
  | --- | --- | --- |
  | 1 | `su` | Unconsolidated sediments |
  | 2 | `vb` | Basic volcanics |
  | 3 | `ss` | Siliciclastic sedimentary |
  | 4 | `pb` | Basic plutonics |
  | 5 | `sm` | Mixed sedimentary |
  | 6 | `sc` | Carbonate sedimentary |
  | 7 | `va` | Acid volcanics |
  | 8 | `mt` | Metamorphics |
  | 9 | `pa` | Acid plutonics |
  | 10 | `vi` | Intermediate volcanics |
  | 11 | `wb` | Water bodies |
  | 12 | `py` | Pyroclastics |
  | 13 | `pi` | Intermediate plutonics |
  | 14 | `ev` | Evaporites |
  | 15 | `nd` | No data |
  | 16 | `ig` | Ice and glaciers |

- **Probed on the real file:**
  - El Pinacate (31.8, −113.4) is `vb`, Tibesti (21, 18) is `vb`, the Sahara (26, 3) is `ss`, and the Atacama (−24.5, −69.3) is `ss`.
  - The McMurdo Dry Valleys (−77.5, 162.0) are `sm`, **not ice**, which is correct. The interiors of Greenland and Antarctica are `ig`.
  - The 40,244 T5 Earth patches split as:

    | Class | Patches | Class | Patches |
    | --- | --- | --- | --- |
    | `ig` | 12,397 | `vb` | 726 |
    | `su` | 10,808 | `pa` | 680 |
    | `sm` | 4,435 | `vi` | 370 |
    | `ss` | 3,737 | `wb` | 337 |
    | `sc` | 2,828 | `va` | 247 |
    | `mt` | 2,636 | `ev` | 180 |
    | `pb` | 144 | `pi` | 87 |
    | `py` | 60 | `nd` | 34 |
    | nodata | 538 (coast) | | |

  - **Of the 14,680 "polar cold" patches** that T7 capped (`lst_day_c < −10`), **12,339 are `ig`**. GLiM can finally tell ice sheets from bare cold ground.

**Mars geology: USGS SIM 3292** (Tanaka et al. 2014, 1:20M).

- Database: `https://pubs.usgs.gov/sim/3292/downloads/sim3292_database.zip` (~790 MB).
- Readme: `https://pubs.usgs.gov/sim/3292/downloads/sim3292_readme.txt`.
- Unit descriptions: `https://pubs.usgs.gov/sim/3292/pdf/sim3292_tabled1.pdf`.

**Moon geology: USGS Unified Geologic Map of the Moon, 1:5M, 2020** (Fortezzo, Spudis & Harrel; CC0, cite the authors).

- GIS: `https://asc-astropedia.s3.us-west-2.amazonaws.com/Moon/Geology/Unified_Geologic_Map_of_the_Moon_GIS_v2.zip` (~224 MB).
- Raster version: `https://asc-astropedia.s3.us-west-2.amazonaws.com/Moon/Geology/Ancillary/unified_geologic_map_of_the_moon_raster.zip`.

**Mars dust: Montabone et al. climatology** (LMD/MCD; CC BY-SA 3.0; cite Montabone et al. 2015, Icarus 251, 65–95, doi:10.1016/j.icarus.2014.12.034, and Montabone et al. 2020, JGR Planets, doi:10.1029/2019JE006111).

- **Page:** `https://www-mars.lmd.jussieu.fr/mars/dust_climatology/`. No registration; the authors ask for a short Google Form if you download.
- **Product used:** the daily **kriged** maps (complete coverage), 3° × 3°, MY24–MY36. Single files are at `.../dataset_v2/dustscenario_MY{24..36}_v2-*.nc` (MY34 ≈ 58 MB), and all years at `.../dataset_v2/krigedcdod_v2.tar.gz` (591 MB).
- **Format:** **NetCDF3 classic** (magic bytes `CDF\x01`), which `xarray` reads with `engine="scipy"`. **`netCDF4` and `h5py` are NOT installed** and are not needed.
- **Content:** column dust optical depth (absorption, 9.3 µm), normalised to 610 Pa, plus a version normalised to local surface pressure. Extinction = absorption × 1.3.
- **Variable names:** not documented on the page. The first step prints them (§3.2).

**Earth aerosols: MODIS MOD08_M3, collection 6.1** (Terra, monthly, 1° × 1°, HDF4 → `pyhdf`, same as T6).

- **Source:** NASA Earthdata (LAADS), through `earthaccess` with the existing `~/.netrc`, as in `download_earthdata.py`.
- **SDS:** most likely `Deep_Blue_Aerosol_Optical_Depth_550_Land_Mean_Mean`, inferred from the collection 6.1 naming pattern and **not confirmed**. The first step lists the SDS names and checks.

**Data already in hand:**

- **Moon:** Diviner `diviner_tavg_k`, `diviner_tmax_k`, `ice_depth_m`, `ice_favorability` and `ice_stable_frac`. On the targets, these exist only for the 8 polar curated targets (8 of 38 Moon targets). On T3, there are ~375 Moon patches with Diviner.
- **Earth:** `lst_day_c`, `lst_night_c` and `lst_amplitude_c` on every T5 patch.

**Environment:** `xarray`, `scipy`, `geopandas`, `pyogrio`, `pyhdf` and `earthaccess` are installed. Do not install anything else.

---

## 1. Downloads (one job)

**New file:** `jobs/download_t12_t14.slurm`. It has the same shape as the other jobs, with 2 CPUs, 8G, `--time=02:00:00` and the log `download_t12_t14_%j.log`.

- **Tool:** `curl -L --fail --retry 3 --retry-delay 10 -o <tmp> <url> && mv <tmp> <final>`.
- **Skip:** if the final file already exists with a non-zero size, skip it.
- **Never** use `-k`.
- **At the end:** print the size and `sha256sum` of every file.

| What | URL | Destination (`/lustre/proyectos/p089/data/raw/…`) |
| --- | --- | --- |
| GLiM 0.5° | `https://hdl.handle.net/10013/epic.39939.d001` | `geology/earth_glim/glim_0p5deg.zip` (unzip in place) |
| Mars SIM 3292 | `https://pubs.usgs.gov/sim/3292/downloads/sim3292_database.zip` + `sim3292_readme.txt` | `geology/mars_sim3292/` (unzip) |
| Moon unified map | `https://asc-astropedia.s3.us-west-2.amazonaws.com/Moon/Geology/Unified_Geologic_Map_of_the_Moon_GIS_v2.zip` | `geology/moon_unified/` (unzip) |
| Mars dust (kriged, all years) | `https://www-mars.lmd.jussieu.fr/mars/dust_climatology/dataset_v2/krigedcdod_v2.tar.gz` | `mars/dust_montabone/` (untar) |
| Earth AOD | `earthaccess.search_data(short_name="MOD08_M3", version="061", temporal=("2019-01-01","2023-12-31"))` → 60 files | `earth/modis/aod/` |

- **MOD08_M3 step:** a small new script, `download_aod.py` in the repo root next to `download_earthdata.py`, run inside the same job. Check the granule count (expected 60) and fail if it is lower.
- **Disk:** about 4–5 GB in total, well within the 18 TB quota.

---

## 2. T14 — Geology and surface materials (`pipeline/geology.py`)

### 2.1 Shared class taxonomy

Units from three different maps are compared through **8 shared classes**. The Earth mapping is fixed here. The Moon and Mars mappings are generated by rules (§2.3) and **reviewed by Claude** before T15.

| Class | Meaning | Earth (GLiM) | Moon | Mars |
| --- | --- | --- | --- | --- |
| `VOLCANIC_BASIC` | Basaltic lava plains, shields | `vb` | Mare units | Volcanic units |
| `VOLCANIC_OTHER` | Non-basaltic volcanics | `va`, `vi` | — | — |
| `PYROCLASTIC` | Explosive volcanic deposits | `py` | Dark mantle / pyroclastic units | — |
| `CRYSTALLINE` | Plutonic and metamorphic crust | `pa`, `pb`, `pi`, `mt` | Terra / highland units (anorthositic crust) | — |
| `IMPACT` | Crater and basin materials, breccias | — (GLiM has no impact class) | Crater and basin units | Impact units |
| `SEDIMENTARY` | Clastic and chemical sediments, plains fill | `ss`, `sm`, `sc`, `su` | — | Lowland, basin, transition and highland plains/sedimentary units |
| `EVAPORITE` | Salt deposits | `ev` | — | — |
| `ICE` | Ice sheets, glaciers, polar layered deposits | `ig` | — | Polar units |

`wb` and `nd` map to null.

**Similarity matrix `GEO_SIMILARITY`.** It is symmetric, with 1 on the diagonal. These are the related pairs; everything else is 0:

| Pair | Value | Why |
| --- | --- | --- |
| `VOLCANIC_BASIC`–`PYROCLASTIC` | 0.6 | Both basaltic volcanism |
| `VOLCANIC_BASIC`–`VOLCANIC_OTHER` | 0.5 | Volcanic, different chemistry |
| `VOLCANIC_OTHER`–`PYROCLASTIC` | 0.5 | |
| `CRYSTALLINE`–`IMPACT` | 0.4 | Lunar and Martian impact breccias are reworked crust |
| `SEDIMENTARY`–`EVAPORITE` | 0.6 | Both sedimentary |
| `SEDIMENTARY`–`IMPACT` | 0.2 | Crater fill is partly sedimentary on Mars |

**Honesty notes** (they go into the JSON metadata and the report):

- **Earth has almost no preserved impact terrain at map scale,** so `IMPACT` targets (most lunar polar rims) will score low on geology everywhere. That is a real "where it breaks".
- **GLiM is 0.5° (~55 km)** and the planetary maps are 1:5M–1:20M. This is regional geology, not the outcrop under the patch. Say "regional surface material".

### 2.2 Earth sampling

```python
GLIM_CODES = {1:"su",2:"vb",3:"ss",4:"pb",5:"sm",6:"sc",7:"va",8:"mt",9:"pa",10:"vi",11:"wb",12:"py",13:"pi",14:"ev",15:"nd",16:"ig"}
GLIM_TO_CLASS = {"vb":"VOLCANIC_BASIC","va":"VOLCANIC_OTHER","vi":"VOLCANIC_OTHER","py":"PYROCLASTIC",
                 "pa":"CRYSTALLINE","pb":"CRYSTALLINE","pi":"CRYSTALLINE","mt":"CRYSTALLINE",
                 "ss":"SEDIMENTARY","sm":"SEDIMENTARY","sc":"SEDIMENTARY","su":"SEDIMENTARY",
                 "ev":"EVAPORITE","ig":"ICE","wb":None,"nd":None}

def load_glim(path) -> np.ndarray: ...            # np.loadtxt(skiprows=6) -> int16 (360, 720)
def glim_at(grid, lat, lon) -> np.ndarray: ...    # code per point (vectorised); row=floor((90-lat)/0.5), col=floor((lon+180)/0.5)
```

**Coast fallback:** if the centre cell is `-9999`, `wb` or `nd`, use the **most frequent valid code** in the 3 × 3 neighbourhood. If there is none, the result is null. 538 patches are on such cells.

**Output:** `runs/<JOBID>/geology_earth.parquet` with `lat`, `lon`, `glim_code`, `geo_class`, `ice_surface` (= `glim_code == "ig"`) and `lava_tube_terrain` (= `glim_code == "vb"`).

### 2.3 Moon and Mars sampling

1. **Read the polygons with `geopandas.read_file` (pyogrio).**
   - Print the CRS, the attribute columns, and the list of unique units with their names or descriptions. Write it all to `geology_units_{moon,mars}.csv` in the run directory.
   - Use whichever attribute holds the unit symbol (for example `FIRST_Unit` or `UnitSymbol`; check, do not assume) and the description, if there is one.
2. **Map units to classes by rule.** `pipeline/geology_rules.py` holds ordered keyword rules applied to the unit **name or description**, case-insensitive; the first match wins:
   - **Moon:**
     - `mare` / `maria` → `VOLCANIC_BASIC`;
     - `dark mantle` / `pyroclastic` → `PYROCLASTIC`;
     - `crater` / `basin` / `ejecta` / `impact` → `IMPACT`;
     - `terra` / `highland` / `plains` (Imbrian or Nectarian light plains) → `CRYSTALLINE`;
     - otherwise `CRYSTALLINE`, logged as `default`.
   - **Mars:**
     - `polar` / `ice` / `layered deposit` → `ICE`;
     - `volcanic` / `volcano` / `lava` / `edifice` / `Tharsis` → `VOLCANIC_BASIC`;
     - `impact` / `crater` → `IMPACT`;
     - `lowland` / `basin` / `transition` / `plains` / `sedimentary` / `Vastitas` / `apron` / `channel` → `SEDIMENTARY`;
     - `highland` → `IMPACT` (Noachian highlands are heavily cratered breccia);
     - otherwise null, logged.
3. **Write the review table** `geology_mapping_review.md`: one row per unit, with its symbol, description (truncated to 120 characters), the class, the rule that matched, and the **area share** of the unit on its body. Units under the `default` rule or null are highlighted. **This is the review stop** (§5.6).
4. **Sample.**
   - **Points:** reproject from lon/lat on the body sphere (`+proj=longlat +R=<body radius>`) to the map CRS, then `geopandas.sjoin(predicate="within")`.
   - **Targets:** `point`/`rim` anchors take the majority class over their anchor points. Clusters use their representative point.
   - **Every T3 patch** of the body is also sampled; T15 needs it for the class shares in the report.

**Outputs:**

- `geology_moon.parquet` and `geology_mars.parquet`: one row per T3 patch, with `lat`, `lon`, `unit`, `geo_class`;
- `geology_targets.parquet`: one row per T4 target, with `target_id`, `unit`, `geo_class` and `geo_class_share` (the fraction of anchor points that agree);
- `geology_earth.parquet` (§2.2).

### 2.4 Checks (`t14_checks.json`; hard checks fail the job)

| # | Check | Expected | Kind |
| --- | --- | --- | --- |
| 1 | Earth: Pinacate (31.8, −113.4), Tibesti (21, 18) | `VOLCANIC_BASIC` | Hard |
| 2 | Earth: Dry Valleys (−77.5, 162.0) | `SEDIMENTARY` (not `ICE`) | Hard |
| 3 | Earth: interior of Greenland (72, −40) and Antarctica (−80, 0) | `ICE` | Hard |
| 4 | Moon: Mare Imbrium (35, −15), Mare Tranquillitatis (8, 31) | `VOLCANIC_BASIC` | Hard |
| 5 | Moon: Shackleton rim target | `IMPACT` or `CRYSTALLINE` | Soft |
| 6 | Mars: Olympus Mons (18.65, −133.8), Arsia Mons (−8.3, −120.1) | `VOLCANIC_BASIC` | Hard |
| 7 | Mars: north polar cap (87, 0) | `ICE` | Hard |
| 8 | Mars: Arcadia SWIM target, Utopia (Zhurong) | `SEDIMENTARY` | Soft |
| 9 | Units mapped by `default` or null | < 10 % of each body's area; list them | Soft |

---

## 3. T13 — Processes: dust and seasons (`pipeline/dust.py`)

**Idea (Owen's):** compare Mars's dust seasons with Earth's. A site on Earth is a **dust-process analog** of a Martian site when three things match, **each ranked within its own planet**:

1. **Dust level:** how dusty the place is compared with the rest of the planet;
2. **Seasonality:** how strongly that dust varies through the year;
3. **Peak season:** when in the **local** seasonal cycle the dust peaks.

The Moon has no atmosphere: dust is null for every Moon target. Lunar dust is lofted electrostatically, which goes in the limits text.

### 3.1 Seasonal phase on both planets

- **Mars:** use the solar longitude `Ls` that comes with each daily map. Bin it into **12 bins of 30°** (bin `k` covers `[30k, 30k+30)`).
- **Earth:** for each month, take the day of year at mid-month, `doy`, and compute `Ls_E = ((doy − 79.5) / 365.2422 · 360) mod 360`. Ls_E = 0 is the March equinox, which matches Mars, where Ls = 0 is the northern spring equinox. That is good to ±3° and gives one value per month, assigned to its 30° bin.
- **Local season.** For a site at latitude < 0, `local_phase = (Ls + 180) mod 360`; otherwise `local_phase = Ls`. With this, "summer" means local summer in both hemispheres.
  - **Why:** Mars's global dust season is in southern spring and summer (perihelion). A southern Martian site therefore peaks in its local summer, and should match Earth sites that also peak in their local summer.

### 3.2 Mars dust climatology

1. **Inspect** one file with `xr.open_dataset(path, engine="scipy")`. Print `ds` (dimensions, variables, attributes) to the log, and record the variable names in `docs/pipeline.md`.
   - Use the **column dust optical depth normalised to 610 Pa** (absorption, 9.3 µm). It removes the topographic effect of surface pressure, so Tharsis and Hellas are comparable.
   - If the names are ambiguous, **stop and report**. Do not guess.
2. **Climatology per grid cell.**
   - For each Martian year MY24–MY36, and each cell and Ls bin, take the mean CDOD over the sols in that bin.
   - Then take the **median over years** per cell and bin. The median keeps the global dust storm years (MY25, MY28, MY34) from dominating the climatology; their mean is reported separately.
   - Result: a 12-value seasonal curve per 3° cell.
3. **Metrics per cell:**
   - `dust_level = mean(curve)`;
   - `dust_seasonality = (max(curve) − min(curve)) / (mean(curve) + 1e-6)`;
   - `dust_peak_phase_deg`: the centre of the bin with the maximum, converted to the **local phase** of the cell's latitude.
   - Also `storm_year_boost = mean over MY25, MY28, MY34 / median over all years` (informative, not scored).
4. **Sampling:** the nearest 3° cell to the centre of each T3 Mars patch and each Mars target (bilinear interpolation is not needed). Output: `dust_mars.parquet` (T3 patches) and `dust_targets.parquet`.

### 3.3 Earth aerosol climatology

1. **Read** the 60 MOD08_M3 files with `pyhdf`.
   - List the SDS names and print those that contain `Deep_Blue` and `550`.
   - Use **`Deep_Blue_Aerosol_Optical_Depth_550_Land_Mean_Mean`** if it exists. Otherwise stop and report the list.
   - Apply `_FillValue`, `scale_factor` and `add_offset` **exactly as the attributes say**, and print them. MODIS atmosphere products use `value = (raw − add_offset) · scale_factor`. Check this on a known value: the Sahara in summer has AOD ≈ 0.3–0.8.
   - The grid is 1° × 1°, 180 × 360, with row 0 = 89.5°N. Check against the file's lat/lon SDS.
2. **Climatology:** monthly values → 12 bins by `Ls_E`, median over the 5 years, then the same three metrics as Mars, with the local phase. A cell needs ≥ 9 valid bins; otherwise its metrics are NaN. Deep Blue has no retrievals over ice and snow, so Antarctica and Greenland end up NaN, and that is correct.
3. **Sampling:** the nearest 1° cell for each T5 Earth patch. Output: `dust_earth.parquet` (`lat`, `lon`, `dust_level`, `dust_seasonality`, `dust_peak_phase_deg`, `n_valid_bins`).

### 3.4 Ranks and score

- **Ranks within each body.** Compute `rank_pct` (rankdata average / n) of `dust_level` and of `dust_seasonality`:
  - Earth, over the T5 patches with data;
  - Mars, over all T3 Mars patches with data.

  The Mars targets take the rank of their value within the T3 Mars distribution (`searchsorted`, as in T7's thermal rank).
- **Distance:**
  - `d_level = |r_E − r_T| / 0.15`;
  - `d_season = |s_E − s_T| / 0.15`;
  - `d_phase = circular_diff(φ_E, φ_T) / 60°` (in degrees, 0–180).
  - `S_dust = exp(−(d_level² + d_season² + d_phase²) / (2 · 3))`, which is the RBF of the RMS distance.
- **Null** if either side is NaN, and for every Moon target.

### 3.5 Checks (`t13_checks.json`)

| # | Check | Expected | Kind |
| --- | --- | --- | --- |
| 1 | Mars variable names found and printed | Yes | Hard |
| 2 | Earth SDS found; scale and offset printed | Yes | Hard |
| 3 | Mars global mean CDOD per year: MY25, MY28 and MY34 are the 3 highest | Yes (known global dust storm years) | Soft |
| 4 | Mars global-mean curve: maximum bin within Ls 180–330 | Yes (perihelion dust season) | Hard |
| 5 | Earth `dust_level` rank > 0.9 at Bodélé (17, 18) and the Taklimakan (39, 83) | Yes (known dust sources) | Hard |
| 6 | Earth `dust_level` rank < 0.5 in the Atacama (−24.5, −69.3) | Yes (hyperarid but clean air) | Soft |
| 7 | Mars `dust_level` rank: Hellas (−42, 70) > Tharsis (0, −110) | Yes (610 Pa normalisation keeps Hellas dusty) | Soft |
| 8 | Maps | `map_dust_level_{earth,mars}.png`, `map_dust_peak_phase_{earth,mars}.png` written | Soft |

---

## 4. T12 — Water and ice / cold traps (`pipeline/ice.py`)

**Idea:** permanent lunar base sites matter because of cold traps and water ice. The analog question is: which places on Earth are, **within Earth**, as extremely cold and ice-bearing as the target is **within the Moon**? Absolute temperatures differ by ~200 K, so ranks again. Mars gets the ice part through geology (`ICE` units) and one curated hint (Arcadia SWIM).

### 4.1 Columns

**Earth (T5 patches):**

- `cold_rank_E` = rank_pct of `−(lst_day_c + lst_night_c)/2` over the T5 patches (1 = coldest on Earth);
- `ice_E` = 1.0 if `ice_surface` (from T14), 0.5 if `lst_day_c < 0` (frozen ground most of the year, no mapped ice), 0.0 otherwise.

**Moon (targets with Diviner, i.e. the 8 polar curated targets):**

- `cold_rank_T` = rank_pct of `−diviner_tavg_k` within the T3 Moon patches that have Diviner (~375);
- `ice_T` = `ice_stable_frac` (fraction of anchor patches with stable subsurface ice).

**Mars:**

- `cold_rank_T` = null, because there is no comparable surface temperature layer;
- `ice_T` = 1.0 if the T14 class is `ICE`, or if the target is listed in `pipeline/data/ice_hints.json`, which is new and hand-written:

  ```json
  {"version":"2026-11-14","hints":[{"target_id":"mars-arcadia-swim","ice_T":1.0,
    "why":"SWIM maps show shallow, ice-consistent ground in Arcadia Planitia.",
    "source_url":"https://swim.psi.edu/"}]}
  ```

  Otherwise 0.0.
- **Moon targets without Diviner** (non-polar clusters): `S_ice` = null.

### 4.2 Score

- **Moon:** `d = sqrt(((cold_rank_E − cold_rank_T)/0.15)² + ((ice_E − ice_T)/0.5)²) / sqrt(2)`, and `S_ice = exp(−d²/2)`.
- **Mars:** only the ice term, `S_ice = exp(−((ice_E − ice_T)/0.5)² / 2)`. It applies **only when `ice_T > 0`**; otherwise it is null, because "this Martian site has no ice" says nothing useful about Earth sites.

**Outputs:** `ice_earth.parquet` (`lat`, `lon`, `cold_rank_E`, `ice_E`) and `ice_targets.parquet` (`target_id`, `cold_rank_T`, `ice_T`, `ice_source`).

### 4.3 Checks (`t12_checks.json`)

| # | Check | Expected | Kind |
| --- | --- | --- | --- |
| 1 | Coldest 1 % of Earth patches | All in Antarctica or Greenland | Soft |
| 2 | Moon: `cold_rank_T` of Haworth and Slater (the coldest, 65–75 K) | > 0.9 | Hard |
| 3 | Dry Valleys patches have `ice_E = 0.5` (frozen, not ice-covered) | Yes | Soft |
| 4 | Mars targets with `ice_T > 0` | `mars-arcadia-swim` plus any polar clusters; list them | Soft |

---

## 5. T15 — Integration into matching and export

### 5.1 Dimensions

T7 had 4 dimensions. After T15 there are 7:

| Key | Label (English, for the JSON) | Bodies | Module |
| --- | --- | --- | --- |
| `topography` | Topography | all | T7 |
| `roughness` | Roughness | all | T7 |
| `environment` | Aridity (no vegetation) | all | T7 |
| `thermal` | Day–night thermal contrast (rank) | Mars | T7 |
| `geology` | Surface materials (regional geology) | all | T14 |
| `dust` | Dust process and seasons (rank) | Mars | T13 |
| `ice` | Cold traps and ice (rank) | Moon; Mars when ice is mapped | T12 |

`metadata.dimensions` in the JSON lists them, as `{key, label, description, bodies, source}`, so the app can build its sliders from data instead of hard-coding them.

### 5.2 Presets (replace T7's three)

| Preset key | Label | topo | rough | env | thermal | geology | dust | ice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `mobility_and_traction` | Rover mobility and traction | 0.40 | 0.35 | 0.10 | 0 | 0.15 | 0 | 0 |
| `construction_and_base` | Base construction and landing | 0.45 | 0.20 | 0.05 | 0.05 | 0.25 | 0 | 0 |
| `geology_and_materials` | Geology and surface materials | 0.20 | 0.10 | 0.10 | 0 | 0.60 | 0 | 0 |
| `dust_and_seasons` | Dust storms and seasons | 0.10 | 0.05 | 0.15 | 0.20 | 0.10 | 0.40 | 0 |
| `isru_and_ice` | Water ice and cold traps (ISRU) | 0.20 | 0.10 | 0.05 | 0 | 0.15 | 0 | 0.50 |

`MSI = Σ w·S / Σ w` over the **non-null** dimensions, unchanged. A Moon target therefore drops `thermal` and `dust` on its own, and `dust_and_seasons` on the Moon effectively becomes terrain plus geology. The export notes this in `metadata` per preset as `applies_to: ["Mars"]`, and the app may hide it for the Moon.

### 5.3 Selection changes

- **Score the whole Earth, no candidate pool.** Compute every S_k for **all** 40,244 Earth patches per target: 76 × 40k × 7 is ~21M values, which is vectorised and takes seconds. Drop the 2000-neighbour pool.
  - **Why:** the pool was built on terrain only, so for the geology, dust and ice presets it would discard the best process analogs before they are scored.
- **Polar cap → ice cap.** Replace `polar_cold` (`lst_day_c < −10`) with `ice_surface` (GLiM `ig`) for the cap of ≤ 3 per preset. The cap does **not** apply to `isru_and_ice`, where ice sheets are legitimate analogs. The Dry Valleys (`sm`) are no longer capped.
  - **Why:** the cap existed only because the data could not tell ice from rock, and now it can.
- **Unchanged:** 30 per preset, ≥ 150 km apart, and the union across presets goes into the JSON. With 5 presets that is ≤ 150 analogs per target; the estimate is ~76 × 150 × 1.4 KB ≈ 16 MB. Keep the split rule at 20 MB.

### 5.4 Mismatches (where it breaks)

Add to T7's list:

- **`geology`:** when the classes differ. Record `{feature: "geo_class", earth: "SEDIMENTARY", target: "IMPACT", z_diff: null}`.
- **`dust_level` / `dust_seasonality`:** a rank difference > 0.30.
- **`dust_peak_phase`:** a circular difference > 90°.
- **`cold_rank`:** a rank difference > 0.30.

### 5.5 Export additions

**Each analog gets:**

```json
"geology": {"glim_code": "vb", "geo_class": "VOLCANIC_BASIC", "lava_tube_terrain": true, "ice_surface": false},
"dust": {"level_rank": 0.91, "seasonality_rank": 0.77, "peak_phase_deg": 105.0},
"ice": {"cold_rank": 0.12, "ice_E": 0.0}
```

**Each target gets** `geology` (`unit`, `geo_class`, `geo_class_share`), `dust` (Mars) and `ice` (with the `ice_source`).

**Subsurface label.** `subsurface_note` = "Basaltic volcanic terrain: lava tubes are possible here (not mapped)" when the analog has `lava_tube_terrain` and the target's class is `VOLCANIC_BASIC`; otherwise null. It is a label, never a score.

**`metadata` gets:**

- `dimensions` (§5.1);
- `geology_classes` and `geology_similarity` (the matrix);
- the run ids of T12, T13 and T14;
- the citations: GLiM, SIM 3292, the unified lunar map, Montabone 2015/2020, MOD08_M3;
- `not_modelled: ["mineralogy (spectral)", "biology", "caves (mapped)"]`, each with one honest sentence.

### 5.6 Review stop (before running T15)

Owen sends Claude:

- `geology_mapping_review.md` for the Moon and Mars;
- the T13 maps and `t13_checks.json`;
- `t12_checks.json`.

Claude confirms the unit mapping or corrects it, as a commit to `pipeline/data/geology_overrides.json`, which `geology.py` applies after the rules. Only then does T15 run.

### 5.7 Report and checks (`t7_checks.json` / `t7_report.md`, extended)

| # | Check | Expected | Kind |
| --- | --- | --- | --- |
| 1–5 | The T7 checks, now over 5 presets (the ice cap replaces the polar cap) | Pass | Hard |
| 6 | Every non-null `S_geology`, `S_dust`, `S_ice` is in [0, 1]; `S_dust` is null for all Moon targets | Yes | Hard |
| 7 | **Olympus Mons** check with `geology_and_materials`: at least one `VOLCANIC_BASIC` Earth patch in the top 10 | Yes | Hard |
| 8 | Mars plains (InSight, Arcadia, Zhurong, Gusev, Meridiani), `mobility_and_traction`: spread top 1 → top 30 | > 0.012 (the T7 value); print it | Soft |
| 9 | `dust_and_seasons` for the Mars curated targets: print the top 5 with country and dust ranks | Review | Soft |
| 10 | `isru_and_ice` for the lunar curated targets: print the top 5 | Antarctica/Greenland/high cold deserts expected | Soft |
| 11 | Share of exported analogs per `geo_class`, and number with `lava_tube_terrain` | Print | Soft |

---

## 6. Jobs and commands

| Job | Resources | What |
| --- | --- | --- |
| `jobs/download_t12_t14.slurm` | 2 CPUs, 8G, 2 h | §1 |
| `jobs/t14_geology.slurm` | 4 CPUs, 32G, 45 min | `python -m pipeline.geology --project-dir P --out-dir R` |
| `jobs/t13_dust.slurm` | 4 CPUs, 32G, 45 min | `python -m pipeline.dust --project-dir P --out-dir R` |
| `jobs/t12_ice.slurm` | 2 CPUs, 8G, 15 min | `python -m pipeline.ice --t14-dir … --out-dir R` |
| `jobs/t7_match.slurm` (extended) | as before | New exported variables `T12_DIR`, `T13_DIR`, `T14_DIR` passed to `match` and `export` |

**Commands for Owen** (SSH or the Open OnDemand shell, from `/lustre/proyectos/p089/code`). Commit and push before every job.

```bash
cd /lustre/proyectos/p089/code && git pull && sbatch jobs/download_t12_t14.slurm
```

After the download log shows every file with its size:

```bash
sbatch jobs/t14_geology.slurm && sbatch jobs/t13_dust.slurm
```

```bash
sbatch --export=ALL,T14_DIR=/lustre/proyectos/p089/runs/<T14> jobs/t12_ice.slurm
```

Then comes the review stop (§5.6). After it:

```bash
sbatch --export=ALL,T5_DIR=/lustre/proyectos/p089/runs/2242438,T12_DIR=/lustre/proyectos/p089/runs/<T12>,T13_DIR=/lustre/proyectos/p089/runs/<T13>,T14_DIR=/lustre/proyectos/p089/runs/<T14> jobs/t7_match.slurm
```

---

## 7. Tests (synthetic only)

`tests/test_geology.py`:

1. `glim_at` on a tiny synthetic grid: corner and coast fallback (a `wb` centre with 3 `vb` neighbours gives `vb`; all `wb` gives null).
2. `GEO_SIMILARITY` is symmetric, has 1 on the diagonal, and the values of §2.1.
3. The keyword rules, on a synthetic unit table: "Mare basalt" → `VOLCANIC_BASIC`; "Polar layered deposits" → `ICE`; an unknown unit → `default` and logged.

`tests/test_dust.py`:

4. `Ls_E`: mid-March gives ≈ 0°, mid-June ≈ 90°, mid-December ≈ 270° (±5°).
5. The local phase shifts southern sites by 180°; `circular_diff(350, 10) == 20`.
6. Metrics on a synthetic 12-bin curve with a peak at bin 7: `peak_phase` is 225° in the north and 45° in the south; the seasonality formula is right.
7. `S_dust` is 1 for identical ranks and phases, and below 0.5 for a 180° phase difference with equal ranks.

`tests/test_ice.py`:

8. `ice_E` levels (1 / 0.5 / 0) from synthetic `ice_surface` and `lst_day_c`.
9. `S_ice` is null for a Mars target with `ice_T = 0`, and for a Moon target without Diviner.

`tests/test_match.py` (extend):

10. The MSI with 7 dimensions and nulls; the ice cap is not applied to `isru_and_ice`; scoring without a candidate pool returns the same top 1 as the brute-force argmax on a synthetic set.

---

## 8. Documentation

- **[logbook.md](logbook.md):** one entry per task, in English, with the job ids, the check tables and what was learned. In particular: whether the dust peak phases make physical sense, and which geology units needed overrides.
- **[pipeline.md](pipeline.md):** the new raw and derived datasets, the dust variable names, the MOD08 SDS name with its scale and offset, and the runs.
- **[HISTORY.md](HISTORY.md):** a new section, "Beyond terrain: geology, dust seasons and ice", with the reasons in this plan.
- **[handoff.md](handoff.md):** the status table.

## 9. What NOT to do

- Do not compare absolute dust optical depths, temperatures or AOD across bodies. Use ranks and phases only.
- Do not call the geology "mineralogy". It is regional lithology and mapped units, not spectra.
- Do not invent unit-to-class mappings silently. Every unit appears in the review table, and overrides go through `geology_overrides.json`.
- Do not install `netCDF4`, `h5py` or GDAL plugins. NetCDF3 reads with `xarray`'s scipy engine, and HDF4 with `pyhdf`.
- Do not use `-k` or disable TLS in the downloads.
- Do not drop the old T7 run: the new run writes a new `runs/<id>/`, and the app keeps the old JSON until the new one is reviewed.

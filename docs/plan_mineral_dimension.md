# Experiment: a scored Mars-only mineral dimension ("option B")

Status: **spec only, experiment branch `exp/mars-mineral-dimension`. Never merge to `main` without Owen's OK.**
Written 2026-11-14 (submission deadline 2026-11-15 23:59 local). Branched from `origin/main` at `d90cf36` (T16 and T17 merged; the option-A mineral-context work was not on `main` yet when this was written).

Option A (mineralogy as display-only context, not scored) is a separate piece of work on its own branch. This document covers option B only: an 8th scored dimension, `mineral`, that applies to Mars only.

---

## 0. Summary and decision up front

| Mineral family | Mars source | Earth source (EMIT) | Verdict |
| --- | --- | --- | --- |
| **Ferric oxides** | OMEGA `FERRIC_BD530` (0.53 µm Fe³⁺ band depth, VNIR) | `Hematite + Goethite` (VNIR mass fraction, %) | **Defensible as a within-planet rank. Build this one.** Blocked until Owen has an ESA COSMOS account (§1.1). |
| Ferric oxides (alternative) | TES `Hematite` (thermal IR, coarse "grey" crystalline hematite) | `Hematite + Goethite` | **Not defensible.** Different physical phase and grain size (grey specular hematite vs red fine-grained oxides) and different wavelength range. Do not use. |
| Hydrated phyllosilicates and sulfates | OMEGA/CRISM `HYDROUS_SITES` (a list of sites, not a map); TES `Sulfates`, `Sheet Silicates and High-Si Glass` (0–0.2) | `Kaolinite + Montmorillonite + Illite+Muscovite + Gypsum` | **Not defensible as a scored dimension.** There is no continuous global hydration map of Mars in these sources. OMEGA gives sites only. TES sulfate and sheet-silicate abundances sit at or below TES detection limits over most of the planet (Bandfield 2002), and the sheet-silicate band is mixed with high-Si glass. A rank over a field that is mostly zero or noise is meaningless. Keep hydration as display-only context (option A). |
| Carbonates | TES `Carbonates` | `Calcite + Dolomite` | Not defensible, for the same detection-limit reason. Not scored. |

So the experiment is **one family: ferric oxides**, scored as a within-planet rank like the dust level rank. The dimension key is `mineral`, its label is "Iron oxides (rank)", and it applies to `bodies: ["Mars"]`.

**Stop conditions** (if any of these holds, do not force it: write the verdict "drop" in the logbook, §9):

1. Owen cannot get an ESA COSMOS account, or the OMEGA files cannot be read (§1.1). There is no fallback source for this family: TES hematite is ruled out above.
2. A hard check in §4.4 fails, for example the ferric map does not separate dusty Arabia Terra from dark Syrtis Major.
3. On Mars, the ferric rank is mostly a copy of an existing dimension: Spearman |ρ| > 0.7 against `dust_level_rank` over the T3 Mars patches (§4.4, check M5). In that case it adds no new information and double-counts dust.

---

## 1. Data sources (verified on 2026-11-14)

Everything in this section was checked against the live servers or the official documentation on 2026-11-14. Anything marked **unverified** has to be confirmed by the probe job (§4.1) before any scoring code relies on it.

### 1.1 Mars: OMEGA DDR global maps (ESA PSA)

- Dataset: `MEX-M-OMEGA-5-DDR-GLOBAL-MAPS-V1.0`, listed on the ESA PSA "Mars Maps" page (https://www.cosmos.esa.int/web/psa/mars-maps).
- Base URL: `https://archives.esac.esa.int/psa/ftp/MARS-EXPRESS/OMEGA/MEX-M-OMEGA-5-DDR-GLOBAL-MAPS-V1.0/`
- **Access: needs login.** Every file (labels included) returns `HTTP 401 Unauthorized`. The error page says that access is now restricted to authenticated users with an ESA **COSMOS** account (self-registration on the COSMOS site) and recommends `curl -u <user>` or HTTP basic auth. No public mirror was found (PDS Geosciences has no copy of these maps). **Owen has to create the COSMOS account himself.** For a non-interactive `sbatch` download, add a `machine archives.esac.esa.int login … password …` entry to `~/.netrc` (mode 600, as for Earthdata) and use `curl --netrc`.
- Files needed (the GeoTIFF carries the georeferencing; the PDS label documents scaling and nodata):

| Layer | File | Role |
| --- | --- | --- |
| Fe³⁺ band depth at 0.53 µm | `EXTRAS/FERRIC/FERRIC_BD530_EQU_MAP.TIF` + `DATA/FERRIC/FERRIC_BD530_EQU_MAP.LBL` | **scored layer** |
| Nanophase ferric oxides | `EXTRAS/FERRIC/FERRIC_NNPHS_EQU_MAP.TIF` + `.LBL` | diagnostic only (check M6) |
| Hydrous sites | `DATA/HYDROUS/HYDROUS_SITES_GEO_MAP.CSV` + `.LBL` | not used here (option A context) |

- Page metadata: 14400 × 7200 px, "1.48 km/pixel", "44 pixels/degree". **The page is inconsistent:** 14400 px / 360° = 40 px/deg, and 40 px/deg is exactly 1.48 km at the Mars equator. Treat it as **40 px/deg** and confirm from the GeoTIFF transform.
- **Unverified (the labels are behind the login):** data type, scaling/offset, nodata value, longitude convention (0–360 E or −180–180), latitude extent, and whether a larger BD530 means more ferric (expected: yes, it is a band depth). Size: about 415 MB per map if float32, 207 MB if 16-bit (unverified).
- Reference: Ody et al. (2012), *Global maps of anhydrous minerals at the surface of Mars from OMEGA/MEx*, JGR 117, E00J14. The BD530 index tracks fine-grained and nanophase ferric oxides, the reddening agent of Martian dust and bright soils.

### 1.2 Mars: TES mineral maps (ASU), for diagnostics only

- Products page: http://tes.mars.asu.edu/products/ (files are served from `http://tes.asu.edu/mineral_map/`). **No login.** Checked with HTTP HEAD on 2026-11-14.
- `TES_mineral_maps_4_ppd.envi` (53,913,600 bytes) + `TES_mineral_maps_4_ppd.envi.hdr`. The header says `samples = 1440`, `lines = 720`, `bands = 13`, `data type = 4` (float32), `interleave = bsq`, `byte order = 1` (big-endian). 1440 × 720 × 13 × 4 = 53,913,600 bytes, which matches the file size. The products page text says "16-bit integer"; **the header and the size win**.
- Band order (from the products page, in the order listed; **unverified** against the file, so check with M7): 1 Quartz, 2 K-feldspar, 3 Plagioclase, 4 Amphibole, 5 Low-Ca pyroxene, 6 High-Ca pyroxene, 7 Olivine, 8 Hematite, 9 Sulfates, 10 Carbonates, 11 Sheet silicates and high-Si glass, 12 Surface dust (0–1), 13 RMS error (0–0.005). Mineral bands range 0–0.2.
- Grid: simple cylindrical, 4 px/deg. The origin and longitude convention are **unverified** (`dsmap.cat` returns 404). Confirm with check M7: the band-8 hematite maximum must fall in Meridiani Planum (about 2° S, 354° E / −6° E).
- Use in this experiment: **diagnostics only**. Band 12 (surface dust) is used in check M5 to measure how much of the ferric rank is just dust cover. TES hematite is not scored (see §0).
- Reference: Bandfield (2002), *Global mineral distributions on Mars*, JGR 107(E6), 5042, doi:10.1029/2001JE001510.

### 1.3 Earth: EMIT L3 aggregated mineral spectral abundance (`EMITL3ASA`)

Checked in NASA CMR on 2026-11-14. Use **version 002**: it covers more time and the known issue barely touches iron oxides.

| | V001 | **V002 (use this)** |
| --- | --- | --- |
| CMR collection | — | `C3147269019-LPCLOUD` |
| Time coverage | 2022-08-10 to 2023-07-30 | 2022-08-10 to 2024-01-20 |
| Granule | `EMIT_L3_ASA_001` | `EMIT_L3_ASA_002` |
| File | `EMIT_L3_ASA_001.nc`, 12,171,693 B | `EMIT_L3_ASA_002.nc`, ~20,086,468 B (CMR lists the inner file name as `EMIT_L3_ASA_001.nc`; the URL is `_002`) |
| URL (Earthdata login) | `https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/EMITL3ASA.001/EMIT_L3_ASA_001/EMIT_L3_ASA_001.nc` | `https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/EMITL3ASA.002/EMIT_L3_ASA_002/EMIT_L3_ASA_002.nc` |

- Download through `earthaccess` with the existing `~/.netrc`, the same way as `download_aod.py`: `earthaccess.login(strategy="netrc")`, `earthaccess.search_data(short_name="EMITL3ASA", version="002")`, `earthaccess.download(...)`.
- The EMIT-10 minerals: calcite, chlorite, dolomite, goethite, gypsum, hematite, illite+muscovite, kaolinite, montmorillonite, vermiculite.
- Variables (V2 abstract and User Guide, JPL D-107868): 30 science layers, three per mineral: `<Mineral>` (median grain size), `<Mineral>_UQ_low_grainsize` (2.5th percentile) and `<Mineral>_UQ_high_grainsize` (97.5th percentile). Plus `latitude` and `longitude`, which give the **upper-left corner** of each cell. All float32, units `%` (mineral **mass fraction** estimate), `_FillValue = -9999.0`, dimensions (lat, lon), WGS-84, 0.5° cells. Names use the exact spelling of the guide: `Calcite`, `Chlorite`, `Dolomite`, `Goethite`, `Gypsum`, `Hematite`, `Illite+Muscovite`, `Kaolinite`, `Montmorillonite`, `Vermiculite`. V001 used `<Mineral>_uncert` instead. **Confirm the names with `ncdump -h` in the probe job (§4.1)** before relying on them. The guide's own table leaves out Kaolinite, and its grid line ("690 x 220 x 20") does not match a global 0.5° grid.
- Coverage: only arid dust-source regions between 52° N and 52° S. Each cell is masked for vegetation, cloud, water and urban areas. Cells with no EMIT data are fill. **Most Earth patches outside deserts will have no value** (case C, §3.3).

---

## 2. Physics: why only ferric oxides

- **What OMEGA BD530 measures:** the depth of the Fe³⁺ charge-transfer and crystal-field absorption near 0.53 µm in visible and near-infrared reflectance. On Mars it is strong where the surface is covered by bright, reddish, dust-like material rich in fine-grained or nanophase ferric oxides, and weak on dark basaltic surfaces.
- **What EMIT hematite and goethite measure:** mass-fraction estimates fitted to the same family of VNIR Fe³⁺ absorptions (about 0.4–1.0 µm) in Earth reflectance spectra of arid soils and dust sources.
- Both are VNIR iron-oxide signals from the optical surface (the top microns to millimetres). That is why the **ranks** can be compared: "this place is among the most iron-oxide-stained surfaces of its planet". The absolute values cannot be compared: one is a band depth, the other a mass fraction, the instruments and the atmospheric corrections differ, and Martian nanophase oxides are not identical to terrestrial hematite and goethite. **Only within-planet ranks are compared**, exactly like the dust dimension.
- **Known confound:** on Mars the ferric signal is largely a dust-cover signal. Check M5 measures how much of it is already in the dust dimension (atmospheric dust opacity, Montabone) and in TES surface dust. If it duplicates them (|ρ| > 0.7 with `dust_level_rank`), stop (stop condition 3).
- **Why not hydrated minerals:** see §0. Note also that EMIT's clays and gypsum describe a dust source's alteration products, while Martian hydrated sites are mostly ancient outcrops in crater walls, deltas and layered terrains, kilometres wide inside a 32 km patch. Even with a continuous Mars map, a patch-mean rank would mostly measure dust cover over the outcrop.

---

## 3. Scoring design

### 3.1 Per-patch value

- **Mars (T3 patches and T4 targets):** `ferric_bd530` is the mean of valid BD530 pixels in a lat/lon box centred on the patch centre, with a half-width of 16 km: Δlat = 16 / (R_mars · π/180) degrees and Δlon = Δlat / cos(lat), with R_mars from `BODY_RADII_M["Mars"]`. At 1.48 km/px this is about 22 × 22 px, which approximates the 32 km AEQD patch of `pipeline/geo.py` closely enough for a coarse context layer. (`geo.extract_patch` has DEM-specific filters and a 90 % valid rule, so it is not reused.) Require **≥ 50 % valid pixels**, otherwise NaN. Skip boxes that cross the antimeridian or reach |lat| > 88° (NaN). Count and log the skipped boxes.
- **Earth (T5 patches):** `ferric_emit = Hematite + Goethite` (median grain-size layers) from the nearest EMIT cell. A 0.5° cell (~55 km) is larger than a patch, so use nearest-cell sampling like `dust._sample_grid_nearest`, with cell centres = corner + (−0.25° lat, +0.25° lon). Confirm the latitude direction in the probe. If either mineral is fill (`-9999`) or non-finite, the value is NaN. Also store `Hematite`, `Goethite` and the uncertainty half-width `0.5 · ((H_high+G_high) − (H_low+G_low))`. They are reported only and not scored.

### 3.2 Ranks and score

Use the same helpers as T13 (`dust._rank_pct`, `dust._searchsorted_rank`). Reuse or import them; do not copy them.

- `mineral_rank_E`: percentile rank of `ferric_emit` over **Earth patches with a finite value** (arid regions only, because EMIT only covers them).
- Mars: percentile rank of `ferric_bd530` over the **T3 Mars patches** with a finite value. For each Mars target, `mineral_rank_T = _searchsorted_rank(sorted_mars, target_value)`.
- Moon targets: `mineral_rank_T = NaN` (case A, not applicable).

```
S_mineral(e, t) = exp( - ((mineral_rank_E[e] - mineral_rank_T[t]) / MINERAL_RANK_SIGMA)^2 / 2 )
MINERAL_RANK_SIGMA = 0.15        # same scale as DUST_RANK_SIGMA and THERMAL_UNIT
```

NaN if either rank is NaN. Then the T16 rules in `msi()` turn an Earth NaN into 0 when the target has the value.

**Caveat on the reference populations:** the Earth rank is taken over EMIT-covered (arid) patches and the Mars rank over the whole planet. "Top 10 % ferric on Earth" therefore means top 10 % among deserts. This is acceptable because analog candidates have to be bare ground anyway (environment dimension), but write it in the logbook verdict.

### 3.3 T16 missing-data policy (`docs/plan_t16_missing_data.md`)

- **Case A (body):** `DIMENSIONS` gets an 8th entry with `"key": "mineral"`, `"label": "Iron oxides (rank)"`, `"bodies": ["Mars"]`, `"source": "OMEGA BD530 ferric index (Mars), EMIT L3 ASA hematite+goethite (Earth)"` and a one-line description. `DIMENSION_BODIES` picks it up automatically.
- **Case B (target):** in `available_dims`, add `"mineral"` when the body is Mars **and** `tv.mineral_rank` is finite. Make `mineral_scores` return all-NaN for non-Mars bodies and for a NaN target rank, so the scorer and the table agree (T16 §2 rule).
- **Case C (Earth patch):** an Earth patch without EMIT coverage, while the Mars target has a value, is NaN in `S_mineral` → `msi()` counts it as `EARTH_MISSING_SCORE = 0.0`, and `match_all` lists it in `earth_missing_dims` and in `no_earth_data:mineral` mismatches. No new code is needed for case C beyond the dimension being present.
- New mismatch in `layer_mismatches` (Mars only): `mineral_rank` when both ranks are finite and |Δ| > `MISMATCH_RANK` (0.30), in the same format as the dust ranks.

### 3.4 Preset

Do **not** change the five existing presets: their weights get `"mineral": 0.00`, so their outputs must stay byte-identical (check A1). Add one experimental preset:

```python
"geology_and_materials_mineral_exp": {
    "label": "Geology and surface materials + iron oxides (experimental)",
    "applies_to": ["Mars"],
    "weights": {
        "topography": 0.20, "roughness": 0.10, "environment": 0.10, "thermal": 0.00,
        "geology": 0.40, "dust": 0.00, "ice": 0.00, "mineral": 0.20,
    },
},
```

It is `geology_and_materials` with 0.20 moved from geology to mineral, so a before/after comparison isolates the effect of the new dimension. Applying it only to Mars avoids a Moon `not_applicable_body` row that would be noise; T16 already handles that status if it appears.

---

## 4. Implementation tasks (for the implementing model)

Rules: run GitNexus `impact` before editing any existing symbol (CLAUDE.md), commits in English, never `nohup` (Slurm `sbatch` only, account `p089`, partition `cpu`), and Owen runs every Yuca command himself through Open OnDemand.

### 4.1 Download and probe job: `jobs/download_minerals.slurm` + `pipeline/minerals_download.py`

- EMIT V002 through `earthaccess` (netrc) into `data/raw/earth/emit/l3asa/`.
- OMEGA FERRIC_BD530 and FERRIC_NNPHS (TIF + LBL) into `data/raw/mars/omega_global/`, with `curl --netrc --fail`. If the request returns 401, exit non-zero with the message "COSMOS credentials missing in ~/.netrc (machine archives.esac.esa.int)".
- TES 4 ppd ENVI + header into `data/raw/mars/tes_minmap/` (public HTTP).
- Probe output `mineral_probe.json`: `ncdump -h`-equivalent variable list, fill values and lat/lon first and last values for EMIT; the full text of both OMEGA `.LBL` files plus the GeoTIFF CRS, transform, dtype and nodata (rasterio); the TES header and the band-8 argmax location. **Do not write scoring code against an unverified field name.** If the probe disagrees with §1, update this document first.
- Resources: 1 CPU, 4 GB, 1 h. Idempotent: skip a file that already exists with the expected size.

### 4.2 Layer module: `pipeline/mineral.py` (template: `pipeline/dust.py::run_dust`)

`run_mineral(project_dir, t3_dir, t4_dir, t5_dir, out_dir)` writes:

- `mineral_mars.parquet`: `lat, lon, ferric_bd530, mineral_rank` (T3 order).
- `mineral_earth.parquet`: `lat, lon, hematite, goethite, ferric_emit, ferric_emit_uq, mineral_rank_E` (T5 order, row-aligned, as `load_layers` requires).
- `mineral_targets.parquet`: `target_id, ferric_bd530, mineral_rank_T` (NaN for the Moon).
- `t_mineral_checks.json` (§4.4); fails on hard checks like T13. Two diagnostic PNG maps (Mars ferric rank, Earth ferric rank) are optional.
- Pure functions `ferric_box_mean(...)` and `S_mineral(...)`, testable without data.
- Job `jobs/t_mineral.slurm` (copy of `t13_dust.slurm`: 4 CPU, 32 GB, 45 min; the 400 MB OMEGA raster is read with windowed reads, never loaded whole).

### 4.3 Wiring in `pipeline/match.py`

- `DIMENSION_KEYS` += `"mineral"`; `DIMENSIONS` += entry (§3.3); all presets get `"mineral": 0.00` plus the new preset (§3.4).
- `LAYER_EARTH_COLUMNS["tmin"] = ("mineral_earth.parquet", ["mineral_rank_E"])`; `LAYER_TARGET_COLUMNS["tmin"] = ("mineral_targets.parquet", {"mineral_rank_T": "mineral_rank_T"})`.
- `load_layers` and the CLI get an **optional** `--mineral-dir`. When it is absent, the mineral columns are NaN, `S_mineral` is all NaN, the dimension is never in `available_dims` and the new preset runs with mineral excluded (coverage 0.8, see §4.5 item 7). This keeps the branch runnable without the new data, and `main`-like output must result (check A1).
- `EarthArrays.mineral_rank`, `TargetVec.mineral_rank`, `build_earth_arrays`, `target_vec_from_row`, `score_target` (`scores["mineral"] = mineral_scores(...)`), `available_dims`, `layer_mismatches`.
- `jobs/t7_match.slurm`: pass `--mineral-dir "$MINERAL_DIR"` only when `MINERAL_DIR` is set.
- **Export and app: out of scope** for the experiment. Check that `pipeline/export.py` still runs: it iterates `PRESET_KEYS`, so the new preset flows into the JSON. If an export check hard-codes five presets or seven dimensions, relax it on this branch only and say so in the commit. The app is not changed.

### 4.4 Checks in `t_mineral_checks.json`

| ID | Kind | Check |
| --- | --- | --- |
| E1 | hard | EMIT variables `Hematite`, `Goethite` present; fill −9999 masked; ≥ 1 % of T5 patches finite. |
| E2 | hard | Ferric rank of the cell at central Australia (−25, 130) > 0.6 (red desert soils). |
| E3 | soft | White Sands, NM (32.9, −106.3) ferric rank < 0.5 (gypsum dunes; report only, because the 0.5° cell mixes in red soils). |
| M1 | hard | OMEGA BD530 grid = 14400 × 7200 at 40 px/deg (or as the label says, with this doc updated). |
| M2 | hard | Arabia Terra (20° N, 5° E) ferric rank > Syrtis Major (8.5° N, 69.5° E) ferric rank (bright ferric dust vs dark basalt). |
| M3 | hard | ≥ 70 % of T3 Mars patches finite. |
| M4 | soft | Fraction of Mars targets with a finite `mineral_rank_T` (report). |
| M5 | **decision** | Spearman ρ over T3 Mars patches of the ferric rank vs `dust_level_rank` (T13) and vs TES surface dust (band 12). Report both. **If \|ρ(dust_level_rank)\| > 0.7, then verdict "drop"** (stop condition 3). |
| M6 | soft | Spearman ρ of BD530 vs NNPHS (expected strongly positive; a sanity check of the sign). |
| M7 | soft | TES band-8 (hematite) maximum within 10° of Meridiani (2° S, 6° W): confirms the TES band order and longitude convention used in M5. |

### 4.5 Tests: `tests/test_mineral.py` and additions to `tests/test_match.py` (synthetic only, no downloads)

1. `S_mineral`: equal ranks → 1.0; |Δ| = 0.15 → exp(−0.5); NaN on either side → NaN.
2. `ferric_box_mean` on a synthetic 40 px/deg grid: constant field → that constant; < 50 % valid → NaN; a box across the antimeridian → NaN; the box widens with latitude (1/cos lat).
3. EMIT sampling: fill −9999 → NaN; corner-to-centre offset picks the right cell; hematite + goethite sum.
4. `available_dims`: Mars with a finite rank → contains `mineral`; Mars with a NaN rank → does not; Moon → never.
5. Case C: Mars target with a value, Earth patch NaN → the new preset's MSI equals the weighted mean with 0 for mineral (reuse the T16 test pattern).
6. **Non-regression:** with `mineral` weight 0 in the five existing presets, their MSI and top-30 lists are identical to the scores without the mineral dimension on the existing synthetic fixture.
7. Without `--mineral-dir`: for a Mars target the experimental preset's coverage is 0.8 (mineral missing, 0.2 of 1.0), which is ≥ `MIN_PRESET_COVERAGE`, so its status is `ok`, `missing_dims == ["mineral"]`, and it ranks with mineral excluded (case B). Assert this explicitly so nobody mistakes such a run for a scored one. For the same reason the comparison script (§5) must refuse to run when `mineral` is not in `available_dims` for the Mars targets.
8. `layer_mismatches` emits `mineral_rank` for |Δ| > 0.30 on Mars only.

Run with `python -m pytest tests -q` locally (no cluster needed). All existing tests must still pass.

---

## 5. Before/after comparison: `tools/compare_mineral.py`

Input: a `matches.parquet` from the new T7 run. Output: `mineral_comparison.md` + `.csv` in the run directory. For each Mars target:

- top-30 overlap (Jaccard) between `rank_geology_and_materials` and `rank_geology_and_materials_mineral_exp`;
- Spearman ρ of the two MSI columns over the union;
- number of analogs that enter or leave the top 10;
- mean `S_mineral` of the top 10 under each preset, and the share of top-30 analogs with `no_earth_data:mineral` (case C) under the new preset.

Plus a global summary and a list of the 5 targets that changed most, with their top-3 before and after (lat, lon, country if available).

**How to read it** (put this text in the verdict):

- *Improves*: overlap stays moderate (Jaccard 0.4–0.8), the analogs that enter are known red, iron-rich deserts (Pilbara, central Australia, Sahara red sands, Namib) for high-ferric Mars targets (Meridiani, Gale, Oxia), and dark basaltic targets (Syrtis-like) pull toward volcanic fields with low ferric rank.
- *Distorts*: Jaccard < 0.3 for many targets, with case-C zeros pushing out good terrain matches only because EMIT does not cover them, or the entering analogs are explained by dust or latitude rather than iron oxides (check M5).
- Expect the case-C effect to dominate outside EMIT's desert footprint. Report it as a number; do not hide it.

---

## 6. Commands for Owen on Yuca (Open OnDemand shell, no SSH, `sbatch` only)

Owen's own one-time steps (Claude cannot do these for him):

1. Create an ESA COSMOS account (self-registration on the COSMOS site; the link is on https://www.cosmos.esa.int/web/psa/mars-maps).
2. Add it to `~/.netrc` on Yuca, next to the Earthdata entry, and keep the file at mode 600:
   `machine archives.esac.esa.int login <cosmos-user> password <cosmos-password>`

Use a **separate checkout** so the production clone at `/lustre/proyectos/p089/code` stays on `main`:

```bash
cd /lustre/proyectos/p089/code && git fetch origin && git worktree add /lustre/proyectos/p089/code_exp_mineral exp/mars-mineral-dimension
```

```bash
cd /lustre/proyectos/p089/code_exp_mineral && git pull && sbatch jobs/download_minerals.slurm
```

Paste back `output/download_minerals_<job>.log` and `mineral_probe.json`. If the probe changes anything in §1, the implementing model updates this doc and the code before continuing.

```bash
cd /lustre/proyectos/p089/code_exp_mineral && sbatch --export=ALL,T5_DIR=/lustre/proyectos/p089/runs/2242438 jobs/t_mineral.slurm
```

Paste back the log and `t_mineral_checks.json`. Stop here if a hard check fails or check M5 says drop.

```bash
cd /lustre/proyectos/p089/code_exp_mineral && sbatch --export=ALL,T5_DIR=/lustre/proyectos/p089/runs/2242438,T12_DIR=/lustre/proyectos/p089/runs/2242487,T13_DIR=/lustre/proyectos/p089/runs/2242484,T14_DIR=/lustre/proyectos/p089/runs/2242486,MINERAL_DIR=/lustre/proyectos/p089/runs/<t_mineral job id> jobs/t7_match.slurm
```

The T5/T12/T13/T14 directories are those of production run 2242490 (`docs/plan_t16_missing_data.md` §8). `<t_mineral job id>` is the number `sbatch` printed for the previous job: Owen fills it in from his own output.

```bash
cd /lustre/proyectos/p089/code_exp_mineral && conda run -n spaceapps_2026 python tools/compare_mineral.py --run-dir /lustre/proyectos/p089/runs/<t7 job id>
```

(This last step is a few seconds of pandas on one parquet. If the login node policy forbids even that, wrap it in a 5-minute `sbatch --wrap`.)

Paste back `mineral_comparison.md`. Nothing from this run goes into `app/public/data/` on `main`.

---

## 7. Acceptance (definition of done for the branch)

1. This spec, the code of §4, the tests of §4.5 passing locally, and the Slurm jobs of §4.1–4.3, all on `exp/mars-mineral-dimension`, pushed.
2. Check A1: with no `--mineral-dir`, `rank_*` and `msi_*` of the five existing presets are identical to a `main` run on the same inputs (the test of §4.5 item 6 is enough if no cluster run is available).
3. If Owen runs §6: `t_mineral_checks.json` and `mineral_comparison.md` summarised in the logbook.
4. A short **keep / drop** verdict in `docs/logbook.md` on this branch (§9).

## 8. Things that must not change

- The five existing presets, their weights and outputs, the Moon pipeline, and `analogs_universe.json` on `main`.
- The T16 constants (`EARTH_MISSING_SCORE`, `MIN_PRESET_COVERAGE`).
- No absolute cross-planet mineral values anywhere: ranks only.

## 9. Verdict template for `docs/logbook.md`

```
## 2026-11-1x: Experiment B, scored Mars iron-oxide dimension (branch exp/mars-mineral-dimension)

**Verdict: KEEP / DROP.** One or two sentences why.

- Data: OMEGA BD530 (COSMOS login: yes/no), EMIT L3ASA V002. Checks: hard x/y, soft x/y.
- Redundancy: Spearman ρ vs dust_level_rank = …, vs TES surface dust = … .
- Effect (geology_and_materials vs experimental preset, Mars targets): median Jaccard top-30 = …, case-C share in top 30 = … .
- Hydrated minerals and carbonates: not scored (no continuous Mars map; TES near detection limits). Display-only context (option A).
- Not merged to main.
```

If the COSMOS account is not available before the deadline, the verdict is **DROP for the submission**, reason "Mars ferric map behind ESA login, no defensible public substitute", and the pre-registered design above stays on the branch for later.

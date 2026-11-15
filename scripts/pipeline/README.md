# `scripts/pipeline/` — Core Python Processing Engine

The `pipeline` package is a modular Python 3.11+ library engineered for large-scale planetary and terrestrial geoprocessing, morphometric feature extraction, multi-dimensional similarity ranking, and JSON contract serialization.

---

## Module Index & Technical Reference

| Module | Primary Responsibilities | Key Functions / Classes |
| :--- | :--- | :--- |
| **`geo.py`** | **Geodesy & Cartographic Reprojection** | `local_aeqd_projection()`, `haversine_distance()`, `filter_spatial_diversity()`, `reproject_patch()` |
| **`features.py`** | **Scale-Invariant Morphometric Extraction** | `compute_slope_aspect()`, `compute_tri()`, `extract_patch_features()`, `morphometric_vector()` |
| **`planet_features.py`** | **Planetary DEM Ingestion (Moon & Mars)** | `sweep_lola_tiles()`, `sweep_mola_global()`, `process_celestial_body()` |
| **`earth_features.py`** | **Terrestrial DEM Sweep (Copernicus GLO-90)** | `sweep_glo90_tiles()`, `filter_bare_land()`, `sample_terrestrial_grid()` |
| **`earth_layers.py`** | **Context Layers & Ground Logistics** | `apply_modis_ndvi_mask()`, `extract_lst_thermal()`, `calculate_road_distance()`, `calculate_airport_distance()` |
| **`targets.py`** | **Planetary Targets & Unsupervised Clustering** | `load_curated_targets()`, `run_kmeans_clustering()`, `build_target_catalogue()` |
| **`match.py`** | **Multi-Dimensional RBF Matching Engine** | `rbf_kernel_distance()`, `calculate_msi()`, `rank_candidates()`, `apply_mission_presets()` |
| **`export.py`** | **Contract Packaging & Schema Validation** | `build_universe_contract()`, `validate_contract_schema()`, `serialize_universe_json()` |
| **`geology.py`** / **`geology_rules.py`** | **Harmonized Lithology Classifier** | `classify_glim_unit()`, `map_planetary_geology()`, `lithology_compatibility_matrix()` |
| **`dust.py`** | **Atmospheric Particulates & Dust Aerosols** | `process_modis_aod()`, `process_mars_cdod()`, `dust_similarity_score()` |
| **`ice.py`** | **Cryospheric Indicators & Volatiles Stability** | `evaluate_lunar_psr()`, `evaluate_mars_sharad_ice()`, `cryo_similarity_score()` |
| **`iau.py`** | **IAU Geodetic Constants & Planetary Spheroids** | Planetary radii ($R_{\text{Earth}}, R_{\text{Moon}}, R_{\text{Mars}}$), flattening ratios, coordinate conventions |
| **`config.py`** | **Pipeline Paths & Hyperparameters** | Cluster filesystem roots, bandwidths $\sigma$, resolution grids, default presets |

---

## Core Algorithms & Implementation Details

### 1. Local AEQD Projection (`geo.py`)
To prevent severe distortion in polar regions (e.g. Artemis III lunar South Pole landing sites), `geo.py` computes on-the-fly local Azimuthal Equidistant coordinate systems:
- Center of projection is anchored at the target's geodetic latitude and longitude $(\phi_0, \lambda_0)$.
- Distance scale is true along all geodesics radiating from the origin.
- A standardized $64 \times 64$ grid at $500\text{ m/px}$ (spanning $32\text{ km} \times 32\text{ km}$) is sampled via bilinear interpolation.

### 2. Terrain Ruggedness Index (TRI) (`features.py`)
Implemented using vectorized NumPy convolution over 8-connected neighborhoods:
```python
# TRI: Mean elevation difference across N8 neighborhood
diffs = [np.abs(padded[1:-1, 1:-1] - np.roll(np.roll(padded, dy, axis=0), dx, axis=1)[1:-1, 1:-1])
         for dy, dx in NEIGHBORS_8]
tri_grid = np.mean(diffs, axis=0)
```

### 3. Spatial Diversity Constraint (`geo.py` & `match.py`)
Enforces geographic dispersion so no single region dominates candidate rankings:
```python
def enforce_spatial_diversity(candidates: list[Candidate], min_dist_km: float = 150.0) -> list[Candidate]:
    selected = []
    for cand in candidates:
        if all(haversine(cand.coords, s.coords) >= min_dist_km for s in selected):
            selected.append(cand)
    return selected
```

---

## Unit Testing & Verification

All modules in `pipeline/` are backed by automated unit tests in the top-level `tests/` directory:

```bash
# Test all pipeline modules
pytest tests/
```

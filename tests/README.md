# `tests/` — Automated Synthetic Unit Test Suite

This directory contains the automated test suite for **PROTOTERRA**. Engineered for reproducibility and zero-cluster-dependency, all **119 test cases** run against in-memory synthetic fixtures, allowing full algorithmic verification without downloading the 80 GB planetary raster dataset.

---

## Testing Philosophy & Design Principles

1. **Synthetic & Self-Contained:**
   Tests generate mathematical geometric surfaces (synthetic craters, sloping planes, sinusoidal roughness, synthetic DEM arrays) in memory. No external internet connection or Yuca cluster access is required.
2. **Strict Geodetic & Coordinate Invariance:**
   Verifies that local Azimuthal Equidistant (AEQD) projections and Haversine distance functions preserve spatial properties across high-latitude polar regions and equatorial transitions.
3. **Contract & Schema Integrity:**
   Validates that the output JSON contract (`analogs_universe.json`) conforms exactly to the schema expected by the Vue 3 frontend application.
4. **Deterministic Math & Numerical Stability:**
   Tests check RBF kernel tolerances, edge cases (zero slope, missing data bands, nodata masks), and weighted mean numerical precision.

---

## Test Modules Index

| Test Module | Target Pipeline Component | Key Test Scenarios |
| :--- | :--- | :--- |
| **`test_geo.py`** | `pipeline/geo.py` | Local AEQD reprojection accuracy, polar distortion mitigation, Haversine geodesic distances, 150 km spatial diversity filter. |
| **`test_features.py`** | `pipeline/features.py` | Finite-difference slope gradients, aspect angles, 90th percentile slope ($s_{90}$), Terrain Ruggedness Index (TRI) convolution. |
| **`test_match.py`** | `pipeline/match.py` | Multi-dimensional Gaussian RBF kernel behavior, preset weighting calculations, top-N candidate selection, tie-breaking. |
| **`test_export.py`** | `pipeline/export.py` | JSON serialization format, field nullability, range boundaries ($S_d \in [0, 1]$), schema validation of `Universe`. |
| **`test_targets.py`** | `pipeline/targets.py` | Ingestion of 16 curated exploration targets, coordinate boundary sanity checks, k-means clustering deterministic behavior. |
| **`test_earth_features.py`** | `pipeline/earth_features.py` | Copernicus DEM tile parsing, bare-land masking, elevation bounds check. |
| **`test_earth_layers.py`** | `pipeline/earth_layers.py` | MODIS NDVI vegetation thresholding (<0.20), LST diurnal thermal profile extraction, airport/road distance calculation. |
| **`test_geology.py`** | `pipeline/geology.py` | GLiM lithology categorization, USGS SIM 3292 stratigraphic unit translation, compatibility scoring. |
| **`test_dust.py`** | `pipeline/dust.py` | MODIS AOD and Martian CDOD optical depth scoring, seasonal dust storm handling. |
| **`test_ice.py`** | `pipeline/ice.py` | Lunar Permanently Shadowed Regions (PSR) cold-trap conditions, Martian SHARAD radar dielectric ice stability. |
| **`test_iau.py`** | `pipeline/iau.py` | IAU planetary ellipsoids, equatorial/polar radii constants, unit consistency. |
| **`test_mineral.py`** / **`test_minerals*.py`** | `pipeline/mineral*.py` | Mineralogical data parser integrity and NetCDF format tests. |

---

## Running the Test Suite

### Running All Tests

From the repository root with virtual environment activated:

```bash
# Run the complete test suite
pytest tests/
```

### Verbose Output with Timing

```bash
pytest tests/ -v --durations=10
```

### Running Specific Module Tests

```bash
# Test only geodesy and projection logic
pytest tests/test_geo.py

# Test matching and MSI similarity scoring
pytest tests/test_match.py

# Test schema export
pytest tests/test_export.py
```

---

## Test Execution Summary

```text
============================= test session starts =============================
platform: win32 / linux -- Python 3.11+ / 3.15, pytest-9.2+, pluggy-1.7+
rootdir: /Space_Apps_2026_Analogos_Luna_Marte, configfile: pytest.ini
collected 119 items

tests/test_dust.py ....                                                  [  3%]
tests/test_earth_features.py ..ss...                                     [  9%]
tests/test_earth_layers.py ...........                                   [ 18%]
tests/test_export.py ....                                                [ 21%]
tests/test_features.py ....                                              [ 25%]
tests/test_geo.py ..........                                             [ 33%]
tests/test_geology.py ...                                                [ 36%]
tests/test_iau.py ...                                                    [ 38%]
tests/test_ice.py ..                                                     [ 40%]
tests/test_match.py ............................                         [ 63%]
tests/test_mineral.py .......                                            [ 69%]
tests/test_minerals.py .......                                           [ 75%]
tests/test_minerals_loaders.py ...............                           [ 88%]
tests/test_planet_features.py ......                                     [ 93%]
tests/test_targets.py ........                                           [100%]

================= 117 passed, 2 skipped, 2 warnings in 23.28s =================
```

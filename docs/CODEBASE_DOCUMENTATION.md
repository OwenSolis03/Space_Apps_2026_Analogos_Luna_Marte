# Planetary Analog Pipeline & Web Application: Technical Architecture & Codebase Documentation

**NASA Space Apps Challenge 2026**  
**Project:** Planetary Analog Site Selection Pipeline for the Moon and Mars  
**Repository Branch:** `feat/t17-plain-language`  
**Language Standard:** English (Scientific & Engineering Documentation)

---

## Table of Contents
1. [Executive Summary & Scientific Mission](#1-executive-summary--scientific-mission)
2. [Repository Architecture & Directory Structure](#2-repository-architecture--directory-structure)
3. [Core Pipeline Engine (`scripts/pipeline/`)](#3-core-pipeline-engine-pipeline)
   - [3.1 Configuration & Geodesy (`scripts/pipeline/config.py`, `scripts/pipeline/geo.py`)](#31-configuration--geodesy-pipelineconfigpy-pipelinegeopy)
   - [3.2 Geomorphometric Feature Extraction (`scripts/pipeline/features.py`)](#32-geomorphometric-feature-extraction-pipelinefeaturespy)
   - [3.3 Planetary Targets & IAU Nomenclature (`scripts/pipeline/targets.py`, `scripts/pipeline/iau.py`)](#33-planetary-targets--iau-nomenclature-pipelinetargetspy-pipelineiaupy)
   - [3.4 Geological & Lithological Taxonomy (`scripts/pipeline/geology_rules.py`, `scripts/pipeline/geology.py`)](#34-geological--lithological-taxonomy-pipelinegeology_rulespy-pipelinegeologypy)
   - [3.5 Environmental Dimensions: Cryosphere & Atmospheric Dust (`scripts/pipeline/ice.py`, `scripts/pipeline/dust.py`)](#35-environmental-dimensions-cryosphere--atmospheric-dust-pipelineicepy-pipelinedustpy)
   - [3.6 Planetary & Terrestrial DEM Processors (`scripts/pipeline/planet_features.py`, `scripts/pipeline/earth_features.py`)](#36-planetary--terrestrial-dem-processors-pipelineplanet_featurespy-pipelineearth_featurespy)
   - [3.7 Contextual Earth Layers & Logistics (`scripts/pipeline/earth_layers.py`)](#37-contextual-earth-layers--logistics-pipelineearth_layerspy)
   - [3.8 Multidimensional Matching & Scoring Engine (`scripts/pipeline/match.py`)](#38-multidimensional-matching--scoring-engine-pipelinematchpy)
   - [3.9 Validation, Serialization & Export (`scripts/pipeline/export.py`)](#39-validation-serialization--export-pipelineexportpy)
   - [3.10 Package Aggregation (`scripts/pipeline/__init__.py`)](#310-package-aggregation-pipeline__init__py)
4. [Standalone Operational Scripts & Utilities](#4-standalone-operational-scripts--utilities)
   - [4.1 Data Acquisition Scripts (`download_earthdata.py`, `download_aod.py`)](#41-data-acquisition-scripts-download_earthdatapy-download_aodpy)
   - [4.2 Pipeline v1 Legacy & Transition Scripts (`process_analogs.py`, `match_earth_analogs.py`, `enrich_nomenclature.py`)](#42-pipeline-v1-legacy--transition-scripts-process_analogspy-match_earth_analogspy-enrich_nomenclaturepy)
   - [4.3 Verification & Tooling (`scripts/tools/explore_datasets.py`, `scripts/tools/v1_to_sample.py`, `scripts/tools/verify_t16.py`)](#43-verification--tooling-toolsexplore_datasetspy-toolsv1_to_samplepy-toolsverify_t16py)
5. [Automated Test Suite (`tests/`)](#5-automated-test-suite-tests)
6. [Interactive Web Application (`app/`)](#6-interactive-web-application-app)
   - [6.1 Frontend Architecture & Component Tree](#61-frontend-architecture--component-tree)
   - [6.2 State Management & Client-Side MSI Engine](#62-state-management--client-side-msi-engine)
   - [6.3 Narrative Content & Plain-Language Translators](#63-narrative-content--plain-language-translators)
7. [Mathematical Formulations & Scientific Methodology](#7-mathematical-formulations--scientific-methodology)
   - [7.1 Geodesy & Local AEQD Projection](#71-geodesy--local-aeqd-projection)
   - [7.2 Seven Canonical Geomorphometric Metrics](#72-seven-canonical-geomorphometric-metrics)
   - [7.3 Radial Basis Function (RBF) Distance Metric](#73-radial-basis-function-rbf-distance-metric)
   - [7.4 Missing Data Imputation & Re-weighting Policy (T16)](#74-missing-data-imputation--re-weighting-policy-t16)
   - [7.5 Spatial Diversity Constraint Algorithm](#75-spatial-diversity-constraint-algorithm)
8. [Data Contracts & Schema Specifications](#8-data-contracts--schema-specifications)

---

## 1. Executive Summary & Scientific Mission

The **Planetary Analog Pipeline** is a computational framework developed for the NASA Space Apps Challenge 2026. Its primary scientific objective is to identify, characterize, and rank terrestrial geographical sites that exhibit high physical and operational fidelity to target exploration environments on **the Moon** and **Mars**.

Terrestrial planetary analogs are critical for:
- Testing autonomous rover locomotion, hazard detection, and mobility software over representative terrain roughness.
- Developing and validating In-Situ Resource Utilization (ISRU) technologies (e.g., volatile extraction from water ice, regolith sintering).
- Training astronauts in EVA (Extravehicular Activity) operations and geological field reconnaissance.
- Calibrating remote-sensing orbital instruments against known ground truths.

Traditional analog selection has historically relied on anecdotal field choices or isolated geological similarities. This project formalizes analog identification into a **multidimensional, quantitative, data-driven optimization pipeline** leveraging high-resolution global datasets from NASA, USGS, ESA, and Copernicus missions.

```
       +-------------------------------------------------------+
       |                  PLANETARY TARGETS                    |
       |  Curated exploration sites (e.g., Artemis III, Jezero) |
       |     + Global K-Means Morphological Archetypes         |
       +---------------------------+---------------------------+
                                   |
                                   v
+---------------------------------------------------------------------+
|                  MULTIDIMENSIONAL FEATURE EXTRACTION                 |
|                                                                     |
|  [Geomorphometry]     Copernicus GLO-90 vs. MOLA / LOLA DEMs         |
|  [Lithology]          GLiM vs. USGS Lunar / Martian Geological Maps |
|  [Cryosphere]         MODIS LST vs. Diviner South Polar Temperatures|
|  [Dust / Aeolian]     MODIS Deep Blue AOD vs. Montabone CDOD Climatology|
|  [Logistics]          Natural Earth Road Networks & Airports         |
+----------------------------------+----------------------------------+
                                   |
                                   v
+---------------------------------------------------------------------+
|                  MATCHING ENGINE & SCATTER FILTERING                 |
|                                                                     |
|  - Radial Basis Function (RBF) Kernels for Geomorphic Similarity     |
|  - Symmetric 8-Class Planetary Geological Cross-Matrix              |
|  - Missing Data Policy (T16 dynamic re-weighting)                   |
|  - Spatial Diversity Constraint (50 km suppression radius)          |
+----------------------------------+----------------------------------+
                                   |
                                   v
+---------------------------------------------------------------------+
|                 EXPORT & VISUALIZATION PLATFORM                     |
|                                                                     |
|  - JSON Universe Specification (`analogs_universe.json`)            |
|  - Reactive Web Application (Vite + React + TypeScript + Leaflet)   |
|  - Real-time Sub-Score Adjuster & Operational Scenario Simulator    |
+---------------------------------------------------------------------+
```

---

## 2. Repository Architecture & Directory Structure

```
Space_Apps_2026_Analogos_Luna_Marte/
├── .github/                         # Continuous integration & issue templates
├── app/                             # Interactive React/TypeScript web application
│   ├── public/                      # Static assets and GeoJSON/TopoJSON basemaps
│   │   └── data/
│   │       └── analogs_universe.json # Canonical data universe consumed by the frontend
│   ├── src/
│   │   ├── components/              # Modular UI components
│   │   │   ├── Dossier.tsx          # Comprehensive analog scientific report
│   │   │   ├── InfoToggle.tsx       # Explanatory modals & scientific glossary
│   │   │   ├── Radar.tsx            # SVG 5-axis dimensional radar chart
│   │   │   ├── RankList.tsx         # Filterable list of ranked candidate sites
│   │   │   ├── ScenarioPanel.tsx    # Weight presets (Traverse, Habitation, ISRU)
│   │   │   └── SiteMap.tsx          # Leaflet geographic map view
│   │   ├── lib/                     # Client-side algorithmic libraries
│   │   │   ├── content.ts           # Mission overviews & target descriptions
│   │   │   ├── explanations.ts      # Plain-language metric explainers (T17)
│   │   │   └── msi.ts               # Dynamic client-side MSI recalculation
│   │   ├── App.tsx                  # Top-level state coordinator & layout
│   │   ├── index.css                # Tailwind CSS styling directives
│   │   ├── main.tsx                 # React application DOM entry point
│   │   └── types.ts                 # TypeScript data contracts & schema interfaces
│   ├── package.json                 # Node.js dependencies and scripts
│   ├── tsconfig.json                # TypeScript compiler configuration
│   └── vite.config.ts               # Vite bundler configuration
├── docs/                            # Scientific documentation and implementation plans
│   ├── CODEBASE_DOCUMENTATION.md    # This master technical documentation
│   ├── master_plan.md               # Master engineering architecture
│   ├── pipeline.md                  # HPC pipeline runbook and data flow
│   ├── plan_t16_missing_data.md     # Mathematical treatment of missing environmental data
│   └── plan_t17_plain_language.md   # Translation & nomenclature guidelines
├── data/                            # Hand-written definitions the pipeline reads (targets, known analogs, limits, overrides, ice hints)
├── models/                          # Documentation of the similarity model; there are no trained networks
├── scripts/                         # Everything that processes data
│   ├── pipeline/                    # Core Python planetary analog processing engine (python -m pipeline.<module>)
│   │   ├── __init__.py                  # Package exports and module definitions
│   │   ├── config.py                    # Physical planetary constants, paths, and grids
│   │   ├── dust.py                      # Atmospheric dust & optical depth analog module (T13)
│   │   ├── earth_features.py            # Earth DEM processing & vegetation masking
│   │   ├── earth_layers.py              # MODIS NDVI, LST, logistics, and analog catalogs
│   │   ├── export.py                    # Acceptance verification & JSON universe export
│   │   ├── features.py                  # Geomorphometric feature calculation routines
│   │   ├── geo.py                       # Geodesy, local AEQD projections, raster windows
│   │   ├── geology.py                   # GLiM & USGS vector/raster spatial queries
│   │   ├── geology_rules.py             # 8-class planetary geological classification
│   │   ├── iau.py                       # IAU/USGS planetary nomenclature parser
│   │   ├── ice.py                       # Cryosphere & thermal analog matching module (T12)
│   │   ├── match.py                     # Multidimensional Similarity Index (MSI) engine
│   │   ├── planet_features.py           # Global planetary quasi-equiareal grid processor
│   │   └── targets.py                   # Curated exploration targets & K-Means clustering
│   ├── jobs/                        # Slurm jobs, one per task, plus the data downloads
│   ├── tools/                       # Downloaders, dataset explorer, verification and sensitivity scripts, sample converter
│   └── legacy_v1/                   # v1 prototype (scripts, jobs, outputs, logs), kept as reference and never imported
├── tests/                           # Complete pytest unit and integration test suite
│   ├── __init__.py                  # Test package initialization
│   ├── test_dust.py                 # Tests for optical depth and dust seasonality
│   ├── test_earth_features.py       # Tests for GLO-90 VRT and vegetation filtering
│   ├── test_earth_layers.py         # Tests for MODIS compositing and logistics
│   ├── test_export.py               # Tests for JSON serialization & schema compliance
│   ├── test_features.py             # Tests for 7 geomorphometric metric calculations
│   ├── test_geo.py                  # Tests for AEQD projections, antimeridian, nodata
│   ├── test_geology.py              # Tests for GLiM coastal fallbacks and USGS queries
│   ├── test_iau.py                  # Tests for gazetteer reading and Haversine queries
│   ├── test_ice.py                  # Tests for cryospheric thermal rankings
│   ├── test_match.py                # Tests for MSI, missing data cases, diversity
│   ├── test_planet_features.py      # Tests for planetary grid generation and extraction
│   └── test_targets.py              # Tests for curated target schemas & clustering
```

---

## 3. Core Pipeline Engine (`scripts/pipeline/`)

The `pipeline` directory constitutes the scientific core of the system. All modules are implemented in Python 3.10+ using `numpy`, `scipy`, `pandas`, `geopandas`, `shapely`, and `rasterio`.

### 3.1 Configuration & Geodesy (`scripts/pipeline/config.py`, `scripts/pipeline/geo.py`)

#### `scripts/pipeline/config.py`
Defines physical constants, spatial resolutions, directory paths, and default hyperparameters.
- **Planetary Radii**:
  - Mars mean volumetric radius: $R_{Mars} = 3{,}389{,}500\text{ m}$.
  - Moon mean volumetric radius: $R_{Moon} = 1{,}737{,}400\text{ m}$.
  - Earth WGS84 authalic sphere radius: $R_{Earth} = 6{,}371{,}000\text{ m}$.
- **Patch Resolution**:
  - Analysis bounding box: $10\text{ km} \times 10\text{ km}$ ($10{,}000\text{ m} \times 10{,}000\text{ m}$).
  - Canonical raster grid dimensions: $100 \times 100$ cells ($100\text{ m}$ ground sampling distance).
- **Paths**:
  - Dynamically detects the local scratch environment (`/lustre/proyectos/p089` on the HPC cluster or local directory on Windows).

#### `scripts/pipeline/geo.py`
Provides geodetic conversions, local Azimuthal Equidistant (AEQD) projections, and windowed raster extraction.
- `local_aeqd_wkt(lat, lon, body)`: Generates an OGC Well-Known Text (WKT) string defining a custom sphere-centric AEQD projection centered on `(lat, lon)` using the planetary sphere radius.
- `extract_patch(raster_path, lat, lon, size_km, res_m, body)`:
  - Reprojects raster data directly into a local metric projection centered on the region of interest.
  - Automatically handles **antimeridian crossings** ($\pm 180^\circ$ longitude) and **polar singularities** ($\pm 90^\circ$ latitude) via coordinate unwrapping and local metric coordinate grids.
  - Supports scaling and offset correction (e.g., LOLA elevation offset $0.5\text{ m}$ with `int16` encoding).
- `clean_patch(dem_patch, nodata_value)`: Cleans invalid pixels using 2D bi-cubic or nearest-neighbor interpolation; rejects patches containing $>20\%$ nodata pixels.

---

### 3.2 Geomorphometric Feature Extraction (`scripts/pipeline/features.py`)

Computes seven scale-invariant and physically interpretable geomorphometric properties from a $100 \times 100$ elevation patch ($100\text{ m}$ pixel resolution):

```python
FEATURE_NAMES = [
    "mean_slope",          # Mean surface slope in degrees
    "p90_slope",           # 90th percentile slope (obstacle severity)
    "relief",              # Total vertical elevation delta (max - min) in meters
    "hypsometric_integral",# Hypsometric Integral (HI) dimensionless elevation distribution
    "detrended_roughness", # Standard deviation of residuals from fitted best-fit plane (m)
    "tri",                 # Riley et al. Terrain Ruggedness Index (m)
    "mean_elevation",      # Mean local elevation above datum (m)
]
```

Key functions:
- `compute_slope_and_aspect(elevation_grid, pixel_spacing_m)`: Uses Horn's 8-neighbor gradient filter ($\frac{\partial z}{\partial x}, \frac{\partial z}{\partial y}$) with edge padding.
- `compute_hypsometric_integral(elevation_grid)`: Computes $HI = \frac{\bar{z} - z_{min}}{z_{max} - z_{min}}$.
- `compute_detrended_roughness(elevation_grid, pixel_spacing_m)`: Fits a first-order bivariate polynomial $z(x, y) = Ax + By + C$ via Ordinary Least Squares (OLS) and computes the standard deviation of the planar residuals $\sigma_{planar}$.
- `compute_tri(elevation_grid)`: Implements Riley's Terrain Ruggedness Index ($TRI = \sqrt{\frac{1}{8}\sum_{i=1}^8 (z_0 - z_i)^2}$).
- `extract_features_from_patch(elevation_grid, pixel_spacing_m)`: Orchestrates the full 7-feature pipeline into a unified `dict` and validates numerical bounds.

---

### 3.3 Planetary Targets & IAU Nomenclature (`scripts/pipeline/targets.py`, `scripts/pipeline/iau.py`)

#### `scripts/pipeline/targets.py`
Manages exploration targets on Mars and the Moon.
- **Curated Mission Targets**:
  - **Mars**: Jezero Crater (Perseverance), Gale Crater (Curiosity), Olympus Mons, Valles Marineris (Coprates Chasma), Utopia Planitia (Zhurong), Planum Boreum.
  - **Moon**: Shackleton Crater (Artemis III polar region), Malapert Mountain, South Pole-Aitken Basin, Oceanus Procellarum, Hadley Rille (Apollo 15), Copernicus Crater.
- **Clustering Archetypes (`cluster_targets`)**:
  - Uses `scikit-learn`'s `KMeans` algorithm to discover 30 representative morphological archetypes across the entire planetary surface from global grids.
  - Selects the true geographic observation closest to each centroid as the archetype's anchor point.

#### `scripts/pipeline/iau.py`
Parses the official USGS/IAU Gazetteer of Planetary Nomenclature.
- `load_iau_gazetteer(shapefile_path)`: Reads Gazetteer shapefiles, filtering for approved features and extracting feature type, diameter, and coordinate centroids.
- `haversine_distance(lat1, lon1, lat2, lon2, radius)`: Calculates great-circle spherical distance over the target celestial body.
- `find_nearest_iau_feature(lat, lon, gazetteer_gdf, body)`: Identifies the closest named landmark within proximity thresholds to provide human-readable labels (e.g., "14.2 km SW of Shackleton").

---

### 3.4 Geological & Lithological Taxonomy (`scripts/pipeline/geology_rules.py`, `scripts/pipeline/geology.py`)

#### `scripts/pipeline/geology_rules.py`
Defines an 8-class planetary geological classification scheme and cross-body similarity mapping:

```python
PLANETARY_CLASSES = [
    "basaltic_plains",   # Mare basalts, volcanic flows
    "impact_cratered",   # Highly cratered highlands, breccias
    "aeolian_dunes",     # Active ergs, sand sheets, dune fields
    "fluvial_alluvial",  # Inverted river channels, deltas, alluvial fans
    "polar_ice",         # Permanent ice deposits, glaciovolcanic features
    "volcanic_edifice",  # Shield volcanoes, cinder cones, calderas
    "clay_phyllosilicate",# Hydrated alteration minerals, lacustrine clays
    "evaporite_sulfate", # Salt flats, playa lakes, sulfate deposits
]
```

- **Cross-Body Similarity Matrix (`GEOLOGY_SIMILARITY_MATRIX`)**:
  A symmetric $8 \times 8$ matrix defining scientific interchangeability between classes:
  - Exact match: $S = 1.0$
  - Closely related (e.g., `basaltic_plains` $\leftrightarrow$ `volcanic_edifice`): $S = 0.70$
  - Distantly related (e.g., `fluvial_alluvial` $\leftrightarrow$ `clay_phyllosilicate`): $S = 0.60$
  - Unrelated (e.g., `polar_ice` $\leftrightarrow$ `aeolian_dunes`): $S = 0.05$
- **Translation Dictionaries**:
  - `glim_to_planetary_class(glim_code)`: Translates Hartmann & Moosdorf (2012) Global Lithological Map (GLiM) codes (`vb` $\rightarrow$ `basaltic_plains`, `ev` $\rightarrow$ `evaporite_sulfate`, etc.).
  - `parse_usgs_geology(unit_description)`: Uses regular expressions to classify USGS Mars (Tanaka et al. 2014) and Moon (Fortezzo et al. 2020) stratigraphic units.

#### `scripts/pipeline/geology.py`
Spatial querying interface for geological maps.
- `sample_glim_point(glim_gdf, lat, lon)`: Performs point-in-polygon spatial lookups against GLiM.
- **Coastal Fallback**: If an Earth candidate falls within shallow marine or coastal waters due to grid coarseness, the algorithm performs a nearest-neighbor KD-tree search within a $10\text{ km}$ buffer to locate the nearest terrestrial lithological unit.

---

### 3.5 Environmental Dimensions: Cryosphere & Atmospheric Dust (`scripts/pipeline/ice.py`, `scripts/pipeline/dust.py`)

#### `scripts/pipeline/ice.py` (T12)
Models cryospheric, glaciovolcanic, and thermal analog dimensions.
- Evaluates **Land Surface Temperature (LST)** extremes and annual temperature amplitude using MODIS MOD11C3 ($0.05^\circ$ climate modeling grid) for Earth and LRO Diviner South Polar thermal maps for the Moon.
- Computes cold-temperature percentiles ($T_{min}$, $T_{max}$, $\Delta T$) and computes a cryospheric fidelity index $S_{ice} \in [0, 1]$.

#### `scripts/pipeline/dust.py` (T13)
Quantifies atmospheric dust dynamics and aeolian hazard similarity for Mars.
- **Mars Dataset**: Montabone et al. Martian Year 24–36 Column Dust Optical Depth (CDOD) climatology at 9.3 $\mu\text{m}$.
- **Earth Dataset**: MODIS MOD08_M3 Deep Blue Aerosol Optical Depth (AOD) at 550 nm.
- **Hemispheric Phase Alignment**: Automatically shifts Earth seasonal curves by 6 months ($\Delta L_s = 180^\circ$) when matching northern-hemisphere Martian dust events against southern-hemisphere terrestrial desert basins (e.g., Atacama, Namib).

---

### 3.6 Planetary & Terrestrial DEM Processors (`scripts/pipeline/planet_features.py`, `scripts/pipeline/earth_features.py`)

#### `scripts/pipeline/planet_features.py`
Generates global quasi-equiareal analysis grids and extracts planetary DEM patches.
- `generate_planetary_grid(body, spacing_deg)`: Generates latitude-longitude points with longitude steps scaled as $\Delta \lambda = \frac{\Delta \phi}{\cos(\phi)}$, ensuring constant spatial density from the equator to the poles.
- `extract_planetary_patch_worker(...)`: Multiprocessing worker function that extracts $10\text{ km} \times 10\text{ km}$ patches from global MOLA (Mars) and LOLA (Moon) raster mosaics.

#### `scripts/pipeline/earth_features.py`
Processes the terrestrial digital elevation model (Copernicus GLO-90, 90m resolution).
- `build_glo90_vrt(tiles_dir, output_vrt)`: Builds a virtual raster table (VRT) linking over 20,000 Copernicus elevation tiles.
- `filter_by_vegetation(earth_candidates_df, ndvi_raster_path, max_ndvi=0.25)`: Rejects heavily vegetated sites using annual maximum MODIS NDVI, ensuring only bare-earth, desert, and polar terrains are matched.
- `process_earth_stripe(...)`: Stripe-based parallel extraction processor designed for multi-node HPC job arrays (Slurm stripes).

---

### 3.7 Contextual Earth Layers & Logistics (`scripts/pipeline/earth_layers.py`)

Enriches candidate sites with operational logistical constraints:
- `build_infrastructure_tree(natural_earth_roads_path, airports_path)`: Builds `scipy.spatial.cKDTree` / `BallTree` spatial indexes over global road networks and international airport runways.
- `compute_logistics_score(distance_road_km, distance_airport_km, elevation_m)`:
  Calculates an operational feasibility score $S_{logistics} \in [0, 1]$ using exponential decay functions:
  $$S_{logistics} = \exp\left(-\frac{d_{road}}{d_0^{road}}\right) \times \exp\left(-\frac{d_{airport}}{d_0^{airport}}\right) \times P_{altitude}$$
  where $d_0^{road} = 50\text{ km}$ and $d_0^{airport} = 250\text{ km}$, with altitude penalties above $4{,}000\text{ m}$.
- `lookup_country(lat, lon, admin_boundaries_gdf)`: Identifies the sovereign state, administrative region, and jurisdiction for each candidate site.

---

### 3.8 Multidimensional Matching & Scoring Engine (`scripts/pipeline/match.py`)

Executes the scoring and candidate ranking workflows.
- **Radial Basis Function (RBF) Geomorphometry Similarity**:
  $$S_{geom} = \exp\left(-\frac{1}{2}\sum_{i=1}^7 \frac{(x_i^{Earth} - x_i^{Target})^2}{\sigma_i^2}\right)$$
  where $\sigma_i$ is the empirical interquartile standard deviation for feature $i$ across the target planetary body.
- **Multidimensional Similarity Index (MSI)**:
  Aggregates sub-scores using normalized weights:
  $$MSI = w_{geom} S_{geom} + w_{geol} S_{geol} + w_{ice} S_{ice} + w_{dust} S_{dust} + w_{log} S_{log}$$
- **Missing Data Policy (T16)**:
  Handles missing environmental layers dynamically:
  - *Case A (Full data)*: All 5 dimensions active.
  - *Case B (Environmental layer intentionally skipped)*: Inactive weight is redistributed proportionally among the remaining active scientific dimensions.
  - *Case C (Data missing due to sensor bounds/clouds)*: Imputes value using conservative regional fallback or redistributes weight to prevent penalizing candidates due to sensor coverage limits.
- **Spatial Diversity Selection (`select_diverse_top_k`)**:
  Enforces a geographic separation threshold ($\Delta d_{min} \ge 50\text{ km}$) using greedy Euclidean/Haversine non-maximum suppression, preventing all top candidates from clustering within a single mountain range or crater rim.

---

### 3.9 Validation, Serialization & Export (`scripts/pipeline/export.py`)

Produces the final unified data artifact consumed by the frontend application (`analogs_universe.json`).
- `validate_universe_schema(data)`: Performs strict data validation:
  - All targets must contain valid coordinates, body identifiers (`moon` or `mars`), and feature vectors.
  - All analog matches must contain coordinates, overall MSI $\in [0, 1]$, all 5 sub-scores, country codes, and human-readable names.
  - Verified against a minimum of 20 diverse analogs per target.
- `export_to_json(universe_dict, output_path)`: Writes sanitized, indented, and compressed JSON payloads.

---

### 3.10 Package Aggregation (`scripts/pipeline/__init__.py`)

Serves as the library interface, exposing top-level functions and configuration constants:
```python
from pipeline.config import PLANET_CONFIGS, BODY_MOON, BODY_MARS
from pipeline.geo import local_aeqd_wkt, extract_patch, clean_patch
from pipeline.features import extract_features_from_patch, FEATURE_NAMES
from pipeline.targets import load_curated_targets, cluster_targets
from pipeline.match import compute_multidimensional_score, select_diverse_top_k
from pipeline.export import export_to_json, validate_universe_schema
```

---

## 4. Standalone Operational Scripts & Utilities

### 4.1 Data Acquisition Scripts (`download_earthdata.py`, `download_aod.py`)

- **`scripts/tools/download_earthdata.py`**:
  Automates the search and concurrent download of MODIS Terra/Aqua Land Surface Temperature (`MOD11C3`) and Vegetation Indices (`MOD13C2`) via the NASA `earthaccess` Python library. Handles Earthdata Login authentication, spatial bounding box queries, and local cache validation.
- **`scripts/tools/download_aod.py`**:
  Automates the download of MODIS Atmosphere Monthly Global Product (`MOD08_M3`) containing Deep Blue Aerosol Optical Depth (AOD) gridded rasters from the NASA LAADS DAAC archive.

### 4.2 Pipeline v1 Legacy & Transition Scripts

- **`scripts/legacy_v1/process_analogs.py`**:
  Initial v1 prototype for extracting windowed elevation patches from MOLA and LOLA global rasters and clustering planetary surfaces using `MiniBatchKMeans`.
- **`scripts/legacy_v1/match_earth_analogs.py`**:
  v1 matching script that queries Copernicus GLO-90 DEM tiles and computes initial Euclidean distance rankings.
- **`scripts/legacy_v1/enrich_nomenclature.py`**:
  Extracts nomenclature attributes from ESRI Shapefile dBASE (`.dbf`) records and computes nearest IAU landmark proximities.

### 4.3 Verification & Tooling (`scripts/tools/`)

- **`scripts/tools/explore_datasets.py`**:
  Comprehensive diagnostic script that inspects raster and vector inputs (GLO-90 VRT, MOLA, LOLA, GLiM, MODIS, Shapefiles). Evaluates spatial extents, projections, pixel bit-depths, nodata flags, and generates self-contained diagnostic reports in HTML, Markdown, and JSON formats.
- **`scripts/tools/v1_to_sample.py`**:
  Bridge script that parses v1 pipeline output CSV/Parquet files, calculates missing RBF and logistics sub-scores, and generates structured sample datasets for frontend interface testing.
- **`scripts/tools/verify_t16.py`**:
  Mathematical and algorithmic validation suite that verifies the T16 missing-data policy. Evaluates weight renormalization, checks edge-case behavior, and guarantees that total weights always sum strictly to $1.0$.

---

## 5. Automated Test Suite (`tests/`)

The repository includes a comprehensive, modular test suite implemented in `pytest`. Every mathematical routine, coordinate transformation, and data parser is tested with synthetic rasters and known geodetic cases.

| Test File | Primary Modules Under Test | Key Test Cases & Coverage |
| :--- | :--- | :--- |
| `tests/test_geo.py` | `scripts/pipeline/geo.py` | Local AEQD projection validity, antimeridian coordinate unwrapping ($\pm 180^\circ$), polar singularity projection ($\pm 90^\circ$), nodata mask interpolation, int16 elevation scaling/offset. |
| `tests/test_features.py` | `scripts/pipeline/features.py` | Flat plane zero-slope invariance, synthetic $45^\circ$ inclined ramp gradient verification, Horn filter edge padding, Riley TRI symmetry, OLS planar detrending roughness. |
| `tests/test_planet_features.py` | `scripts/pipeline/planet_features.py` | Quasi-equiareal grid point density vs. latitude, meridian convergence scaling, stripe slice boundaries, patch extraction multiprocessing workers. |
| `tests/test_targets.py` | `scripts/pipeline/targets.py` | Curated targets schema compliance, coordinate range checks ($-90 \le \phi \le 90$, $-180 \le \lambda \le 180$), K-Means cluster count verification, anchor selection. |
| `tests/test_earth_features.py` | `scripts/pipeline/earth_features.py` | GLO-90 VRT creation, NDVI vegetation threshold rejection, parallel stripe worker execution, stripe merging. |
| `tests/test_earth_layers.py` | `scripts/pipeline/earth_layers.py` | MODIS monthly compositing, BallTree nearest road/airport queries, logistics exponential distance attenuation, sovereign country lookups. |
| `tests/test_iau.py` | `scripts/pipeline/iau.py` | IAU Gazetteer shapefile reading, Great-circle Haversine distance accuracy, closest named landmark queries. |
| `tests/test_dust.py` | `scripts/pipeline/dust.py` | Montabone CDOD netCDF parsing, MODIS AOD scaling, seasonal $180^\circ$ $L_s$ phase shift for opposite hemispheres. |
| `tests/test_geology.py` | `scripts/pipeline/geology.py`, `scripts/pipeline/geology_rules.py` | GLiM spatial sampling, coastal point KD-tree fallback, 8-class cross-body similarity matrix symmetry and diagonal identity ($S_{i,i} = 1.0$). |
| `tests/test_ice.py` | `scripts/pipeline/ice.py` | MODIS LST extreme extraction, Diviner south polar thermal matching, cryospheric score bounds ($0 \le S_{ice} \le 1$). |
| `tests/test_match.py` | `scripts/pipeline/match.py` | RBF kernel decay properties, multidimensional weighted scoring, T16 missing-data re-weighting (Cases A, B, C), 50 km spatial diversity suppression. |
| `tests/test_export.py` | `scripts/pipeline/export.py` | JSON universe serialization, required fields validation, coordinate bounds, numerical score limits, file writing integrity. |
| `tests/__init__.py` | Test Suite Root | Test package initialization and shared test constants. |

---

## 6. Interactive Web Application (`app/`)

The application frontend is an interactive single-page application (SPA) built using **React 18**, **TypeScript**, and **Vite**, styled with **Tailwind CSS**, and utilizing **Leaflet** for geospatial mapping.

### 6.1 Frontend Architecture & Component Tree

```
                            [ App.tsx ]
         (State: selectedTarget, selectedAnalog, weights, scenario)
                                 |
     +---------------------------+---------------------------+
     |                           |                           |
[ SiteMap.tsx ]           [ RankList.tsx ]           [ ScenarioPanel.tsx ]
(Interactive Map)        (Ranked Matches)          (Operational Presets)
     |                           |                           |
     +---------------------------+---------------------------+
                                 |
                         [ Dossier.tsx ]
                 (Detailed Site Characterization)
                                 |
                 +---------------+---------------+
                 |                               |
          [ Radar.tsx ]                  [ InfoToggle.tsx ]
      (5-Axis Spider Chart)           (Scientific Definitions)
```

- **`App.tsx`**: Central orchestrator. Loads `analogs_universe.json`, maintains active selection states (target, candidate analog), manages custom weighting coefficients, and handles responsive layout views.
- **`SiteMap.tsx`**: Interactive geospatial visualization powered by Leaflet. Renders terrestrial candidate locations as customized SVG pins (color-coded by MSI fidelity score), draws bounding analysis polygons, and centers dynamically on selected targets.
- **`RankList.tsx`**: Displays ranked analog sites. Features sorting, quick filtering by country, and high-level score indicators.
- **`Dossier.tsx`**: Deep-dive scientific dossier for the selected candidate. Provides a multi-tab view:
  - *Overview Tab*: High-level summary, geographic coordinates, matching radar chart, logistical accessibility.
  - *Geomorphometry Tab*: Side-by-side comparison of the 7 terrain metrics against the planetary target.
  - *Geology & Environment Tab*: Lithological classifications, cryospheric LST curves, and atmospheric dust optical depths.
- **`Radar.tsx`**: Responsive SVG radar (spider) chart plotting the 5 scientific dimensions against target requirements.
- **`ScenarioPanel.tsx`**: Allows users to select operational mission scenarios (Traverse Testing, Long-term Habitation, In-Situ Resource Utilization, Deep Drilling) which dynamically reconfigure the dimensional weights.
- **`InfoToggle.tsx`**: Contextual scientific explanations and educational definitions adhering to NASA plain-language standards.

### 6.2 State Management & Client-Side MSI Engine (`app/src/lib/msi.ts`)

The web application provides a real-time client-side calculation engine. Users can manipulate weighting sliders in the UI; `msi.ts` immediately recalculates the composite MSI score and re-sorts all candidate analogs without requiring server re-queries:

```typescript
export interface WeightVector {
  geom: number;
  geol: number;
  ice: number;
  dust: number;
  log: number;
}

export function recalculateMSI(
  analog: AnalogMatch,
  weights: WeightVector
): number {
  const sumWeights = weights.geom + weights.geol + weights.ice + weights.dust + weights.log;
  if (sumWeights === 0) return 0;
  
  const score = (
    analog.sub_scores.morphology * weights.geom +
    analog.sub_scores.geology * weights.geol +
    analog.sub_scores.ice * weights.ice +
    analog.sub_scores.dust * weights.dust +
    analog.sub_scores.logistics * weights.log
  ) / sumWeights;
  
  return parseFloat(score.toFixed(4));
}
```

### 6.3 Narrative Content & Plain-Language Translators (`content.ts`, `explanations.ts`)

- **`content.ts`**: Contains rich scientific background narratives for curated mission targets (e.g., geological history of Jezero's delta, Artemis III landing site illumination conditions).
- **`explanations.ts`**: Provides accessible, plain-language scientific translations for all metrics (e.g., explaining why Hypsometric Integral indicates geological maturity, or how Detrended Roughness impacts rover wheel traction).

---

## 7. Mathematical Formulations & Scientific Methodology

### 7.1 Geodesy & Local AEQD Projection

To avoid geometric distortions associated with global cylindrical projections (e.g., plate carrée), every $10\text{ km} \times 10\text{ km}$ patch is extracted using a local **Azimuthal Equidistant (AEQD)** projection centered on the candidate coordinates $(\phi_0, \lambda_0)$:

$$\rho = R \cdot c$$
$$\theta = \text{atan2}\left(\cos\phi \sin(\lambda - \lambda_0), \cos\phi_0 \sin\phi - \sin\phi_0 \cos\phi \cos(\lambda - \lambda_0)\right)$$

where:
$$\cos c = \sin\phi_0 \sin\phi + \cos\phi_0 \cos\phi \cos(\lambda - \lambda_0)$$
and $R$ is the specific volumetric mean radius of the celestial body.

### 7.2 Seven Canonical Geomorphometric Metrics

1. **Mean Slope ($\bar{S}$)**:
   $$S = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right), \quad \bar{S} = \frac{1}{N}\sum_{i=1}^N S_i$$
2. **Slope 90th Percentile ($P_{90}$)**:
   The 90th percentile of the cumulative distribution function (CDF) of local slopes, capturing extreme escarpments and terrain hazards.
3. **Relief ($\Delta h$)**:
   $$\Delta h = z_{max} - z_{min}$$
4. **Hypsometric Integral ($HI$)**:
   Quantifies the vertical distribution of mass within the landform:
   $$HI = \frac{\bar{z} - z_{min}}{z_{max} - z_{min}}$$
   $HI > 0.6$ indicates youthful, uneroded plateau landscapes; $HI < 0.35$ indicates deeply eroded, concave terrain.
5. **Detrended Roughness ($\sigma_{planar}$)**:
   Given best-fit plane $\hat{z}(x, y) = Ax + By + C$:
   $$\sigma_{planar} = \sqrt{\frac{1}{N}\sum_{i=1}^N (z_i - \hat{z}_i)^2}$$
6. **Terrain Ruggedness Index ($TRI$)**:
   Measures elevation differences between a cell and its 8 contiguous neighbors:
   $$TRI = \frac{1}{N}\sum_{i=1}^N \sqrt{\frac{1}{8}\sum_{k=1}^8 (z_{i,k} - z_i)^2}$$
7. **Mean Elevation ($\bar{z}$)**:
   Local mean elevation relative to the planetary geodetic datum.

### 7.3 Radial Basis Function (RBF) Distance Metric

Geomorphometric similarity is computed using a multi-variate Gaussian Radial Basis Function (RBF) kernel across normalized feature space:

$$S_{geom} = \exp\left(-\frac{1}{2}\sum_{j=1}^7 \frac{(f_{j}^{Earth} - f_{j}^{Target})^2}{\sigma_j^2}\right)$$

where $\sigma_j$ represents the standard deviation (or interquartile scale) of feature $j$ across the reference planetary body.

### 7.4 Missing Data Imputation & Re-weighting Policy (T16)

When an environmental layer is not physically applicable or unavailable for a given celestial body (e.g., Mars has atmospheric dust, but the Moon has no atmosphere; lunar South Pole has cryospheric temperature requirements, but equatorial Mars does not), the pipeline enforces a **dynamic renormalization policy**:

Let $\mathcal{A} \subseteq \{\text{geom}, \text{geol}, \text{ice}, \text{dust}, \text{log}\}$ be the set of active, applicable dimensions.

$$w_k^* = \frac{w_k}{\sum_{m \in \mathcal{A}} w_m}, \quad \forall k \in \mathcal{A}$$
$$MSI = \sum_{k \in \mathcal{A}} w_k^* \cdot S_k$$

This guarantees that:
1. Total weight always sums strictly to $1.0$ ($\sum_{k \in \mathcal{A}} w_k^* = 1.0$).
2. Candidate sites are never penalized for missing sensor data outside their physical regime.

### 7.5 Spatial Diversity Constraint Algorithm

To prevent multiple top-ranked candidates from clustering in close proximity within a single geological landform, the pipeline enforces a minimum separation constraint ($\Delta d_{min} = 50\text{ km}$):

```
Algorithm: Greedy Spatial Non-Maximum Suppression
Input: Candidates C sorted descending by raw MSI, min_distance d_min = 50 km
Output: Diverse top-k set D

1. D = []
2. For each candidate c in C:
3.    too_close = False
4.    For each selected s in D:
5.        If haversine_distance(c.coords, s.coords) < d_min:
6.            too_close = True
7.            Break
8.    If not too_close:
9.        Append c to D
10.   If len(D) == k:
11.       Break
12. Return D
```

---

## 8. Data Contracts & Schema Specifications

The primary exchange contract between the Python computational pipeline and the React visualization application is `analogs_universe.json`.

```json
{
  "version": "2.0.0",
  "generated_at": "2026-11-14T00:00:00Z",
  "targets": [
    {
      "id": "target-jezero-crater",
      "name": "Jezero Crater",
      "body": "mars",
      "category": "curated",
      "latitude": 18.38,
      "longitude": 77.58,
      "features": {
        "mean_slope": 5.42,
        "p90_slope": 12.15,
        "relief": 642.0,
        "hypsometric_integral": 0.442,
        "detrended_roughness": 18.6,
        "tri": 7.3,
        "mean_elevation": -2530.0
      },
      "geology_class": "fluvial_alluvial",
      "description": "Perseverance landing site; ancient deltaic lacustrine system."
    }
  ],
  "analogs": {
    "target-jezero-crater": [
      {
        "id": "analog-lake-salda-turkey",
        "name": "Lake Salda",
        "country": "Turkey",
        "country_code": "TUR",
        "latitude": 37.55,
        "longitude": 29.68,
        "msi_score": 0.8874,
        "sub_scores": {
          "morphology": 0.8650,
          "geology": 0.9500,
          "ice": null,
          "dust": 0.7800,
          "logistics": 0.9200
        },
        "features": {
          "mean_slope": 5.10,
          "p90_slope": 11.80,
          "relief": 580.0,
          "hypsometric_integral": 0.430,
          "detrended_roughness": 17.2,
          "tri": 6.9,
          "mean_elevation": 1180.0
        },
        "geology_class": "clay_phyllosilicate",
        "nearest_iau_feature": "Jezero Delta Remnant",
        "description": "Hydromagnesite microbialites and alluvial deposits mirroring Jezero mineralogy."
      }
    ]
  }
}
```

---

## 9. Conclusion & Maintainer Guidelines

All components of this codebase have been standardized to professional scientific English. When contributing new features:
1. Maintain type annotations across all Python modules (`typing.Tuple`, `typing.Dict`, `typing.Optional`, `typing.List`).
2. Write unit tests in `tests/test_<feature>.py` verifying boundary conditions, nodata handling, and mathematical invariants.
3. Verify that any new environmental sub-scores integrate cleanly with the T16 dynamic re-weighting logic in `scripts/pipeline/match.py` and `app/src/lib/msi.ts`.
4. Keep all docstrings formatted according to NumPy/Google docstring standards in clear English.

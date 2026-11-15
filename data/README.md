# `data/` — Versioned Pipeline Definitions & Curated Schemas

This directory stores the **human-reviewed, version-controlled definitions** that parameterize the PROTOTERRA computational pipeline. Every file in this folder is strictly deterministic, auditable, and versioned directly in git.

---

## Data Segregation Architecture

PROTOTERRA clearly separates light versioned schemas from massive high-resolution planetary rasters:

```text
┌──────────────────────────────────────────────┐
│  data/ (Tracked in Git, ~100 KB)             │
│  • Curated targets (Artemis III, Jezero)     │
│  • Ground-truth analog validation stations   │
│  • Planetary physical limits & overrides     │
└──────────────────────┬───────────────────────┘
                       │ Parameterizes
                       ▼
┌──────────────────────────────────────────────┐
│  Yuca HPC Storage (/lustre/proyectos/p089/)  │
│  • Raw Rasters (+80 GB: LOLA, MOLA, DEM)     │
│  • Slurm intermediate batch caches           │
└──────────────────────┬───────────────────────┘
                       │ Serializes
                       ▼
┌──────────────────────────────────────────────┐
│  Published Universe (app/public/data/)       │
│  • analogs_universe.json (~7.5 MB gzip)      │
│  • 76 targets · 5,010 ranked analog pairs    │
└──────────────────────────────────────────────┘
```

---

## Versioned Files in `data/`

| File | Read by Module | Description & Scientific Purpose |
| :--- | :--- | :--- |
| **`targets.json`** | `scripts/pipeline/targets.py` | **16 Curated Planetary Targets** (8 Moon, 8 Mars). Contains geodetic coordinates, literature anchors (Artemis III candidate zones, Viking 1 & 2, Pathfinder, Spirit, Opportunity, Curiosity, Perseverance Jezero), scientific motivation, and bounding boxes. |
| **`known_analogs.json`** | `scripts/pipeline/earth_layers.py` | **12 Ground-Truth Terrestrial Analogs** (e.g., MDRS Utah, Haughton Crater on Devon Island, Atacama Desert, Tenerife Volcanic Field, Askja Caldera Iceland, McMurdo Dry Valleys Antarctica). Used to automatically cross-reference and flag candidates with the `KNOWN_ANALOG` badge. |
| **`limits.json`** | `scripts/pipeline/export.py` | **Planetary Physical Boundaries**. Defines immutable physical parameters per body (surface gravity, atmospheric surface pressure, diurnal temperature excursions, cosmic radiation flux, magnetic shielding) used to generate "Where the Analogy Breaks" mismatch warnings. |
| **`geology_overrides.json`** | `scripts/pipeline/geology.py` | **Stratigraphic & Lithologic Mappings**. Expert overrides bridging USGS geologic units (SIM 3292 for the Moon, global unified Martian chronostratigraphy) into a unified 5-class lithology taxonomy compatible with Earth's GLiM database. |
| **`ice_hints.json`** | `scripts/pipeline/ice.py` | **Volatiles & Cryospheric Anchors**. Curated ice stability markers: Permanently Shadowed Regions (PSRs) with Diviner thermal traps on the Moon, and SHARAD radar dielectric subsurface ice detections on Mars. |

---

## Heavy Rasters & Compute Caches (Not Tracked in Git)

In compliance with repository hygiene and open-source best practices, the heavy raw datasets (~80 GB) and intermediate processing caches are hosted on the **Yuca supercomputer (ACARUS)** at `/lustre/proyectos/p089/data/` and excluded via `.gitignore`:

- **`/data/raw/`**:
  - `moon_lola_118m/`: LOLA polar DEM tiles (LRO, 118 m/px).
  - `mars_mola_463m/`: MOLA global topographic model (MGS, 463 m/px).
  - `mars_themis_night_100m/`: THEMIS night-time infrared thermal inertia mosaic (Mars Odyssey, 100 m/px).
  - `earth_copernicus_glo90/`: 26,475 Copernicus DEM GLO-90 tiles (ESA/Airbus, 90 m/px).
  - `earth_modis/`: MODIS MOD08_M3 AOD dust aerosol and MOD13C2 NDVI monthly composited HDF files.
- **`/data/derived/`**:
  - Intermediate numpy memory-mapped feature arrays (`.npy`, `.npz`).
  - Spatial KD-Tree spatial lookup indices.

---

## Output Data Contract

The pipeline aggregates the curated targets, 60 unsupervised terrain clusters, and ~45,000 bare-ground terrestrial candidate patches into a single published JSON file:

- **Location:** `app/public/data/analogs_universe.json`
- **Total Targets:** 76 (16 curated + 60 cluster medoids)
- **Ranked Analog Pairs:** 5,010 matches
- **Verification:** Validated by automated unit tests in `tests/test_export.py` against strict JSON schema definitions.

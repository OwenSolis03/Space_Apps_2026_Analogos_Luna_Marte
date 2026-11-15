# `scripts/` — High-Performance Computational Pipeline & HPC Jobs

This directory contains the computational heart of **PROTOTERRA**. Engineered to execute on the **Yuca supercomputer** at **ACARUS** (*Área de Cómputo de Alto Rendimiento de la Universidad de Sonora*), this codebase ingests over **80 GB** of open planetary rasters and computes multi-dimensional similarity across Earth, Moon, and Mars.

---

## Directory Overview

```text
scripts/
├── pipeline/                     # Core Python geoprocessing and matching package
│   ├── geo.py                   # Local AEQD projections, coordinate transforms, geodesy
│   ├── features.py              # Morphometric feature extraction (relief, slopes, TRI)
│   ├── sweeps.py                # Grid generation and raster tiling engines
│   ├── earth_layers.py          # MODIS NDVI masking, LST processing, accessibility
│   ├── match.py                 # Multi-dimensional RBF distance & MSI ranking engine
│   ├── export.py                # Schema validation & JSON universe serialization
│   ├── targets.py               # 16 curated targets ingestion + 60 k-means clusters
│   ├── geology.py               # USGS/GLiM stratigraphic unit harmonizer
│   ├── dust.py                  # Aerosol Optical Depth (AOD) dust climatology
│   └── ice.py                   # Lunar PSR & Martian cryospheric stability markers
├── jobs/                         # Slurm batch submission scripts (.slurm) for Yuca HPC
│   ├── t1_download_rasters.slurm
│   ├── t3_planet_features.slurm
│   ├── t4_targets_clusters.slurm
│   ├── t5_earth_sweep.slurm
│   ├── t6_earth_layers.slurm
│   ├── t7_matching.slurm
│   └── t8_export_universe.slurm
├── tools/                        # Diagnostic, verification, and inspection utilities
│   ├── verify_datasets.py       # Checksum and coordinate bounding box integrity checker
│   ├── inspect_cluster_hpc.py   # Telemetry reader for intermediate memory-mapped arrays
│   ├── download_copernicus.py   # Multi-threaded tile downloader for GLO-90 DEM
│   └── sensitivity_analysis.py  # Weights perturbation and rank-stability test suite
└── legacy_v1/                    # Initial hackathon prototype (kept for provenance, non-functional)
```

---

## The 8-Stage Processing Pipeline

```text
  [T1 / T2: Data Ingestion & Integrity Check]
      │  Download LOLA, MOLA, THEMIS, Copernicus GLO-90, MODIS (80 GB)
      ▼
  [T3: Planetary Feature Sweep]
      │  Process 140,916 Mars patches + 36,741 Moon patches (32 km AEQD, 500 m/px)
      ▼
  [T4: Target Definition & Clustering]
      │  16 Curated targets (Artemis III, Jezero) + 60 k-means cluster medoids
      ▼
  [T5: Terrestrial Bare-Land Sweep]
      │  Process 26,475 Copernicus tiles; filter by MODIS NDVI < 0.20 (~45,000 patches)
      ▼
  [T6: Context Layers Integration]
      │  MODIS LST thermal profiles + Natural Earth roads and airports distance vectors
      ▼
  [T7: Multi-Dimensional Matching Engine]
      │  7-dimensional Gaussian RBF kernels, mission presets, 150 km Haversine dispersion
      ▼
  [T8: Contract Packaging & Verification]
      │  Strict JSON schema export -> app/public/data/analogs_universe.json
```

---

## Execution Environment & Instructions

### Supercomputer Execution (Slurm Batch)

All heavy compute runs on the Yuca cluster using the Slurm workload manager. Slurm scripts automatically set `PYTHONPATH=scripts` and handle cluster module loading:

```bash
# Example: Submit Task T3 (Planet Feature Sweep) across compute nodes
sbatch scripts/jobs/t3_planet_features.slurm

# Check job status
squeue -u $USER
```

### Standalone Local Execution

All pipeline modules can be executed directly from the repository root:

```bash
# Set PYTHONPATH to include scripts/
export PYTHONPATH=scripts

# Inspect command-line parameters for targets ingestion
python -m pipeline.targets --help

# Run export verification
python -m pipeline.export --verify
```

### Synthetic Verification (No Cluster Needed)

To verify the pipeline logic on a local development machine without downloading the 80 GB raster dataset, run the automated synthetic test suite:

```bash
# Run 119 unit tests with synthetic numpy rasters
pytest tests/
```

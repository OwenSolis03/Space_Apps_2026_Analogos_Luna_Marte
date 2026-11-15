# Planetary Analog Finder

**NASA Space Apps Challenge 2026 · Team Endurance CXXV · NASA Space Apps Sonora (Hermosillo, Mexico)**

Planetary Analog Finder searches the whole Earth for places that resemble candidate landing and base sites on the Moon and Mars. It ranks them with an explainable score, and for every site it shows **where the analogy breaks**. Every comparison uses the same measurement on all three bodies: 32 × 32 km terrain patches, resampled to 500 m per pixel and reprojected around their own centre. The heavy processing runs on the Yuca supercomputer (Universidad de Sonora), and a static web app reads the result.

> **Status (2026-11-13):** prototype in progress.
>
> - **Done:** the Mars and Moon global sweeps (T3), the targets (T4) and the Earth layers (T6). The Earth sweep (T5) is implemented and passed its test run.
> - **Next:** matching and export (T7/T8), and connecting the app to the real results. Until then the app runs on sample data converted from the v1 prototype.
> - **Details:** [docs/handoff.md](docs/handoff.md) and [docs/HISTORY.md](docs/HISTORY.md).

---

## The challenge

[Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/). Find places, environments or processes on Earth that can stand in for future lunar bases or Mars landing and exploration sites, characterise them with open data from NASA and other agencies, and explain:

1. what makes the analogy strong;
2. where it breaks;
3. how the analog would help prepare Moon or Mars exploration.

The challenge stresses that visual resemblance is not enough, that scale matters, that well-known analogs (Atacama, Antarctica, Iceland, Hawaii) are already studied, and that Earth cannot reproduce reduced gravity, vacuum, the thin Martian atmosphere or space radiation.

## How it works

```text
Raw data on Yuca (/lustre/proyectos/p089/data)
  │
  ├─ T3  Mars and Moon: global grid of 32 km patches ─► 140,916 Mars + 36,741 Moon patches
  ├─ T4  Targets: Artemis III regions, Mars landing sites, 30 terrain clusters per body ─► 76 targets
  ├─ T6  Earth layers: MODIS NDVI and land surface temperature, roads, airports, countries
  ├─ T5  Earth: same patches, only on bare (unvegetated) land ─► ~45,000 candidates
  ├─ T7  Matching: per-dimension RBF similarity, mission presets, 150 km diversity, mismatches
  └─ T8  Export ─► analogs_universe.json ─► web app (React + Vite)
```

- **Same measurement everywhere.**
  - Every patch is a 64 × 64 grid at 500 m/px in a local azimuthal equidistant projection, so slope and roughness are comparable across bodies and latitudes.
  - The features (mean and p90 slope, relief, hypsometric integral, detrended roughness, terrain ruggedness index) come from one shared function.
  - Elevation is never compared, because the datums differ.
- **Targets that matter for the challenge:**
  - the nine Artemis III candidate regions near the lunar south pole (NASA, 2024), as seven targets because two pairs share an anchor, plus the rim of Shackleton;
  - eight Mars sites: Jezero, Gale, Gusev, Meridiani, Utopia, Elysium, Oxia Planum and the shallow-ice region of Arcadia Planitia;
  - 30 global terrain archetypes per body, for exploration.
- **Explainable score.**
  - Seven dimensions: topography, roughness, aridity (vegetation mask), thermal contrast, regional lithology, dust seasons, and cold traps/ice.
  - The Mission Similarity Index (MSI) is their weighted mean. Five mission presets set the weights, and the user can re-weight them in the browser.
  - Missing-data policy: dimensions not applicable to the body are ignored; dimensions missing on the target drop that weight, but if remaining preset weight is < 60% the target is unranked; dimensions present on the target but missing on Earth score 0 (no evidence, no credit).
- **Where it breaks.** Each analog lists the features that differ by more than 1.5 typical Earth deviations, in physical units, plus the fixed physical limits of each body.
- **New vs. known.** Sites inside 12 well-studied analog regions are labelled `KNOWN_ANALOG`; everything else is a `NEW_CANDIDATE`. Each site also shows its distance to the nearest road and airport.

The reasoning behind every design decision is in [docs/HISTORY.md](docs/HISTORY.md). The full specifications are in [docs/implementation_plan.md](docs/implementation_plan.md) and the per-task plans.

## Data

| Body | Dataset | Use | Source |
| --- | --- | --- | --- |
| Mars | MGS MOLA DEM, 463 m | Terrain features | [USGS Astrogeology](https://astrogeology.usgs.gov/search) (from NASA PDS) |
| Mars | Mars Odyssey THEMIS IR day and night, 100 m | Relative thermal contrast | USGS Astrogeology |
| Moon | LRO LOLA LDEM, 118 m | Terrain features | USGS Astrogeology |
| Moon | LRO LROC WAC mosaic, 100 m | Relative brightness (percentile within the Moon) | USGS Astrogeology |
| Moon | LRO Diviner Polar Resource Product (south) | Mean and max temperature, ice stability depth | [NASA PDS Geosciences](https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/) |
| Moon | Lunar ice favorability index | Polar ice context | USGS Astrogeology |
| Earth | Copernicus DEM GLO-90 (26,475 tiles) | Terrain features | [ESA Copernicus, AWS open data](https://registry.opendata.aws/copernicus-dem/) |
| Earth | MODIS MOD13C2 (NDVI) and MOD11C3 (land surface temperature), 2023 | Vegetation mask, thermal amplitude | [NASA Earthdata](https://doi.org/10.5067/MODIS/MOD13C2.061), [MOD11C3](https://doi.org/10.5067/MODIS/MOD11C3.061) |
| Earth | Natural Earth roads, airports, countries | Logistics and country | [Natural Earth](https://www.naturalearthdata.com/) |
| Moon, Mars | Gazetteer of Planetary Nomenclature | Target anchors and names | [USGS / IAU](https://planetarynames.wr.usgs.gov/) |

The raw data (~80 GB) lives on Yuca and is not in this repository. Units, scales and nodata values of every file are documented in [docs/pipeline.md](docs/pipeline.md). For example, LOLA stores half-metres, and MODIS NDVI and LST use opposite scale conventions.

## Quick start

**Web app** (needs Node 20):

```bash
cd app && npm install && npm run dev
```

It opens at http://localhost:5173 and reads `app/public/data/`.

**Pipeline** (on Yuca, with the `spaceapps_2026` conda environment). Every heavy step is a Slurm job; nothing heavy runs on the login node.

```bash
cd /lustre/proyectos/p089/code && git pull
```

```bash
sbatch jobs/t3_planet_features.slurm
```

The command for every task (tests, T4, T5, T6, T7) is in its plan: [plan_t4.md](docs/plan_t4.md), [plan_t5.md](docs/plan_t5.md), [plan_t6.md](docs/plan_t6.md) and [plan_t7_t8.md](docs/plan_t7_t8.md). To run the Python dependencies elsewhere: `pip install -r pipeline/requirements.txt`. The tests (`pytest -q tests`) are synthetic and do not need the raw data.

## Repository layout

| Path | Content |
| --- | --- |
| `pipeline/` | v2 pipeline: patch extraction (`geo.py`), features (`features.py`), Mars/Moon sweep (`planet_features.py`), targets (`targets.py`, `iau.py`), Earth layers (`earth_layers.py`), Earth sweep (`earth_features.py`) |
| `pipeline/data/` | Hand-written definitions: curated targets, known analog regions, physical limits |
| `jobs/` | Slurm jobs for each task |
| `tests/` | Synthetic unit tests |
| `app/` | Web app (React, Vite, TypeScript, Tailwind, Leaflet) |
| `tools/` | Dataset explorer and the v1-to-v2 sample converter |
| `docs/` | Documentation (see below) |
| Root `*.py`, `*.sh`, `*.slurm` | v1 prototype and the download jobs, kept as reference |
| `output/`, `logs/` | v1 outputs and logs |

## Documentation

| File | What it covers |
| --- | --- |
| [diagrams/](docs/diagrams/) | Architecture and pipeline diagrams (standalone HTML): [system architecture](docs/diagrams/system-architecture.html), [pipeline lineage](docs/diagrams/pipeline-lineage.html), [pipeline stages](docs/diagrams/pipeline-stages.html), [app sequence](docs/diagrams/app-sequence.html), [data contract](docs/diagrams/data-contract.html), [repository layout](docs/diagrams/repository-layout.html) |
| [HISTORY.md](docs/HISTORY.md) | How the project was built and why each decision was made, with commits and Slurm jobs |
| [handoff.md](docs/handoff.md) | Current status per task, run ids and the queue of pending cluster commands |
| [implementation_plan.md](docs/implementation_plan.md) | The v2 specification, task by task (T0–T11), and the data contract |
| [plan_t4.md](docs/plan_t4.md), [plan_t5.md](docs/plan_t5.md), [plan_t6.md](docs/plan_t6.md), [plan_t7_t8.md](docs/plan_t7_t8.md), [plan_t12_t15.md](docs/plan_t12_t15.md), [plan_t16_missing_data.md](docs/plan_t16_missing_data.md), [plan_t17_plain_language.md](docs/plan_t17_plain_language.md), [plan_mineralogy_context.md](docs/plan_mineralogy_context.md) | Detailed plans per task |
| [pipeline.md](docs/pipeline.md) | Data, scales and nodata per file, Yuca resources and the run log |
| [logbook.md](docs/logbook.md) | Day-by-day log |
| [submission.md](docs/submission.md) | What is submitted, checklist and timeline for 14–15 November |
| [value_proposition.md](docs/value_proposition.md) | Problem, value proposition and differentiators (for the pitch) |
| [working_without_ssh.md](docs/working_without_ssh.md) | Working through Open OnDemand when SSH is blocked; offline kit |
| [gemini_prompt.md](docs/gemini_prompt.md) | Working instructions given to the coding agent |
| [master_plan.md](docs/master_plan.md), [ideas.md](docs/ideas.md) | Original master plan and the evolution of the idea |

## Use of AI

AI was used throughout and is documented in [docs/HISTORY.md](docs/HISTORY.md) and [docs/logbook.md](docs/logbook.md).

| Tool | Role |
| --- | --- |
| Claude (Anthropic) | Detailed implementation plans, documentation, data inspection on the cluster, and review of code and results. It also wrote the app skeleton and the dataset tools |
| Gemini 4 (Google Antigravity, Orchestrator mode) | Wrote the v2 pipeline code from those plans and ran tests and jobs through Slurm |

Every cluster job was approved and run by a team member.

## Team and event

**Endurance CXXV:** Fernando Borquez Guerrero, Owen Adiel Solis Zatarain, Emily Beltrán Zazueta, Flor María Machado Félix, Elías Peregrina Cázares and Javier Leonardo Miranda Sanchez.

**Venue:** [NASA Space Apps Sonora 2026](https://spaceappssonora.org/), Tec de Monterrey, Campus Sonora Norte, Hermosillo, 13–15 November 2026.

| When | What |
| --- | --- |
| Friday 13 | Bootcamp and opening |
| Saturday 14, 9:00–21:00 | Hackathon |
| Sunday 15, 9:00–14:00 | Pitches |

The venue rules and our checklist are in [docs/submission.md](docs/submission.md). Computing resources: Yuca supercomputer, Área de Cómputo de Alto Rendimiento (ACARUS), Universidad de Sonora.

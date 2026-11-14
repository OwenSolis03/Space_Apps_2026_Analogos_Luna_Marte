# Planetary Analog Finder (PAF): master plan

## NASA Space Apps Challenge 2026: operational and methodological blueprint (v2.0)

> **Status:** this is the original master plan, written before the hackathon. It describes the target vision, not the current state. The implemented design differs in several places, each for a reason recorded in [HISTORY.md](HISTORY.md):
>
> | Master plan | Implemented instead | Why |
> | --- | --- | --- |
> | Uber H3 hexagons and Google Earth Engine pre-aggregation | 32 km local AEQD patches computed directly from the raw rasters on Yuca | — |
> | HDBSCAN | k-means archetypes | — |
> | Spectral dimension (Sentinel-2, CRISM) and SAR roughness | Not implemented | Out of scope for the time available |
> | Mapbox | Leaflet | — |
>
> The specification in force is [implementation_plan.md](implementation_plan.md).

---

## 1. Executive summary and purpose

The project builds an interactive web platform for mission engineers and planetary geologists. It identifies, characterises and ranks **terrestrial analog sites** against strategic landing or permanent-base locations on the **Moon (Artemis programme)** and **Mars**.

**What sets it apart:**

- It is not a static catalogue, a manual selection or an arbitrary visual comparison.
- It scores correspondence with a multidimensional **Mission Similarity Index (MSI)**, built from **Gaussian radial basis function (RBF) kernels** and logistic feasibility indices, derived from open NASA, USGS, ESA and JAXA satellite data.
- It discovers **new, uncatalogued analogs** with a spatial tiling pipeline (**Uber H3**) and unsupervised clustering (**HDBSCAN**) on the **Yuca supercomputer**.
- It contrasts **morphological/static analogs** with **dynamic/seasonal process analogs** (for example, dust storms).
- It always includes a **"Limits of the analog"** section: the physical differences that cannot be bridged, such as gravity, radiation and atmosphere.

---

## 2. Scope decisions and risk mitigation (48 hours)

| Factor | Scope decision | Technical and operational justification |
| --- | --- | --- |
| **Global exploration and tiling** | A boolean mask of exposed surface (~12 % of the globe), pre-aligned in Google Earth Engine (GEE) and grouped into **Uber H3 hexagonal cells (resolution 6, ~36 km²)** | Avoids the I/O and reprojection bottleneck of terabytes of raw GeoTIFFs. Reduces 2.2 × 10⁹ pixels to ~1.8 × 10⁵ statistical vectors that fit in RAM without diluting geological features |
| **Role of supercomputing (Yuca)** | Offline batch processing via Slurm over the H3 grid: statistics extraction, HDBSCAN and RBF kernel evaluation | No live dependency during the presentation; the web reads the exported static artefact (`analogs_universe.json`) |
| **The scale problem (roughness)** | Formal separation of **macro-topography** (regional slope) and **micro-roughness** through proxy variables before downsampling (TRI on GLO-30 and Sentinel-1 SAR vs. THEMIS thermal inertia and LOLA Hurst exponent) | Sub-metre rover obstacles cannot physically be measured from global 90–200 m/px DEMs |
| **Analog typology** | Bimodal: **static** (terrain, roughness proxy, spectral ratios) and **dynamic** (seasonal aeolian processes and aerosols) | Answers NASA's call to analyse *processes* as well as *places* |
| **Logistic feasibility** | Distance to the paved road network and to nearby airports (`logistics_score`) | Shows why a new candidate (for example, Sonora) can beat remote classic sites (Antarctica, Devon Island) on cost-benefit |
| **Client-side logic and maps** | Weights recomputed in memory (< 1 ms) and a pragmatic dual viewer (Mapbox for Earth + NASA Trek WMTS / Leaflet for the Moon and Mars) | Instant interactivity, without planetary-projection blockers or CORS failures when exporting reports |

---

## 3. System architecture and HPC pipeline (Yuca)

```text
[Cloud pre-aggregation (GEE / STAC) + PDS catalogue (Moon / Mars)]
                                │
                                ▼
         ┌──────────────────────────────────────────────┐
         │    HPC BATCH PIPELINE (YUCA SUPERCOMPUTER)   │
         │                                              │
         │  1. Boolean mask and H3 tiling (res 6):      │
         │     drop oceans, NDVI > 0.20, urban          │
         │  2. Per-H3-cell statistics:                  │
         │     [Slope_μ, TRI_proxy, Fe_Ratio, Clay_Ratio│
         │      Albedo, Aridity_Idx, MODIS_AOD, Dist_Rd]│
         │  3. Unsupervised clustering (HDBSCAN)        │
         │  4. Gaussian (RBF) scoring vs. targets       │
         └──────────────────────┬───────────────────────┘
                                │
                                ▼
              [Static artefact: analogs_universe.json]
                                │
                                ▼
         ┌──────────────────────────────────────────────┐
         │             WEB FRONTEND REACT + VITE        │
         │                                              │
         │  • Dual viewer (Mapbox Earth + NASA WMTS)    │
         │  • Operational presets + in-memory sliders   │
         │  • Radar charts + feasibility filter (km)    │
         │  • Critical panel: "Limits of the analog"    │
         └──────────────────────────────────────────────┘
```

### Execution protocol on Yuca

1. **Pre-aligned ingestion (H+0 to H+6):** reduced bands per H3 cell from Google Earth Engine or STAC APIs into Yuca, avoiding massive raw raster downloads.
2. **Pilot (H+6 to H+12):** validate the Python script (`h3`, `numpy`, `scipy`, `scikit-learn`, `hdbscan`) on the Sonoran Desert / US Southwest quadrant.
3. **Global batch (H+18 to H+26):** overnight Slurm run over the H3 cells of the world's arid zones, against the vector of Mars and Moon target sites.
4. **Export (H+26):** generate `analogs_universe.json` with the best 50 to 100 grouped clusters, enriched with logistic and mineralogical metadata.
5. **Contingency:** if the Slurm queue is delayed, the frontend runs on the pilot dataset plus the curated reference catalogue.

---

## 4. Static data contract (`analogs_universe.json`)

The schema separates the **operational presets** (`mission_presets`) from the **candidate sites** (`analogs`). The frontend therefore computes the MSI in real time (< 1 ms) from the user's sliders, without depending on a fixed pre-computed index.

The original master-plan example (H3 cells, spectral and aerosol metrics) is superseded by the v2 contract in [plan_t7_t8.md](plan_t7_t8.md) §4.1. Its shape was:

```json
{
  "metadata": { "version": "2.0.0", "grid_system": "Uber H3 Resolution 6 (~36 km2)", "hpc_node": "Yuca Supercomputer (UNISON) - Slurm Batch", "generated_at": "..." },
  "mission_presets": {
    "mobility_and_traction": { "label": "Rover mobility and traction", "weights": { "topography": 0.40, "roughness": 0.40, "spectral": 0.10, "environmental": 0.10 } },
    "isru_and_mining": { "label": "ISRU and resource extraction", "weights": { "topography": 0.15, "roughness": 0.15, "spectral": 0.55, "environmental": 0.15 } },
    "dust_and_atmospheric": { "label": "Aeolian abrasion and dust mitigation", "weights": { "topography": 0.10, "roughness": 0.15, "spectral": 0.15, "environmental": 0.60 } }
  },
  "analogs": [
    {
      "id": "pinacate-crater-elegante",
      "name": "El Elegante crater, El Pinacate volcanic field",
      "location": { "lat": 31.848, "lon": -113.390, "country": "Mexico", "region_type": "Volcanic / Maar Crater" },
      "classification": "NEW_CANDIDATE",
      "analog_type": "STATIC_GEOLOGY",
      "target_body": "Mars",
      "target_site": { "id": "mars-jezero-floor", "name": "Jezero Crater Floor", "lat": 18.38, "lon": 77.58 },
      "sub_scores": { "topography": 0.92, "roughness": 0.88, "spectral": 0.84, "environmental": 0.86 },
      "logistics": { "accessibility_score": 0.91, "nearest_paved_road_km": 14.5, "nearest_airport_code": "PPE", "nearest_airport_km": 92.0 },
      "breakdown_limits": {
        "atmospheric_pressure": "Earth ~1013 hPa vs. Mars ~6 hPa.",
        "gravity": "Earth 1.0 g vs. Mars 0.38 g.",
        "radiation": "Earth's magnetosphere blocks GCR and solar particle events."
      },
      "test_protocol": "Traction tests on loose basaltic slopes, tread wear and visual odometry calibration (SLAM)."
    }
  ]
}
```

That example was illustrative: its numbers were placeholders, not results.

---

## 5. Methodology: Mission Similarity Index (MSI)

**Why a Gaussian kernel.** It avoids the scale distortions of cosine similarity, and the numerical instability of dividing by near-zero values on flat plains. Each geophysical dimension k ∈ {topo, rough, spect, env} is evaluated with a **Gaussian radial basis function (RBF)**, calibrated with an engineering tolerance σ_k:

$$
S_k(x_{\text{Earth}}, x_{\text{Target}}) = \exp\left( - \frac{(x_{k,\text{Earth}} - x_{k,\text{Target}})^2}{2\sigma_k^2} \right)
$$

This guarantees that:

- S_k ∈ (0, 1] is strictly bounded, continuous and differentiable;
- tiny differences on flat terrain (≈ 0°) give similarities close to 1.0, with no artificial penalties;
- deviations beyond the operational tolerance σ_k decay exponentially.

### In-memory computation (web client)

The **Mission Similarity Index (MSI)** is computed reactively in the browser, combining the weight vector chosen by the mission engineer:

$$
\text{MSI} = \sum_{k} w_k \cdot S_k \quad \text{subject to} \quad \sum_{k} w_k = 1.0, \quad w_k \ge 0
$$

Optionally, the user can turn on the **logistics-adjusted index (MSI_log)** to favour sites that are accessible for low-cost field campaigns:

$$
\text{MSI}_{\text{log}} = \text{MSI} \cdot \left(1 - \lambda + \lambda \cdot A_{\text{log}}\right)
$$

where λ ∈ [0, 0.3] is the logistics weight and A_log = exp(−d_road / 100 km) measures road accessibility.

### Geophysical sub-indices (S_k)

1. **S_topo (macro-topography and slopes):** the slope distribution (mean μ_θ and p90), computed on digital elevation models at regional scale (σ_topo = 5.0°).
2. **S_rough (surface roughness through thermophysical and topographic proxies).** Global DEMs (30–200 m/px) cannot resolve sub-metre obstacles at rover-chassis scale. S_rough therefore crosses proxy variables, normalised to [0, 1] before downsampling:
   - **Earth:** the Terrain Ruggedness Index (TRI; local elevation deviation in a 3 × 3 window on GLO-30), combined with Sentinel-1 VV/VH radar backscatter, which is sensitive to centimetre roughness;
   - **Mars / Moon:** Mars Odyssey THEMIS thermal inertia (which quantifies grain size and surface rock abundance), and LRO LOLA bidirectional roughness maps (Hurst exponent) for the Moon.
3. **S_spect (mineralogical and spectral affinity):** continuous spectral indices from multispectral reflectance (Sentinel-2 / Landsat 8-9 on Earth vs. MRO CRISM / Chandrayaan-1 M³):
   - **mafic / ferrous index (R_Fe):** SWIR1 / NIR ratio, for olivine and pyroxene in basalts;
   - **ferric oxide index (R_Ox):** Red / Blue ratio, for oxidised regolith;
   - **phyllosilicate / clay index (R_Clay):** SWIR1 / SWIR2 ratio, for aqueous alteration and ISRU.

   The specific mineralogy text would be assigned by semantic enrichment of the top 100 clusters generated on Yuca.
4. **S_env (environmental conditions and dynamic processes):**
   - **static mode:** a hyper-aridity index from inverted vegetation (NDVI < 0.15) and surface moisture (NDWI);
   - **dynamic mode:** the seasonal frequency of dust events, from aerosol optical depth (MODIS Deep Blue AOD at 550 nm), compared with atmospheric dust opacity profiles from the Mars Climate Sounder (MCS).

---

## 6. Official datasets (NASA, USGS, ESA, JAXA)

| Body | Dimension | Sensor / mission | Product |
| --- | --- | --- | --- |
| **Moon** | Topography and slope | LRO LOLA | Global lunar DTM 118 m / polar SLDEM 20–60 m |
| **Moon** | Surface roughness | LRO LOLA roughness | Lunar surface roughness maps (Hurst exponent) |
| **Moon** | Composition / mineralogy | Chandrayaan-1 / M³ | Spectral reflectance / Diviner Christiansen Feature |
| **Moon** | Extreme temperatures | LRO Diviner | Thermal maps of permanently shadowed regions (PSRs) |
| **Mars** | Global topography | MGS MOLA + MEX HRSC | Blended global DEM (200 m/px) |
| **Mars** | Local topography | MRO HiRISE | 1 m/px DTMs of landing sites |
| **Mars** | Thermophysics / roughness proxy | Mars Odyssey THEMIS | Global thermal inertia map (grain/rock size) |
| **Mars** | Atmospheric dynamics | Mars Climate Sounder | Global atmospheric dust profiles |
| **Earth** | Topography and roughness proxy | Copernicus GLO-30 + Sentinel-1 | Global DEM (TRI 30 m) + SAR backscatter |
| **Earth** | Spectral indices and soil | Sentinel-2 / Landsat 8/9 | SWIR1/NIR (iron), SWIR1/SWIR2 (clays) and NDVI ratios |
| **Earth** | Aeolian dynamics and aerosols | Terra/Aqua MODIS | Deep Blue aerosol optical depth (AOD 550 nm) |
| **Earth** | Logistic accessibility | OpenStreetMap / Natural Earth | Global paved road network and airfields (distance) |

The datasets actually used are listed in the [README](../README.md#data).

---

## 7. User flow (frontend)

```text
[1. Scenario definition]
       │
       ▼
   • Body selector: Moon (Artemis) | Mars
   • Analog type: static terrain / geology | dynamic process (dust / wind)
   • Operational case (weight preset): mobility | ISRU and ice | dust abrasion
       │
       ▼
[2. In-memory weighting and logistics filter]
   • Reactive sliders per geophysical dimension + "logistics priority (km)" toggle
       │
       ▼
[3. Dual exploration on screen]
   • Earth view: markers ranked by affinity
   • Planetary view (Leaflet + NASA Trek WMTS): orbital context of Mars / Moon
   • Results bar: comparison cards with live MSI
       │
       ▼
[4. Technical card and scientific inspection]
   • 4-axis radar chart + road accessibility indicator
   • CRITICAL PANEL: "Limits of the analog" (gravity, pressure, radiation)
   • Suggested field engineering test protocol
   • Direct provenance links to NASA / PDS datasets
       │
       ▼
[5. Comparison and export]
   • Side-by-side "versus" view of two sites (for example, classic vs. new candidate)
   • Clean export of the card as JSON / Markdown (and a CSS print view)
```

---

## 8. Team organisation (6 people)

```text
                              ┌────────────────────────┐
                              │  GENERAL COORDINATION  │
                              └───────────┬────────────┘
                                          │
            ┌─────────────────────────────┴─────────────────────────────┐
            ▼                                                           ▼
 ┌──────────────────────┐                                    ┌──────────────────────┐
 │    CODE TEAM (2)     │                                    │ DATA, SCIENCE AND    │
 │                      │                                    │ PRESENTATION TEAM (4)│
 └──────────┬───────────┘                                    └──────────┬───────────┘
   ┌────────┴────────┐                                         ┌────────┴────────┐
   ▼                 ▼                                         ▼                 ▼
[Dev 1]           [Dev 2]                                   [P1: Pitch]       [P2: Data]
Frontend, UI      Yuca pipeline                             Main speaker,     Targets and
and dual map      and JSON                                  script, defence   curated JSON
                                                                │
                                                            [P3: Science]     [P4: Media/Deck]
                                                            Physical limits,  Slides and
                                                            official docs     backup demo video
```

### Roles

| Role | Responsibilities |
| --- | --- |
| **Dev 1 (frontend)** | The reactive interface (Vite, React, Tailwind, maps for Earth and the target, charts) and the side-by-side "versus" view |
| **Dev 2 (HPC pipeline and deployment)** | The pipeline on Yuca (RBF scoring and clustering), assembling `analogs_universe.json`, and deploying to Vercel or Netlify |
| **P1 (pitch lead and speaker)** | Writing and rehearsing the timed script for the judges; leading the technical defence in Q&A |
| **P2 (satellite data and targets)** | Encoding the target-site metadata, so Dev 2 does not have to clean it by hand |
| **P3 (planetary physics and documentation)** | The quantitative justification of the "limits of the analog", the field test protocols, the NASA Space Apps form and the documentation of AI use |
| **P4 (deck and backup demo)** | The slides, and the recorded demo video in case the network fails |

---

## 9. Execution timeline (48 hours)

The real timeline, adjusted to the venue (one working day plus Sunday morning), is in [submission.md](submission.md).

| Phase | Code team + data lead (Dev 1, Dev 2, P2) | Science and presentation team (P1, P3, P4) |
| --- | --- | --- |
| **H00–H06** | **Dev 1:** set up Vite, React and Tailwind, and a mock `analogs_universe.json`. **P2 + Dev 2:** target vectors for the Moon and Mars | Choose mission cases, draft the base physical limits (gravity, pressure, radiation) and the pitch narrative |
| **H06–H14** | **Dev 1:** dual map viewer and reactive sliders with in-memory RBF. **Dev 2:** pilot of the scoring script on Yuca | Engineering test protocols for the key sites; first slides |
| **H14–H24** | **Dev 2:** global batch run on Yuca. **Dev 1 + P2:** connect the frontend to the pilot dataset and the logistics filter | Enrich the best clusters; finish the NASA Space Apps project texts |
| **H24–H36** | **Dev 1 + Dev 2:** load the final `analogs_universe.json`, radar charts, the "limits of the analog" panel and the "versus" view | First timed rehearsals with the deployed app; architecture and methodology slides |
| **H36–H42** | **Code freeze.** Interface polish and performance | Record the backup demo video; adversarial Q&A practice |
| **H42–H48** | Publish and document the open repository on GitHub, including the Slurm/Yuca scripts | Final timed rehearsal and submission on the NASA Space Apps platform |

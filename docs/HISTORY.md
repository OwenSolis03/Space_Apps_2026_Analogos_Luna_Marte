# Project history

How Planetary Analog Finder was built, in English, with the reasoning behind each decision. Every step points to the commits and Slurm jobs that back it up. Most commit messages up to 2026-11-13 are in Spanish; this file is their English record. The commits are not rewritten, because their hashes are cited in the docs and in the Slurm logs. Day-by-day detail (in Spanish until 2026-11-13) is in [logbook.md](logbook.md).

**Who did what**

| Who | Role |
| --- | --- |
| Owen Solis | Pipeline lead. Runs everything on the Yuca supercomputer (UniSon), reviews results, approves every job |
| Claude (Anthropic) | Detailed implementation plans (`docs/plan_*.md`), documentation, data inspection on Yuca, and review of results and code. Also wrote the app skeleton (T10), `tools/explore_datasets.py` and `tools/v1_to_sample.py` |
| Gemini 4 (Antigravity, Orchestrator mode) | Implemented the v2 pipeline code (T1–T6) from Claude's plans, ran tests and jobs through Slurm |
| Javier Miranda | App (T10) |
| Rest of Endurance CXXV | Pitch, content and presentation |


---

## 1. Idea and first plan (before 2026-11-12)

- [ideas.md](ideas.md) records how the idea evolved:
  - from "process every layer of the whole planet with image models";
  - to "a pre-computed set of sites with adjustable weights and a 'where the analogy breaks' section";
  - to "a numeric similarity index plus unsupervised clustering, computed on Yuca".
- [master_plan.md](master_plan.md) set the target: a web app that ranks Earth sites against Moon and Mars targets with a Mission Similarity Index (MSI) built from Gaussian (RBF) kernels per dimension, with presets per mission type and a mandatory "limits of the analog" panel.

**Why:** the challenge asks for analogies justified with data, explicitly says where they fail, and rewards finding sites beyond the famous ones (Atacama, Antarctica, Iceland, Hawaii). A weighted, explainable score fits that better than a black-box model.

## 2. The v1 prototype and what was wrong with it (2026-11-12)

The first version ran end to end on Yuca. Its outputs are in `output/`, its logs in `logs/`, and its scripts are kept at the repo root as reference.

| Job | What |
| --- | --- |
| 2241770, 2241771, 2241773 | Clustering of Mars and Moon DEM windows into 40 archetypes per body |
| 2241781, 2241782, 2241783 | Matching against Copernicus GLO-90 tiles |

The review (commit `5cbf360`, documented in the bitácora) found problems that shaped v2:

| v1 problem | Consequence |
| --- | --- |
| Windows of different size and resolution per body (~118 km at 463 m on Mars, ~30 km at 118 m on the Moon, ~46 km at 90 m on Earth) | Slope and roughness depend on scale, so the comparison was not fair |
| Equirectangular windows without correction | Shapes stretched away from the equator |
| No vegetation mask | Lunar "analogs" landed in the Himalaya and the Colombian Andes |
| Only 6,983 of 26,475 Earth tiles downloaded | Partial coverage of Earth |
| Lunar "albedo" layer was actually a colour-shaded relief | Wrong data in the lunar layer |
| Targets were only global clusters | No real Artemis or Mars landing sites |
| Ad-hoc score `100/(1+0.35d)` | Not explainable, no notion of where the analogy fails |

## 3. Repository, value proposition and data completion (T0)

**Commits:** `5cbf360`, `e977c5e`, `a382beb`, `7fec550` (PR #1), `0866e5c`, `9b3341a`, `3f92906`, `3ed3f94`, `2bd255b`, `89c2cf7`, `0acfb72`.

- **Repository and value proposition:** the repository was created and [value_proposition.md](value_proposition.md) written for the pitch team.
- **Data download:** everything was (re-)downloaded with Slurm jobs, never on the login node.

| Job | Result |
| --- | --- |
| 2242198 | All 26,475 Copernicus GLO-90 tiles (0 failures), THEMIS IR Night, LROC WAC 100 m and the USGS lunar ice favorability index |
| 2242203 | MODIS MOD13C2 (NDVI) and MOD11C3 (land surface temperature) for 2023, plus Natural Earth roads, airports and countries |
| 2242221 | LRO Diviner Polar Resource Product (south pole), from NASA PDS Geosciences |

- **Explorer:** `tools/explore_datasets.py` generates an HTML report of every downloaded dataset.

**Why these datasets:** they map to the challenge's official resources (PDS, LRO, LRO Diviner, NASA Earthdata, NASA Worldview/GIBS, Copernicus). The mapping is in `implementation_plan.md` §2.

## 4. The v2 design (commit `9b3341a`, `implementation_plan.md`)

| Decision | Why |
| --- | --- |
| Compare **32 × 32 km patches resampled to 500 m/px (64 × 64)** on all three bodies | Slope and roughness depend on scale; one scale for every body makes the comparison fair |
| Reproject each patch to a **local azimuthal equidistant (AEQD)** projection centred on it | Removes the stretching of equirectangular mosaics at high latitude |
| **One function** for patch extraction (T1) and one for terrain features (T2), shared by Earth, Moon and Mars | Guarantees the same measurement everywhere |
| Features: mean and p90 slope, relief (p95−p5), hypsometric integral, detrended roughness, Riley's TRI. Elevation is stored but **not compared** | Datums of different bodies are not comparable |
| **MODIS NDVI mask** for Earth | Analogs of airless or arid bodies must be bare ground |
| **Curated targets** (Artemis III regions, Mars landing sites) plus **global clusters** | Real mission sites for the challenge, plus an exploration mode |
| **RBF kernel per dimension**, MSI = weighted mean, re-weighted in the browser | Bounded, explainable, adjustable by the user |
| **Mismatches per site** plus fixed physical limits per body | The challenge asks where the analogy breaks |
| **KNOWN_ANALOG / NEW_CANDIDATE** label and logistics (distance to road and airport) | Shows when a site is new and whether it is practical to visit |

## 5. T1 and T2: patch extraction and features

**Commits:** `ac743ce` (T1, `pipeline/geo.py`), `a661bb7` (T2, `pipeline/features.py`). Code by Gemini, verified with synthetic tests.

- **Key test:** the same tilted plane gives the same slope at 0° and 70° latitude on the Moon, which v1 failed.
- Patches with < 90 % valid pixels are dropped.
- Patches crossing ±180° are skipped and counted.

## 6. T3: global Mars and Moon sweep, and the LOLA scale bug

**Commits:** `19e3899`, `920f812`, `9bc9f91`, `bcf10de`, `401709b`, `57f4f36`.

- **Bug found:** a test run (job 2242227) showed lunar relief twice as large as expected. Inspecting every mosaic on Yuca revealed that **LOLA LDEM stores half-metres** (int16, `scale = 0.5`). rasterio does not apply the scale automatically, so v1 and the first v2 test had **every lunar vertical metric doubled**.
- **Fix:** `geo.py` now applies `scale`/`offset` after masking nodata. Job 2242231 confirmed that lunar relief and elevation dropped exactly by half, and that median slope went from 13.2° to 6.9°.
- **Other scale facts** documented in `pipeline.md`:
  - LROC WAC is relative brightness (uint8 with scale/offset), compared by **percentile within the Moon**;
  - THEMIS mosaics are raw grey levels, not kelvin;
  - the ice index uses a huge float nodata value.
- **Full run (jobs 2242278 and 2242279, merge):**

| Body | Valid patches | Of candidates |
| --- | --- | --- |
| Mars | 140,916 | 99.6 % |
| Moon | 36,741 | 99.3 % |

  The slope maps show Valles Marineris, Olympus Mons, Hellas and Argyre on Mars, and maria against highlands, Crisium and Orientale on the Moon.

## 7. T10: app skeleton

**Commits:** `9dc20cc`, `d3ed3ab`, `9325dea` (PR #2).

- **Stack:** React + Vite + TypeScript + Tailwind, with Leaflet maps on NASA Trek (Moon, Mars) and NASA GIBS (Earth) tiles.
- **Ranking:** the MSI is recomputed in the browser from per-dimension sub-scores.
- **Sample data:** `tools/v1_to_sample.py` converts the v1 output into the v2 JSON schema, so the app could be built before the v2 pipeline finished.

## 8. Working setup on Yuca

**Commits:** `51678d9`, `501aef2`, `0e1e43c`.

- **Remote access:** the venue network blocks SSH, so work goes through **Open OnDemand** (HTTPS). Gemini codes locally and pushes; Owen pulls and submits jobs in the OOD shell and passes logs back. Documented in [working_without_ssh.md](working_without_ssh.md).
- **Offline kit:** an 88 MB kit (T3 outputs, IAU gazetteer, Natural Earth, Diviner cache) lets development continue without the cluster.
- **Safety rules for every job:** account `p089`, logs in `output/`, a new `runs/<jobid>/` directory per run, no `rm -rf`, no TLS bypass, and a group limit of 500 CPUs.
- **Incident without damage:** importing the v1 script `enrich_nomenclature.py` executed it, because it has no `__main__` guard, and it rewrote a v1 output file. The content came out identical. Rule since then: never import the v1 scripts.

## 9. T4: targets

**Commits:** `89ae6ef` (plan), `e6072ba`, `115e0c3`. **Jobs:** 2242421 (tests), 2242422 (smoke test), 2242423 (full run).

- **Lunar anchors.** NASA lists the nine Artemis III candidate regions (2024-10-28) **without centre coordinates**. Each region is anchored on the **IAU feature of the same name** (USGS Gazetteer). "Rim" regions are measured with 8 patches on the crater rim, and the JSON says the locations are approximate. Two pairs of regions that share an anchor are merged:

| Merged target | NASA regions |
| --- | --- |
| Nobile rim | Nobile Rim 1 and 2 |
| Mons Mouton | Mons Mouton and Mons Mouton Plateau |

- **Shackleton:** it is 0.33° from the pole, so its patch contains the pole. `geo.py` got a polar branch that reads a full latitude band. It is only triggered beyond ~89.25°, so T3 is unaffected.
- **Mars:** published landing coordinates for Perseverance, Curiosity, Spirit, Opportunity, Zhurong and InSight, the IAU centre of Oxia Planum, and the SWIM shallow-ice region in Arcadia Planitia.
- **Clusters:** k-means with k = 30 per body on the six terrain features (log for long-tailed ones, standardised). Each representative is a **real T3 patch**.
- **Results:**
  - 16/16 curated targets valid, Shackleton included, plus 60 cluster targets;
  - the flat landing plains (InSight, Arcadia, Zhurong, Gusev, Meridiani) are all below 0.55° mean slope against a Mars median of 1.16°;
  - Gale has ~39× the relief of InSight.
- **Fix:** `.gitignore` was ignoring `pipeline/data/` through a generic `data/` rule, so that folder was re-included.

## 10. T6: Earth layers

**Commits:** `5b33704` (plan), `29fbb88`, `6adbb04`, `84888cd`, `a4e039f`. **Jobs:** 2242424 and 2242425 (tests), 2242426 (cache build and checks), 2242427–2242429 (read-only diagnostics), 2242430 (checks: 8/8 hard, 5/5 soft).

- **MODIS reading:** the GDAL build has **no HDF4 driver**, so MODIS is read with `pyhdf`.
- **Opposite scale conventions:** NDVI is `raw / 10000` (its `scale_factor` attribute is 10000), while LST is `raw × 0.02` K. Both are hard-coded, because applying the attribute generically would have made NDVI 10,000 times too large.
- **Cache:** annual maximum NDVI and annual mean day/night LST for 2023 in `data/derived/`.
- **Logistics:**
  - distance to the nearest road, excluding ferry routes and with roads densified every ~2 km so long straight segments are measured correctly;
  - distance to the nearest non-military airport;
  - country.
- **12 well-known analog regions** with approximate bounding boxes. They only decide the KNOWN_ANALOG label and never enter the score.
- **First run, two failed checks:** they were badly specified in the plan, not caused by bugs.
  - **Bare bright desert soil** has NDVI around 0.05–0.12, so the Sahara threshold became < 0.12.
  - **MOD13C2 has no data south of 59.45°S**, so the land-coverage check is area-weighted.

## 11. T5: Earth sweep

**Commits:** `446c93f` (plan), `52bf3d7`. **Jobs:** 2242431 (tests), 2242432–2242434 (500-patch smoke test).

- **Sea mask:** Copernicus tiles have **no nodata**, and the sea inside coastal tiles is exactly 0.0. The tiles are mosaicked in a VRT with **0 treated as nodata**, so `extract_patch` drops any patch with > 10 % sea.
- **Prefilter:**
  - no tile, or NDVI > 0.25 (vegetation), is dropped;
  - a missing NDVI passes **only where LST exists** (Antarctica);
  - missing NDVI and LST together means sea, and the patch is dropped.

  The rule came from measuring the real cache: 20,524 of the "missing NDVI" centres were over the sea.
- **Three Slurm stages:**
  - prepare (prefilter and Earth layers computed once);
  - a 32-stripe array with balanced work;
  - merge with checks.
- **Smoke test:**
  - 44,375 candidates worldwide, matching the ~45,000 estimate;
  - 445/500 valid patches;
  - 5/5 hard checks.

## 12. Venue rules and language

**Commit:** `8d93240`.

- **Venue:** the team competes at NASA Space Apps Sonora 2026 (Tec de Monterrey, Campus Sonora Norte).
  - Hacking: Saturday 14 November, 9:00–21:00.
  - Pitches: Sunday 15 November, morning.
  - Pitch: 3 minutes, with an English write-up, a ≤ 30 s English video and a deployed app.
  - Checklist and timeline: [submission.md](submission.md).
- **Language:** from this point on, commit messages, new documentation and new code comments are in **English**.

## 13. T7/T8: RBF matching, MSI presets and export

**Commits:** `f3d0685` (plan), `997a0c0`. **Jobs:** `2242472` (61 tests), `2242473` (smoke test on `runs/2242432`), `2242474` (full run on `runs/2242438`).

- **Normalisation in "Earth units":** after applying `log1p` to long-tailed metrics (`relief_m`, `detrended_std_m`, `tri_m`), features are normalised using only Earth candidates' median and `1.4826 * MAD` (`floor = 1e-6`), so distances read directly as deviations relative to arid/barren Earth terrain.
- **Dimension-wise RBF and `σ = 1.0` honesty:** topography (4 features), roughness (2 features) and NDVI environment use RBF kernels with default `σ_scale = 1.0`. Missing NDVI (Antarctica) receives `S_environment = 1.0` with `ndvi_missing = true` so cold, unvegetated dry valleys remain valid.
- **Mars-only percentile thermal score:** Earth `lst_amplitude_c` and Mars `themis_delta` use incompatible physical units, so both are converted to percentile ranks within Earth candidates and within the T3 Mars sweep (`themis_delta`), divided by `0.15` percentile units. Moon targets set `S_thermal = null` and renormalise MSI weights automatically.
- **Candidate search, 150 km diversity and polar cap:** `NearestNeighbors` finds `k = 2000` topographic+roughness candidates per target (retrying with `k = 8000` if any preset yields `< 30`), then each of the three presets greedily accepts top-30 patches spaced `>= 150 km` apart while capping `polar_cold` (`lst_day_c < -10 °C`) at `<= 3` per preset so Antarctic ice sheets do not swamp flat Mars targets.
- **Explainability and provisional limits:** pairs record per-feature physical mismatches (`|z_diff| > 1.5`) and thermal rank differences (`> 0.30`). Until T11 creates `pipeline/data/limits.json`, `export.py` falls back with a warning to the provisional limits in `app/public/data/sample.json`.
- **Full run outcome (`2242474`):** `5/5` hard checks, `3,908` pairs (`213 KNOWN_ANALOG`, `3,695 NEW_CANDIDATE`) exported in `analogs_universe.json` (`3.18 MB`), pending review of `t7_report.md` before publishing into the app.

---

## Next

- **Beyond terrain (T12–T15, [plan_t12_t15.md](plan_t12_t15.md)).** The T7 run (job 2242474) showed that terrain alone cannot separate flat Mars plains (top-1 vs top-30 MSI differ by 0.012) and does not recognise volcanoes as volcanoes. Three evidence dimensions are added, each with open data checked on 2026-11-14:
  - regional geology, a shared class taxonomy over GLiM (Earth), USGS SIM 3292 (Mars) and the USGS unified lunar map;
  - dust processes and seasons, Montabone's Mars dust climatology against MODIS Deep Blue AOD, compared by rank and local seasonal phase;
  - cold traps and ice, Diviner against MODIS LST and GLiM ice.

  GLiM also lets the pipeline tell ice sheets from bare cold ground, so the polar cap of T7 becomes an ice cap.

- **Review `runs/2242474/t7_report.md`** (score distribution and Olympus Mons check) and publish `analogs_universe.json` to `app/public/data/`.
- **T11:** physical limits per body (`pipeline/data/limits.json`) and verified dataset URLs.
- **App (T10):** connect `app/` (`DATA_URL`) to `analogs_universe.json` and deploy.
- **Code in English:** finish translating older Spanish docstrings/comments in `pipeline/` (T1–T6).

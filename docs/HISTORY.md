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

## 14. Beyond terrain: geology, dust seasons and ice (T12–T14, before T15)

**Commits:** `6df4021` (plan), `bec78d7`–`25f2e7e`, `c834727`, `16db5db` (`geology_overrides.json`). **Jobs:** `2242478` (70 tests), `2242481` (downloads), `2242482` (T14), `2242484` (T13), `2242485` (T12).

- **Why:** T7 showed that pure topography leaves flat Mars plains tied (top 1 vs top 30 MSI differ by 0.012) and does not recognise volcanic edifices like Olympus Mons as volcanic. T12–T14 add lithology (`GEO_CLASSES` + `GEO_SIMILARITY`), dust level/seasonality/local peak phase, and water/cold-trap ice without changing `geo.py` or `features.py`.
- **T14 Geology (`2242482`, 6/6 hard, 2/3 soft):** GLiM separates Antarctic/Greenland ice sheets (`12,742` patches) from exposed polar rock (`McMurdo Dry Valleys` = `sm -> SEDIMENTARY`). Lunar polygons use `Shapefiles/GeoUnits.shp` (`12,247` polygons, `49` units + DOMU CSV) because the lunar `.gdb` uses ESRI CDF compression unhandled by `OpenFileGDB`; Mars uses `SIM3292_geodatabase.gdb / SIM3292_Global_Geology` (`1,311` polygons, `44` units). Word-boundary matching prevented `"edifice"` from matching `"ice"`. After inspecting `geology_mapping_review.md`, `16db5db` added `pipeline/data/geology_overrides.json` for Moon terra/basin units and Mars polar dunes (`lApd`).
- **T13 Dust & Seasons (`2242484`, 3/4 hard, 3/4 soft):** Printed NetCDF3 variable metadata selected Montabone `cdod610` (`Pa/Pa`, `MY24`–`MY36`, perihelion peak at `Ls=225°`, storm years `[25, 34, 28]` highest), and printed HDF4 metadata selected MODIS Terra `MOD08_M3` v6.1 `Deep_Blue_Aerosol_Optical_Depth_550_Land_Mean_Mean` (`scale_factor=0.001`, `add_offset=0.0`, summer Sahara `0.4546`). Ranks and hemisphere-shifted local peak phase enable honest cross-body comparison. Check #5 failed only at Taklimakan `(39, 83)` (`rank=0.7281` vs `> 0.9`) because year-round annual mean 550 nm AOD across non-ice land peaks in the Indo-Gangetic Plain and Sahel/Sahara while Taklimakan's dust is strongly seasonal; paused at §5.6 for review.
- **T12 Water & Ice (`2242485`, 1/1 hard, 3/3 soft):** Uses T14 `ice_surface` (`12,742`), winter-frozen `lst_day_c < 0` (`ice_E=0.5`, including 9/9 Dry Valleys patches), and `pipeline/data/ice_hints.json` (`mars-arcadia-swim`), plus within-body `cold_rank` (Haworth `0.9734`, Slater Plain `0.9574`).

## 15. T15 and T11: seven dimensions and physical limits — the model is complete

**Commits:** `d3a255f` (review and amendments), `bda0acf` (T15 code, written by Gemini 3.8 Flash from Claude's plan), `16db5db` (geology overrides), `e24162e` (`limits.json`, by Claude), `899cd0d` and the final data commit. **Jobs:** `2242486` (T14 re-run with overrides), `2242487` (T12 re-run), `2242488` (81 tests), `2242489` (T15), `2242490` (final export with `limits.json`).

- **Review before integration.** Claude approved T12–T14 with corrections (plan_t12_t15.md §5.8):
  - lunar terra → crystalline crust, basin formations → impact, Mars polar dunes → sedimentary;
  - two dust checks were badly specified and were corrected (the Taklimakan is ranked among arid peers; Hellas ≈ Tharsis is expected under the 610 Pa normalisation);
  - **why the equator rule:** the dust phase term is dropped within 15° of the equator, where seasons are weak and the hemisphere switch would flip the local phase by 180°.
- **Integration.** Seven dimensions and five presets: mobility, construction, geology and materials, dust and seasons, and ice and ISRU.
  - **Why score the whole Earth:** every Earth patch is now scored. The old terrain-only candidate pool would have hidden the best process analogs.
  - **Why the ice cap:** the polar cap became an ice-sheet cap based on GLiM `ig`, so ice-free cold deserts such as the Dry Valleys are no longer penalised. It does not apply to the ice preset.
- **Result (2242489/2242490), all 7 hard and 4 soft checks passed:**
  - **Olympus Mons:** 10 of its top 10 Earth analogs are basaltic volcanic terrain. Terrain alone had found none.
  - **Mars plains:** the top-1 to top-30 spread grew from 0.012 to 0.059, so the flat plains are no longer ties.
  - **Dust and seasons:** Jezero's best analog is Yemen (0.93), then Algeria, China and Sudan.
  - **Ice:** Arcadia's shallow ice matches the Antarctic and Greenland ice sheets (0.85). The Artemis regions reach 0.55, because rugged crater rims are not flat ice sheets.
  - **Lava tubes:** 656 analogs carry the "basaltic terrain, lava tubes possible" note.
- **Physical limits (T11).** `pipeline/data/limits.json` has six sourced limits per body, from NASA fact sheets and measured surface doses (Curiosity RAD, Chang'e-4 LND), plus Diviner cold traps, Phoenix perchlorates, Apollo dust reports and the Montabone dust climatology. They replace the provisional limits.
- **Known limits of the model.** They are stated in `metadata.not_modelled` and in [value_proposition.md](value_proposition.md):
  - no spectral mineralogy and no biology;
  - geology is regional (GLiM 0.5°, Mars map 1:20M), so Gale and Meridiani appear as impact or highland and not as their sedimentary fill;
  - Deep Blue AOD includes some non-dust aerosols outside the arid filter;
  - the Moon has no dust dimension, because it has no atmosphere.
- **Published:** `app/public/data/analogs_universe.json` (6.2 MB, 76 targets, 5,010 analog pairs). The app has to switch `DATA_URL` and support 7 dimensions (T10, owned by the app developer).

## 16. Missing data as a free pass in the MSI and the T16 policy (T16)

**Commits:** `fed9d16` (T16.1), `0a4b801` (T16.2), `0c2fa71` (T16.3), `dabbc4c` (T16.4), `730165a` (T16.5), and data commit. **Job:** `2242506` (`commit 730165a`, 10/10 hard, 7/7 soft checks).

- **The problem:** In run 2242490, Mars targets ranked under the `dust_and_seasons` preset were dominated by Antarctica, and targets under `isru_and_ice` by the Sahara. Because `msi()` dropped null sub-scores and renormalised the remaining weights, missing data acted as a free pass: MODIS Deep Blue AOD has no retrievals over ice/snow, so 17 Mars targets had Antarctic analogs winning on dust because the 40% dust weight simply vanished; similarly, 37 of 38 Mars targets lacked ice data, so the 50% ice weight vanished and terrain decided.
- **The policy:** Three distinct cases:
  1. *Case A (Body):* Dimensions not applicable to the body are ignored, and presets only compute for bodies listed in `applies_to` (e.g. Moon has no dust preset).
  2. *Case B (Target):* Dimensions missing on the target are ignored, but if available weight drops below 60% (`min_preset_coverage = 0.6`), the target is not ranked for that preset (`insufficient_target_data`).
  3. *Case C (Earth):* If the target has data for a dimension but the Earth patch does not, the Earth sub-score is penalized to 0.0 (`earth_missing_score = 0.0`: no evidence, no credit). Missing NDVI over permanent snow/ice retains `S_environment = 1.0` (bare ground).
- **Outcome (run 2242506):**
  - Mars `dust_and_seasons`: top-1 analogs in Antarctica dropped from 17 to **0**; winners are genuine arid dust basins (Yemen, Algeria, Oman, Chad, Sudan, Iraq). Zero top-1 analogs miss dust data.
  - `isru_and_ice`: exactly 1 Mars target ranked (`mars-arcadia-swim`) and 8 Moon targets ranked (the Diviner cold trap sites). All other targets cleanly marked `insufficient_target_data`.
  - Moon `dust_and_seasons`: cleanly marked `not_applicable_body` (0 ranked).
  - Check 12 (browser MSI recomputation matches pipeline export within 0.002): 0 violations.

---

## Next

- **App (T10):** deploy the app running on `analogs_universe.json` (7 dimensions, 5 presets, missing data policy).
- **Code in English:** translate the older Spanish docstrings and comments in `pipeline/` (T1–T6), without behaviour changes.
- **Code in English:** translate the older Spanish docstrings and comments in `pipeline/` (T1–T6), without behaviour changes.
- **Optional refinements**, not needed for the submission:
  - keep only dust-dominated months using the Deep Blue Ångström exponent;
  - finer geology for landing sites (HiRISE/CTX-scale maps);
  - spectral mineralogy (CRISM/M³ against ASTER/Sentinel-2).

# T18: mineralogy as display-only context

Written by Claude on 2026-11-14. Status: Moon and Mars targets done with real data; Earth analogs ready to run on Yuca (one job).

**Decision.** Mineral maps are shown on the site sheet as context and are **not scored**. Reason: each instrument sees different minerals on each body, so a like-for-like score would be misleading. The Moon and Mars maps cover the minerals that make up fresh rock (olivine, pyroxenes, plagioclase, hematite); EMIT on Earth maps minerals that form when rock weathers (clays, carbonates, gypsum, iron oxides). Comparing bands directly does not work either, because the sensors measure different wavelengths under different illumination. The geology dimension already scores rock families.

The scored variant (option B) was explored on `exp/mars-mineral-dimension`; see the correction in the [logbook](logbook.md) about why its verdict does not stand on the evidence it cites.

---

## 1. Sources (all checked live on 2026-11-14)

| Body | Product | Where | Resolution and coverage | Variables shown |
| --- | --- | --- | --- | --- |
| Moon, targets | Kaguya Multiband Imager mineral maps (JAXA SELENE, USGS Astrogeology) | USGS bucket `mosaic/Lunar_MI_mineral_maps/4ppd/`, nine GeoTIFFs of 2.3 MB each, public | 4 pixels per degree (about 7.6 km), 50N to 50S | FeO (wt%), olivine, orthopyroxene, clinopyroxene, plagioclase, optical maturity |
| Mars, targets | MGS TES mineral abundance (Bandfield 2002), ASU Mars Global Data Sets | WMS export in VICAR, one 4 MB file per mineral, public, plain HTTP (`ms-mars.mars.asu.edu`); the page `https://www.mars.asu.edu/data/tes_<mineral>/` has the exact link | 4 pixels per degree (about 15 km), global, about 28% of cells masked (value -1) | olivine, orthopyroxene, clinopyroxene, plagioclase, hematite |
| Earth, analogs | EMIT L3 aggregated mineral abundance v002 (NASA JPL, LP DAAC) | `EMITL3ASA` v002, one 21.8 MB netCDF, needs the Earthdata login in `~/.netrc` | 0.5 degrees (about 55 km), 52N to 52S, arid regions the ISS observed | calcite, chlorite, dolomite, goethite, gypsum, hematite, illite + muscovite, kaolinite, montmorillonite, vermiculite |

Notes that came out of the checks:

- **Kaguya values.** The mineral maps are modal fractions from 0 to 1 even though the band tags say "%"; they are multiplied by 100 for display. A mare site gave FeO 18.5 wt% and a far-side highland gave 5.8 wt% with 86% plagioclase, which is right. The FeO map has a few absurd values (up to 107), so values above 30 wt% are dropped.
- **Mars OMEGA needs a login.** ESA's archive (`archives.esac.esa.int`) now answers 401 without an ESA COSMOS account, so OMEGA is not used here; TES from ASU needs no login. (Option B created that account to get OMEGA.)
- **TES sanity.** Meridiani Planum gives hematite 13% (published: about 10 to 15%); Syrtis Major gives clinopyroxene 18% and plagioclase 17%. TES detection level is about 5 to 10%, so smaller values are close to noise; the summary says so instead of naming a mineral at 0%.
- **EMIT variables.** The user guide lists the variables as `Calcite`, `Hematite`, `Illite+Muscovite`... in percent, fill value -9999, plus `_UQ_high_grainsize` and `_UQ_low_grainsize` uncertainty variants (skipped here). Latitude and longitude are documented as the upper-left corner of each cell; the reader detects the corner or centre convention from the coordinate lattice.
- **Coverage on the site sheet.** The eight Artemis III regions are all at 80 to 90 degrees south, outside Kaguya (50N to 50S): their card says so. 19 of 38 lunar targets and 37 of 38 Mars targets have values; the other Mars target has no valid TES pixel around it.

## 2. What the code does

`scripts/pipeline/minerals.py` reads the maps and adds a `mineralogy` block to `analogs_universe.json`. It never touches the matching or the scores (a test compares every other field before and after).

```json
"mineralogy": {
  "source": "tes_bandfield2002",
  "status": "ok",                  // ok | outside_coverage | no_data
  "values": {"olivine": 3.54, "orthopyroxene": 0.0, "clinopyroxene": 4.93, "plagioclase": 8.63, "hematite": 12.53},
  "summary": "Most abundant of the four silicates: plagioclase (9%); hematite present (13%)"
}
```

- Each value is the median of the valid pixels inside a window of about 16 km radius around the site (the same half-patch used everywhere else), converted to percent.
- `status` is `outside_coverage` beyond the source's latitude range, and `no_data` when no valid pixel is found (TES masked, EMIT cell not observed).
- `summary` is a plain-language line. Moon: FeO class (at least 14 wt% iron-rich, mare-like; at most 8 wt% iron-poor, highland-like; between, intermediate) and the most abundant mineral. Mars: most abundant silicate if it is at least 5%, otherwise "no silicate above the TES detection level"; hematite is added when it is at least 5%. Earth: the three most abundant EMIT minerals above 0.5%. These are rules of thumb, stated as such.
- `metadata.mineralogy` carries `scored: false`, the list of sources with their latitude range, variables, units and caveats; `metadata.datasets` and `metadata.citations` get the three sources.
- A source that is not given leaves the blocks the input already has, so the step runs in two passes.

App: `MineralogyPanel.tsx` shows both sides of the selected pair with labels and units taken from the export, the caveats under "How reliable is this?", an info button with the four-part plain-language explanation, and the tag "Context, not scored". If the export has no EMIT block yet it says "Earth mineral data are not in this export yet" instead of claiming an analog is outside coverage.

## 3. What is done and what is left

| Part | Status |
| --- | --- |
| Moon targets (Kaguya) and Mars targets (TES) | Done with real data, in `app/public/data/analogs_universe.json` |
| Panel in the app | Done |
| Tests | 20 in `tests/test_minerals.py` and `tests/test_minerals_loaders.py`: grids, wrap-around, VICAR layout and truncation, GeoTIFF layout, scaling, EMIT netCDF names and fill, `_UQ_` skipping, corner versus centre coordinates, enrichment that keeps what it is not asked to touch |
| Earth analogs (EMIT) | **Ready, not run.** The EMIT file was already downloaded to Yuca by option B (`data/raw/earth/emit/l3asa/`); the job finds it |

**Run on Yuca** (Owen, in the OOD shell; about a minute):

```bash
cd /lustre/proyectos/p089/code && git pull && sbatch scripts/jobs/t18_minerals.slurm
```

The log prints which readers the environment has, the EMIT variables it found, how many Earth analogs have a value, and a short report. Then bring `runs/<job>/analogs_universe.json` into `app/public/data/` as for the earlier runs and commit it.

**Not verified yet.** The EMIT file was never opened on the laptop (it needs the login), so the variable names and the half-cell convention rest on the user guide. The reader logs what it finds and tries two backends (GDAL, then xarray); if both fail it prints both errors. If the corner detection looks wrong in the log, rerun with `--emit-corner yes` or `--emit-corner no`.

The real share of Earth analogs with an EMIT value comes out of that job. Until then, no EMIT coverage figure should be quoted.

## 4. Limits to state in the submission

- The maps are orbital estimates at 8 to 55 km per pixel, not lab analyses or outcrop mineralogy.
- The Moon and Mars lists are mafic rock-forming minerals; the Earth list is alteration and dust minerals. A mineral on one side and not the other is not a mismatch.
- No mineral map reaches the lunar poles, so the Artemis regions have no mineral card.
- It does not change the score.

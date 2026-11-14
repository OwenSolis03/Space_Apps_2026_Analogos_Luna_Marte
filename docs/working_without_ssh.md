# Working without SSH to Yuca (14–15 November)

The venue network (Tec de Monterrey, Campus Sonora Norte) blocks SSH, but **Open OnDemand (OOD) works**: it is Yuca's web portal and runs over HTTPS. That is how the team worked on 2026-11-13, and how it works during the hackathon. This document describes that workflow, the offline kit and the fallback plan. Written by Claude on 2026-11-13.

---

## 1. Workflow with Open OnDemand (MODE B)

Gemini works in the **local** clone on the laptop and has no access to Yuca. Owen is the bridge, through the browser.

```text
Gemini (laptop)  ──commit + push──►  GitHub  ──git pull──►  Yuca (OOD shell, Owen)
       ▲                                                         │
       └────────── Owen pastes the log or passes the file ◄──────┘
```

1. Gemini writes the code and runs the synthetic tests on the laptop.
2. Gemini commits, pushes to GitHub and gives Owen the exact Yuca commands, each in its own block.
3. Owen opens the Yuca shell (login node) in OOD and runs the commands.
4. Owen gives Gemini the result: the log text copied from the shell, or the file downloaded with the OOD file manager.
5. Gemini checks the log against the acceptance criteria and continues.

**Rules that do not change with OOD.** The OOD shell runs on the login node, so:

- Only short commands go there: `git pull`, `sbatch`, `squeue`, `sacct`, `tail` of logs and `ls`.
- Tests and all processing go through `sbatch`, exactly as over SSH.
- If OOD offers "Interactive Apps" or desktop sessions, do not use them to run the pipeline. Jobs go through `sbatch`, with their logs in `output/`.

**Useful OOD shortcuts:**

- **Read a log without copying it from the shell:** the file manager (Files) opens `/lustre/proyectos/p089/output/<log>` directly.
- **Download small outputs to the laptop:** use Files → Download, for example for `targets.json`, `analogs_universe.json`, the PNG maps and the kits in `/lustre/proyectos/p089/kit/`.
- **Uploading a file to Yuca:** avoid it. Code always arrives through `git pull`, so Yuca and GitHub never drift apart.

---

## 2. What lives where

| What | Where it lives | From the venue |
| --- | --- | --- |
| Code | GitHub, the local clone and the Yuca clone (`/lustre/proyectos/p089/code`) | Laptop → GitHub → `git pull` in OOD |
| Rasters (MOLA, THEMIS, LOLA, WAC, Copernicus 26,475 tiles, MODIS) | Yuca only (~80 GB) | Only used by Yuca jobs; never downloaded |
| Runs (`runs/<JOBID>/`) | Yuca | Viewed and downloaded through OOD. The T3 runs are also in the offline kit |
| Slurm jobs | Yuca | Submitted and monitored from the OOD shell |
| Claude Code memory | Yuca (`/lustre/home/owen/.claude/...`) | Claude on the laptop **does not have it**; the context is in `docs/` |

---

## 3. Checklist for the night of the 13th

1. **Repository up to date.** On the laptop, `git pull` in the local clone.
2. **Download the offline kit** (§4), through OOD or with `scp`. It lets Gemini test with real T3 data without waiting for Yuca.
3. **Local environment on the laptop**, so Gemini can run the tests:

   ```bash
   cd <local-clone> && python -m venv .venv && source .venv/bin/activate && pip install -r pipeline/requirements.txt
   ```

   ```bash
   pytest -q tests
   ```

   The tests are synthetic, so they must all pass on the laptop. The app needs Node 20 and `cd app && npm install`.
4. **Check that OOD is reachable** from a network other than home, if possible (for example, phone data). That rules out OOD also being blocked elsewhere.

---

## 4. Offline kit

Already built on Yuca:

| Property | Value |
| --- | --- |
| File | `/lustre/proyectos/p089/kit/offline_kit_2026-11-13.tar.gz` |
| Size | 88 MB |
| sha256 (prefix) | `54cb3c5c0403a2dd` |

| Path inside the kit | What it is |
| --- | --- |
| `runs/2242278/features_mars.parquet` | T3: 140,916 Mars patches (features and THEMIS) |
| `runs/2242278/features_moon.parquet` | T3: 36,741 Moon patches (features, WAC, ice and Diviner) |
| `runs/2242278/map_*_mean_slope_deg.png` | T3 control maps |
| `data/raw/nomenclature/{MARS,MOON}_nomenclature_center_pts.*` | IAU gazetteer (`.shp`, `.dbf`, …) |
| `data/raw/earth/naturalearth/ne_10m_{roads,airports,admin_0_countries}.zip` | Logistics and countries (T6 and T8) |
| `data/derived/diviner_prp_south.parquet` | Diviner PRP south cache |

The kit does not include MODIS (2 GB) or any raster.

**Download:** in OOD, open Files, go to `/lustre/proyectos/p089/kit/` and use Download. With SSH, `scp owen@<yuca-host>:/lustre/proyectos/p089/kit/offline_kit_2026-11-13.tar.gz .` also works. Then:

```bash
mkdir -p ~/p089_offline && tar -xzf offline_kit_2026-11-13.tar.gz -C ~/p089_offline
```

`~/p089_offline` mirrors the layout of `/lustre/proyectos/p089`, and the pipeline scripts accept `--project-dir`. For example, the T4 clusters run on the laptop with:

```bash
python -m pipeline.targets --project-dir ~/p089_offline --t3-dir ~/p089_offline/runs/2242278 --out-dir ~/p089_offline/runs/local_t4 --skip-curated
```

Curated targets **cannot** be computed on the laptop, because they need the rasters; that part runs on Yuca.

**New kits.** When a run produces something Gemini needs locally, for example the T5 output to develop T7, pack it in the OOD shell and download it through Files:

```bash
cd /lustre/proyectos/p089 && tar -czf kit/t5_<PREP>.tar.gz runs/<PREP>/features_earth.parquet runs/<PREP>/prefilter_stats.json runs/<PREP>/t5_checks.json runs/<PREP>/map_earth_*.png
```

Already packed for T5 (`runs/2242438/`, 40,244 valid Earth patches):

| Property | Value |
| --- | --- |
| File | `/lustre/proyectos/p089/kit/t5_2242438.tar.gz` |
| Size | 3.7 MB |
| sha256 (prefix) | `8396d59ab029c2da` (`8396d59ab029c2dab1059326791f84f86c46f97fa23eb917a6a08ee934e0b76f`) |
| Contents | `runs/2242438/features_earth.parquet`, `prefilter_stats.json`, `t5_checks.json`, `map_earth_*.png` |

A `tar` of a few MB takes seconds and is allowed on the login node. Anything over 1 GB goes in a job.

---

## 5. What can move forward, and where

| Task | On the laptop (Gemini) | On Yuca (Owen through OOD) |
| --- | --- | --- |
| T5 | Done | Done (`runs/2242438/`, kit `t5_2242438.tar.gz`) |
| T7 and T8 | Code and tests; develop with the T5 smoke output or `t5_2242438.tar.gz` | Smoke test and real run; download `analogs_universe.json` through OOD |
| T10 app | Complete, with `sample.json` and then the real JSON | — |
| T11 content | Complete | — |
| Code in English | Complete | Run the tests in a job |

**Rule for Gemini in MODE B:** every pending Yuca command goes into the "Queue of pending cluster commands" in [handoff.md](handoff.md#queue-of-pending-cluster-commands), even if it will be run through OOD. That way Owen has a single list.

---

## 6. If OOD does not work either

In this order:

1. **Phone hotspot.** Mobile data usually allows both SSH and OOD. To test SSH, run `ssh -o ConnectTimeout=8 owen@<yuca-host> hostname`. If it answers `login-01`, switch back to MODE A.
2. **Ask the venue** (participants' WhatsApp group) whether another network without the block exists.
3. **Another team member** with a `p089` account (`aborquez` or `javier`), on a network without the block, following the queue.

Do not try tunnels, proxies or anything that bypasses the institution's network block.

---

## 7. If there is no access to Yuca at all

This is the plan B of [implementation_plan.md](implementation_plan.md) §6 and [submission.md](submission.md) §4. The app works on its own with `app/public/data/sample.json`, which is v1 converted to the v2 schema. In the presentation:

- say it is the v1 result, and show the v2 methodology with its tests;
- show the T3 run (maps in the kit) and the T4 targets;
- **do not** claim v2 results that were not run (see "what we must not claim" in [value_proposition.md](value_proposition.md)).

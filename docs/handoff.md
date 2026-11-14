# Handoff de progreso v2 — Planetary Analog Finder (NASA Space Apps 2026)

Documento de continuidad para retomar el desarrollo directamente por SSH en Yuca (`/lustre/proyectos/p089/code`, rama `main`).

- **Último commit previo en `main`:** `57f4f36` (`2026-11-13`)
- **Especificación fuente de verdad:** `docs/implementation_plan.md`
- **Estado de datos y corridas en Yuca:** `docs/pipeline.md` y `docs/logbook.md`
- **Instrucciones operativas de trabajo y SLURM:** `docs/gemini_prompt.md` (MODO A con SSH / MODO B sin SSH)
- **Plan detallado de la siguiente tarea:** `docs/plan_t4.md`
- **Entrega y cronograma real (NASA Space Apps Sonora, Tec de Monterrey):** `docs/submission.md`
- **Sin SSH (sede del hackathon, 14 y 15 de noviembre):** `docs/working_without_ssh.md`. Yuca sigue accesible por Open OnDemand (HTTPS): Gemini trabaja en local, Owen hace `git pull` y `sbatch` en la terminal de OOD y le pasa los logs

---

## 1. Resumen de estado por tarea

| Tarea | Archivo(s) principal(es) | Estado | Verificación / Evidencia |
| --- | --- | --- | --- |
| **T0** | `run_download_missing.slurm`, `run_download_extra.slurm`, `jobs/download_diviner.slurm` | **Hecho** | MOLA, THEMIS Day/Night, LOLA, LROC WAC, IceFavorability, Diviner PRP verificados en Yuca. Copernicus GLO-90 completo: **26,475 tiles** (todos `.tif`, sin `.aria2`) y `copernicus_90m_fallidos_2242198.txt` vacío (revisado por Claude el 2026-11-13). Natural Earth incluye `ne_10m_admin_0_countries` |
| **T1** | `pipeline/config.py`, `pipeline/geo.py`, `tests/test_geo.py` | **Hecho** (`ac743ce`, ajustes en `920f812`, `bcf10de`) | `extract_patch()` AEQD 64×64 a 500 m/px con `scales`/`offsets` aplicados en `_clean_nodata` antes de reproyectar; 7 tests en `tests/test_geo.py` |
| **T2** | `pipeline/features.py`, `tests/test_features.py` | **Hecho** (`a661bb7`, ajuste `np.gradient` en `920f812`) | `compute_features()` (alias `extract_features`) calcula los 7 rasgos en `float32`; 4 tests en `tests/test_features.py` |
| **T3** | `pipeline/planet_features.py`, `jobs/t3_planet_features.slurm`, `tests/test_planet_features.py` | **Hecho y ejecutado en Yuca** (`19e3899` .. `57f4f36`) | Barrido global `0-15` + `--merge` (jobs `2242278` / `2242279`): Marte `140,916` parches y Luna `36,741` parches; 6 tests en `tests/test_planet_features.py`. Criterio visual cumplido (revisado por Claude): Valles Marineris, Olympus Mons y Tharsis, Hellas y Argyre en Marte; mares lisos frente a tierras altas, Crisium y Orientale en la Luna |
| **T9** | `tests/` (31 pruebas unitarias sintéticas) | **Parcial (T1–T4 cubiertos)** | Yuca (job `2242421`, env `spaceapps_2026`): **`31 passed` in 3.76s** |
| **T10** | `app/`, `tools/v1_to_sample.py` | En curso en paralelo (`9325dea`, PR #2) | Primer esqueleto React + Vite + Tailwind en `main` con `app/public/data/sample.json` |
| **T4** | `pipeline/targets.py`, `pipeline/iau.py`, `pipeline/data/targets.json`, `jobs/t4_targets.slurm`, `tests/test_targets.py`, `tests/test_iau.py` | **Hecho y ejecutado en Yuca** | Job `2242423` (`/lustre/proyectos/p089/runs/2242423/`): `76` blancos (`16` curados `8/8` Luna + `8/8` Marte y `60` clusters), soporte polar T4.0 en `geo.py` y `PointSampler` en `planet_features.py` |
| **T6** | `pipeline/earth_layers.py`, `pipeline/data/known_analogs.json`, `jobs/t6_earth_layers.slurm`, `tests/test_earth_layers.py` | **Hecho y ejecutado en Yuca** | Jobs `2242426` / `2242430` (`84888cd`): cachés `/lustre/proyectos/p089/data/derived/ndvi_max_2023.tif` (18 MB) y `lst_2023.tif` (56 MB), **`8/8` duros y `5/5` blandos** en `/lustre/proyectos/p089/runs/2242430/t6_checks.json`, `1,650,450` vértices de vías, 11 tests sintéticos (`42 passed` en `2242425`) |
| **T5** | `pipeline/earth_features.py`, `jobs/t5_earth_features.slurm` | **Pendiente (siguiente tarea)** | Por implementar tras T6 según `docs/plan_t5.md` |
| **T7 / T8 / T11** | `pipeline/match.py`, `pipeline/export.py`, `jobs/t7_match.slurm`, `pipeline/data/limits.json` | Pendiente | Integración final hacia `app/public/data/analogs_universe.json` |

---

## 2. Qué ya está implementado en código (`main`)

### `pipeline/config.py`
- Constantes del parche: `PATCH_SIZE_KM = 32.0`, `PATCH_RES_M = 500.0`, `PATCH_PIXELS = 64`, `MIN_VALID_FRAC = 0.90`, `MAX_ABS_ELEV_M = 1e5`, `WINDOW_MARGIN_PX = 2`.
- Radios: `WGS84_SEMI_MAJOR_M = 6378137.0`, `BODY_RADII_M = {"Earth": 6371000.0, "Moon": 1737400.0, "Mars": 3396190.0}`.
- Nombres de rasgos: `FEATURE_NAMES = ["mean_slope_deg", "p90_slope_deg", "relief_m", "hypsometric_integral", "detrended_std_m", "tri_m", "mean_elev_m"]`.
- Rutas Yuca (`YUCA_PROJECT_DIR = Path("/lustre/proyectos/p089")`) y diccionarios `MARS_RAW_FILES`, `MOON_RAW_FILES`, `DIVINER_PARQUET_REL = "diviner_prp_south.parquet"`.

### `pipeline/geo.py`
- `extract_patch(src, lat, lon, body, size_km=32.0, res_m=500.0, resampling=Resampling.average) -> np.ndarray | None`
- `get_antimeridian_skipped_count()`, `reset_antimeridian_skipped_count()`.
- Aplica `PROJ_IGNORE_CELESTIAL_BODY=YES`, verifica radio del elipsoide/esfera vs cuerpo, detecta cruce del antimeridiano ±180°, reduce lectura con `out_shape` cuando `res_source_m <= res_m / 2` usando `out_dtype="float32"`, y en `_clean_nodata(...)`:
  1. Enmascara no-finitos y centinelas `|valor| > 1e5` (antes de `np.isclose`, evitando overflow en `float32` con `nodata=-3.4e38`).
  2. Enmascara `src.nodata` antes de escalar.
  3. Aplica `valor = crudo * src.scales[0] + src.offsets[0]` cuando difiere de `(1.0, 0.0)`.
  4. Reproyecta a AEQD local y devuelve `None` si `< 90 %` de píxeles son válidos.

### `pipeline/features.py`
- `compute_features(z, res_m=500.0) -> dict[str, np.float32]` (con alias `extract_features`).
- Rellena NaNs restantes con la mediana del parche y devuelve `mean_slope_deg`, `p90_slope_deg`, `relief_m`, `hypsometric_integral`, `detrended_std_m`, `tri_m`, `mean_elev_m` en `np.float32` usando `np.gradient(z_clean, res, res)`.

### `pipeline/planet_features.py` y `jobs/t3_planet_features.slurm`
- Grilla global casi equiareal (`generate_grid`, `-88°` a `88°`), partición en franjas (`select_stripe`), submuestreo (`apply_limit`), carga/caché única de Diviner PRP (`prepare_diviner_parquet`, `load_diviner_prp`) y consulta polar por parche con `cKDTree` en estereográfica sur (`-999` en `ice_depth` se convierte a `NaN`).
- Imprime al inicio `[META]` (`dtype`, `nodata`, `scales`, `offsets`, `res`) de cada raster usado (`DEM` y capas auxiliares).
- Provee `compute_lunar_wac_percentile(values, reference=None)` para transformar el brillo relativo de LROC WAC (`uint8`, `scale=1.00395, offset=-0.00395, nodata=0`) a percentil `[0, 1]` dentro de la distribución lunar.
- Refactorizado en T4 con `resolve_body_paths()` y `PointSampler` para muestrear parches puntuales con exactamente `_process_point` de T3.

### `pipeline/iau.py`, `pipeline/targets.py`, `pipeline/data/targets.json` y `jobs/t4_targets.slurm`
- `geo.py` incorpora soporte polar T4.0 (`_patch_contains_pole`) para parches que contienen un polo (usado por Shackleton a `-89.67°`).
- `iau.py`: lee el gacetero IAU con `geopandas`, convierte `center_lon` `0–360 -> -180..180` y `http -> https`, y expone `haversine_km`, `iau_label` y `find_feature`.
- `targets.json` + `targets.py`: 16 blancos curados (`8` Luna Artemis III + Shackleton, `8` Marte sitios de aterrizaje + Arcadia SWIM), muestreados promediando `point` (`5` parches, min `3`) o `rim` (`8` parches, min `5`) con `wac_percentile` e `ice_stable_frac`, más 30 clusters k-means por cuerpo (`log1p` + `StandardScaler`).

---

## 3. Salidas y hallazgos verificados en Yuca

### Corrida global T4 completada (`/lustre/proyectos/p089/runs/2242423/`)
Job `2242423` (32 s sobre `runs/2242278/`):
- **`/lustre/proyectos/p089/runs/2242423/targets.parquet`** y **`targets.json`**: **`76` blancos** (`16` curados `8/8 ok` en Luna y `8/8 ok` en Marte + `60` clusters que suman `140,916` en Marte y `36,741` en la Luna).
- **`/lustre/proyectos/p089/runs/2242423/targets_patches.parquet`**, **`clusters_mars.parquet`**, **`clusters_moon.parquet`**, **`map_targets_mars.png`** y **`map_targets_moon.png`**.

### Corrida global T3 completada (`/lustre/proyectos/p089/runs/2242278/`)
Jobs `2242278_0..15` (`--array=0-15`, 8 CPUs c/u) + `2242279` (`--merge`):
- **`/lustre/proyectos/p089/runs/2242278/features_mars.parquet`**: **`140,916`** parches válidos (de `141,472` candidatos, `99.61 %`; cumple criterio `~141k ± 10 %`). Columnas: `body, lat, lon, <7 rasgos T2>, themis_day, themis_night, themis_delta, valid_frac`.
- **`/lustre/proyectos/p089/runs/2242278/features_moon.parquet`**: **`36,741`** parches válidos (de `37,014` candidatos, `99.26 %`; cumple criterio `~37k ± 10 %`). Columnas: `body, lat, lon, <7 rasgos T2>, wac_reflectance, ice_favorability, diviner_tmax_k, diviner_tavg_k, ice_depth_m, valid_frac`.
- **Mapas scatter generados (inspección visual hecha, criterio cumplido):**
  - `/lustre/proyectos/p089/runs/2242278/map_mars_mean_slope_deg.png`
  - `/lustre/proyectos/p089/runs/2242278/map_moon_mean_slope_deg.png`
- **Caché Diviner PRP sur:** `/lustre/proyectos/p089/data/derived/diviner_prp_south.parquet` (`2,880,000` triángulos).

### Escalas de mosaicos y validación antes/después (`--limit 500`: `2242227` vs `2242231_0`)
Confirmado en `docs/pipeline.md` con `rasterio` sobre los archivos reales de Yuca:
- **Solo LOLA y WAC tienen escala != `(1.0, 0.0)`:**
  - `Lunar_LRO_LOLA_Global_LDEM_118m.tif`: `int16`, `scale=0.5`, `offset=0.0`, `nodata=-32768` (la v1 y el job `2242227` tenían todas las métricas lunares verticales al doble). Tras corregir `geo.py`, en `2242231_0` (`494/500` parches lunares): `mean_slope_deg` mediana bajó `13.24° -> 6.93°`, `relief_m` mediana `3229.80 -> 1614.90 m` (`0.50×`) y `mean_elev_m` mediana `-1424.61 -> -712.31 m` (`0.50×`).
  - `Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif`: `uint8`, `scale=1.00395256917`, `offset=-0.0039525691699605`, `nodata=0`. Entrega brillo relativo (`≈ 1–256`), no reflectancia absoluta; compararlo por percentil dentro de la Luna (`compute_lunar_wac_percentile`).
  - `Mars_ODY_THEMIS_IR_Day_Mosaic_100m.tif` y `Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif`: `uint8`, `scale=1.0`, `offset=0.0`, `nodata=0` (nivel de gris crudo, no kelvin).
  - `Moon_IceFavorabilityIndex_{90N,90S}000E_591mp.tif`: `float32`, `scale=1.0`, `offset=0.0`, `nodata=-3.4028226550889045e+38`.
  - `Mars_MGS_MOLA_DEM_mosaic_global_463m.tif`: `int16`, `scale=1.0`, `offset=0.0`, `nodata=-32768` (en `2242231_0`, `498/500` válidos, `mean_slope_deg` mediana `1.08°`).

---

## 4. Detalles operativos importantes en Yuca / Repo

1. **Pitfall de `sbatch --wrap` con `conda activate`:** el `--wrap` por defecto corre bajo `/bin/sh`, donde `conda activate spaceapps_2026` falla con exit code `2` por `_gdal-config` en `share/bash-completion/completions/gdalinfo`. Usar scripts `.slurm` con `#!/usr/bin/env bash` o envolver `--wrap 'bash -c "..."'`.
2. **No tocar archivos v1 ni archivo preexistente sin rastrear:**
   - Dejar intactos `process_analogs.py`, `match_earth_analogs.py`, `enrich_nomenclature.py` en la raíz.
   - Existe un archivo no rastreado preexistente `documentaci_n_t_cnica_del_pipeline_de_an_logos_planetarios.md`: **no** agregarlo ni borrarlo.
3. **Reglas del clúster:** cuenta `-A p089`, partición `-p cpu`, `--time`, `--mem`, logs en `/lustre/proyectos/p089/output/`, salidas nuevas en `/lustre/proyectos/p089/runs/$SLURM_JOB_ID/`, tope grupal `500 CPUs / 4 GPUs` (usar `%30` si un array con 16 CPUs supera 500 CPUs), nunca `rm -rf` (usar `_to_delete/`) ni desactivar TLS.

---

## 5. Siguientes pasos inmediatos al conectar la nueva sesión

1. ~~Inspeccionar descargas T0 y los PNG de T3~~: hecho el 2026-11-13 (ver tabla).
2. ~~**T4 (`pipeline/targets.py`, `pipeline/iau.py`, `pipeline/data/targets.json`, `jobs/t4_targets.slurm`, tests)**~~: hecho el 2026-11-13 (job `2242423`, `/lustre/proyectos/p089/runs/2242423/`).
3. ~~**T6 (`pipeline/earth_layers.py`, `pipeline/data/known_analogs.json`, `tests/test_earth_layers.py`)**~~: hecho el 2026-11-13 (jobs `2242426` / `2242430`, `/lustre/proyectos/p089/data/derived/{ndvi_max_2023,lst_2023}.tif`, `/lustre/proyectos/p089/runs/2242430/`).
4. **T5 (`pipeline/earth_features.py`, `jobs/t5_*.slurm`, `jobs/t5_submit.sh`):** VRT `copernicus_90m.vrt`, prefiltro `ndvi_max <= 0.25` (NaN pasa solo si LST finito), prueba `--limit 500` y array `--array=0-31%30`.
5. **T7 + T8 + T11 (`pipeline/match.py`, `pipeline/export.py`, `jobs/t7_match.slurm`, `pipeline/data/limits.json`, `tests/test_match.py`):** matching RBF + MSI + diversidad (> 150 km) + `mismatches` + `country` (`ne_10m_admin_0_countries`) sobre `runs/2242423/targets.parquet` y generación de `app/public/data/analogs_universe.json`.

---

## 6. Sesión del 2026-11-13 (noche, Claude por SSH en Yuca)

- Claude revisó toda la documentación, confirmó T0 (Copernicus completo) y el criterio visual de T3.
- Escribió [plan_t4.md](plan_t4.md):
  - NASA no publica coordenadas de las regiones Artemis III, así que se anclan en rasgos IAU;
  - soporte polar para Shackleton;
  - 8 blancos curados lunares y 8 marcianos con fuentes;
  - clusters, salidas, pruebas y comandos.
- Actualizó [gemini_prompt.md](gemini_prompt.md) para Gemini 4 Orchestrator (Argon) con MODO A (SSH) y MODO B (sin SSH).
- Escribió [working_without_ssh.md](working_without_ssh.md) y armó el kit offline `/lustre/proyectos/p089/kit/offline_kit_2026-11-13.tar.gz` (88 MB).
- Incidente sin daño: Claude importó `enrich_nomenclature.py` para revisar el gacetero. Como no tiene `if __name__ == "__main__"`, el script se ejecutó y reescribió `/lustre/proyectos/p089/output/planetary_baselines.json`. El resultado quedó byte a byte idéntico a `code/output/planetary_baselines.json`; solo cambió la fecha de modificación. Regla nueva: no importar los scripts v1.

---

## Cola para cuando haya SSH

Comandos de Yuca pendientes, en orden. Quien trabaje sin SSH (MODO B) agrega aquí lo que deja listo. Owen los corre de arriba hacia abajo, por SSH o en la terminal de Open OnDemand, revisa cada log contra el criterio indicado y tacha la línea.

| # | Comando (desde `/lustre/proyectos/p089/code`, tras `git pull`) | Revisar en el log |
| --- | --- | --- |
| 1 | ~~Pruebas: `sbatch ... pytest -q tests`~~ (job `2242421`) | `31 passed in 3.76s` |
| 2 | ~~Humo T4: `sbatch jobs/t4_targets.slurm --k 5 --body Moon`~~ (job `2242422`) | `8/8` lunares `ok`, `iau_nearest == iau_feature` |
| 3 | ~~T4 completo: `sbatch jobs/t4_targets.slurm`~~ (job `2242423`) | `76` blancos (`16` curados `ok` + `60` clusters) en `/lustre/proyectos/p089/runs/2242423/` |

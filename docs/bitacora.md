# Bitácora

Registro de lo que se hace en el proyecto, de lo más reciente a lo más antiguo. Sirve también para la descripción de uso de IA de la entrega.

## 2026-11-13 (noche): T6 — capas terrestres (NDVI, LST, logística, país y análogos conocidos)

**Qué se hizo (código escrito por Gemini a partir de `docs/plan_t6.md` de Claude)**

- **Configuración y dependencias (`pipeline/config.py`, `pipeline/requirements.txt`):** se agregaron `EARTH_RAW_FILES`, `EARTH_DERIVED_FILES` (`ndvi_max_2023.tif`, `lst_2023.tif`) y `MODIS_CMG_RES_DEG = 0.05`, más `pyhdf>=0.10` solo para la construcción de cachés en Yuca.
- **Regiones conocidas (`pipeline/data/known_analogs.json`):** 12 bboxes aproximados curados (`atacama`, `mcmurdo-dry-valleys`, `iceland`, `hawaii-big-island`, `devon-island`, `utah-mdrs`, `rio-tinto`, `svalbard`, `pilbara`, `meteor-crater`, `lanzarote`, `mojave`) validados al cargar (`id` único, bboxes válidos, `source_url` no vacío).
- **Módulo `pipeline/earth_layers.py` + `jobs/t6_earth_layers.slurm`:**
  - Funciones puras CMG 0.05° (`ndvi_from_raw` con `/ 10000.0`, fill `-3000`; `lst_c_from_raw` con `* 0.02 - 273.15`, fill `0`, `< 7500 -> NaN`), acumuladores anuales (`running_nanmax`, `running_sum_count`, `finalize_mean(..., min_count=3)`) y ventana de parche equiareal (`cell_index`, `patch_window_stat` con envoltura del antimeridiano).
  - Constructores de caché en Yuca (`build_ndvi_max`, `build_lst`, `ensure_cache`) usando `pyhdf` importado de forma diferida y escritura atómica (`.tmp.tif` + `os.replace`, sin sobrescribir archivos existentes).
  - Índices espaciales `Logistics` (`BallTree` haversine sobre `ne_10m_roads` densificada cada `0.02°` excluyendo `Ferry` = `1,650,450` vértices, y aeropuertos civiles excluyendo militares/spaceports), `Countries` (`within` + `sjoin_nearest` en `EPSG:4087` a `<= 25 km`), `KnownRegions` y fachada `EarthLayers` (~420 MB pensada para crearse una vez antes de `fork` en T5).
- **Pruebas unitarias (`tests/test_earth_layers.py`):** 11 pruebas sintéticas sin `pyhdf`.

**Verificación en Yuca (vía SLURM)**

- **Suite unitaria (`job 2242425`, `pytest -q tests`):** **`42 passed` in 3.79s** (31 previas + 11 de T6, 0 warnings del módulo T6).
- **Construcción de cachés y primera verificación (`job 2242426`, commit `29fbb88`):**
  - Generó `/lustre/proyectos/p089/data/derived/ndvi_max_2023.tif` (18 MB, 2 bandas `float32`, `3600×7200`, `EPSG:4326`) y `/lustre/proyectos/p089/data/derived/lst_2023.tif` (56 MB, 3 bandas `float32`, `3600×7200`, `EPSG:4326`).
  - Pasó `5/5` blandos y `6/8` duros; fallaron #2 (Egipto `(24.0, 28.0)` dio `0.1028` con confiabilidad `0` en los 12 meses) y #8 (fracción finita sin ponderar `0.2438`, porque MOD13C2 no trae datos al sur de `-59.45°S` y omite la Antártida).
  - Claude aprobó en `plan_t6.md` §6.2.1 ajustar `#2 < 0.12` y `#8` ponderado por `cos(lat) > 0.25`.
- **Re-verificación tras ajuste (`job 2242430`, commit `84888cd`, reutilizando las cachés existentes en `/lustre/proyectos/p089/runs/2242430/`):** **`8/8` duros, `5/5` blandos (PASS)** y 3 PNGs revisados visualmente (`map_ndvi_max.png`, `map_lst_amplitude.png`, `map_known_analogs.png` con los 12 bbox sobre sus regiones):

| # | Tipo | Verificación | Observado | Esperado | Estado |
| --- | --- | --- | --- | --- | --- |
| 1 | Duro | `cache_metadata` | `ndvi` 2 bandas, `lst` 3 bandas, `3600×7200`, `EPSG:4326` | `3600×7200 EPSG:4326` | PASS |
| 2 | Duro | `ndvi_sahara` | `dz=0.0919`, `eg=0.1028` | `< 0.12` en ambos | PASS |
| 3 | Duro | `ndvi_atacama` | `0.0760` | `< 0.10` | PASS |
| 4 | Duro | `ndvi_tropical_forests` | `amazonia=0.8684`, `congo=0.8650` | `> 0.70` en ambos | PASS |
| 5 | Duro | `dist_road_hermosillo` | `0.596 km` | `< 5 km` | PASS |
| 6 | Duro | `countries_lookup` | `Mexico` / `Chile` / `Algeria` | `Mexico` / `Chile` / `Algeria` | PASS |
| 7 | Duro | `known_region_lookup` | `utah-mdrs` / `None` | `utah-mdrs` / `None` | PASS |
| 8 | Duro | `ndvi_finite_land_frac` | `cos_weighted=0.2696` (`unweighted=0.2438`) | `> 0.25 (ponderado por cos(lat))` | PASS |
| 9 | Blando | `lst_day_dry_valleys` | `-28.18 °C` | `< 0 °C` | PASS |
| 10 | Blando | `lst_amp_sahara_vs_amazonia` | Sahara `21.30 °C` vs Amazonía `4.16 °C` | Sahara `> 15 °C` y `>` Amazonía | PASS |
| 11 | Blando | `dist_road_dry_valleys` | `3447.74 km` | `> 1000 km` | PASS |
| 12 | Blando | `ndvi_prefilter_pass_frac` | `grid=0.0543` (`land=0.2228`) | Informativo | PASS |
| 13 | Blando | `sample_10k_runtime_s` | `1.216 s` | `< 30 s` | PASS |

**Qué falta**

- **T5 (`pipeline/earth_features.py`)**, **T7 (`pipeline/match.py`)**, **T8 (`pipeline/export.py`)** y **T11 (`pipeline/data/limits.json`)**.

## 2026-11-13 (noche): sede real y reglas de entrega

- El equipo está inscrito en **NASA Space Apps Sonora 2026** (Tec de Monterrey, Campus Sonora Norte), no en la sede de la UTH que aparecía en el README.
- Claude revisó [spaceappssonora.org](https://spaceappssonora.org/) y su [guía de pitches](https://spaceappssonora.org/pitches):
  - hackathon el sábado 14 de 9:00 a 21:00; pitches el domingo 15 de 9:00 a 14:00;
  - pitch de 3 minutos en Canva, con el número de equipo en la primera lámina;
  - documentación y video de 30 s en inglés;
  - app publicada;
  - criterios de evaluación: innovación, impacto social, documentación y escalabilidad.
- Se actualizó el README (sede, horario y reglas) y se creó [entrega.md](entrega.md) con la lista de entregables, el cronograma ajustado a un solo día útil, el checklist y el plan B. Se marcó como reemplazado el cronograma de 48 horas de `plan_implementacion.md`.
- La sede dio permiso al equipo de empezar a trabajar desde el 13 de noviembre. Con eso queda resuelto el pendiente de la entrada "revisión del prototipo y repositorio", que preguntaba si las corridas previas contaban como trabajo previo.

## 2026-11-13: T4 — blancos curados, soporte polar T4.0 y clusters globales

**Qué se hizo (código escrito por Gemini a partir de `docs/plan_t4.md` de Claude)**

- **T4.0 (`pipeline/geo.py`, `tests/test_geo.py`):** se agregó `_patch_contains_pole()` y la rama polar en `extract_patch()` para leer una banda de latitud completa cuando un parche contiene el polo (`lat = -89.67°` en Shackleton), sin tocar el flujo fuera de los polos ni el conteo del antimeridiano (`|lat| <= 88°` en T3 no cambia).
- **Refactor de muestreo (`pipeline/planet_features.py`):** se extrajo `resolve_body_paths()` y se creó `PointSampler` para muestrear parches puntuales reutilizando exactamente `_process_point()` de T3.
- **Nomenclatura IAU (`pipeline/iau.py`, `tests/test_iau.py`):** módulo limpio sin efectos secundarios al importar; carga `MARS_nomenclature_center_pts.shp` / `MOON_nomenclature_center_pts.shp` con `geopandas`, normaliza `center_lon` (`0–360 -> -180..180`) y enlaces `https://`, e implementa `haversine_km`, `iau_label` y `find_feature`.
- **Blancos curados y clusters (`pipeline/data/targets.json`, `pipeline/targets.py`, `jobs/t4_targets.slurm`, `tests/test_targets.py`):**
  - `targets.json` con **16 blancos curados**: 8 lunares (7 regiones Artemis III ancladas a sus rasgos IAU por no existir centros oficiales publicados + borde de Shackleton, usando anclas `point` de 5 parches y `rim` de 8 parches) y 8 marcianos (Jezero, Gale, Gusev, Meridiani Planum, Utopia Planitia, Elysium/InSight, Oxia Planum y Arcadia Planitia SWIM).
  - Cálculo de `wac_percentile` por parche frente a `runs/2242278/features_moon.parquet` y `ice_stable_frac` en Diviner antes de promediar.
  - Clustering k-means (`k = 30`, `seed = 42`, `log1p` en `relief_m`, `detrended_std_m`, `tri_m` + `StandardScaler` por cuerpo) sobre `runs/2242278/features_{mars,moon}.parquet`, tomando el parche real más cercano a cada centroide y nombrándolo con `iau_label`.

**Verificación en Yuca (vía SLURM)**

- **Suite unitaria (job `2242421`, `pytest -q tests`):** **`31 passed` in 3.76s** (17 previas + 3 en `test_geo.py` + 3 en `test_iau.py` + 8 en `test_targets.py`).
- **Prueba de humo lunar (job `2242422`, `jobs/t4_targets.slurm --k 5 --body Moon`, 17 s):** `8/8` curados lunares `ok` (incluido Shackleton) y 5 clusters.
- **Corrida completa T4 (job `2242423`, `jobs/t4_targets.slurm`, 32 s, salidas en `/lustre/proyectos/p089/runs/2242423/`):**
  - Total: **`76` blancos** (`16` curados + `60` clusters) en `targets.parquet` y `targets.json`, más `targets_patches.parquet`, `clusters_{mars,moon}.parquet`, `map_targets_mars.png` y `map_targets_moon.png`. Ningún curado quedó fuera (`0 insufficient_coverage`).
  - **Luna (`8/8 ok`):** todos los anclas coinciden exactamente con su `anchor.iau_feature` (`d = 0.0 km`), tienen `diviner_tavg_k` (`64.9–133.3 K`), `ice_favorability`, `ice_depth_m` (`ice_stable_frac = 1.0`) y `wac_percentile` finitos; `moon-shackleton-rim` completó `8/8` parches (`mean_slope = 14.27°`, `relief = 3616 m`). Los 30 clusters suman `36,741` parches (`min/mediana/max = 518/1040/2332`).
  - **Marte (`8/8 ok`):** todos con `5/5` parches y `themis_day`, `themis_night`, `themis_delta` finitos. Los 30 clusters suman `140,916` parches (`min/mediana/max = 494/4715/8933`).
- **Revisión de sentido común (`plan_t4.md` §10):**
  - En **Marte** (mediana global `mean_slope_deg = 1.16°`), las 5 planicies de aterrizaje quedan muy por debajo de la mediana global: InSight es el #1 más plano (`0.25°`, `relief = 71.6 m`), seguido de Arcadia SWIM (`0.30°`, `39.1 m`), Zhurong/Utopia (`0.42°`, `126.9 m`), Spirit/Gusev (`0.49°`, `80.4 m`) y Opportunity/Meridiani (`0.54°`, `132.5 m`; top-3 absoluto es InSight, Arcadia SWIM, Zhurong, con Opportunity #5 dentro del bloque plano `< 0.55°` porque sus vecinos a 16 km tocan bordes de cráteres cercanos como Victoria). Gale tiene `relief_m = 2793.1 m` frente a `71.6 m` de InSight (`~39×`).
  - En la **Luna** (mediana global `mean_slope_deg = 6.78°`), los 8 curados polares están entre `8.09°` (Mons Mouton) y `14.27°` (Shackleton rim), todos por encima de la mediana global lunar.
  - En los PNG (`map_targets_mars.png`, `map_targets_moon.png`), los curados caen en sus regiones esperadas y Tharsis/Valles Marineris se separan de las llanuras del norte.

**Qué falta**

- **T6 (`pipeline/earth_layers.py`, `pipeline/data/known_analogs.json`)**, **T5 (`pipeline/earth_features.py`)**, **T7 (`pipeline/match.py`)**, **T8 (`pipeline/export.py`)** y **T11 (`pipeline/data/limits.json`)**.

## 2026-11-13 (noche): plan de T4, prompt para Gemini 4 y operación sin SSH

**Qué se hizo (documentos escritos por Claude, en sesión directa en Yuca)**

- Se revisó el estado real en Yuca:
  - Copernicus GLO-90 está completo: 26,475 tiles y la lista de fallidos del job 2242198 está vacía.
  - Los mapas de T3 (`runs/2242278/`) cumplen el criterio visual: Valles Marineris, Olympus Mons, Hellas y Argyre en Marte; mares frente a tierras altas, Crisium y Orientale en la Luna.
- [plan_t4.md](plan_t4.md): especificación completa de T4.
  - NASA solo publica los nombres de las 9 regiones de Artemis III, sin coordenadas, así que se anclan en el rasgo IAU del mismo nombre. Las regiones de borde se miden con 8 parches sobre el borde del cráter.
  - Nobile Rim 1 y 2 se fusionan en un blanco, y también Mons Mouton y su meseta.
  - Coordenadas de aterrizaje verificadas para 8 sitios en Marte; quedan `TODO(verificar)` en Spirit, Oxia y Arcadia.
  - Se agrega soporte de parches que contienen el polo (Shackleton) sin cambiar T3.
  - Clusters k-means (30 por cuerpo) sobre los rasgos de T3.
- [prompt_gemini.md](prompt_gemini.md) se reescribió para Gemini 4 en modo Orchestrator (Argon) de Antigravity, que ya tiene acceso a Yuca. Tiene MODO A (con SSH) y MODO B (sin SSH), y reglas reforzadas: nada de `pytest` en el login y no importar los scripts v1.
- [operacion_sin_ssh.md](operacion_sin_ssh.md): la red de la sede bloquea SSH el 14 y 15 de noviembre, pero Open OnDemand (HTTPS) sí funciona; así se trabajó el 13. El documento cubre el flujo con OOD (Gemini en local, push a GitHub, Owen corre `git pull`/`sbatch` en la terminal de OOD y le pasa los logs), la lista para esta noche, el kit offline, qué avanzar en cada lado y el plan B.
  - El kit offline (`/lustre/proyectos/p089/kit/offline_kit_2026-11-13.tar.gz`, 88 MB) tiene los parquet de T3, el gacetero IAU, Natural Earth y la caché de Diviner.
- [progreso_handoff.md](progreso_handoff.md) se actualizó y ahora incluye la "Cola para cuando haya SSH".
- Incidente sin daño: al revisar el gacetero, Claude importó `enrich_nomenclature.py`, que se ejecutó y reescribió `/lustre/proyectos/p089/output/planetary_baselines.json`. El contenido quedó idéntico a la copia del repo.

**Qué falta**

- Que Gemini implemente T4 con `plan_t4.md` y correrlo en Yuca, de ser posible esta misma noche.
- Bajar el kit offline a la laptop y preparar el entorno local para las pruebas.
- Planes detallados de T6, T5 y T7/T8 (Claude).

## 2026-11-13: T10, primer esqueleto de la app (branch `feat/app-t10-esqueleto`)

**Qué se hizo (código escrito por Claude, a partir del mockup publicado como artefacto)**

- `app/`: React 18 + Vite 5 + TypeScript + Tailwind 4. Interfaz en inglés. Secciones: selector Marte / Luna, tesis con cifras, explorador (presets de misión, sliders de pesos, MSI mínimo, mapas dobles, ranking), ficha del sitio (tabla blanco contra Tierra con coincide / no coincide, radar de 4 dimensiones, uso sugerido, "Where the analogy breaks") y metodología con las fuentes.
- El MSI se recalcula en el navegador con `MSI = Σ w·S / Σ w`, solo sobre las dimensiones que tienen `sub_score` (`app/src/lib/msi.ts`). Ambiente y térmico aparecen deshabilitados con la tarea que los trae (T5/T6, T7).
- Mapas: Leaflet para los tres cuerpos (Marte con MOLA de Trek, la Luna con LROC WAC de Trek, ambos en EPSG:4326; la Tierra con Blue Marble de GIBS en Web Mercator). El plan pedía MapLibre para la Tierra; se dejó Leaflet para tener una sola librería en el esqueleto. Radar dibujado en SVG propio en lugar de Recharts por la misma razón.
- `tools/v1_to_sample.py` convierte `output/analogs.json` (v1) al esquema v2 de la sección 5 y escribe `app/public/data/sample.json` (80 blancos, 400 análogos, 260 KB). Los `sub_scores` son provisionales: kernel RBF por rasgo con σ = 35 % del valor del blanco y un mínimo absoluto (1.5° y 2.5° para pendientes, 30 m y 25 m para σ de elevación y TRI). `mismatches` marca los rasgos a más de 1.5 σ (desviación del conjunto por cuerpo): 67 de 400 análogos tienen al menos uno. Presets y límites físicos van con texto en inglés provisional; T11 los reemplaza.
- Diseño con los tokens en `app/src/index.css` (una capa de variables CSS, tema claro y oscuro por `prefers-color-scheme`, acento óxido para Marte y gris azulado para la Luna).
- Verificado: `npm run build` sin errores; en el navegador cargan los tiles de Trek y GIBS sin errores de consola, el preset, el cambio de cuerpo y la selección de blanco y análogo actualizan ranking, mapas y ficha; sin scroll horizontal a 320 y 414 px. Gates del kit de diseño: sin emoji, sin valores fijos, sin `<select>` nativo. Contraste AA medido en los pares de tokens de ambos temas; `--faint` claro se oscureció a `#5c6370` porque fallaba sobre `--surface-2`. Los gates de render del kit no se corrieron porque esperan un HTML suelto y la app necesita servidor para leer el JSON.
- `.claude/launch.json` con la configuración `app` (puerto 5173) para levantarla desde Claude Code.

**Qué falta**

- Conectar `analogs_universe.json` real cuando exista T8 (basta con cambiar `DATA_URL` en `app/src/App.tsx`).
- Vista "Compare" de dos sitios, exportar ficha (JSON / Markdown) y vista de impresión.
- Filtro "solo nuevos candidatos" y prioridad logística (λ) cuando T6 traiga `dist_road_km`.
- Aviso y vista polar para el polo sur lunar (la proyección equirectangular deforma mucho).
- Medir el criterio de aceptación de 50 ms al mover un slider y revisar la app en 1366 × 768 y en el proyector.

Para correrla: `cd app && npm install && npm run dev`.

## 2026-11-13: T1/T3 — aplicación de `scales`/`offsets` en `geo.py`, WAC por percentil lunar y metadatos de rasters

**Qué se hizo (código escrito por Gemini)**

- Se registró la corrida de prueba `--limit 500` de T3 en Yuca (job `2242227`, 1 min 18 s): Marte `498/500` válidos (`mean_slope_deg` mediana `1.08°`, p95 `4.63°`, máx `17.15°`), Diviner PRP cacheado (`2,880,000` triángulos en `data/derived/diviner_prp_south.parquet`) y Luna `494/500` válidos (`mean_slope_deg` mediana `13.24°`, p95 `21.50°`, máx `27.68°`).
- **Confirmación en Yuca sobre LOLA y tabla completa de escalas (`docs/pipeline.md`):**
  - `Lunar_LRO_LOLA_Global_LDEM_118m.tif` es `int16` con `scales=(0.5,)`, `offsets=(0.0,)` y `nodata=-32768`. Por no aplicar `scale=0.5`, tanto la **v1** como la primera prueba `2242227` tenían todas las métricas verticales lunares (`mean_elev_m`, `relief_m`, `roughness_std_m`, `tri` y `tan(slope)`) **al doble** de su valor real. (Se retira la nota previa sobre el rango de elevaciones de la v1).
  - Entre todos los mosaicos revisados en Yuca, únicamente LOLA (`scale=0.5`, `offset=0.0`) y LROC WAC (`uint8`, `scale=1.00395`, `offset=-0.00395`, `nodata=0`) tienen escala distinta de `(1.0, 0.0)`.
  - Además, WAC entrega brillo relativo (`≈ 1–256`), no reflectancia física absoluta, por lo que debe compararse por percentil dentro de la propia Luna; `Moon_IceFavorabilityIndex_{90N,90S}000E_591mp.tif` es `float32` con `nodata=-3.4e38`.
- Se actualizó `pipeline/geo.py` (`extract_patch` y `_clean_nodata`): lectura con `out_dtype="float32"` (incluyendo la rama `out_shape`), filtrado previo de no-finitos y centinelas `|z| > 1e5` (para evitar overflow de `float32` con `nodata=-3.4e38`), enmascarado de `src.nodata` y aplicación de `src.scales[0]` / `src.offsets[0]` antes de reproyectar.
- En `pipeline/features.py` se dejó explícito `np.gradient(z_clean, res, res)` para ambos ejes.
- En `pipeline/planet_features.py` se agregó `_log_raster_meta` para imprimir al inicio `dtype`, `nodata`, `scales`, `offsets` y `res` de cada raster usado (`DEM`, `themis_day`, `themis_night`, `wac_reflectance`, `ice_south`, `ice_north`), el resumen (`min`, `mediana`, `p95`, `max`) de `mean_slope_deg`, `relief_m`, `mean_elev_m` y `wac_reflectance`, y la función `compute_lunar_wac_percentile` para transformar el brillo WAC a percentil `[0, 1]` dentro de la Luna.
- En `tests/test_geo.py` y `tests/test_planet_features.py` se añadieron pruebas para `int16` escalado (`scale=0.5`, `offset=100.0`, `nodata=-32768`), `uint8` WAC escalado a `100 m/px`, filtrado de `nodata=-3.4e38` sin warnings y `compute_lunar_wac_percentile`.
- **Verificación en Yuca (commit `bcf10de`):**
  - Suite `pytest -q tests` (`tests_v2`): **`17 passed` in 3.30s** en `spaceapps_2026`.
  - Prueba `--limit 500` **DESPUÉS** del arreglo (job `2242231_0`, 22 s en `amdcpu-hpc-23`), comparada frente al job `2242227` (ANTES, mismo conjunto de `494/500` parches lunares válidos):
    - `mean_slope_deg` (Luna): min `0.33° -> 0.17°`, mediana `13.24° -> 6.93°`, p95 `21.50° -> 11.51°`, máx `27.68° -> 16.04°`.
    - `relief_m` (Luna): min `67.92 -> 33.96 m`, mediana `3229.80 -> 1614.90 m`, p95 `7460.09 -> 3730.05 m`, máx `11210.04 -> 5605.02 m` (exactamente a la mitad).
    - `mean_elev_m` (Luna): min `-10630.40 -> -5315.20 m`, mediana `-1424.61 -> -712.31 m`, p95 `8225.56 -> 4112.78 m`, máx `14751.13 -> 7375.57 m` (exactamente a la mitad y ya dentro del rango físico lunar `-9.1` a `+10.8 km`).
    - `wac_reflectance` (Luna, brillo relativo `uint8` con `scale=1.00395, offset=-0.00395, nodata=0`): min `1.00`, mediana `67.26`, p95 `93.85`, máx `136.71` (`n=494`).
    - `ice_south` / `ice_north` (`float32`, `nodata=-3.4028226550889045e+38`): leídos sin warnings y `Diviner polar` con 5 parches de cobertura en la muestra `--limit 500`.
    - Marte en `2242231_0` (`498/500` válidos, `scale=1.0`): `mean_slope_deg` min `0.04°`, mediana `1.08°`, p95 `4.63°`, máx `17.15°`; `relief_m` min `6.04 m`, mediana `239.32 m`, p95 `1476.28 m`, máx `5310.49 m`; `mean_elev_m` min `-6864.79 m`, mediana `-282.06 m`, p95 `4256.35 m`, máx `9031.45 m`.
  - **Corrida global completa de T3 (jobs `2242278` `0..15` + merge `2242279`):**
    - Marte: 16 franjas -> **`140,916` parches válidos** (de `141,472`, `99.61 %`; cumple `~141k ± 10 %`) en `/lustre/proyectos/p089/runs/2242278/features_mars.parquet` y mapa `/lustre/proyectos/p089/runs/2242278/map_mars_mean_slope_deg.png`.
    - Luna: 16 franjas -> **`36,741` parches válidos** (de `37,014`, `99.26 %`; cumple `~37k ± 10 %`) en `/lustre/proyectos/p089/runs/2242278/features_moon.parquet` y mapa `/lustre/proyectos/p089/runs/2242278/map_moon_mean_slope_deg.png`.

**Qué falta**

- Inspección visual rápida de los mapas `map_mars_mean_slope_deg.png` y `map_moon_mean_slope_deg.png` de `runs/2242278/` (Valles Marineris / Olympus Mons en Marte; tierras altas frente a mares en la Luna).
- Implementar **T4** (`pipeline/targets.py` + `pipeline/data/targets.json` + tests): blancos curados (Artemis III + Shackleton, sitios de aterrizaje en Marte con coordenadas verificadas) y 30 clusters por cuerpo sobre los parquet de T3 (`2242278`), luego T6, T5, T7 y T8.

## 2026-11-13: T3 — barrido global de Marte y la Luna (pipeline/planet_features.py)

**Qué se hizo (código escrito por Gemini)**

- Se verificó la suite T1+T2 en Yuca (job `2242225`, entorno `spaceapps_2026`: `9 passed in 1.16s`).
- Se actualizó `pipeline/config.py` y `pipeline/requirements.txt` (`matplotlib>=3.7` y rutas de rasters planetarios y Diviner PRP).
- Se implementó `pipeline/planet_features.py` y `jobs/t3_planet_features.slurm`: grilla global de `32 km` (`-88°` a `88°`, ~141k centros en Marte y ~37k en la Luna), extracción paralela por franjas (`--array=0-15`, `8 CPUs`), muestreo de capas auxiliares (`themis_day`, `themis_night`, `themis_delta` en Marte; `wac_reflectance`, `ice_favorability` polar y lectura/caché de `dlre_prp_south.tab` a `data/derived/diviner_prp_south.parquet` con consulta `cKDTree` en parches polares para `diviner_tmax_k`, `diviner_tavg_k`, `ice_depth_m` ignorando `-999`), opción `--limit` para pruebas y `--merge` para combinar franjas y generar mapas scatter PNG de `mean_slope_deg`.
- Se añadieron pruebas unitarias sintéticas en `tests/test_planet_features.py` (`14 passed` en total localmente).

**Qué falta**

- Correr T3 en Yuca primero en modo prueba (`--limit 500`), revisar el log y el PNG, y después lanzar el job array completo (`0-15`) + `--merge`.
- Continuar con T4 (`pipeline/targets.py` + `pipeline/data/targets.json`) y T5–T11.

## 2026-11-13: descarga de Diviner

- Se encontró el Diviner Polar Resource Product en el paquete PDS4 `lro_diviner_derived1`, colección `data_derived_prp` (Yuca sí llega a PDS Geosciences; la laptop no).
- Nuevo `jobs/download_diviner.slurm`: baja `dlre_prp_south.tab` (604800210 bytes), `.lbl` y `.xml` a `data/raw/moon/diviner/`. El polo norte (mismo tamaño) no se baja porque los blancos están en el sur.
- Descargado y verificado en Yuca: `.tab` de 604800210 bytes exactos, sin `.aria2`. Se envió dos veces por error, pero el segundo job (2242221) solo encontró los archivos ya completos.
- Formato real (CSV con encabezado): `tri1_x..tri3_z` (vértices de la malla, en km), `tri_clon`, `tri_clat` (centro del triángulo, grados), `tri_calt`, `temp_avg` y `temp_max` (K), `ice_depth` (m; `-999` = sin hielo estable). La malla es un cuadrado centrado en el polo, así que en las esquinas llega hasta ~75.9°S.

## 2026-11-13: explorador de datasets

- Claude escribió `tools/explore_datasets.py` y `jobs/explore_datasets.slurm`: un reporte HTML autocontenido con miniatura, metadatos (CRS, resolución, nodata, radio del cuerpo), estadísticas, histograma y valores en sitios conocidos de cada raster; cobertura y validación de los tiles de Copernicus (abre cada tile); mapas de NDVI y temperatura de MODIS; carreteras, aeropuertos y países; nomenclatura IAU. También escribe `resumen.md` y `resumen.json`.
- Solo depende de numpy, rasterio y pyproj (las imágenes se generan sin matplotlib). MODIS se lee con GDAL o, si no tiene HDF4, con pyhdf (el job lo instala si falta).
- Probado en la laptop con datos sintéticos (rasters equirectangulares, tiles válidos y uno dañado, shapefile y dbf). Falta correrlo en Yuca con los datos reales.

## 2026-11-13: verificación de mosaicos descargados (job 2242198)

- THEMIS IR Night 60N-60S: 15179427309 bytes, igual que en S3, sin `.aria2`.
- LROC WAC 100 m: 5959263751 bytes, igual que en S3, sin `.aria2`.
- Índice de favorabilidad de hielo, ambos polos: 4003661 bytes cada uno.
- Copernicus: seguía bajando (17,293 tiles a las 18:06, ahora en la Antártida); falta revisar el final del log y la lista de fallidos.

## 2026-11-13: T2 — rasgos geomorfométricos del parche (pipeline/features.py)

**Qué se hizo (código escrito por Gemini)**

- Se implementó `compute_features` (alias `extract_features`) en `pipeline/features.py` para parches de `64 × 64` a `500 m/px`, rellenando `NaN` restantes con la mediana del parche y devolviendo los 7 rasgos en `float32`: `mean_slope_deg`, `p90_slope_deg`, `relief_m`, `hypsometric_integral`, `detrended_std_m`, `tri_m` (TRI de Riley sobre 8 vecinos en píxeles interiores) y `mean_elev_m`.
- Se agregaron pruebas sintéticas en `tests/test_features.py` (plano inclinado de 10°, plano horizontal, cono sintético con integral hipsométrica ≈ 1/3, relleno de `NaN` y tipos `float32`).
- Suite completa verificada localmente: 9/9 pruebas pasan con `pytest -q tests`.

**Qué falta**

- Instalar `pipeline/requirements.txt` si falta algún paquete en el entorno `spaceapps_2026` de Yuca y correr `pytest -q tests` en Yuca.
- Siguientes tareas del plan: T3 (`pipeline/planet_features.py` + `jobs/t3_planet_features.slurm`) y T4 (`pipeline/targets.py` + `pipeline/data/targets.json`), además de completar descargas T0.

## 2026-11-13: T1 — extracción de parches sin distorsión (pipeline/geo.py)

**Qué se hizo (código escrito por Gemini)**

- Se creó la base del paquete `pipeline/` (`__init__.py`, `config.py`, `requirements.txt`).
- Se implementó `extract_patch` en `pipeline/geo.py`: extrae parches de `32 × 32 km` a `500 m/px` (`64 × 64 px`) en proyección AEQD local centrada en `(lat, lon)`, verificando el radio del elipsoide (`WGS84` para Tierra, `1737400 m` para Luna, `3396190 m` para Marte), reduciendo lectura con `out_shape` en rasters finos, saltando y contando cruces del antimeridiano `±180°`, convirtiendo `nodata` y `|z| > 1e5` a `NaN` y exigiendo al menos 90 % de píxeles válidos.
- Se agregaron pruebas sintéticas en `tests/__init__.py` y `tests/test_geo.py` (invarianza de pendiente entre lat 0° y 70° en la Luna, cruce de borde entre tiles en VRT terrestre sin huecos, descarte de océano/nodata, cruce de antimeridiano y validación de radio): 5/5 pruebas pasan con `pytest`.

**Qué falta**

- T2 (`pipeline/features.py` + `tests/test_features.py`) y tareas T3–T11 del plan.
- Ejecutar `pytest -q tests` en Yuca y validar cobertura de descargas T0.

## 2026-11-13: datos que faltan

- Gemini ya empezó con el plan.
- Se agregó `ne_10m_admin_0_countries` (Natural Earth, 5 MB) a `run_download_extra.slurm` para llenar el país de cada análogo. Hay que volver a enviar el job; lo ya descargado se salta.
- Siguen pendientes: terminar Copernicus (job 2242198) y verificar tamaños, y Diviner PRP (manual).

## 2026-11-13: prompt de trabajo para Gemini

- Claude escribió [prompt_gemini.md](prompt_gemini.md): instrucciones para que Gemini implemente el plan tarea por tarea (qué leer primero, reglas de commits y bitácora, reglas de Yuca, formato de respuesta) y el orden sugerido de sesiones.

## 2026-11-13: descargas enviadas en Yuca

- Se clonó el repo en `/lustre/proyectos/p089/code`; los jobs se envían desde ahí. Las copias viejas de los scripts en la raíz de `p089/` quedan sin uso.
- Se creó `~/.netrc` de Earthdata en Yuca (a mano, por Owen).
- Jobs enviados: `2242198` (`run_download_missing.slurm`) y `2242199` (`run_download_extra.slurm`).
- `2242199` bajó Natural Earth, pero MODIS falló por credenciales de Earthdata inválidas. Tras corregir el `.netrc`, `2242203` bajó MODIS completo: 12 archivos MOD13C2 (NDVI) en `data/raw/earth/modis/ndvi` y 12 MOD11C3 (LST) en `data/raw/earth/modis/lst`, todo 2023.
- `2242194` era un envío duplicado de `run_download_missing.slurm` (17:49) que corrió unos minutos a la vez que `2242198`; se canceló.
- **Pendiente:** como dos descargas escribieron a la vez, verificar al final que los mosaicos tengan el tamaño de S3 (THEMIS Night 15179427309 bytes, WAC 5959263751 bytes) y que no queden `.aria2` junto a ellos y que todos los tiles de Copernicus abran con rasterio (lo hace T5 al registrar los tiles que fallan).

## 2026-11-13: plan de implementación v2 y recursos oficiales

**Qué se hizo**

- Se revisó la pestaña Resources del challenge. Ya usamos PDS, LRO (LOLA, LROC WAC) y Copernicus. Faltaban Diviner (temperaturas polares) y NASA Earthdata (MODIS); CSA RADARSAT, ESA Open Science Catalog y JAXA G-Portal quedan fuera de alcance.
- Claude escribió [plan_implementacion.md](plan_implementacion.md): tareas T0–T11 con archivos, fórmulas, criterios de aceptación, contrato JSON v2 y cronograma. El código lo implementará Gemini a partir de ese plan.
- Decisiones clave del plan: parches de 32 × 32 km a 500 m/px en proyección AEQD local para los tres cuerpos; máscara con NDVI de MODIS; blancos curados (Artemis III, sitios de aterrizaje en Marte) más clusters; puntaje RBF por dimensión; etiqueta de análogos conocidos.
- Nuevo job `run_download_extra.slurm` con `download_earthdata.py`: Natural Earth (carreteras, aeropuertos) y MODIS NDVI (MOD13C2) y LST (MOD11C3) de 2023 vía `earthaccess`.
- Se verificaron las URLs de tiles de NASA GIBS (Tierra) y NASA Trek (Luna y Marte) para la app.

**Pendiente**

- Diviner Polar Resource Product (`LRO-L-DLRE-5-PRP-V2.0`): la URL exacta no se pudo verificar desde la red de la laptop; bajarlo a mano.
- Crear cuenta de Earthdata y `~/.netrc` en Yuca antes de enviar `run_download_extra.slurm`.

## 2026-11-13: job para re-descargar lo que faltó

**Qué se hizo**

- Se revisó el bucket de USGS (`asc-pds-services`, prefijo `mosaic/`) para encontrar los nombres reales:
  - THEMIS Night existe solo como `Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif` (15.2 GB, 60°N–60°S). Por eso la URL global daba 404.
  - Para la Luna se eligió `Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif` (6.0 GB, reflectancia real) en vez del ClrShade.
  - Se agregó `Moon_IceFavorabilityIndex_{90S,90N}000E_591mp.tif` (~4 MB c/u), útil para la base permanente en el polo.
- Nuevo job `run_download_missing.slurm`: baja lo anterior y retoma Copernicus GLO-90 con la lista sin `\r`, guarda los fallidos en `copernicus_90m_fallidos_<job>.txt` y al final verifica conteos y cuota. Corre como `sbatch`, no con `nohup` en el login.
- `process_analogs.py` ahora lee THEMIS Night y WAC con sus nombres nuevos (`wac_reflectance` reemplaza a `lola_albedo_shade`).

**Pendiente**

- SSH a Yuca está bloqueado desde la red actual; el job está listo pero no se ha corrido.
- Cuota de `p089` revisada: 78.9 GB usados de 18.63 TB (15,839 archivos). Sobra espacio para los ~75–80 GB estimados.
- Después de la descarga, mover a `_to_delete/` el `Lunar_LRO_LOLA_Albedo_Global_128ppd.tif` (es ClrShade) y el intento fallido `Mars_ODY_THEMIS_IR_Night_Mosaic_100m.tif` si quedó.

## 2026-11-13: propuesta de valor

- Claude redactó [propuesta_de_valor.md](propuesta_de_valor.md) para el equipo de presentación y video: problemática, propuesta de valor, qué agrega el proyecto frente a lo que pide la NASA, diferenciador frente a otros equipos y candidatos en México del prototipo.
- Incluye una lista de lo que no debe afirmarse todavía, por las limitaciones del prototipo.
- El diferenciador frente a otros equipos es una hipótesis: sus proyectos no son visibles antes de la entrega.
- Se subió el mismo contenido a un doc de Claude para el equipo: [Propuesta de valor: Planetary Analog Finder](https://claude.ai/artifact/563rMStp47364hAEc9pCmV). Es privado hasta que se comparta.

## 2026-11-13: revisión del prototipo y repositorio

**Qué se hizo**

- Se bajaron de Yuca los scripts, los logs y `output.zip` (sin los rasters).
- Claude revisó scripts, logs y salidas.
- Se ordenó la carpeta: logs en `logs/`, JSON de salida en `output/`, documentación en `docs/`.
- Se creó el repositorio en GitHub (privado) y se invitó al equipo con permiso de escritura: Javier033x, FernyBoy, EmiB-05, FlorMMF y verdielias.

**Estado del prototipo**

El pipeline corre completo: DEM de Marte y Luna, luego 40 arquetipos por cuerpo con nombre IAU, y luego top-5 análogos terrestres. `output/analogs.json` ya sirve para conectar la app.

**Puntos a mejorar, por prioridad**

1. **Escala.** Las ventanas miden ~118 km en Marte (256 px × 463 m), ~30 km en la Luna (256 × 118 m) y ~46 km en la Tierra (512 × 90 m). La pendiente y la rugosidad dependen de la resolución, así que hay que remuestrear a una resolución común y usar ventanas de la misma extensión en km.
2. **Máscara árida.** No hay filtro de vegetación (`masks/` vacía). Muchos análogos lunares caen en el Himalaya, Tíbet y los Andes de Colombia.
3. **Capa lunar.** El archivo llamado "Albedo" se bajó de la URL de `ClrShade` (relieve sombreado a color). Hay que cambiar la URL por una capa de albedo o de rugosidad real.
4. **Cobertura terrestre.** Solo 6,983 de 26,475 tiles; los análogos quedan entre 0.4° y 45.8° N. La descarga nocturna se cortó y 976 tiles fallaron por un `\r` en las URLs, que ya está corregido en el script.
5. **THEMIS Night.** La URL `..._v14.tif` da 404; falta encontrar la correcta.
6. **Blancos.** El k-means es global; faltan blancos reales del reto (polo sur lunar / Artemis, sitios de aterrizaje en Marte).
7. **Puntaje.** Pasar de `100/(1+0.35d)` al RBF con σ por dimensión del plan maestro.
8. **Menores.** `tri` es en realidad desviación absoluta a la mediana; `themis_ir_day` está en valores crudos; las etiquetas IAU lunares suelen ser cráteres satélite; `analyze_earth_tile` ignora errores sin avisar.

**Pendiente de confirmar**

- Con el Local Lead: si la descarga de datos y las corridas antes del 14 de noviembre cuentan como trabajo previo.

## 2026-11-12: descargas y primeras corridas en Yuca

- Descarga de MOLA, THEMIS Day y LOLA LDEM (`logs/descargas/download.log`).
- Descarga nocturna de Copernicus GLO-90; se interrumpió a medias (`logs/descargas/night_download.log`).
- Corridas de clustering (jobs 2241770, 2241771, 2241773) y de matching (2241781, 2241782, 2241783). Detalle en [pipeline.md](pipeline.md).

## Antes del 12 de noviembre

- Ideas del equipo y su evaluación: [../ideas.md](../ideas.md).
- Plan maestro: [../plan_maestro_y_especificaciones_del_proyecto.md](../plan_maestro_y_especificaciones_del_proyecto.md).

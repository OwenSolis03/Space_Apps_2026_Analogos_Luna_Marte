# Plan de implementación v2

Plan para construir la versión 2 del pipeline y la app. Está escrito para que otro agente de código (Gemini) o una persona del equipo lo implemente tarea por tarea sin tener que adivinar. Cada tarea dice qué archivo crear, qué debe hacer, con qué fórmulas y cómo saber que quedó bien.

Leer antes: [pipeline.md](pipeline.md) (cómo funciona la v1 y recursos de Yuca) y [bitacora.md](bitacora.md) (qué está mal en la v1).

---

## 0. Reglas para quien implemente

1. **Una tarea, un commit.** Mensaje en español que diga qué tarea es (`T3: features globales de Marte y Luna`). Agregar una entrada en `docs/bitacora.md` en el mismo commit.
2. **No borrar la v1.** Los scripts de la raíz (`process_analogs.py`, `match_earth_analogs.py`, `enrich_nomenclature.py`) se quedan como referencia. El código nuevo va en `pipeline/`.
3. **Nada pesado en el repo.** Rasters, parquet y shards van en Yuca (`/lustre/proyectos/p089/...`). Al repo solo sube el JSON final que consume la app (`app/public/data/`) si pesa menos de 20 MB.
4. **Reglas de Yuca (obligatorias):**
   - Todo lo que tarde más de un minuto corre con `sbatch`. Nunca `nohup`, `&` ni `python` largo en el login node.
   - Cada job declara `-A p089`, `-p cpu`, `--time`, `--mem`, y escribe su log en `/lustre/proyectos/p089/output/`.
   - Las salidas de cada corrida van a un directorio nuevo: `/lustre/proyectos/p089/runs/<SLURM_JOB_ID>/`. Nunca sobrescribir corridas anteriores.
   - No usar `rm -rf`. Para limpiar, mover a `/lustre/proyectos/p089/_to_delete/`.
   - No desactivar verificación TLS (`curl -k`, `verify=False`, etc.).
   - Límite del grupo: 500 CPUs y 4 GPUs en total. Nodos CPU de 64 núcleos y ~1 TB RAM.
5. **El código vive en Yuca en** `/lustre/proyectos/p089/code/` (copia del repo). Se actualiza con `scp -r` o `git pull` desde ahí.
6. **Entorno:** conda `spaceapps_2026`. Dependencias nuevas se agregan a `pipeline/requirements.txt` y se instalan con `pip install -r` dentro de un job o en el login si es rápido.
7. **Si un dato o URL no se puede verificar, no inventarlo.** Dejar `null` y un `TODO(verificar)` con la fuente sugerida.

---

## 1. Qué cambia respecto a la v1

| Problema de la v1 | Solución en la v2 |
| --- | --- |
| Ventanas de distinto tamaño y resolución (Marte ~118 km a 463 m, Luna ~30 km a 118 m, Tierra ~46 km a 90 m) | **Todos los cuerpos se comparan en parches de 32 × 32 km remuestreados a 500 m/px (64 × 64 px)**, proyectados localmente sin distorsión |
| La proyección equirectangular estira el eje X lejos del ecuador y la v1 no lo corrige | Cada parche se reproyecta a una proyección azimutal equidistante (AEQD) centrada en el parche |
| Sin máscara de vegetación | Máscara con NDVI máximo anual de MODIS (NASA Earthdata) |
| Blancos = solo clusters globales | Blancos curados del reto (regiones Artemis en el polo sur lunar, sitios de aterrizaje en Marte) **más** los clusters globales como modo exploración |
| Puntaje `100/(1+0.35d)` | Kernel RBF por dimensión y MSI ponderado, recalculable en la app |
| No dice dónde se rompe la analogía | Cada análogo lleva la lista de rasgos que no coinciden y los límites físicos del cuerpo |
| No distingue sitios famosos | Etiqueta `KNOWN_ANALOG` / `NEW_CANDIDATE` según una lista de regiones análogas conocidas |
| Sin logística | Distancia a carretera y aeropuerto (Natural Earth) |

---

## 2. Recursos oficiales del challenge y cómo los usamos

Fuente: pestaña Resources del challenge (revisada el 2026-11-13).

| Recurso oficial | ¿Lo usamos? | Producto concreto |
| --- | --- | --- |
| NASA Planetary Data System (PDS) | Sí | MOLA DEM 463 m, THEMIS IR Day/Night 100 m, LOLA LDEM 118 m, LROC WAC 100 m (mosaicos de USGS Astrogeology a partir de PDS) |
| NASA Lunar Reconnaissance Orbiter (LRO) | Sí | LOLA (topografía), LROC WAC (reflectancia) |
| NASA LRO Diviner Lunar Data | **Pendiente** | Diviner Polar Resource Product (PDS `LRO-L-DLRE-5-PRP-V2.0`, archivo `DLRE_PRP_SOUTH.TAB`): temperatura media y máxima anual y profundidad de estabilidad del hielo, 80–90°S. Ver T0.3 |
| NASA Earthdata Search | **Nuevo** | MODIS MOD13C2 (NDVI mensual) y MOD11C3 (temperatura superficial día/noche), 0.05° |
| NASA Worldview | En la app | Capas base de NASA GIBS (la tecnología detrás de Worldview) para el mapa de la Tierra |
| Copernicus Data Space Ecosystem (ESA) | Sí | Copernicus DEM GLO-90 |
| ESA Open Science Catalog | No | Opcional: no aporta algo que no tengamos |
| CSA RADARSAT / tutorial SAR | No (fuera de alcance) | Mencionar en "trabajo futuro": rugosidad centimétrica por radar |
| JAXA G-Portal | No | Opcional: precipitación / nieve como alternativa al NDVI |

Además, fuera de la lista: índice de favorabilidad de hielo lunar (USGS) y Natural Earth (logística).

---

## 3. Arquitectura v2

```
Datos crudos (Yuca, /lustre/proyectos/p089/data/raw)
   │
   ├── T3  pipeline/planet_features.py   (job array)  ─► runs/<id>/features_{mars,moon}.parquet
   ├── T5  pipeline/earth_features.py    (job array)  ─► runs/<id>/features_earth_*.parquet
   │        └── usa T6 pipeline/earth_layers.py (NDVI, LST, logística, regiones conocidas)
   ├── T4  pipeline/targets.py + pipeline/data/targets.json  ─► blancos curados + clusters
   │
   ├── T7  pipeline/match.py   ─► runs/<id>/matches.parquet
   └── T8  pipeline/export.py  ─► runs/<id>/analogs_universe.json  ─► app/public/data/
                                                                         │
                                               T10 app/ (React + Vite) ◄─┘
```

Todo el cálculo de rasgos usa **una sola función** (T1 + T2) para los tres cuerpos. Esa es la garantía de que la comparación es justa.

### Estructura de carpetas

```
pipeline/
  __init__.py
  config.py            # constantes: tamaño de parche, resolución, rutas, radios
  geo.py               # T1: extraer parche AEQD de cualquier raster
  features.py          # T2: rasgos geomorfométricos de un parche
  planet_features.py   # T3: barrido global de Marte y Luna
  targets.py           # T4: blancos curados + clusters
  earth_layers.py      # T6: NDVI, LST, logística, regiones conocidas
  earth_features.py    # T5: barrido de la Tierra
  match.py             # T7: RBF, MSI, diversidad, dónde se rompe
  export.py            # T8: JSON para la app
  data/
    targets.json       # T4: blancos curados (con fuente por cada uno)
    known_analogs.json # T6: regiones análogas famosas
    limits.json        # T11: límites físicos por cuerpo (texto de P3)
  requirements.txt
jobs/
  t3_planet_features.slurm
  t5_earth_features.slurm
  t7_match.slurm
tests/
  test_geo.py
  test_features.py
  test_match.py
app/                   # T10
```

---

## 4. Tareas

### T0. Datos (Owen, en Yuca, antes de todo)

Comandos en la sección 7. Resumen:

| ID | Qué | Job | Estado |
| --- | --- | --- | --- |
| T0.1 | THEMIS Night, LROC WAC, hielo lunar, resto de Copernicus | `run_download_missing.slurm` | Corriendo (job 2242198, enviado el 2026-11-13) |
| T0.2 | Natural Earth (carreteras, aeropuertos) + MODIS NDVI y LST 2023 | `run_download_extra.slurm` | Hecho (job 2242203) |
| T0.3 | Diviner Polar Resource Product (sur): `dlre_prp_south.tab` (604800210 bytes) + `.lbl` + `.xml` | `jobs/download_diviner.slurm` | Listo. Fuente: `https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/` |
| T0.4 | Mosaico virtual de Copernicus | Dentro de T5 | `gdalbuildvrt copernicus_90m.vrt copernicus_90m/*.tif` (en un job) |

### T1. `pipeline/geo.py`: extraer un parche sin distorsión

**Objetivo:** dado cualquier raster (Tierra, Luna o Marte) y un punto (lat, lon), devolver un arreglo de 64 × 64 elevaciones a 500 m/px en una proyección azimutal equidistante centrada en ese punto.

**Función principal:**

```python
def extract_patch(src, lat, lon, body, size_km=32.0, res_m=500.0, resampling=Resampling.average) -> np.ndarray | None
```

**Pasos:**

1. Radio del cuerpo: Tierra usa el elipsoide WGS84; Luna `R = 1737400 m`; Marte `R = 3396190 m`. Si el CRS del raster trae el radio, tomarlo de ahí con `pyproj.CRS(src.crs).ellipsoid.semi_major_metre` y verificar que coincide.
2. CRS destino: `+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +units=m` más `+R={R}` (Luna, Marte) o `+datum=WGS84` (Tierra).
3. Transformación destino: `Affine(res_m, 0, -size_km*500, 0, -res_m, size_km*500)`, forma `(64, 64)`.
4. Calcular los límites del parche en el CRS fuente con `rasterio.warp.transform_bounds(dst_crs, src.crs, *bounds, densify_pts=21)`, convertir a ventana con `src.window(...)`, agregar margen de 2 px y recortar al raster. Cuidado con el antimeridiano: si la ventana cruza ±180°, leer en dos partes o saltar el parche (en la v2 basta con saltarlo y contarlo).
5. Si la resolución fuente es mucho más fina que 500 m (Copernicus 90 m, LOLA 118 m), leer la ventana con `out_shape` reducido (factor `floor(500 / res_fuente)`) y `Resampling.average`, para no leer millones de píxeles de más.
6. `rasterio.warp.reproject` del arreglo leído al destino, `dst_nodata = np.nan`.
7. Devolver `None` si menos del 90 % de los píxeles es válido.

**Nodata:** convertir `src.nodata` y valores con `|z| > 1e5` a NaN.

**Criterios de aceptación (tests en `tests/test_geo.py`):**

- Raster sintético equirectangular de la Luna con un plano inclinado conocido: el parche en lat 0° y en lat 70° debe dar la misma pendiente (±0.2°). En la v1 esto falla.
- Un parche de la Tierra que cruza el borde de dos tiles de Copernicus (usando el VRT) no tiene huecos.
- Un parche en el océano devuelve `None`.

### T2. `pipeline/features.py`: rasgos del parche

**Entrada:** arreglo `z` de 64 × 64 (metros), `res_m = 500`.

**Rasgos** (todos en float32; nombres exactos, se usan en el JSON):

| Nombre | Fórmula | Dimensión |
| --- | --- | --- |
| `mean_slope_deg` | `gy, gx = np.gradient(z, res_m)`; `slope = degrees(arctan(hypot(gx, gy)))`; media | topografía |
| `p90_slope_deg` | percentil 90 de `slope` | topografía |
| `relief_m` | `p95(z) - p5(z)` | topografía |
| `hypsometric_integral` | `(mean(z) - min(z)) / (max(z) - min(z))`; 0.5 si `max == min` | topografía |
| `detrended_std_m` | ajustar plano `z ≈ a·x + b·y + c` por mínimos cuadrados; desviación estándar del residuo | rugosidad |
| `tri_m` | TRI de Riley: para cada píxel interior, `sqrt(Σ (z_vecino - z_centro)²)` sobre 8 vecinos; media | rugosidad |
| `mean_elev_m` | media de `z` | se guarda, **no** se usa para comparar (los datums de cada cuerpo no son comparables) |

Antes de calcular, rellenar los NaN restantes con la mediana del parche.

**Criterios de aceptación (`tests/test_features.py`):**

- Plano inclinado 10°: `mean_slope_deg ≈ 10` (±0.1), `detrended_std_m ≈ 0`, `tri_m` constante y conocido.
- Plano horizontal: todo ≈ 0, `hypsometric_integral = 0.5`.
- Cono sintético: `hypsometric_integral ≈ 1/3` (±0.05).

### T3. `pipeline/planet_features.py` + `jobs/t3_planet_features.slurm`

**Objetivo:** barrer Marte y la Luna con parches de 32 km y guardar sus rasgos.

**Grilla de centros (igual para todos los cuerpos, incluida la Tierra):**

- Paso en latitud: `dlat = degrees(32000 / R)` (Marte ≈ 0.54°, Luna ≈ 1.06°, Tierra ≈ 0.29°).
- Para cada latitud, paso en longitud: `dlon = dlat / cos(lat)`.
- Latitudes de −88° a 88° (en el polo la AEQD funciona; el límite lo pone la cobertura del raster).
- Marte ≈ 141 mil parches; Luna ≈ 37 mil.

**Capas auxiliares por parche** (mediana dentro del parche, también con `extract_patch` y `Resampling.average`, NaN si no hay cobertura):

- Marte: `themis_day`, `themis_night` (valores crudos del mosaico; documentar que no son temperatura) y `themis_delta = themis_day - themis_night`.
- Luna: `wac_reflectance`; `ice_favorability` (solo en los polos); y `diviner_tmax_k`, `diviner_tavg_k`, `ice_depth_m` desde la tabla PRP (T0.3, ya descargada).
  - Formato de `dlre_prp_south.tab`: CSV con encabezado y espacios; columnas `tri1_x, tri1_y, tri1_z, tri2_x, …, tri3_z, tri_clon, tri_clat, tri_calt, temp_avg, temp_max, ice_depth`. Usar solo `tri_clon`, `tri_clat` (centro del triángulo, grados), `temp_avg`, `temp_max` (K) e `ice_depth` (m; `-999` = sin hielo estable → NaN para la mediana, pero contar como "sin hielo").
  - 2.88 millones de filas (577 MB): leer con `pandas.read_csv(..., usecols=[...], skipinitialspace=True)` una sola vez y guardar en `data/derived/diviner_prp_south.parquet`.
  - Para cada parche polar, tomar los triángulos cuyo centro cae dentro del parche (con `scipy.spatial.cKDTree` sobre coordenadas polares estereográficas) y usar la mediana. Cobertura: de ~76°S a 90°S.

**Paralelismo:** job array por franjas de latitud (por ejemplo 16 franjas, `--array=0-15`, 8 CPUs cada una, `multiprocessing.Pool`). Cada tarea escribe `runs/<id>/features_<body>_<franja>.parquet`.

**Salida (columnas):** `body, lat, lon, <rasgos de T2>, <auxiliares>, valid_frac`.

**Criterio de aceptación:** el número de parches válidos por cuerpo coincide con lo esperado (±10 %) y un mapa rápido de `mean_slope_deg` (scatter lat/lon, guardado como PNG en `runs/<id>/`) muestra rasgos reconocibles: Valles Marineris y Olympus Mons en Marte, las tierras altas frente a los mares en la Luna.

### T4. `pipeline/targets.py` + `pipeline/data/targets.json`

**Objetivo:** definir contra qué sitios de la Luna y Marte se buscan análogos.

> **Especificación detallada:** [plan_t4.md](plan_t4.md) (coordenadas verificadas, anclas IAU, soporte polar, firmas, salidas y pruebas). Para T4 manda ese documento.

**Dos tipos de blanco:**

1. **Curados (`CURATED`)**, en `targets.json`. Cada uno con `id`, `body`, `name`, `lat`, `lon`, `category`, `why` (una línea), `source_url`. **Las coordenadas se toman de la fuente oficial**; si no se encuentran, `lat/lon = null` y el blanco se omite.
   - Luna, polo sur: las regiones candidatas de Artemis III publicadas por NASA (en la actualización de 2024: Peak near Cabeus B, Haworth, Malapert Massif, Mons Mouton Plateau, Mons Mouton, Nobile Rim 1, Nobile Rim 2, de Gerlache Rim 2, Slater Plain; confirmar la lista vigente en nasa.gov). Más el borde del cráter Shackleton.
   - Marte: Jezero (Perseverance), Gale (Curiosity), Gusev (Spirit), Meridiani Planum (Opportunity), Utopia Planitia (Zhurong), Elysium Planitia (InSight), Oxia Planum (Rosalind Franklin), y una región con hielo somero de los mapas SWIM (Arcadia Planitia). Coordenadas desde la página de cada misión.
2. **Clusters (`CLUSTER`)**: k-means sobre los rasgos de T3 (rasgos de topografía y rugosidad estandarizados), 30 clusters por cuerpo. El representante es el parche más cercano al centroide. Nombre con el rasgo IAU más cercano, reutilizando la lógica de `enrich_nomenclature.py`.

**Rasgos del blanco:** se extraen con exactamente las mismas funciones T1 + T2 en sus coordenadas. Para un blanco curado se promedian los rasgos de un parche central y 4 vecinos (desplazados 16 km), para no depender de un solo parche.

**Criterio de aceptación:** `targets.json` tiene al menos 6 blancos lunares y 6 marcianos con `source_url`, y cada uno tiene rasgos válidos.

### T5. `pipeline/earth_features.py` + `jobs/t5_earth_features.slurm`

**Objetivo:** lo mismo que T3, pero para la Tierra, filtrando antes lo que no sirve.

**Pasos:**

1. Crear (una vez, dentro del job) el VRT de Copernicus: `gdalbuildvrt /lustre/proyectos/p089/data/derived/copernicus_90m.vrt .../copernicus_90m/*.tif`.
2. Generar la grilla global de centros (misma función que T3, con el radio de la Tierra).
3. **Prefiltro barato** antes de extraer el parche, con las capas de T6 a 0.05°:
   - Descartar si `ndvi_max > 0.25` (vegetación).
   - Descartar si no hay tile de Copernicus en esa celda de 1°.
4. Extraer el parche del VRT y calcular los rasgos de T2.
5. Adjuntar las capas de T6: `ndvi_max`, `lst_day_c`, `lst_night_c`, `lst_amplitude_c`, `dist_road_km`, `dist_airport_km`, `known_region` (nombre o null).

**Paralelismo:** job array por franjas de latitud, por ejemplo `--array=0-31`, 16 CPUs cada una: hasta 512 CPUs, que pasa el límite. Usar `%30` en el array (`--array=0-31%30`) para no rebasar 500 CPUs entre todas.

**Criterio de aceptación:** entre 40 mil y 120 mil parches válidos en la Tierra; ningún parche en la Amazonía, el Congo o Indonesia ecuatorial; Atacama, Sahara, desiertos de Sonora, Australia central y los Valles Secos de la Antártida presentes.

### T6. `pipeline/earth_layers.py`: capas terrestres

Funciones que cargan una vez (en memoria, por proceso) y responden por (lat, lon):

- **NDVI máximo anual:** de los 12 HDF de MOD13C2 (subdataset `CMG 0.05 Deg Monthly NDVI`, factor de escala 0.0001, valores < −0.3 o el fill → NaN), tomar el máximo por píxel. Guardar como GeoTIFF en `data/derived/ndvi_max_2023.tif` la primera vez.
- **Temperatura superficial (LST):** de MOD11C3, `LST_Day_CMG` y `LST_Night_CMG` (escala 0.02, en kelvin → °C). Media anual de día, de noche y la amplitud `día − noche`. Guardar en `data/derived/lst_2023.tif` (3 bandas).
- **Logística:** con `geopandas` cargar `ne_10m_roads` y `ne_10m_airports`; construir `shapely.STRtree` y calcular la distancia geodésica aproximada en km al elemento más cercano. Para que sea rápido, calcular en la proyección `EPSG:4087` o con `sklearn.neighbors.BallTree` (métrica haversine) sobre vértices de las carreteras.
- **Regiones conocidas:** `pipeline/data/known_analogs.json` con polígonos aproximados (bbox) y fuente de: Desierto de Atacama, Valles Secos de McMurdo, Islandia, Hawái (Mauna Kea / Kilauea), Isla Devon (cráter Haughton), Utah (MDRS, Hanksville), Río Tinto (España), Svalbard, Pilbara (Australia), Meteor Crater (Arizona), Lanzarote, Mojave. Un parche dentro de cualquiera recibe `classification = KNOWN_ANALOG`; si no, `NEW_CANDIDATE`.

**Criterio de aceptación:** `ndvi_max` en el Sahara < 0.1 y en la Amazonía > 0.7; distancia a carretera en Hermosillo < 5 km.

### T7. `pipeline/match.py`: puntaje y selección

**1. Normalización común.** Juntar todos los parches (Tierra + blancos). A los rasgos con cola larga (`relief_m`, `detrended_std_m`, `tri_m`) aplicarles `log1p`. Luego, para cada rasgo, z robusto: `z = (x - mediana) / (1.4826 · MAD)`, con mediana y MAD **calculadas sobre la Tierra** (así las unidades son "desviaciones típicas terrestres").

**2. Dimensiones y RBF.**

| Dimensión `k` | Rasgos | σ por defecto |
| --- | --- | --- |
| `topography` | `mean_slope_deg`, `p90_slope_deg`, `relief_m`, `hypsometric_integral` | 1.0 |
| `roughness` | `detrended_std_m`, `tri_m` | 1.0 |
| `environment` | Aridez: `ndvi_max` del parche terrestre | ver abajo |
| `thermal` | Solo Marte: z de `lst_amplitude_c` (Tierra) contra z de `themis_delta` (Marte), cada uno normalizado dentro de su cuerpo | 1.0 |

- Geomorfología: `d_k = ||z_tierra - z_blanco|| / sqrt(n_rasgos_k)`; `S_k = exp(-d_k² / (2 σ_k²))`.
- Ambiente: `S_env = exp(-max(0, ndvi_max - 0.10)² / (2 · 0.10²))`. Un sitio sin vegetación vale 1.
- Térmico: es una comparación por rango (qué tan extrema es la amplitud **dentro de su propio cuerpo**), no de temperaturas absolutas. Documentarlo así en la app. Para la Luna, `S_thermal = null` (no hay equivalente terrestre).

**3. MSI.** `MSI = Σ w_k · S_k / Σ w_k`, sobre las dimensiones no nulas. Presets (iguales que en el plan maestro, adaptados):

| Preset | topography | roughness | environment | thermal |
| --- | --- | --- | --- | --- |
| `mobility_and_traction` | 0.45 | 0.40 | 0.15 | 0 |
| `construction_and_base` | 0.55 | 0.25 | 0.10 | 0.10 |
| `dust_and_thermal` | 0.15 | 0.15 | 0.40 | 0.30 |

`MSI_log = MSI · (1 - λ + λ · exp(-dist_road_km / 100))`, con λ entre 0 y 0.3 (lo controla la app).

**4. Selección con diversidad.** Para cada blanco y cada preset: ordenar por MSI y tomar los mejores 30 que estén a más de 150 km entre sí (haversine). La unión de los tres presets (máximo 90 sitios por blanco) va al JSON, con sus `sub_scores`, para que la app pueda reordenar con cualquier peso.

Para que sea rápido con ~100 mil parches: calcular primero la distancia en topografía + rugosidad con `sklearn.neighbors.NearestNeighbors` (k = 2000), y aplicar el MSI completo solo a esos candidatos.

**5. Dónde se rompe la analogía (por sitio).** Para cada rasgo con `|z_tierra - z_blanco| > 1.5`, agregar a `mismatches` un objeto `{feature, earth, target, z_diff}` con los valores en unidades físicas. Además, copiar al JSON los límites fijos del cuerpo desde `limits.json` (T11).

**Criterios de aceptación (`tests/test_match.py` + revisión):**

- Un blanco idéntico a un parche terrestre obtiene `S_topography = S_roughness = 1`.
- Ningún par de análogos del mismo blanco está a menos de 150 km.
- Revisión de sentido común: para un blanco en Olympus Mons, entre los 30 primeros debe aparecer algún volcán en escudo (Hawái, Galápagos, Islandia). Si no aparece, revisar escalas antes de seguir.

### T8. `pipeline/export.py`: JSON para la app

Escribe `runs/<id>/analogs_universe.json` y una copia en `app/public/data/analogs_universe.json`. El esquema está en la sección 5. Redondear a 4 decimales las coordenadas y a 3 los puntajes. Si pesa más de 20 MB, partirlo en un archivo por cuerpo (`analogs_moon.json`, `analogs_mars.json`).

### T9. Pruebas

- `tests/` con `pytest`, solo con datos sintéticos (no tocan los rasters). Se corren en un job corto: `sbatch --wrap "pytest -q tests"` con `-A p089 -p cpu --time=00:15:00 --mem=4G`.
- Antes de lanzar T3 o T5 completos, correr cada uno con `--limit 500` (opción de línea de comandos que limita el número de parches) y revisar la salida.

### T10. App (Javier)

**Stack:** React + Vite + TypeScript + Tailwind. Mapas con **MapLibre GL** (no necesita token, a diferencia de Mapbox) para la Tierra y **Leaflet** para la Luna y Marte. Gráficas con Recharts.

**Capas base verificadas el 2026-11-13:**

| Mapa | URL de tiles |
| --- | --- |
| Tierra (NASA GIBS, relieve) | `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg` |
| Tierra (NASA GIBS, color real) | `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2023-07-01/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg` |
| Luna (NASA Trek, LROC WAC) | `https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/default/default028mm/{z}/{y}/{x}.jpg` |
| Luna (NASA Trek, relieve LOLA) | `https://trek.nasa.gov/tiles/Moon/EQ/LRO_LOLA_ClrShade_Global_128ppd_v04/1.0.0/default/default028mm/{z}/{y}/{x}.png` |
| Marte (NASA Trek, Viking color) | `https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg` |
| Marte (NASA Trek, relieve MOLA) | `https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg` |

Los tiles de Trek están en proyección geográfica (EPSG:4326, 2 tiles en X en el nivel 0): en Leaflet usar `crs: L.CRS.EPSG4326`. Para el polo sur lunar, la vista equirectangular deforma mucho; mostrar un aviso y, como mínimo, centrar en la región. Buscar en trek.nasa.gov una capa polar sur (SP) si hay tiempo.

**Pantallas y componentes:**

1. **Selector de escenario:** cuerpo (Luna / Marte), tipo de blanco (curado / cluster), preset de misión.
2. **Panel de pesos:** un slider por dimensión (normalizar para que sumen 1), switch de prioridad logística (λ de 0 a 0.3) y filtro "solo nuevos candidatos".
3. **Vista doble:** a la izquierda el blanco en Leaflet; a la derecha la Tierra en MapLibre con marcadores coloreados por MSI. Al hacer clic en un análogo se centra el mapa.
4. **Lista de resultados:** tarjetas ordenadas por MSI recalculado en el navegador (`MSI = Σ w·S / Σ w` con los `sub_scores` del JSON; no se recalcula nada geofísico en el cliente).
5. **Ficha del sitio:**
   - Gráfica de radar con las 4 dimensiones
   - Tabla de rasgos Tierra contra blanco, en unidades físicas
   - Sección **"Dónde se rompe la analogía"**: los `mismatches` del sitio más los límites fijos del cuerpo
   - Protocolo de prueba sugerido
   - Logística (distancia a carretera y aeropuerto)
   - Etiqueta `KNOWN_ANALOG` o `NEW_CANDIDATE`
   - Enlaces a los datasets de origen
6. **Comparar:** dos sitios lado a lado.
7. **Exportar:** la ficha en JSON y en Markdown, y una vista de impresión con CSS.
8. **Metodología:** página corta con las fórmulas de la sección T7 y la tabla de recursos de la sección 2.

**Datos:** mientras T8 no esté, usar un JSON de ejemplo que siga el esquema de la sección 5 (`app/public/data/sample.json`), generado a mano o a partir de `output/analogs.json` de la v1.

**Despliegue:** GitHub Pages o Vercel desde la rama `main`.

**Criterio de aceptación:**
- Mover un slider reordena la lista en menos de 50 ms.
- Funciona sin conexión a Yuca.
- Se ve bien en una laptop de 1366 × 768 y en el proyector.

### T11. Contenido (P1, P3, P4)

- `pipeline/data/limits.json`: por cuerpo, una lista de `{factor, earth, target, consequence}` con fuente. Mínimo:
  - Luna: gravedad, vacío, radiación, ciclo térmico, iluminación polar y regolito.
  - Marte: gravedad, presión, radiación, ciclo térmico, polvo y percloratos.
- Protocolo de prueba por preset (texto corto que la app muestra según la dimensión que más pesa).
- Pitch, presentación y video de respaldo. Base: [propuesta_de_valor.md](propuesta_de_valor.md).
- Descripción del uso de IA, sacada de la bitácora.

---

## 5. Contrato de datos `analogs_universe.json` (v2)

```json
{
  "metadata": {
    "version": "2.0.0",
    "generated_at": "ISO-8601",
    "slurm_job_id": "123456",
    "patch": { "size_km": 32, "res_m": 500, "projection": "AEQD local" },
    "earth_patches_evaluated": 0,
    "datasets": [ { "name": "Copernicus DEM GLO-90", "source": "ESA", "url": "..." } ]
  },
  "mission_presets": {
    "mobility_and_traction": { "label": "Movilidad y tracción de rovers", "weights": { "topography": 0.45, "roughness": 0.40, "environment": 0.15, "thermal": 0 } }
  },
  "limits": {
    "Moon": [ { "factor": "gravity", "earth": "1 g", "target": "0.166 g", "consequence": "...", "source": "..." } ],
    "Mars": [ ]
  },
  "targets": [
    {
      "id": "moon-artemis-haworth",
      "type": "CURATED",
      "body": "Moon",
      "name": "Haworth",
      "lat": null,
      "lon": null,
      "category": "Artemis III candidate region",
      "why": "...",
      "source_url": "...",
      "iau_label": "...",
      "features": { "mean_slope_deg": 0, "p90_slope_deg": 0, "relief_m": 0, "hypsometric_integral": 0, "detrended_std_m": 0, "tri_m": 0 },
      "aux": { "wac_reflectance": 0, "ice_favorability": 0, "diviner_tmax_k": null },
      "analogs": [
        {
          "id": "earth-<lat>-<lon>",
          "lat": 0,
          "lon": 0,
          "country": null,
          "classification": "NEW_CANDIDATE",
          "known_region": null,
          "sub_scores": { "topography": 0, "roughness": 0, "environment": 0, "thermal": null },
          "msi_by_preset": { "mobility_and_traction": 0 },
          "features": { "mean_slope_deg": 0 },
          "earth_env": { "ndvi_max": 0, "lst_day_c": 0, "lst_night_c": 0, "lst_amplitude_c": 0 },
          "logistics": { "dist_road_km": 0, "dist_airport_km": 0 },
          "mismatches": [ { "feature": "relief_m", "earth": 0, "target": 0, "z_diff": 0 } ]
        }
      ]
    }
  ]
}
```

`country` se llena con Natural Earth `ne_10m_admin_0_countries` (columna `ADMIN`), que baja `run_download_extra.slurm` a `data/raw/earth/naturalearth/ne_10m_admin_0_countries/`.

---

## 6. Orden y tiempos (48 horas desde el 14 de noviembre, 9:00)

| Horas | Pipeline (Owen + Gemini) | App (Javier) | Contenido |
| --- | --- | --- | --- |
| 0–2 | Enviar T0.1 y T0.2 (si no se enviaron antes). T1, T2 y sus tests | Proyecto Vite, mapas con capas base, JSON de ejemplo | `limits.json`, lista de blancos con fuentes (T4) |
| 2–8 | T3 con `--limit`, luego completo. T4 | Panel de pesos, lista, cálculo de MSI | Protocolos de prueba |
| 8–16 | T6, T5 con `--limit`, luego completo (job array) | Ficha del sitio, radar, "dónde se rompe" | Guion del pitch |
| 16–22 | T7, T8, revisión de sentido común | Comparar, exportar | Presentación |
| 22–30 | Ajustar σ y umbrales; segunda corrida si hace falta | Conectar el JSON real | Ensayos con la app |
| 30–40 | Congelar datos. Documentar | Pulir, desplegar | Video de respaldo |
| 40–48 | Bitácora y uso de IA | Congelar código | Envío |

**Plan B:** si T5 no termina a tiempo, usar solo las franjas de latitud que sí terminaron y decirlo en la app ("cobertura parcial: X % de la superficie terrestre"). Si T3/T5 fallan por completo, la app sigue funcionando con `output/analogs.json` de la v1, convertido al esquema nuevo.

---

## 7. Comandos de descarga (Owen, en Yuca)

Todo se corre **ya dentro de Yuca** (en `login-01`). El código llega clonando el repo (público) en `/lustre/proyectos/p089/code`; no hace falta token.

Primera vez:

```bash
git clone https://github.com/OwenSolis03/Space_Apps_2026_Analogos_Luna_Marte.git /lustre/proyectos/p089/code
```

Las siguientes veces, para traer cambios:

```bash
cd /lustre/proyectos/p089/code && git pull
```

Probar sin encolar y luego enviar (siempre desde `code/`):

```bash
cd /lustre/proyectos/p089/code && sbatch --test-only run_download_missing.slurm && sbatch --test-only run_download_extra.slurm
```

```bash
cd /lustre/proyectos/p089/code && sbatch run_download_missing.slurm && sbatch run_download_extra.slurm
```

Para MODIS hace falta una cuenta gratuita en https://urs.earthdata.nasa.gov y crear `~/.netrc` en Yuca **a mano** (la contraseña no debe pasar por ningún agente):

```bash
nano ~/.netrc
```

Contenido: `machine urs.earthdata.nasa.gov login TU_USUARIO password TU_CONTRASEÑA`. Después:

```bash
chmod 600 ~/.netrc
```

Ver el avance:

```bash
squeue -u owen
```

```bash
tail -n 30 /lustre/proyectos/p089/output/descargas_*.log
```

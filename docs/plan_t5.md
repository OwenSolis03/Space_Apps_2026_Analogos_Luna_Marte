# Plan detallado T5: barrido de la Tierra

Especificación completa de T5. Amplía la sección T5 de [implementation_plan.md](implementation_plan.md); si algo choca, **este documento manda para T5**. Escrito por Claude el 2026-11-13 sobre `main` en `5b33704`, con los tiles de Copernicus revisados en Yuca ese día.

**Depende de T6:** usa `EarthLayers` y la caché `data/derived/{ndvi_max_2023,lst_2023}.tif` de [plan_t6.md](plan_t6.md). El código de T5 se puede escribir en paralelo, pero la corrida de T5 va **después** de la corrida de T6.

---

## 0. Resumen

| Qué | Dónde |
| --- | --- |
| Mosaico virtual, prefiltro, extracción y combinación | `pipeline/earth_features.py` |
| Jobs (3 etapas encadenadas) | `jobs/t5_prepare.slurm`, `jobs/t5_earth_features.slurm`, `jobs/t5_merge.slurm` |
| Envío de las 3 etapas con un comando | `jobs/t5_submit.sh` |
| Pruebas | `tests/test_earth_features.py` |
| Caché compartida (no va al repo) | `data/derived/copernicus_90m.vrt` |
| Salidas (en `runs/<PREP_JOBID>/`) | `candidates.parquet`, `prefilter_stats.json`, `features_earth_<i>.parquet`, `features_earth.parquet`, `t5_checks.json`, `map_earth_mean_slope_deg.png`, `map_earth_classification.png` |

Commit: `T5: barrido de la Tierra`. **Commitear y hacer push antes de enviar los jobs.**

---

## 1. Hechos verificados en Yuca (2026-11-13)

**Tiles de Copernicus GLO-90:**

| Qué | Dato |
| --- | --- |
| Ubicación | `data/raw/earth/copernicus_90m/` |
| Número de tiles | 26,475, 67 GB, todos `.tif` |
| Nombre | `Copernicus_DSM_COG_30_{N|S}{lat:02d}_00_{E|W}{lon:03d}_00_DEM.tif`, donde `lat`/`lon` es la esquina **inferior izquierda** de la celda de 1° |
| Formato | EPSG:4326, float32, `scales=(1.0,)` |

- **No tienen `nodata`.**
- **El mar dentro de un tile costero vale exactamente `0.0`.** Por ejemplo, `N29_00_W113` (golfo de California) tiene el 52.3 % de sus píxeles en 0.0, mientras que `N29_00_W112` (tierra adentro) tiene 0 %.
- **El ancho del tile cambia con la latitud** (Copernicus reduce la resolución en longitud lejos del ecuador). La altura siempre es 1200 px (0.000833°):

| Latitud | Ancho | Resolución en longitud |
| --- | --- | --- |
| < 50° | 1200 px | 0.000833° |
| 50–60° | 800 px | — |
| 60–70° | 600 px | — |
| 70–80° | 400 px | 0.0025°, ej. `S78_00_E162`, `N75_00_W090` |
| 80–85° | 240 px | — |
| 85–90° | 120 px | — |

- Donde no hay tierra **no hay tile**.

**Grilla terrestre** (`generate_grid("Earth")`, la misma función de T3):

| Conjunto | Centros |
| --- | --- |
| Grilla completa | 497,818 |
| Con tile en su celda de 1° | 179,663 |
| … al sur de −60° (Antártida) | 14,959 |
| … entre −60° y 60° | 143,426 |
| … al norte de 60° | 21,278 |

**Herramientas:** `gdalbuildvrt` está en el entorno (`~/.conda/envs/spaceapps_2026/bin/`); fuera de conda no está en el `PATH`.

---

## 2. Decisiones (no cambiarlas sin avisar)

1. **El mar se enmascara en el mosaico, no en Python.** El VRT se construye con `-srcnodata 0 -vrtnodata -9999`:
   - los ceros de los tiles y las zonas sin tile quedan como nodata `-9999`;
   - `extract_patch` ya enmascara `src.nodata` y devuelve `None` si menos del 90 % del parche es válido;
   - resultado: **un parche con más del 10 % de mar se descarta solo**.
   - Efecto secundario aceptado: la tierra con elevación exactamente 0.0 m también se enmascara. Es despreciable, porque los valores son float32 continuos.
2. **Resolución del VRT:** `-resolution highest` (0.000833°). Los tiles de latitudes altas se muestrean con vecino más cercano dentro del VRT. No importa, porque `extract_patch` promedia después a 500 m.
3. **Tres etapas en vez de un solo array:**
   - **`prepare`**: un job. Construye el VRT si falta, aplica el prefiltro y calcula **una sola vez** todas las columnas terrestres de T6 de cada candidato.
   - **array**: 32 tareas que solo extraen parches del DEM. Cada tarea toma la misma cantidad de candidatos, así que la carga queda balanceada.
   - **`merge`**: une las franjas con las columnas de `prepare` y corre las verificaciones.

   Así `EarthLayers` (~420 MB) no se carga 32 veces y las franjas pesan lo mismo.
4. **Identificador de la corrida:** el JOBID de `prepare`. Las tres etapas escriben en `runs/<PREP_JOBID>/`. Es la única excepción a "cada job en su `runs/$SLURM_JOB_ID/`", y se documenta en `pipeline.md`. Los logs sí van con su propio JOBID.
5. **Prefiltro**, en este orden, contando cada descarte en `prefilter_stats.json`:
   1. Sin tile de Copernicus en la celda de 1° del **centro** se descarta (`no_tile`).
   2. `ndvi_max` del parche (mediana de la ventana, `EarthLayers.ndvi_prefilter`) **> 0.25** se descarta (`vegetated`).
   3. `ndvi_max` **NaN** pasa **solo si** `lst_day_c` de la ventana (`patch_window_stat(..., 'mean')` sobre la banda 1 de LST) es finito: es tierra sin NDVI, como la Antártida, donde MOD13C2 no tiene datos al sur de −59.45°. Se marca `ndvi_missing = True`. Si NDVI y LST son NaN a la vez, el centro está sobre el mar (tiles costeros, atolones) y se descarta (`no_land_data`). Medido con la caché de T6 (job `2242426`): 35,483 centros con tile tienen NDVI NaN; 14,959 están al sur de −60° y 20,524 al norte, casi todos sobre el mar.
6. **Mismas funciones que T3:** `extract_patch(src, lat, lon, body="Earth")` y `compute_features`. Sin cambios en `geo.py` ni en `features.py`. Los parches que cruzan ±180° se saltan y se cuentan (hay 140 centros con tile y `|lon| > 179.5°`).

---

## 3. `pipeline/earth_features.py`

### 3.1 Tiles y VRT

```python
TILE_RE = re.compile(r"_(?P<ns>[NS])(?P<lat>\d{2})_00_(?P<ew>[EW])(?P<lon>\d{3})_00_DEM\.tif$")
VRT_NODATA = -9999.0

def parse_tile_cell(name: str) -> tuple[int, int]:
    """'..._S78_00_E162_00_DEM.tif' -> (-78, 162); '..._N00_00_W001_00_DEM.tif' -> (0, -1).
    ValueError si el nombre no coincide."""

def load_tile_cells(copernicus_dir: Path) -> set[tuple[int, int]]:
    """Celdas (lat_floor, lon_floor) con tile, a partir de los nombres (sin abrir archivos)."""

def has_tile(lat: np.ndarray, lon: np.ndarray, cells: set[tuple[int, int]]) -> np.ndarray:
    """bool por punto: (floor(lat), floor(lon)) en cells. Ojo con negativos: floor(-0.5) = -1."""

def build_vrt(copernicus_dir: Path, vrt_path: Path) -> Path:
    """Si vrt_path existe, no hace nada y lo devuelve.
    Si no: escribe la lista de tiles (orden alfabético) en vrt_path.with_suffix('.list.txt') y corre
      gdalbuildvrt -overwrite -resolution highest -srcnodata 0 -vrtnodata -9999 \
                   -input_file_list <lista> <vrt_path>.tmp.vrt
    con subprocess.run(check=True), y luego os.replace(<tmp>, vrt_path).
    Busca gdalbuildvrt con shutil.which; si no está, RuntimeError('activa spaceapps_2026').
    Después abre el VRT con rasterio y verifica: crs EPSG:4326, nodata == -9999,
    |res| == (1/1200, 1/1200) con tolerancia 1e-9; imprime ancho, alto y bounds."""
```

### 3.2 Etapa `prepare`

```python
CANDIDATE_COLUMNS = ["lat", "lon", *EARTH_ENV_COLUMNS, "ndvi_missing"]   # EARTH_ENV_COLUMNS de T6
NDVI_PREFILTER_MAX = 0.25

def prefilter(lat, lon, cells, layers: EarthLayers) -> tuple[np.ndarray, dict]:
    """Máscara de candidatos y conteos {grid, no_tile, vegetated, no_land_data, ndvi_missing, kept}."""

def prepare_candidates(project_dir: Path, out_dir: Path, limit: int | None = None) -> Path:
    """1) build_vrt(...) en data/derived/copernicus_90m.vrt.
       2) generate_grid('Earth').
       3) prefilter. Llamar a ndvi_prefilter solo sobre los puntos con tile.
       4) Si limit: apply_limit sobre los candidatos YA filtrados (la prueba usa candidatos reales).
       5) layers.sample(...) sobre los candidatos -> columnas de T6; ndvi_missing.
       6) Ordenar por (lat, lon) y escribir out_dir/candidates.parquet y prefilter_stats.json.
       Imprimir los conteos y la distribución de classification."""
```

### 3.3 Etapa de extracción (array)

```python
EARTH_FEATURE_COLUMNS = ["lat", "lon", *FEATURE_NAMES, "valid_frac"]

def _init_earth_worker(vrt_path: str, size_km: float, res_m: float) -> None   # abre el VRT una vez por proceso
def _process_earth_point(point: tuple[float, float]) -> dict | None           # extract_patch + compute_features

def extract_stripe(run_dir: Path, stripe_idx: int, num_stripes: int, workers: int,
                   vrt_path: Path) -> Path:
    """Lee run_dir/candidates.parquet (solo lat y lon), select_stripe (la de T3),
    Pool(workers, initializer=_init_earth_worker), imap con chunksize como en T3.
    Escribe run_dir/features_earth_<stripe_idx>.parquet con EARTH_FEATURE_COLUMNS
    (lat/lon float64, el resto float32). Imprime: válidos / candidatos de la franja, tiempo,
    y min/mediana/p95/max de mean_slope_deg, relief_m y mean_elev_m (como T3)."""
```

### 3.4 Etapa `merge`

```python
EARTH_COLUMNS = ["body", "lat", "lon", *FEATURE_NAMES, "valid_frac",
                 *[c for c in EARTH_ENV_COLUMNS], "ndvi_missing"]

def merge_earth(run_dir: Path, num_stripes: int, allow_missing: bool = False) -> Path:
    """Concatena features_earth_<i>.parquet. Si falta alguno: error, salvo con allow_missing
    (plan B: cobertura parcial; imprimir qué franjas faltan y el % de candidatos cubiertos).
    Hace inner join con candidates.parquet en (lat, lon) exactos (vienen de la misma grilla,
    redondeada a 6 decimales). Comprueba que ninguna fila de las franjas queda sin pareja.
    body = 'Earth'. Escribe run_dir/features_earth.parquet con EARTH_COLUMNS."""

def plot_earth_maps(df: pd.DataFrame, run_dir: Path) -> None:
    """map_earth_mean_slope_deg.png (mismo estilo que plot_slope_map de T3) y
    map_earth_classification.png (NEW_CANDIDATE gris, KNOWN_ANALOG naranja, ndvi_missing azul)."""

def run_checks(df: pd.DataFrame, run_dir: Path) -> bool:
    """Sección 6. Escribe t5_checks.json; devuelve False si falla un criterio duro."""
```

### 3.5 CLI

```text
python -m pipeline.earth_features prepare --project-dir P --run-dir R [--limit N]
python -m pipeline.earth_features extract --project-dir P --run-dir R --stripe-idx I --num-stripes K --workers W
python -m pipeline.earth_features merge   --run-dir R --num-stripes K [--allow-missing]
```

`merge` sale con código 1 si `run_checks` devuelve False.

---

## 4. Jobs

Los tres `.slurm` siguen la forma de `jobs/t4_targets.slurm`: `#!/usr/bin/env bash`, `set -euo pipefail`, conda, eco con el commit y **sin `pip install`** (todo ya está en el entorno). `RUN_DIR` llega por `--export`.

| Script | Recursos | Comando |
| --- | --- | --- |
| `t5_prepare.slurm` | `-J p089-t5-prepare`, 4 CPUs, 24G, `--time=01:30:00`, log `t5_prepare_%j.log` | `RUN_DIR=${RUN_DIR:-$PROJECT_DIR/runs/$SLURM_JOB_ID}`; `python -m pipeline.earth_features prepare ... "$@"` |
| `t5_earth_features.slurm` | `-J p089-t5-earth`, `--array=0-31%30`, 16 CPUs, 32G, `--time=03:00:00`, log `t5_earth_%A_%a.log` | `extract --stripe-idx $SLURM_ARRAY_TASK_ID --num-stripes ${NUM_STRIPES:-32} --workers $SLURM_CPUS_PER_TASK`; exportar `GDAL_CACHEMAX=256`, `OMP_NUM_THREADS=1` |
| `t5_merge.slurm` | `-J p089-t5-merge`, 2 CPUs, 16G, `--time=00:30:00`, log `t5_merge_%j.log` | `merge --num-stripes ${NUM_STRIPES:-32} ${ALLOW_MISSING:+--allow-missing}` |

Límite del grupo: 30 tareas simultáneas × 16 CPUs = 480 CPUs, por debajo de 500. Si hay otros jobs del grupo corriendo, el `%30` evita pasarse.

**`jobs/t5_submit.sh`**: corre en el login, solo hace `sbatch`. Es un comando corto, permitido también en la terminal de OOD.

```bash
#!/usr/bin/env bash
# Uso: bash jobs/t5_submit.sh            (corrida completa, 32 franjas)
#      bash jobs/t5_submit.sh --limit 500 (prueba: 1 franja)
set -euo pipefail
cd "$(dirname "$0")/.."
LIMIT_ARGS=(); NUM_STRIPES=32; ARRAY="0-31%30"
if [[ "${1:-}" == "--limit" ]]; then LIMIT_ARGS=(--limit "$2"); NUM_STRIPES=1; ARRAY="0-0"; fi
PREP=$(sbatch --parsable jobs/t5_prepare.slurm "${LIMIT_ARGS[@]}")
RUN_DIR=/lustre/proyectos/p089/runs/$PREP
ARR=$(sbatch --parsable --dependency=afterok:$PREP --array="$ARRAY" \
      --export=ALL,RUN_DIR=$RUN_DIR,NUM_STRIPES=$NUM_STRIPES jobs/t5_earth_features.slurm)
MRG=$(sbatch --parsable --dependency=afterok:$ARR \
      --export=ALL,RUN_DIR=$RUN_DIR,NUM_STRIPES=$NUM_STRIPES jobs/t5_merge.slurm)
echo "prepare=$PREP array=$ARR merge=$MRG run_dir=$RUN_DIR"
```

Con `--array` en la línea de comandos se anula el `#SBATCH --array` del archivo.

**Plan B**, si alguna franja falla y no hay tiempo de repetirla:

```bash
sbatch --export=ALL,RUN_DIR=<run_dir>,NUM_STRIPES=32,ALLOW_MISSING=1 jobs/t5_merge.slurm
```

En ese caso la app debe decir "cobertura parcial: X % de los candidatos".

---

## 5. `tests/test_earth_features.py` (sintéticas)

1. **`test_parse_tile_cell`**:
   - `S78_00_E162` da `(-78, 162)`;
   - `N00_00_W001` da `(0, -1)`;
   - `N89_00_E179` da `(89, 179)`;
   - un nombre inválido lanza `ValueError`.
2. **`test_has_tile_negative_floor`**: con `cells = {(-1, -1)}`, `(-0.5, -0.5)` da True y `(0.5, -0.5)` da False.
3. **`test_build_vrt_masks_sea`** (`skipif` si `shutil.which('gdalbuildvrt')` es None):
   - Dos tiles sintéticos de 1° × 1° en EPSG:4326 a 1/1200° y sin nodata: uno de tierra (z = 100 + rampa) y otro con la mitad oeste en 0.0 (mar).
   - En el VRT, `src.nodata == -9999` y un píxel de mar se lee como −9999.
   - `extract_patch` sobre el mar da `None`; sobre tierra, un arreglo 64×64.
4. **`test_build_vrt_mixed_widths`** (`skipif` igual):
   - Un tile de 1200 × 1200 en lat 69–70 y uno de 1200 × 400 (alto × ancho) en lat 70–71.
   - El VRT se construye y un parche centrado en la costura (lat 70.0) no tiene huecos: todo finito.
5. **`test_build_vrt_does_not_overwrite`**: si `vrt_path` ya existe, `build_vrt` no lo modifica (misma fecha de modificación).
6. **`test_prefilter_counts`**: un `EarthLayers.from_arrays` sintético (de T6) y 5 puntos: sin tile, NDVI 0.4, NDVI 0.2, NDVI NaN con LST finito (hielo) y NDVI NaN con LST NaN (mar). Resultado:
   - máscara `[F, F, T, T]`;
   - máscara `[F, F, T, T, F]`; `ndvi_missing` solo en el cuarto;
   - conteos `{grid: 5, no_tile: 1, vegetated: 1, no_land_data: 1, ndvi_missing: 1, kept: 2}`.
7. **`test_merge_join`**: `candidates.parquet` con 5 filas y dos franjas con 2 y 1 filas válidas. El resultado tiene 3 filas, las `EARTH_COLUMNS` exactas, `body == 'Earth'`, y las columnas de T6 copiadas bien.
   - Si falta una franja, `merge_earth` falla; con `allow_missing=True`, funciona.

---

## 6. Criterios de aceptación

### 6.1 `prepare`, en su log y en `prefilter_stats.json`

- `grid = 497,818` y `grid − no_tile = 179,663`, exactos.
- `kept` entre 35,000 y 80,000. La estimación con la caché de T6 es ~45,000: 30,245 con NDVI ≤ 0.25 más ~15,000 en la Antártida. Si sale fuera de ese rango, **parar y avisar** antes de lanzar el array.
- Imprimir `ndvi_missing` y `no_land_data` con su distribución por latitud. Se espera que `ndvi_missing` esté casi todo al sur de −60°.

### 6.2 Prueba (`bash jobs/t5_submit.sh --limit 500`)

- Las tres etapas terminan sin error.
- Al menos el 70 % de los 500 son válidos. Los que no pasan son sobre todo parches costeros con más del 10 % de mar.
- La franja tarda menos de 5 minutos.
- En `features_earth.parquet`, `mean_elev_m` está entre −500 y 7000 m, y `mean_slope_deg` tiene una mediana entre 0.5° y 6°.

### 6.3 Corrida completa (`merge` → `t5_checks.json`)

**Duros:**

| # | Verificación | Criterio |
| --- | --- | --- |
| 1 | Parches válidos | Entre 30,000 y 80,000. El plan general decía 40–120 mil antes de tener datos; con la caché de T6 se esperan ~45 mil candidatos, menos los costeros que el VRT descarta. Si sale menos de 30 mil, revisar la máscara de mar del VRT |
| 2 | Amazonía `lat ∈ [-10, 2], lon ∈ [-75, -50]` | ≤ 5 parches, y listarlos |
| 3 | Congo `lat ∈ [-5, 5], lon ∈ [12, 30]` | ≤ 5, listarlos |
| 4 | Indonesia ecuatorial `lat ∈ [-5, 5], lon ∈ [95, 120]` | ≤ 5, listarlos |
| 5 | Presentes (≥ 1 parche cada uno): Atacama `known_region == 'atacama'`; Sahara `lat ∈ [15, 30], lon ∈ [-10, 30]`; Sonora `lat ∈ [28, 33], lon ∈ [-115, -110]`; Australia central `lat ∈ [-28, -20], lon ∈ [125, 138]`; Valles Secos `known_region == 'mcmurdo-dry-valleys'` | Todos presentes |
| 6 | Unión con `candidates` | Sin filas huérfanas; ninguna columna de T6 totalmente NaN |

El plan general pedía "ningún parche" en la Amazonía, el Congo e Indonesia. Aquí se toleran hasta 5, porque la mediana del NDVI de un parche sobre un claro, una mina o un pueblo podría bajar de 0.25. Si son más de 5, el filtro está mal.

**Blandos** (imprimir y avisar si salen raros):

| # | Verificación | Esperado |
| --- | --- | --- |
| 7 | Conteo por `known_region` | Imprimir las 12. Algunas pueden tener 0 por vegetación (Islandia, Hawái, Svalbard, Río Tinto); eso no es error, pero hay que anotarlo en la bitácora porque afecta qué análogos conocidos aparecen en la app |
| 8 | `NEW_CANDIDATE` frente a `KNOWN_ANALOG` | Imprimir proporción; se espera más del 95 % `NEW_CANDIDATE` |
| 9 | Por país | Imprimir el top 15 de países por número de parches. México debe aparecer |
| 10 | `ndvi_missing` | Imprimir cuántos válidos tienen `ndvi_missing` |
| 11 | Mapa | En `map_earth_mean_slope_deg.png` se reconocen los Andes, el Himalaya y el Tíbet, el Sahara plano y la meseta antártica |

---

## 7. Comandos para Owen en Yuca

Por SSH o en la terminal de Open OnDemand, desde `/lustre/proyectos/p089/code`. **Requisito:** T6 ya corrió y su caché existe.

```bash
cd /lustre/proyectos/p089/code && git pull && ls -la /lustre/proyectos/p089/data/derived/
```

```bash
sbatch -A p089 -p cpu --time=00:15:00 --mem=4G -o /lustre/proyectos/p089/output/tests_t5_%j.log --wrap 'bash -c "source /apps/miniconda3/etc/profile.d/conda.sh && conda activate spaceapps_2026 && cd /lustre/proyectos/p089/code && pytest -q tests"'
```

```bash
bash jobs/t5_submit.sh --limit 500
```

```bash
squeue -u owen
```

Revisar `t5_prepare_<PREP>.log`, `t5_earth_<ARR>_0.log` y `t5_merge_<MRG>.log` en `/lustre/proyectos/p089/output/`. Si todo cumple el §6.2:

```bash
bash jobs/t5_submit.sh
```

Al terminar, empaquetar la salida para el kit offline (unos MB), porque T7 la necesita para desarrollar en la laptop:

```bash
cd /lustre/proyectos/p089 && tar -czf kit/t5_<PREP>.tar.gz runs/<PREP>/features_earth.parquet runs/<PREP>/prefilter_stats.json runs/<PREP>/t5_checks.json runs/<PREP>/map_earth_*.png
```

---

## 8. Bitácora y documentación

- **`docs/logbook.md`:** entrada nueva con los JOBID de prepare, array y merge, `prefilter_stats` y la tabla de verificaciones. Aclarar que el código lo escribió Gemini a partir de este plan.
- **`docs/pipeline.md`:**
  - el VRT en datos derivados;
  - la nota "Copernicus: sin nodata, mar = 0.0, ancho variable por latitud";
  - la excepción del directorio de corrida compartido;
  - la corrida.
- **`docs/handoff.md`:** T5 hecho, con `runs/<PREP>/features_earth.parquet` como entrada de T7.
- **`docs/working_without_ssh.md`:** agregar el kit `t5_<PREP>.tar.gz` a la sección del kit.

---

## 9. Qué NO hacer

- No modificar `geo.py` ni `features.py`: la Tierra usa las mismas funciones que Marte y la Luna.
- No tratar 0.0 como elevación válida ni filtrar el mar en Python con umbrales: lo hace el VRT.
- No cargar `EarthLayers` en las tareas del array.
- No sobrescribir `copernicus_90m.vrt`; si hay que rehacerlo, mover el viejo a `/lustre/proyectos/p089/_to_delete/`.
- No lanzar la corrida completa sin revisar la de `--limit 500`, y no reenviar el array completo si falla: diagnosticar con el log de la franja que falló y reenviar solo esa: `sbatch --array=<i> --export=ALL,RUN_DIR=<run_dir>,NUM_STRIPES=32 jobs/t5_earth_features.slurm`, y después el `merge` con el mismo `--export`.

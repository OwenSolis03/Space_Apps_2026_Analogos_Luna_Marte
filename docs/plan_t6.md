# Plan detallado T6: capas terrestres (NDVI, LST, logística, país y análogos conocidos)

Especificación completa de T6. Amplía la sección T6 de [plan_implementacion.md](plan_implementacion.md). Si algo choca, **este documento manda para T6**. Escrito por Claude el 2026-11-13 sobre `main` en `115e0c3`, con los datos de Yuca revisados ese día.

T6 no barre la Tierra (eso es T5). T6 entrega:

1. Dos rasters derivados en caché (NDVI máximo y LST anual de 2023).
2. Una clase que, dados muchos puntos (lat, lon), devuelve **todas** las columnas terrestres que T5 adjunta a cada parche.

T5 solo importa esa clase.

---

## 0. Resumen

| Qué | Dónde |
| --- | --- |
| Lectura de MODIS y cálculo de NDVI máximo y LST anual | `pipeline/earth_layers.py` |
| Regiones análogas conocidas (escrito a mano, va al repo) | `pipeline/data/known_analogs.json` |
| Rutas nuevas | `pipeline/config.py` |
| Job: construir caché y verificar | `jobs/t6_earth_layers.slurm` |
| Pruebas | `tests/test_earth_layers.py` |
| Caché compartida (no va al repo) | `data/derived/ndvi_max_2023.tif`, `data/derived/lst_2023.tif` |
| Salidas de la corrida | `runs/<JOBID>/t6_checks.json`, `map_ndvi_max.png`, `map_lst_amplitude.png`, `map_known_analogs.png` |

Commit: `T6: capas terrestres (NDVI, LST, logística, regiones conocidas)`. **Commitear antes de enviar el job**, para que el log registre el commit correcto (en T4 el log de la corrida registró `0e1e43c` porque el job corrió antes del commit).

---

## 1. Hechos verificados en Yuca (no asumir otra cosa)

**MODIS: GDAL no puede leerlo.** El GDAL del entorno `spaceapps_2026` (3.12.3) **no tiene el plugin HDF4**: `gdalinfo` y `rasterio` no abren los `.hdf`. `pyhdf` **sí** está instalado y funciona. Por lo tanto:

- Leer con `from pyhdf.SD import SD, SDC`, haciendo `SD(path, SDC.READ).select(<nombre>).get()`.
- Hacer el `import pyhdf` **dentro** de las funciones que leen HDF, no arriba del módulo. Así las pruebas corren en la laptop aunque `pyhdf` no esté instalado.
- No instalar `libgdal-hdf4` ni tocar el entorno de conda.

**MOD13C2 (NDVI), 12 archivos en `data/raw/earth/modis/ndvi/`, uno por mes de 2023:**

| SDS | Tipo | Atributos reales |
| --- | --- | --- |
| `CMG 0.05 Deg Monthly NDVI` | int16, 3600 × 7200 | `scale_factor=10000.0`, `_FillValue=-3000`, `valid_range=[-2000, 10000]` |
| `CMG 0.05 Deg Monthly pixel reliability` | int8 | `valid_range=[0, 4]`, `_FillValue=-1` |

- ⚠️ **Convención MODIS VI: `NDVI = crudo / 10000`.** Se **divide** por el `scale_factor`, no se multiplica. Escribir la constante explícita, `NDVI_DIVISOR = 10000.0`, y no leer el atributo de forma genérica.

**MOD11C3 (LST), 12 archivos en `data/raw/earth/modis/lst/`:**

| SDS | Tipo | Atributos reales |
| --- | --- | --- |
| `LST_Day_CMG`, `LST_Night_CMG` | uint16, 3600 × 7200 | `scale_factor=0.02`, `_FillValue=0`, `valid_range=[7500, 65535]`, unidades K |

- ⚠️ **Aquí se multiplica:** `K = crudo · 0.02`, y luego `°C = K − 273.15`. Constante explícita: `LST_SCALE = 0.02`.

**Malla común a los dos productos** (`StructMetadata.0`):

- `Projection=GCTP_GEO`, `UpperLeft=(-180, 90)`, `LowerRight=(180, -90)`, 7200 × 3600.
- Es decir: **EPSG:4326, celda de 0.05°, fila 0 = 90°N, columna 0 = 180°W**.
- Transformación: `rasterio.transform.from_origin(-180.0, 90.0, 0.05, 0.05)`.

**Natural Earth (`data/raw/earth/naturalearth/`, EPSG:4326):**

| Capa | Datos verificados |
| --- | --- |
| `ne_10m_roads` | 56,600 líneas, 709,166 vértices. `featurecla` ∈ {`Road`: 56,312, `Ferry`: 288}. **Excluir `Ferry`** |
| `ne_10m_airports` | 893 puntos. `type` ∈ {`mid` 475, `major` 369, `mid and military` 14, `major and military` 14, `military mid` 10, `military major` 4, `spaceport` 3, `small` 2, `military` 2}. Tiene las columnas `name`, `iata_code` |
| `ne_10m_admin_0_countries` | 258 polígonos, columna `ADMIN` |

Natural Earth no tiene carreteras en la Antártida, así que ahí `dist_road_km` será muy grande. Es correcto: los Valles Secos son logísticamente remotos.

---

## 2. `pipeline/config.py`: agregar

```python
EARTH_RAW_FILES: dict[str, str] = {
    "ndvi_dir": "earth/modis/ndvi",
    "lst_dir": "earth/modis/lst",
    "roads": "earth/naturalearth/ne_10m_roads/ne_10m_roads.shp",
    "airports": "earth/naturalearth/ne_10m_airports/ne_10m_airports.shp",
    "countries": "earth/naturalearth/ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp",
}
EARTH_DERIVED_FILES: dict[str, str] = {
    "ndvi_max": "ndvi_max_2023.tif",
    "lst": "lst_2023.tif",
}
MODIS_CMG_RES_DEG: float = 0.05
```

Todas las rutas son relativas a `<project_dir>/data/raw` y a `<project_dir>/data/derived`. Nada en T6 debe usar `/lustre/...` directamente: así funciona igual con el kit offline (`--project-dir ~/p089_offline`).

---

## 3. `pipeline/earth_layers.py`

### 3.1 Funciones puras (sin E/S; se prueban con arreglos sintéticos)

```python
NDVI_SDS = "CMG 0.05 Deg Monthly NDVI"
NDVI_FILL = -3000
NDVI_DIVISOR = 10000.0
NDVI_MIN_VALID = -0.3          # valores menores -> NaN (agua/ruido), como dice el plan general
LST_DAY_SDS, LST_NIGHT_SDS = "LST_Day_CMG", "LST_Night_CMG"
LST_FILL = 0
LST_MIN_RAW = 7500
LST_SCALE = 0.02
KELVIN_0C = 273.15
MIN_MONTHS_LST = 3             # meses válidos mínimos para la media anual

def ndvi_from_raw(raw: np.ndarray) -> np.ndarray:
    """int16 -> float32. Fill, crudo < -2000 o > 10000 -> NaN; luego /10000; < -0.3 -> NaN."""

def lst_c_from_raw(raw: np.ndarray) -> np.ndarray:
    """uint16 -> float32 °C. Fill (0) o crudo < 7500 -> NaN; luego crudo*0.02 - 273.15."""

def running_nanmax(acc: np.ndarray | None, x: np.ndarray) -> np.ndarray:
    """Máximo acumulado ignorando NaN (np.fmax). acc=None -> copia de x."""

def running_sum_count(sum_: np.ndarray | None, cnt: np.ndarray | None, x: np.ndarray
                      ) -> tuple[np.ndarray, np.ndarray]:
    """Acumula suma (float64) y conteo (uint8) de valores finitos."""

def finalize_mean(sum_, cnt, min_count) -> np.ndarray:
    """sum/cnt como float32; NaN donde cnt < min_count."""

def cell_index(lat: np.ndarray, lon: np.ndarray, res: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """Fila y columna de la celda que contiene cada punto en la malla CMG.
    row = floor((90 - lat)/res) recortado a [0, 3599]; col = floor((lon + 180)/res) recortado a [0, 7199].
    lon se normaliza antes a [-180, 180)."""

def patch_window_stat(grid: np.ndarray, lat: np.ndarray, lon: np.ndarray, half_km: float,
                      stat: str, res: float = 0.05) -> np.ndarray:
    """Estadístico (stat ∈ {'median','mean','max'}) de las celdas dentro del cuadrado del parche:
    medio lado en latitud = degrees(half_km / 6371.0); en longitud = ese valor / max(cos(lat), 0.05).
    Celdas por fila y columna con cell_index en las esquinas; en longitud, envolver con módulo 7200
    (el antimeridiano no se salta aquí: es una malla global). Ignora NaN; todo NaN -> NaN.
    Vectorizar por punto con un bucle simple: son <= ~150k puntos y ventanas de <= ~15x40 celdas."""
```

**Por qué la ventana y no la celda central:** un parche de 32 km cubre ~6 × 6 celdas de 0.05° en el ecuador. Con la celda central, un oasis o un río podrían cambiar la clasificación del parche entero.

**Estadístico de cada variable:**

| Variable | Estadístico | Por qué |
| --- | --- | --- |
| `ndvi_max` | mediana (`median`) | Representa al parche y no a una franja de vegetación |
| `lst_day_c`, `lst_night_c`, `lst_amplitude_c` | media (`mean`) | — |

### 3.2 Construcción de la caché (solo en el job)

```python
def build_ndvi_max(ndvi_dir: Path, out_tif: Path) -> Path:
    """Lee los 12 MOD13C2 (ordenados por nombre) uno por uno con pyhdf, aplica ndvi_from_raw y
    acumula running_nanmax y el conteo de meses válidos. Escribe GeoTIFF de 2 bandas:
      banda 1 ndvi_max (float32, nodata NaN), banda 2 n_months (uint8 guardado como float32).
    EPSG:4326, from_origin(-180, 90, 0.05, 0.05), compress='deflate', tiled=True, BIGTIFF='IF_SAFER'.
    Escribir a out_tif.with_suffix('.tmp.tif') y os.replace al final (atómico).
    Falla con ValueError si no hay exactamente 12 archivos o si algún SDS no tiene forma (3600, 7200)."""

def build_lst(lst_dir: Path, out_tif: Path) -> Path:
    """Igual con los 12 MOD11C3: medias anuales con finalize_mean(min_count=3) de día y de noche.
    Escribe 3 bandas float32: 1 lst_day_c, 2 lst_night_c, 3 lst_amplitude_c = día - noche
    (NaN si falta cualquiera). Mismos parámetros de escritura."""

def ensure_cache(project_dir: Path, force: bool = False) -> dict[str, Path]:
    """Construye lo que falte en data/derived/. Si ya existe, no lo toca.
    Con force=True NO sobrescribe: falla y pide mover el archivo viejo a _to_delete/ a mano
    (regla de Yuca: nunca sobrescribir)."""
```

Memoria: se procesa un mes a la vez. Los acumuladores son 3600 × 7200 en float64 (~207 MB c/u), así que el pico está por debajo de 2 GB.

### 3.3 Logística, país y regiones conocidas

```python
ROAD_DENSIFY_DEG = 0.02        # ~2.2 km: error máximo por vértice ~1.1 km
AIRPORT_EXCLUDE_TYPES = {"military", "military mid", "military major", "spaceport"}
EARTH_RADIUS_KM = 6371.0

class Logistics:
    def __init__(self, roads_shp: Path, airports_shp: Path): ...
        # Carreteras: featurecla != 'Ferry'; shapely.segmentize(geom, ROAD_DENSIFY_DEG);
        # tomar todos los vértices (shapely.get_coordinates); BallTree(np.radians([[lat, lon]]),
        # metric='haversine'). Imprimir el número de vértices tras densificar.
        # Aeropuertos: type no en AIRPORT_EXCLUDE_TYPES; BallTree igual; guardar name e iata_code.
    def dist_road_km(self, lat, lon) -> np.ndarray: ...
    def nearest_airport(self, lat, lon) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(dist_km float32, iata object, name object); iata vacío o '-' -> None."""

class Countries:
    def __init__(self, countries_shp: Path): ...   # geopandas + .sindex
    def lookup(self, lat, lon, max_coast_km: float = 25.0) -> np.ndarray:
        """ADMIN del polígono que contiene el punto (geopandas.sjoin con predicate='within').
        Si ninguno lo contiene (costa, islas pequeñas), usar el país más cercano solo si está a
        <= 25 km (sjoin_nearest en EPSG:4087 con max_distance=25_000). Si no, None."""

class KnownRegions:
    def __init__(self, json_path: Path = KNOWN_ANALOGS_JSON): ...  # valida (ver sección 4)
    def lookup(self, lat, lon) -> np.ndarray:
        """id de la primera región cuyo bbox contiene el CENTRO del parche, o None."""
    def name_of(self, region_id: str) -> str: ...
```

### 3.4 Fachada que usa T5

```python
EARTH_ENV_COLUMNS = ["ndvi_max", "lst_day_c", "lst_night_c", "lst_amplitude_c",
                     "dist_road_km", "dist_airport_km", "nearest_airport_iata",
                     "nearest_airport_name", "country", "known_region", "classification"]

class EarthLayers:
    @classmethod
    def from_project(cls, project_dir: Path, need: set[str] | None = None) -> "EarthLayers":
        """Carga en memoria: ndvi_max (banda 1) y las 3 bandas de LST como arreglos float32,
        más Logistics, Countries y KnownRegions. `need` permite cargar solo una parte
        (ej. {'ndvi'} para el prefiltro). Falla con un mensaje claro si falta la caché:
        'Corre primero jobs/t6_earth_layers.slurm'."""

    def ndvi_prefilter(self, lat, lon, half_km: float = 16.0) -> np.ndarray:
        """ndvi_max del parche (mediana de la ventana). Para el prefiltro de T5 (> 0.25 descarta)."""

    def sample(self, lat, lon, half_km: float = 16.0) -> pd.DataFrame:
        """DataFrame con EARTH_ENV_COLUMNS, una fila por punto, en el mismo orden.
        classification = 'KNOWN_ANALOG' si known_region no es None; si no, 'NEW_CANDIDATE'.
        dtypes: float32 para los numéricos, string para los textos."""
```

Uso de memoria en T5: un `EarthLayers` ocupa ~420 MB (4 mallas de 104 MB más los árboles). T5 lo crea **una vez antes del `fork`** del `Pool`, para que los procesos lo compartan sin copiarlo (copy-on-write). Anotarlo en el docstring.

### 3.5 CLI

```text
python -m pipeline.earth_layers --project-dir P --out-dir RUN_DIR [--build] [--check]
```

- `--build`: llama a `ensure_cache`.
- `--check`: corre la verificación de la sección 6, escribe `t6_checks.json` e imprime una tabla; sale con código 1 si falla un criterio **duro**.
- Los PNG (sección 6.3) se escriben siempre que se pase `--check`.

---

## 4. `pipeline/data/known_analogs.json` (escrito a mano)

Copiar **tal cual**. Los bbox son **aproximados**: los trazó Claude para que contengan las zonas de estudio citadas, no vienen de una fuente oficial. Por eso cada uno lleva `bbox_note`. El criterio de la sección 6 los revisa en un mapa. Formato del bbox: `[lon_min, lat_min, lon_max, lat_max]`.

Validación al cargar (`KnownRegions.__init__`):

- `id` único.
- `lon_min < lon_max` y `lat_min < lat_max`.
- Rangos válidos.
- `source_url` no vacío.

```json
{
  "version": "2026-11-13",
  "notes": "Well-studied terrestrial analog regions. Bounding boxes are approximate (drawn by Claude to contain the cited study areas) and only decide the KNOWN_ANALOG / NEW_CANDIDATE label.",
  "regions": [
    { "id": "atacama", "name": "Atacama Desert", "country": "Chile", "analog_for": ["Mars"],
      "bbox": [-71.5, -30.0, -68.0, -18.0],
      "why": "Hyper-arid desert used for Mars life-detection and rover tests.",
      "source_url": "https://en.wikipedia.org/wiki/Atacama_Desert",
      "bbox_note": "Approximate: coastal range to the Andean foothills, 18-30 S." },
    { "id": "mcmurdo-dry-valleys", "name": "McMurdo Dry Valleys", "country": "Antarctica", "analog_for": ["Mars", "Moon"],
      "bbox": [160.0, -78.5, 164.5, -76.5],
      "why": "Cold, dry, ice-free valleys used as a Mars polar analog.",
      "source_url": "https://en.wikipedia.org/wiki/McMurdo_Dry_Valleys",
      "bbox_note": "Approximate: Victoria Land dry valleys." },
    { "id": "iceland", "name": "Iceland", "country": "Iceland", "analog_for": ["Mars", "Moon"],
      "bbox": [-24.6, 63.2, -13.4, 66.7],
      "why": "Basaltic volcanism, lava fields and glaciers; Apollo astronauts trained there.",
      "source_url": "https://en.wikipedia.org/wiki/Iceland",
      "bbox_note": "Whole island." },
    { "id": "hawaii-big-island", "name": "Hawaii (Mauna Kea / Kilauea)", "country": "United States", "analog_for": ["Mars", "Moon"],
      "bbox": [-156.1, 18.9, -154.8, 20.3],
      "why": "Basaltic shield volcanoes and lava tubes used for ISRU and habitat tests.",
      "source_url": "https://en.wikipedia.org/wiki/Mauna_Kea",
      "bbox_note": "Island of Hawaii." },
    { "id": "devon-island", "name": "Devon Island (Haughton crater)", "country": "Canada", "analog_for": ["Mars", "Moon"],
      "bbox": [-96.0, 74.5, -79.5, 76.8],
      "why": "Polar desert with the Haughton impact crater; home of the Haughton-Mars Project.",
      "source_url": "https://en.wikipedia.org/wiki/Haughton_impact_crater",
      "bbox_note": "Approximate: whole island." },
    { "id": "utah-mdrs", "name": "Utah (MDRS, Hanksville)", "country": "United States", "analog_for": ["Mars"],
      "bbox": [-111.4, 37.9, -110.2, 38.9],
      "why": "Red sedimentary badlands around the Mars Desert Research Station.",
      "source_url": "https://en.wikipedia.org/wiki/Mars_Desert_Research_Station",
      "bbox_note": "Approximate: about 50 km around Hanksville." },
    { "id": "rio-tinto", "name": "Rio Tinto", "country": "Spain", "analog_for": ["Mars"],
      "bbox": [-7.0, 37.1, -6.4, 37.8],
      "why": "Acidic, iron-rich river used as an analog for Meridiani-type environments.",
      "source_url": "https://en.wikipedia.org/wiki/Rio_Tinto_(river)",
      "bbox_note": "Approximate: river basin from the source to the estuary." },
    { "id": "svalbard", "name": "Svalbard", "country": "Norway", "analog_for": ["Mars"],
      "bbox": [10.0, 76.4, 34.0, 80.9],
      "why": "Arctic volcanic and permafrost sites (AMASE expeditions).",
      "source_url": "https://en.wikipedia.org/wiki/Svalbard",
      "bbox_note": "Whole archipelago." },
    { "id": "pilbara", "name": "Pilbara", "country": "Australia", "analog_for": ["Mars"],
      "bbox": [116.0, -23.5, 121.5, -20.0],
      "why": "Archean stromatolites; reference for ancient biosignatures.",
      "source_url": "https://en.wikipedia.org/wiki/Pilbara",
      "bbox_note": "Approximate: Pilbara Craton outcrop area, not the whole administrative region." },
    { "id": "meteor-crater", "name": "Meteor Crater", "country": "United States", "analog_for": ["Moon", "Mars"],
      "bbox": [-111.35, 34.75, -110.70, 35.30],
      "why": "Well-preserved simple impact crater; Apollo crews trained there.",
      "source_url": "https://en.wikipedia.org/wiki/Meteor_Crater",
      "bbox_note": "Approximate: about 30 km around the crater, larger than a 32 km patch." },
    { "id": "lanzarote", "name": "Lanzarote", "country": "Spain", "analog_for": ["Mars", "Moon"],
      "bbox": [-13.88, 28.83, -13.40, 29.25],
      "why": "Basaltic lava fields and lava tubes; ESA PANGAEA training site.",
      "source_url": "https://en.wikipedia.org/wiki/Lanzarote",
      "bbox_note": "Whole island." },
    { "id": "mojave", "name": "Mojave Desert", "country": "United States", "analog_for": ["Mars", "Moon"],
      "bbox": [-118.0, 34.0, -114.5, 36.5],
      "why": "Arid desert used for rover field tests (JPL Mars Yard trials, Mojave volcanic fields).",
      "source_url": "https://en.wikipedia.org/wiki/Mojave_Desert",
      "bbox_note": "Approximate core of the desert; excludes the Colorado Desert." }
  ]
}
```

En la presentación, si se habla de esta lista, decir que los bbox son aproximados. No hace falta ser más precisos: solo deciden la etiqueta y nunca entran al puntaje.

---

## 5. `tests/test_earth_layers.py` (solo datos sintéticos, sin `pyhdf`)

1. **`test_ndvi_from_raw`**: `[-3000, -2500, -2000, 0, 2500, 10000, 12000]` da `[nan, nan, -0.2, 0.0, 0.25, 1.0, nan]`. El fill y lo que sale de `valid_range` da NaN; `-2000` es válido y da `-0.2`.
2. **`test_lst_c_from_raw`**: `0` da NaN, `7499` da NaN, `14658` da `20.01 °C` (±0.01), y `65535` da un valor finito.
3. **`test_running_ops`**: tres "meses" de 2 × 2 con NaN intercalados. Comprueba que el `nanmax` es correcto, que la media exige `min_count` y que una celda con 2 meses válidos y `min_count=3` da NaN.
4. **`test_cell_index_edges`**: `(90, -180)` da `(0, 0)`; `(-90, 180)` da `(3599, 0)`, porque `lon` 180 se normaliza a −180; `(0, 0)` da `(1800, 3600)`.
5. **`test_patch_window_stat_antimeridian`**: malla con 1.0 en la columna 0 y 0.0 en la 7199. `max` en `(0, 179.99)` con `half_km = 16` da 1.0, porque la ventana envuelve el antimeridiano.
6. **`test_patch_window_stat_lat`**: a 60° de latitud la ventana tiene ~2 veces más columnas que en el ecuador (±1).
7. **`test_logistics_densify`**: un `GeoDataFrame` con **una** línea de 2 vértices de `(0, 0)` a `(0, 10)` (lat 0, lon 0→10) y otra de ferry pegada al punto. Comprueba:
   - `dist_road_km(0.5, 5.0)` ≈ 55.6 km (±1.5). Sin densificar daría ~556 km.
   - El ferry se ignora.
8. **`test_airports_exclude_military`**: un aeropuerto `military` a 1 km y uno `mid` a 50 km: el resultado es el `mid`, a ~50 km.
9. **`test_countries_lookup`**: un polígono sintético "Testland" sobre `[0,1]×[0,1]`.
   - `(0.5, 0.5)` da "Testland";
   - `(0.5, 1.1)`, a ~11 km fuera, da "Testland" por la regla de costa;
   - `(0.5, 3)` da None.
10. **`test_known_regions_real_file`**: carga `pipeline/data/known_analogs.json` real. Comprueba:
    - 12 regiones, ids únicos y bbox válidos;
    - `lookup(38.4064, -110.7919)` (MDRS) da `utah-mdrs`;
    - `lookup(29.07, -110.96)` (Hermosillo) da None.
11. **`test_sample_schema`**: un `EarthLayers` armado a mano con mallas sintéticas (agregar un constructor `EarthLayers.from_arrays(...)` para pruebas). `sample` devuelve exactamente `EARTH_ENV_COLUMNS` y `classification` es correcta.

---

## 6. Job y verificación

### 6.1 `jobs/t6_earth_layers.slurm`

Misma forma que `jobs/t4_targets.slurm` (`#!/usr/bin/env bash`, `set -euo pipefail`, conda, eco con el commit), con estos cambios:

```bash
#SBATCH -J p089-t6-earth-layers
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH -o /lustre/proyectos/p089/output/t6_earth_layers_%j.log
#SBATCH -e /lustre/proyectos/p089/output/t6_earth_layers_%j.log
...
python -c "import pyhdf" || { echo "Falta pyhdf en spaceapps_2026"; exit 2; }
python -m pipeline.earth_layers --project-dir "$PROJECT_DIR" --out-dir "$OUT_DIR" --build --check "$@"
```

`pyhdf` ya está instalado en el entorno. El job **no** debe instalar nada: si falta, que falle. Agregar `pyhdf>=0.10` a `pipeline/requirements.txt` con el comentario `# solo para construir la caché de T6 (Yuca)`.

No hace falta una corrida de prueba aparte: el job completo dura minutos y sus verificaciones son la prueba. Si falla, se diagnostica antes de reenviarlo. Una caché a medias no queda en su lugar, porque se escribe a `.tmp.tif` y luego `os.replace`.

### 6.2 Criterios (en `--check`, escritos en `t6_checks.json`)

**Duros:** si fallan, el job sale con código 1.

| # | Verificación | Criterio |
| --- | --- | --- |
| 1 | Caché | Las mallas de los dos `.tif` son 3600 × 7200 en EPSG:4326 con `from_origin(-180, 90, 0.05, 0.05)` |
| 2 | `ndvi_max` Sahara: parches en `(26.0, 3.0)` (Argelia) y `(24.0, 28.0)` (desierto occidental de Egipto) | < 0.10 |
| 3 | `ndvi_max` Atacama `(-24.5, -69.3)` | < 0.10 |
| 4 | `ndvi_max` Amazonía `(-3.5, -62.0)` y Congo `(0.5, 20.0)` | > 0.70 |
| 5 | `dist_road_km` Hermosillo `(29.07, -110.96)` | < 5 |
| 6 | `country` en Hermosillo / Atacama / Sahara `(26.0, 3.0)` | `Mexico` / `Chile` / `Algeria` |
| 7 | `known_region` en MDRS `(38.4064, -110.7919)` y Hermosillo | `utah-mdrs` / None |
| 8 | Fracción de celdas de tierra con `ndvi_max` finito | > 0.25 de toda la malla (la tierra ocupa ~29 % del globo) |

**Blandos:** se reportan pero no hacen fallar el job. Si alguno falla, avisar.

| # | Verificación | Esperado |
| --- | --- | --- |
| 9 | `lst_day_c` Valles Secos `(-77.5, 162.0)` | < 0 °C |
| 10 | `lst_amplitude_c` Sahara `(26.0, 3.0)` frente a Amazonía | Sahara > 15 °C y mayor que Amazonía |
| 11 | `dist_road_km` Valles Secos | > 1000 km (no hay carreteras en la Antártida) |
| 12 | Fracción de la malla con `ndvi_max ≤ 0.25` | Imprimirla; es la estimación de cuántos parches pasan el prefiltro de T5. El plan general espera entre 40 y 120 mil parches terrestres válidos |
| 13 | Tiempo de `EarthLayers.sample` sobre 10,000 puntos aleatorios en tierra | Imprimirlo; debe ser < 30 s para que T5 no se atore |

### 6.2.1 Ajustes tras la primera corrida (job `2242426`, decididos por Claude el 2026-11-13)

Los dos criterios duros que fallaron estaban mal planteados en este plan; el código y los datos son correctos.

- **#2:** el umbral del Sahara pasa a **`< 0.12`**. El suelo desnudo brillante da NDVI de 0.05–0.12: en `(24.0, 28.0)` los 12 meses tienen confiabilidad 0 ("good") y la mediana del máximo es 0.103. Sigue muy lejos del corte de 0.25 del prefiltro.
- **#8:** la fracción de celdas con `ndvi_max` finito se mide **ponderada por área** (`cos(lat)`) y debe ser `> 0.25`. El valor medido es 0.2696. La versión sin ponderar sobrerrepresenta los polos, y MOD13C2 no tiene datos al sur de −59.45°.
- Consecuencia para T5: un NDVI NaN pasa el prefiltro solo si hay LST (ver `plan_t5.md` §2.5.3).

### 6.3 PNG en `runs/<JOBID>/`

Imágenes de control, no para la presentación:

- **`map_ndvi_max.png`:** la malla submuestreada ×4, con `cmap='YlGn'`, `vmin=0`, `vmax=0.9` y contorno de NDVI = 0.25 en rojo.
- **`map_lst_amplitude.png`:** igual, con `cmap='magma'`.
- **`map_known_analogs.png`:** NDVI en gris con los 12 bbox dibujados y etiquetados. Hay que revisar a ojo que cada rectángulo cae sobre su región.

---

## 7. Comandos para Owen en Yuca

Por SSH o en la terminal de Open OnDemand, desde `/lustre/proyectos/p089/code`:

```bash
cd /lustre/proyectos/p089/code && git pull
```

```bash
sbatch -A p089 -p cpu --time=00:15:00 --mem=4G -o /lustre/proyectos/p089/output/tests_t6_%j.log --wrap 'bash -c "source /apps/miniconda3/etc/profile.d/conda.sh && conda activate spaceapps_2026 && cd /lustre/proyectos/p089/code && pytest -q tests"'
```

```bash
sbatch jobs/t6_earth_layers.slurm
```

```bash
tail -n 80 /lustre/proyectos/p089/output/t6_earth_layers_<JOBID>.log
```

Después se bajan por OOD Files los 3 PNG de `runs/<JOBID>/` para revisarlos. Agregar `data/derived/ndvi_max_2023.tif` y `lst_2023.tif` al kit offline **no** hace falta (~200 MB cada uno). En la laptop, las pruebas usan mallas sintéticas.

---

## 8. Bitácora y documentación (mismo commit, y una actualización tras el job)

- **`docs/bitacora.md`:** entrada nueva con lo hecho, el JOBID, la tabla de verificaciones (duras y blandas) y la nota de que el código lo escribió Gemini a partir de este plan.
- **`docs/pipeline.md`:**
  - en la tabla de datos, agregar las dos cachés derivadas;
  - en la tabla de escalas, agregar MOD13C2 (`/10000`, fill −3000) y MOD11C3 (`×0.02`, fill 0) con la advertencia de convenciones opuestas;
  - la nota "GDAL sin HDF4: usar pyhdf";
  - la corrida T6.
- **`docs/progreso_handoff.md`:** T6 como hecho, con el JOBID y las rutas de la caché.

---

## 9. Qué NO hacer

- No leer el `scale_factor` de MODIS de forma genérica (`valor * scale_factor`): en MOD13C2 daría NDVI × 10000.
- No instalar `libgdal-hdf4` ni modificar el entorno de conda.
- No sobrescribir la caché; si hay que rehacerla, mover la vieja a `/lustre/proyectos/p089/_to_delete/`.
- No usar `known_region` ni `country` en el puntaje: solo etiquetan.
- No inventar coordenadas ni bbox nuevos. Si una región parece mal trazada en `map_known_analogs.png`, reportarlo y proponer el cambio.
- No importar los scripts v1 de la raíz.

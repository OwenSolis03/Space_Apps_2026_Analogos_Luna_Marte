# Plan detallado T4: blancos curados y clusters

Especificación completa de T4 para implementarla sin adivinar. Amplía la sección T4 de [plan_implementacion.md](plan_implementacion.md); si algo choca, **este documento manda para T4**. Escrito por Claude el 2026-11-13 con el código de `main` en `51678d9` y la corrida T3 `2242278`.

Leer antes: sección 0 (reglas) de `plan_implementacion.md`, y `pipeline/planet_features.py` completo.

---

## 0. Resumen

| Qué | Dónde |
| --- | --- |
| Definición de blancos curados (escrita a mano, va al repo) | `pipeline/data/targets.json` |
| Soporte polar en la extracción de parches (solo para Shackleton) | `pipeline/geo.py` (T4.0) |
| Muestreo de un punto con el mismo código de T3 | `pipeline/planet_features.py` (refactor sin cambio de comportamiento) |
| Nomenclatura IAU reutilizable | `pipeline/iau.py` (nuevo) |
| Rasgos de curados, clusters, salida | `pipeline/targets.py` (nuevo) |
| Job | `jobs/t4_targets.slurm` (nuevo) |
| Pruebas | `tests/test_targets.py`, `tests/test_iau.py` (nuevos) y 2 pruebas nuevas en `tests/test_geo.py` |
| Salidas de la corrida (no van al repo) | `runs/<JOBID>/targets.parquet`, `targets_patches.parquet`, `targets.json`, `clusters_{mars,moon}.parquet`, `map_targets_{mars,moon}.png` |

Commits sugeridos: `T4.0: soporte de parches que contienen el polo` y `T4: blancos curados y clusters`. Si prefieren uno solo, que sea `T4: ...` y que la bitácora mencione ambas partes.

**Idioma:** el código, los comentarios y los logs van en español, como en el resto del pipeline. Los textos que ve el usuario de la app (`name`, `category`, `why`) van en **inglés**, porque la interfaz es en inglés (ver bitácora T10).

---

## 1. Decisiones que ya están tomadas (no cambiarlas sin avisar)

1. **NASA no publica coordenadas del centro de las regiones de Artemis III.** El comunicado del 2024-10-28 y el resumen de LPSC 2026 (NTRS 20250011660) solo dan nombres. Por eso cada región se ancla en el rasgo IAU del mismo nombre, tomado del gacetero que ya está en Yuca (`data/raw/nomenclature/MOON_nomenclature_center_pts.*`). El JSON lo declara en `anchor.note`, y la app debe decir "approximate location".
2. **Regiones fusionadas:** "Nobile Rim 1" y "Nobile Rim 2" son un solo blanco (`moon-a3-nobile-rim`). "Mons Mouton" y "Mons Mouton Plateau" también son uno (`moon-a3-mons-mouton`). Con el mismo ancla darían rasgos idénticos, y contarlas dos veces engañaría.
3. **Tipos de ancla:**
   - `point`: parche central más 4 vecinos desplazados 16 km a los acimuts 0°, 90°, 180° y 270°. Son 5 parches.
   - `rim`: 8 parches centrados sobre el borde del cráter, a `radius_km = diámetro_IAU / 2` del centro, en los acimuts 0°, 45°, …, 315°. Este ancla representa una región de borde ("Rim").
4. **Mínimo de parches válidos:** `point` necesita ≥ 3 de 5 y `rim` ≥ 5 de 8. Si no se cumple, el blanco queda con `status = "insufficient_coverage"`, sin rasgos, y no pasa a T7.
5. **Rasgos del blanco** = media (`nanmean`) de los rasgos de sus parches válidos, calculados con **exactamente** `_process_point` de T3. Esa es la garantía de comparabilidad.
6. **Clusters:** k-means con k = 30 por cuerpo sobre los 6 rasgos geomorfométricos (sin `mean_elev_m`). Antes se aplica `log1p` a `relief_m`, `detrended_std_m` y `tri_m`, y después se estandariza por cuerpo. Es la misma transformación que usará T7. El representante es un **parche real** de T3: el miembro más cercano al centroide.
7. **No importar `enrich_nomenclature.py`.** No tiene `if __name__ == "__main__"`: al importarlo se ejecuta y reescribe `/lustre/proyectos/p089/output/planetary_baselines.json`. Ya pasó una vez el 2026-11-13; el archivo quedó idéntico, pero no debe repetirse. Su lógica se **copia** a `pipeline/iau.py`.
8. El gacetero trae `center_lon` en 0–360 °E. Hay que convertirlo siempre a −180…180 con `((lon + 180) % 360) - 180`.

---

## 2. T4.0: soporte polar en `pipeline/geo.py`

**Problema:** Shackleton está en −89.67°. Su parche de 32 km contiene el polo sur. Hoy `extract_patch` lo descarta por dos caminos:

- `_patch_crosses_antimeridian` ve un rango de longitudes > 180°.
- `(right - left) > max_span` en el CRS fuente.

En los dos casos devuelve `None` y suma al contador del antimeridiano.

**Cambio:** antes de la verificación del antimeridiano, detectar si el parche contiene un polo y, si es así, leer una banda completa de filas.

```python
def _patch_contains_pole(lat: float, half_m: float, r_sphere: float) -> int:
    """Devuelve -1 si el parche contiene el polo sur, +1 si contiene el norte y 0 si no.
    Criterio: distancia angular del centro al polo <= semidiagonal angular del parche."""
    half_diag_deg = math.degrees(half_m * math.sqrt(2.0) / r_sphere)
    if 90.0 - lat <= half_diag_deg:
        return 1
    if 90.0 + lat <= half_diag_deg:
        return -1
    return 0
```

Rama polar dentro de `extract_patch`, solo si `has_cut` y `_patch_contains_pole(...) != 0`:

1. No llamar a `_patch_crosses_antimeridian` ni a la verificación `max_span`.
2. Latitud límite de la banda: `lat_edge = lat_polo ∓ (distancia_al_polo + semidiagonal) + margen`. Concretamente, para el polo sur: `lat_lim = -90 + (90 + lat) + half_diag_deg + 0.05`.
3. Ventana fuente: **todas las columnas** (`col_off=0`, `width=src.width`) y las filas desde el borde polar del raster hasta `lat_lim`.
   - Para obtener la fila, transformar `(0, lat_lim)` de lon/lat del cuerpo al CRS fuente con `pyproj.Transformer` (`always_xy=True`) y usar `src.index(x, y)`.
   - Si el CRS es geográfico, usar `src.index(0, lat_lim)` directamente.
4. Lectura reducida igual que hoy, pero con un factor propio para esta rama, porque a 89° el factor actual sale muy chico: `factor_polar = max(1, floor(res_m / res_y_m))`, aplicado **solo al eje Y**. En X reducir a `out_w = min(src.width, 8192)`. Así LOLA (≈ 92 600 columnas) se lee a ~8192 columnas, que a −89° siguen siendo más finas que 500 m. Memoria: ≈ 8192 × (≤ 300 filas) × 4 B < 10 MB.
5. Pasar el arreglo con su `win_transform` a `reproject` exactamente como hoy. El destino AEQD centrado en el parche no tiene costura en el polo; la costura de ±180° del arreglo fuente queda en una sola línea de píxeles y `Resampling.average` la tolera.
6. El resto (umbral de 90 % válidos, limpieza de nodata) no cambia.

**Garantía de que T3 no cambia:** en la grilla de T3 (|lat| ≤ 88) ningún parche contiene el polo.

| Cuerpo | Cuenta | ¿Contiene el polo? |
| --- | --- | --- |
| Luna | semidiagonal 0.75°; 88 + 0.75 < 90 | No |
| Marte | semidiagonal 0.38° | No |
| Tierra | semidiagonal 0.20° | No |

Por lo tanto la rama nueva nunca se activa en T3. Las 17 pruebas existentes deben seguir pasando sin tocarlas.

**Pruebas nuevas en `tests/test_geo.py`:**

- `test_polar_patch_constant`: raster sintético equirectangular de la Luna (CRS `+proj=eqc +R=1737400`, 0.05°/px, cubre −90…−80) con `z = 100` constante. `extract_patch(lat=-89.67, lon=129.78, body="Moon")` devuelve un arreglo 64×64, no `None`, con todos los valores `≈ 100` (±0.01).
- `test_polar_patch_plane`: mismo raster con `z = y_m * tan(5°)` (un plano en coordenadas de la proyección). Comprobar que **no** devuelve `None` y que los valores son finitos en ≥ 90 % de los píxeles. No se exige la pendiente, porque un plano en eqc no es plano cerca del polo.
- `test_antimeridian_count_unchanged`: un parche en lat −60, lon 179.9 sigue devolviendo `None` y suma 1 al contador, igual que antes.

Si T4.0 se complica más de 1 hora, **plan B**: dejar Shackleton con `status = "insufficient_coverage"`. Siguen quedando 7 blancos lunares, por encima del mínimo de 6. Avisar y seguir con el resto de T4.

---

## 3. Refactor en `pipeline/planet_features.py` (sin cambio de comportamiento)

Objetivo: que T4 calcule rasgos de un punto con **el mismo** `_process_point` que T3, sin copiar código.

1. Extraer de `run_body_extraction` la resolución de rutas a una función pública:

```python
def resolve_body_paths(body: str, raw_dir: Path, derived_dir: Path | None,
                       need_diviner: bool,
                       file_overrides: dict[str, Path] | None = None
) -> tuple[Path, dict[str, str], str | None, str | None]:
    """Devuelve (dem_path, aux_paths, diviner_tab_path, diviner_parquet_path).
    Misma lógica que hoy: las capas auxiliares ausentes se omiten con [WARN] y Diviner
    solo se prepara si need_diviner y body == 'Moon'."""
```

   `run_body_extraction` la usa con `need_diviner = any(lat <= -75 for lat, _ in stripe_points)`. Los `[META]` se siguen imprimiendo igual.

2. Agregar un muestreador puntual público:

```python
class PointSampler:
    """Abre el DEM y las capas auxiliares de un cuerpo una vez y calcula la fila T3 de un punto."""
    def __init__(self, body: str, raw_dir: Path, derived_dir: Path,
                 size_km: float = PATCH_SIZE_KM, res_m: float = PATCH_RES_M,
                 file_overrides: dict[str, Path] | None = None): ...
        # Llama a resolve_body_paths(..., need_diviner=True) y a _init_worker(...)
    def sample(self, lat: float, lon: float) -> dict[str, object] | None:
        return _process_point((lat, lon))
    def close(self) -> None: _close_worker()
    def __enter__(self): return self
    def __exit__(self, *exc): self.close()
```

   Nota: `_WORKER_STATE` es global por proceso, así que solo puede haber un `PointSampler` abierto a la vez por proceso. Documentarlo en el docstring y lanzar `RuntimeError` si se abre un segundo sin cerrar el primero.

3. Criterio: `pytest -q tests` sigue en verde y una corrida `--limit 500` de T3 daría las mismas filas. No hace falta correrla; basta con que el diff de `run_body_extraction` sea solo mover código.

---

## 4. `pipeline/iau.py` (nuevo)

Copia limpia de la lógica de `enrich_nomenclature.py`, como funciones y sin efectos al importar.

```python
IAU_SHP: dict[str, str] = {
    "Mars": "nomenclature/MARS_nomenclature_center_pts.shp",
    "Moon": "nomenclature/MOON_nomenclature_center_pts.shp",
}

def load_gazetteer(body: str, raw_dir: Path) -> pd.DataFrame:
    """Lee el gacetero con geopandas (ya en requirements) y devuelve un DataFrame con
    name, type, diameter_km, lat, lon (−180..180), link (https). Descarta filas sin nombre o
    con coordenadas no finitas."""

def haversine_km(lat1, lon1, lat2, lon2, radius_km) -> np.ndarray:  # vectorizada

def iau_label(lat: float, lon: float, gaz: pd.DataFrame, radius_km: float,
              near_km: float = 80.0, major_diam_km: float = 30.0) -> dict[str, object]:
    """Igual que la v1:
    nearest = rasgo más cercano; regional = más cercano con diameter >= 30 km (o todos si no hay);
    display_label = f"{nearest} ({type})" si d_nearest < 80 km, si no f"Near {regional} ({type})".
    Devuelve {nearest_feature, feature_type, distance_km, regional_landmark, regional_type,
    regional_distance_km, display_label, link} con distancias redondeadas a 0.1 km.
    `link` es el del rasgo usado en display_label."""

def find_feature(gaz: pd.DataFrame, name: str) -> pd.Series:
    """Busca por nombre exacto (sin distinguir mayúsculas). KeyError si no existe."""
```

- `radius_km` sale de `BODY_RADII_M[body] / 1000`.
- Convertir `http://planetarynames.wr.usgs.gov/...` a `https://` en `link`.
- Columnas reales del gacetero (verificadas en Yuca): `name`, `clean_name`, `diameter`, `center_lat`, `center_lon`, `type`, `link`, …

`tests/test_iau.py` (con un DataFrame sintético, sin leer archivos):

- Conversión 0–360 → −180…180: `center_lon = 354.83` da `-5.17`.
- `iau_label` a 10 km de un rasgo devuelve su nombre en `display_label`.
- A 200 km de todo, devuelve `"Near <regional> (<type>)"`.
- La distancia haversine entre (0, 0) y (0, 1°) en la Luna es `≈ 30.32 km` (±0.01).

---

## 5. `pipeline/data/targets.json` (nuevo, escrito a mano)

Copiar **tal cual**. Las coordenadas lunares son centros IAU del gacetero de Yuca, ya convertidos a −180…180; las marcianas son puntos de aterrizaje verificados el 2026-11-13. No cambiar ningún número sin una fuente.

Validaciones que hace `load_curated` al cargar el archivo:

- `id` único.
- `body` ∈ {Moon, Mars}.
- `lat` ∈ [−90, 90] y `lon` ∈ [−180, 180].
- `anchor.type` ∈ {point, rim}; si es `rim`, `radius_km > 0`.
- `source_url` y `coord_source_url` no vacíos.

```json
{
  "version": "2026-11-13",
  "notes": "Moon: NASA does not publish center coordinates for Artemis III regions; each is anchored on the IAU feature of the same name (USGS Gazetteer of Planetary Nomenclature). Mars: published landing coordinates.",
  "targets": [
    {
      "id": "moon-a3-haworth",
      "body": "Moon",
      "name": "Haworth rim",
      "category": "Artemis III candidate region",
      "why": "Rim of a permanently shadowed crater near the south pole; candidate landing region with access to cold traps.",
      "lat": -87.45, "lon": -5.17,
      "anchor": { "type": "rim", "iau_feature": "Haworth", "radius_km": 25.71, "note": "Approximate: ring on the rim of IAU crater Haworth (D = 51.4 km)." },
      "source_url": "https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/",
      "coord_source_url": "https://planetarynames.wr.usgs.gov/Feature/14502"
    },
    {
      "id": "moon-a3-malapert-massif",
      "body": "Moon",
      "name": "Malapert Massif",
      "category": "Artemis III candidate region",
      "why": "High massif with long sunlit periods and direct line of sight to Earth.",
      "lat": -85.98, "lon": -1.67,
      "anchor": { "type": "point", "iau_feature": "Mons Malapert", "note": "Approximate: IAU center of Mons Malapert." },
      "source_url": "https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/",
      "coord_source_url": "https://planetarynames.wr.usgs.gov/Feature/16338"
    },
    {
      "id": "moon-a3-mons-mouton",
      "body": "Moon",
      "name": "Mons Mouton and Mons Mouton Plateau",
      "category": "Artemis III candidate region",
      "why": "Broad flat-topped massif; NASA lists both Mons Mouton and its plateau as candidate regions.",
      "lat": -84.6, "lon": 31.0,
      "anchor": { "type": "point", "iau_feature": "Mons Mouton", "note": "Approximate: IAU center of Mons Mouton; merges two NASA regions that share this anchor." },
      "source_url": "https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/",
      "coord_source_url": "https://planetarynames.wr.usgs.gov/Feature/16070"
    },
    {
      "id": "moon-a3-nobile-rim",
      "body": "Moon",
      "name": "Nobile rim",
      "category": "Artemis III candidate region",
      "why": "Rim of Nobile crater; NASA lists two separate rim regions (Nobile Rim 1 and 2).",
      "lat": -85.2752, "lon": 53.2725,
      "anchor": { "type": "rim", "iau_feature": "Nobile", "radius_km": 39.64, "note": "Approximate: ring on the rim of IAU crater Nobile (D = 79.3 km); merges Nobile Rim 1 and 2." },
      "source_url": "https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/",
      "coord_source_url": "https://planetarynames.wr.usgs.gov/Feature/4321"
    },
    {
      "id": "moon-a3-de-gerlache-rim",
      "body": "Moon",
      "name": "de Gerlache rim",
      "category": "Artemis III candidate region",
      "why": "Rim of de Gerlache crater, next to Shackleton; NASA region 'de Gerlache Rim 2'.",
      "lat": -88.4849, "lon": -88.3447,
      "anchor": { "type": "rim", "iau_feature": "de Gerlache", "radius_km": 16.35, "note": "Approximate: ring on the rim of IAU crater de Gerlache (D = 32.7 km)." },
      "source_url": "https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/",
      "coord_source_url": "https://planetarynames.wr.usgs.gov/Feature/1439"
    },
    {
      "id": "moon-a3-slater-plain",
      "body": "Moon",
      "name": "Slater Plain",
      "category": "Artemis III candidate region",
      "why": "Low-relief terrain around Slater crater close to the pole.",
      "lat": -88.0792, "lon": 111.2881,
      "anchor": { "type": "point", "iau_feature": "Slater", "note": "Approximate: IAU center of crater Slater; the NASA region is the plain around it." },
      "source_url": "https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/",
      "coord_source_url": "https://planetarynames.wr.usgs.gov/Feature/15325"
    },
    {
      "id": "moon-a3-cabeus-b",
      "body": "Moon",
      "name": "Peak near Cabeus B",
      "category": "Artemis III candidate region",
      "why": "Elevated terrain next to Cabeus B, near the Cabeus cold trap where LCROSS detected water ice.",
      "lat": -82.2587, "lon": -54.5846,
      "anchor": { "type": "rim", "iau_feature": "Cabeus B", "radius_km": 29.81, "note": "Approximate: ring on the rim of IAU crater Cabeus B (D = 59.6 km); the exact peak is not published." },
      "source_url": "https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/",
      "coord_source_url": "https://planetarynames.wr.usgs.gov/Feature/8058"
    },
    {
      "id": "moon-shackleton-rim",
      "body": "Moon",
      "name": "Shackleton rim",
      "category": "South pole reference site",
      "why": "Crater almost on the south pole; its rim has near-continuous sunlight and its floor is permanently shadowed.",
      "lat": -89.67, "lon": 129.78,
      "anchor": { "type": "rim", "iau_feature": "Shackleton", "radius_km": 10.46, "note": "Ring on the rim of IAU crater Shackleton (D = 20.9 km). Needs the polar patch support of T4.0." },
      "source_url": "https://ntrs.nasa.gov/citations/20250011660",
      "coord_source_url": "https://planetarynames.wr.usgs.gov/Feature/5450"
    },
    {
      "id": "mars-jezero-perseverance",
      "body": "Mars",
      "name": "Jezero crater (Perseverance)",
      "category": "Rover landing site",
      "why": "Ancient lake delta; Perseverance is collecting samples for return to Earth.",
      "lat": 18.4447, "lon": 77.4508,
      "anchor": { "type": "point", "note": "Octavia E. Butler Landing." },
      "source_url": "https://www.nasa.gov/image-article/welcome-octavia-e-butler-landing/",
      "coord_source_url": "https://en.wikipedia.org/wiki/Octavia_E._Butler_Landing"
    },
    {
      "id": "mars-gale-curiosity",
      "body": "Mars",
      "name": "Gale crater (Curiosity)",
      "category": "Rover landing site",
      "why": "Crater with a layered sedimentary mound (Aeolis Mons) recording a long history of water.",
      "lat": -4.5895, "lon": 137.4417,
      "anchor": { "type": "point", "note": "Bradbury Landing." },
      "source_url": "https://www.jpl.nasa.gov/images/pia16459-curiosity-traverse-map-sol-123/",
      "coord_source_url": "https://en.wikipedia.org/wiki/Bradbury_Landing"
    },
    {
      "id": "mars-gusev-spirit",
      "body": "Mars",
      "name": "Gusev crater (Spirit)",
      "category": "Rover landing site",
      "why": "Basaltic plains with volcanic rocks; Spirit found evidence of past hydrothermal activity.",
      "lat": -14.5692, "lon": 175.4729,
      "anchor": { "type": "point", "note": "Columbia Memorial Station, IAU 2000 coordinates. TODO(verificar): fuente primaria (Parker et al. / Golombek et al.)." },
      "source_url": "https://www.jpl.nasa.gov/news/space-shuttle-columbia-crew-memorialized-on-mars/",
      "coord_source_url": "https://photojournal.jpl.nasa.gov/catalog/PIA05826"
    },
    {
      "id": "mars-meridiani-opportunity",
      "body": "Mars",
      "name": "Meridiani Planum (Opportunity)",
      "category": "Rover landing site",
      "why": "Very flat hematite-bearing plain; Opportunity found sedimentary rocks formed in water.",
      "lat": -1.9462, "lon": -5.5266,
      "anchor": { "type": "point", "note": "Challenger Memorial Station (354.4734 E), IAU 2000 areocentric." },
      "source_url": "https://science.nasa.gov/photojournal/challenger-memorial-station-meridiani-planum-mars/",
      "coord_source_url": "https://science.nasa.gov/photojournal/challenger-memorial-station-meridiani-planum-mars/"
    },
    {
      "id": "mars-utopia-zhurong",
      "body": "Mars",
      "name": "Utopia Planitia (Zhurong)",
      "category": "Rover landing site",
      "why": "Southern Utopia Planitia, a northern lowland plain with possible buried ice and mud features.",
      "lat": 25.066, "lon": 109.925,
      "anchor": { "type": "point", "note": "Tianwen-1 / Zhurong landing point." },
      "source_url": "https://link.springer.com/10.1038/s41550-021-01519-5",
      "coord_source_url": "https://www.mdpi.com/2072-4292/17/14/2400"
    },
    {
      "id": "mars-elysium-insight",
      "body": "Mars",
      "name": "Elysium Planitia (InSight)",
      "category": "Lander site",
      "why": "Chosen for being flat, smooth and low in rocks; the reference for safe, benign terrain.",
      "lat": 4.5024, "lon": 135.6234,
      "anchor": { "type": "point", "note": "Georeferenced lander position (Golombek et al. 2020)." },
      "source_url": "https://www.jpl.nasa.gov/news/press_kits/insight/landing/mission/landing-site",
      "coord_source_url": "https://repository.arizona.edu/handle/10150/657891"
    },
    {
      "id": "mars-oxia-rosalind-franklin",
      "body": "Mars",
      "name": "Oxia Planum (Rosalind Franklin)",
      "category": "Planned rover landing site",
      "why": "Clay-rich plain selected for ESA's ExoMars rover to search for signs of past life.",
      "lat": 17.28, "lon": -25.71,
      "anchor": { "type": "point", "iau_feature": "Oxia Planum", "note": "IAU center of Oxia Planum. TODO(verificar): center of the 2022 landing ellipse (ESA / Fawdon et al. 2024)." },
      "source_url": "https://planetarynames.wr.usgs.gov/Feature/15821",
      "coord_source_url": "https://planetarynames.wr.usgs.gov/Feature/15821"
    },
    {
      "id": "mars-arcadia-swim",
      "body": "Mars",
      "name": "Arcadia Planitia (shallow ice)",
      "category": "Candidate human landing region (ice)",
      "why": "Plains where SWIM maps find shallow, accessible water ice; a leading resource region for crewed missions.",
      "lat": 47.25, "lon": -164.0,
      "anchor": { "type": "point", "note": "Center of the SWIM Arcadia pilot-study figure (47.25 N, 196 E). It is a mapped region, not a landing site. TODO(verificar): figure in SWIM materials." },
      "source_url": "https://swim.psi.edu/",
      "coord_source_url": "https://swim.psi.edu/resources/abstracts/LPSC2019/2069.pdf"
    }
  ]
}
```

En total son 8 blancos lunares y 8 marcianos.

---

## 6. `pipeline/targets.py` (nuevo)

### 6.1 Constantes

```python
CLUSTER_FEATURES = ["mean_slope_deg", "p90_slope_deg", "relief_m",
                    "hypsometric_integral", "detrended_std_m", "tri_m"]
LOG_FEATURES = ["relief_m", "detrended_std_m", "tri_m"]
N_CLUSTERS = 30
KMEANS_SEED = 42
NEIGHBOR_OFFSET_KM = 16.0
MIN_OK = {"point": 3, "rim": 5}
TARGETS_JSON = Path(__file__).parent / "data" / "targets.json"
AUX_COLS = {
    "Mars": ["themis_day", "themis_night", "themis_delta"],
    "Moon": ["wac_reflectance", "wac_percentile", "ice_favorability",
             "diviner_tmax_k", "diviner_tavg_k", "ice_depth_m"],
}
```

### 6.2 Funciones

```python
def load_curated(path: Path = TARGETS_JSON) -> list[dict]:
    """Lee y valida targets.json (reglas de la sección 5). ValueError con el id que falla."""

def anchor_points(target: dict) -> list[tuple[float, float]]:
    """Centros de los parches del blanco, con pyproj.Geod(a=R, b=R) del cuerpo.
    point: [centro] + fwd a 16 km en acimuts 0, 90, 180, 270  -> 5 puntos.
    rim:   fwd a radius_km en acimuts 0, 45, ..., 315          -> 8 puntos (sin el centro).
    Longitudes normalizadas a −180..180."""

def aggregate_patches(rows: list[dict | None], anchor_type: str, body: str) -> dict:
    """Recibe las filas de PointSampler.sample (None = parche inválido).
    Devuelve {status, n_patches, n_ok, <FEATURE_NAMES: nanmean>, <aux: nanmean>,
    mean_slope_std (desv. est. de mean_slope_deg entre parches válidos)}.
    status = 'ok' si n_ok >= MIN_OK[anchor_type]; si no, 'insufficient_coverage' y rasgos NaN.
    Ojo: ice_depth_m usa nanmean (NaN = sin hielo estable); agregar además
    ice_stable_frac = fracción de parches con ice_depth_m finito entre los que tienen Diviner."""

def curated_features(targets: list[dict], raw_dir: Path, derived_dir: Path,
                     t3_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Por cuerpo abre un PointSampler, muestrea todos los anchor_points de sus blancos.
    Devuelve (targets_df, patches_df). patches_df tiene una fila por parche intentado:
    target_id, k (índice), lat, lon, ok (bool) y los rasgos/aux de T3.
    Para la Luna, wac_percentile = compute_lunar_wac_percentile(valor,
    reference=features_moon.parquet['wac_reflectance']) calculado POR PARCHE antes de promediar."""

def build_clusters(df: pd.DataFrame, body: str, k: int = N_CLUSTERS,
                   seed: int = KMEANS_SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """X = df[CLUSTER_FEATURES]; log1p a LOG_FEATURES; StandardScaler (fit en este cuerpo).
    KMeans(n_clusters=k, n_init=10, random_state=seed).
    Ordenar clusters por tamaño descendente -> rank 1..k.
    Representante = índice del miembro con menor distancia euclidiana a su centroide (en X escalado).
    Devuelve (reps_df, summary_df):
      reps_df: una fila por cluster = la fila T3 del representante + cluster_rank, cluster_size,
               cluster_frac, dist_to_centroid.
      summary_df: cluster_rank, size, frac y la MEDIANA de cada rasgo de CLUSTER_FEATURES
               entre los miembros (unidades físicas) más el centroide desescalado.
    Además devuelve las etiquetas por parche si se pide (para el PNG)."""

def cluster_targets(reps_df: pd.DataFrame, summary_df: pd.DataFrame, body: str,
                    gaz: pd.DataFrame) -> pd.DataFrame:
    """Convierte los representantes en blancos con el mismo esquema que los curados:
    id = f"{body.lower()}-cluster-{rank:02d}", type = "CLUSTER",
    name = iau_label(...)['display_label'],
    category = "Global terrain archetype (k-means)",
    why = (f"Archetype covering {frac:.1%} of {body}'s 32 km patches: median mean slope "
           f"{s:.1f}°, relief {r:.0f} m, TRI {t:.0f} m."),   # medianas del cluster
    source_url = link IAU del rasgo usado en name, coord_source_url = None,
    anchor = {"type": "patch", "note": "Representative T3 patch closest to the cluster centroid."},
    status = "ok", n_patches = 1, n_ok = 1.
    Los rasgos y aux son los de la fila T3 del representante (no se recalculan)."""

def plot_targets_map(t3_df, labels, targets_df, body, png_path) -> Path:
    """Scatter lat/lon de T3 coloreado por cluster (tab20 + tab10, 30 colores),
    con los blancos curados como estrellas negras con su id y los representantes como
    círculos con su rank. Mismo tamaño de figura que plot_slope_map."""

def run(t3_dir: Path, out_dir: Path, project_dir: Path, bodies: list[str],
        k: int = N_CLUSTERS, skip_curated: bool = False) -> None:
    """Orquesta todo y escribe las salidas de la sección 6.3. Imprime el resumen de la sección 7."""

def main(argv=None): ...   # argparse: --t3-dir (obligatorio), --out-dir (obligatorio),
                           # --project-dir (default YUCA_PROJECT_DIR), --body {Mars,Moon,all},
                           # --k (default 30), --skip-curated
```

### 6.3 Salidas en `runs/<JOBID>/`

**`targets.parquet`**: una fila por blanco (curados + clusters de ambos cuerpos). Columnas, en este orden:

| Columna | Tipo | Nota |
| --- | --- | --- |
| `target_id` | string | |
| `type` | string | `CURATED` o `CLUSTER` |
| `body` | string | |
| `name`, `category`, `why` | string | En inglés |
| `lat`, `lon` | float64 | Ancla (curado) o centro del representante (cluster) |
| `anchor_type` | string | `point`, `rim` o `patch` |
| `anchor_note` | string | |
| `source_url`, `coord_source_url` | string (nullable) | |
| `status` | string | `ok` o `insufficient_coverage` |
| `n_patches`, `n_ok` | int16 | |
| `mean_slope_deg` … `mean_elev_m` | float32 | Los 7 de `FEATURE_NAMES` |
| `mean_slope_std` | float32 | |
| `themis_day`, `themis_night`, `themis_delta` | float32 | NaN en la Luna |
| `wac_reflectance`, `wac_percentile`, `ice_favorability`, `diviner_tmax_k`, `diviner_tavg_k`, `ice_depth_m`, `ice_stable_frac` | float32 | NaN en Marte |
| `iau_label`, `iau_nearest`, `iau_distance_km`, `iau_link` | | De `iau_label()` en (lat, lon) |
| `cluster_rank`, `cluster_size`, `cluster_frac` | | Null en curados |

**Las demás salidas:**

- **`targets_patches.parquet`:** salida de `curated_features`, para auditoría.
- **`clusters_mars.parquet`, `clusters_moon.parquet`:** el `summary_df` de cada cuerpo.
- **`targets.json`:** lo mismo que `targets.parquet`, como `{"metadata": {...}, "targets": [...]}`.
  - Floats redondeados a 4 decimales; NaN → `null`.
  - Los rasgos van anidados en `features` (los 6 de comparación más `mean_elev_m`) y `aux`, con los mismos nombres que la sección 5 de `plan_implementacion.md`, para que T8 los copie directo.
  - `metadata` lleva `slurm_job_id`, `t3_run`, `k`, `seed`, `generated_at` y el commit (`git rev-parse --short HEAD`).
- **`map_targets_mars.png`, `map_targets_moon.png`.**

`targets.json` de la corrida **no** se copia al repo; T8 lo lee de `runs/`.

---

## 7. Log esperado (lo que debe imprimir `run`)

```text
[T4] t3_dir=/lustre/proyectos/p089/runs/2242278 out_dir=... commit=...
[CURADO] moon-a3-haworth  rim   8/8 ok  slope=..° relief=.. m  iau=Haworth (Crater, craters) d=.. km  div_tavg=.. K
...
[CURADO] mars-arcadia-swim point 5/5 ok ...
[CURADO] resumen: Moon 8/8 ok, Mars 8/8 ok   (o lista de los insufficient_coverage)
[CLUSTER] Mars: N=140,916  k=30  tamaño min/mediana/max = ../../..  inercia=..
[CLUSTER] Mars #01  frac=..%  rep=(lat, lon)  slope_med=..°  relief_med=.. m  -> <display_label>
...
[OK] targets.parquet: 76 blancos (16 curados + 60 clusters) -> .../targets.parquet
```

El nombre IAU de cada ancla curada debe ser el rasgo esperado. Si para `moon-a3-haworth` el `iau_nearest` del **centro** no es "Haworth", algo está mal con la conversión de longitudes. Hay que imprimir el `iau_label` del centro del ancla, no el de los parches del anillo.

---

## 8. `jobs/t4_targets.slurm` (nuevo)

Igual de forma que `jobs/t3_planet_features.slurm`: `#!/usr/bin/env bash`, `set -euo pipefail`, conda, eco de job/nodo/commit. Diferencias:

```bash
#SBATCH -A p089
#SBATCH -J p089-t4-targets
#SBATCH -p cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:45:00
#SBATCH -o /lustre/proyectos/p089/output/t4_targets_%j.log
#SBATCH -e /lustre/proyectos/p089/output/t4_targets_%j.log
...
T3_DIR="${T3_DIR:-$PROJECT_DIR/runs/2242278}"
OUT_DIR="${OUT_DIR:-$PROJECT_DIR/runs/${SLURM_JOB_ID:-manual}}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"   # KMeans usa hilos; aquí sí se permiten
python -m pipeline.targets --project-dir "$PROJECT_DIR" --t3-dir "$T3_DIR" --out-dir "$OUT_DIR" --body all "$@"
```

Es un solo job, sin array. Trabajo estimado: 16 blancos × ≤ 8 parches con lecturas por ventana más k-means sobre 141k × 6. Debería tardar menos de 10 minutos.

**Prueba antes de la corrida real:** `--k 5 --body Moon` sirve como humo rápido, porque `--limit` no aplica aquí. Después va la corrida completa.

---

## 9. `tests/test_targets.py` (nuevo, solo datos sintéticos)

1. **`test_load_curated_real_file`**: carga `pipeline/data/targets.json` real (no toca rasters). Comprueba:
   - ≥ 6 blancos por cuerpo.
   - ids únicos.
   - todos con `source_url` y `coord_source_url`.
   - coordenadas en rango.
   - `rim` ⇒ `radius_km > 0`.
2. **`test_load_curated_rejects_bad`**: un JSON temporal con `lat = 95` lanza `ValueError` que menciona el id.
3. **`test_anchor_points_point`**: 5 puntos; los 4 vecinos están a 16.0 km (±0.01) del centro según `haversine_km` con el radio del cuerpo.
4. **`test_anchor_points_rim_near_pole`**: ancla `rim` de Haworth (−87.45, −5.17, r = 25.71 km). Comprueba 8 puntos, todos a 25.71 km (±0.01) y todas las longitudes en [−180, 180].
5. **`test_aggregate_min_ok`**: con `rim` y 4 de 8 válidos da `status == "insufficient_coverage"` y rasgos NaN; con 5 de 8 da `ok`, la media correcta y `n_ok == 5`.
6. **`test_aggregate_ice_stable_frac`**: 4 parches con Diviner, 1 con `ice_depth_m` finito ⇒ `ice_stable_frac == 0.25`.
7. **`test_build_clusters_blobs`**: 3 nubes gaussianas bien separadas en los 6 rasgos (300 filas, valores positivos) y `k = 3`. Comprueba:
   - cada representante es una fila existente del DataFrame de entrada (mismo `lat/lon`).
   - los 3 representantes caen en nubes distintas.
   - `cluster_size` suma 300 y los ranks están ordenados por tamaño.
   - con la misma semilla, dos corridas dan el mismo resultado.
8. **`test_cluster_targets_schema`**: `id` con formato `mars-cluster-01` y `type == "CLUSTER"`; `why` contiene el porcentaje.

---

## 10. Criterios de aceptación

**Automáticos (pytest, en un job corto como en T9):**

- Todas las pruebas pasan: las 17 de antes, las 3 nuevas de `test_geo.py`, las de `test_iau.py` y las de `test_targets.py`.

**En la corrida real (revisar el log):**

1. Al menos 6 curados `ok` por cuerpo. La meta son 8 y 8; si Shackleton queda fuera, 7 y 8 está bien.
2. Cada curado lunar `ok` tiene `diviner_tavg_k`, `ice_favorability` y `wac_percentile` finitos. Todos los parches quedan al sur de 81°S, dentro de la cobertura de Diviner y del índice de hielo.
3. Cada curado marciano tiene `themis_day` finito. `themis_night` es finito en todos (todos están a menos de 60° de latitud).
4. El `iau_nearest` del centro de cada ancla lunar coincide con `anchor.iau_feature`.
5. Hay 30 clusters por cuerpo, sus tamaños suman 140,916 en Marte y 36,741 en la Luna, y los 60 representantes son parches distintos.
6. **Revisión de sentido común:** es una revisión, no una prueba. Si falla, avisar antes de seguir a T6.
   - InSight y Opportunity deben quedar entre los 3 curados marcianos de menor `mean_slope_deg`, y por debajo de la mediana global de Marte (1.16°). Se eligieron por ser planos.
   - Gale debe tener más `relief_m` que InSight.
   - En la Luna, los curados polares deben tener `mean_slope_deg` por encima de la mediana de los mares. Basta con comparar contra la mediana global lunar (6.8°) e imprimirlo.
7. Los PNG muestran clusters espacialmente coherentes. En Marte, Tharsis y Valles Marineris deben salir en clusters distintos de las llanuras del norte. Las estrellas de los curados deben caer donde corresponde: la Luna en el polo sur; Marte con Jezero ≈ 18°N 77°E y Gale ≈ 5°S 137°E.

---

## 11. Comandos para Owen en Yuca

Desde `/lustre/proyectos/p089/code`, en este orden. Cada paso se corre después de leer el log del anterior.

```bash
cd /lustre/proyectos/p089/code && git pull
```

```bash
sbatch -A p089 -p cpu --time=00:15:00 --mem=4G -o /lustre/proyectos/p089/output/tests_t4_%j.log --wrap 'bash -c "source /apps/miniconda3/etc/profile.d/conda.sh && conda activate spaceapps_2026 && cd /lustre/proyectos/p089/code && pytest -q tests"'
```

```bash
sbatch jobs/t4_targets.slurm --k 5 --body Moon
```

```bash
sbatch jobs/t4_targets.slurm
```

```bash
tail -n 120 /lustre/proyectos/p089/output/t4_targets_<JOBID>.log
```

---

## 12. Bitácora y documentación (mismo commit)

- **`docs/bitacora.md`:** entrada nueva arriba. Debe decir:
  - que el código lo escribió Gemini a partir de este plan de Claude;
  - el JOBID de la corrida y los conteos de curados y clusters;
  - qué curados quedaron fuera y por qué;
  - el resultado de la revisión de sentido común.
- **`docs/pipeline.md`:**
  - agregar la corrida T4 a "Corridas registradas";
  - agregar una línea en "Flujo" con `pipeline/targets.py` → `runs/<id>/targets.parquet`.
- **`docs/progreso_handoff.md`:** marcar T4 como hecho y dejar el JOBID para T7.

---

## 13. Qué NO hacer

- No inventar ni "redondear mejor" coordenadas. Los `TODO(verificar)` se quedan hasta que alguien encuentre la fuente.
- No recalcular rasgos de clusters con otra función; se usan las filas de T3 tal cual.
- No usar `mean_elev_m` para el clustering ni para comparar (los datums no son comparables).
- No importar `enrich_nomenclature.py` ni modificar los scripts v1.
- No escribir nada en `runs/2242278/`; T4 solo lo lee.

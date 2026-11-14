# Pipeline de análogos (prototipo)

Cómo funciona hoy el pipeline que corre en Yuca (proyecto `p089`). Describe el estado real del código, no el plan maestro.

## Flujo

```
setup_and_download.sh ──┐
download_full_night.sh ─┴─> /lustre/proyectos/p089/data/raw/{moon,mars,earth}
                                   │
            run_clustering.slurm ──┤  process_analogs.py
                                   ▼
                    output/planetary_baselines.json   (40 arquetipos por cuerpo)
                                   │
                                   │  enrich_nomenclature.py  (nombres IAU)
                                   ▼
                    output/planetary_baselines.json   (con iau_nomenclature)
                                   │
        run_earth_matching.slurm ──┤  match_earth_analogs.py
                                   ▼
                    output/analogs.json               (top-5 análogos terrestres por arquetipo)
```

## Datos

Rutas en Yuca, bajo `/lustre/proyectos/p089/data/raw/`.

| Cuerpo | Archivo | Fuente | Estado |
| --- | --- | --- | --- |
| Marte | `mars/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif` (2 GB) | USGS Astrogeology | OK |
| Marte | `mars/Mars_ODY_THEMIS_IR_Day_Mosaic_100m.tif` (22 GB) | USGS Astrogeology | OK |
| Marte | `mars/Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif` (15.2 GB) | USGS Astrogeology | Pendiente: `run_download_missing.slurm` |
| Luna | `moon/Lunar_LRO_LOLA_Global_LDEM_118m.tif` (8 GB) | USGS Astrogeology | OK |
| Luna | `moon/Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif` (6.0 GB) | USGS Astrogeology | Pendiente: `run_download_missing.slurm` |
| Luna | `moon/Moon_IceFavorabilityIndex_{90S,90N}000E_591mp.tif` | USGS Astrogeology | Pendiente: `run_download_missing.slurm` |
| Luna | `moon/Lunar_LRO_LOLA_Albedo_Global_128ppd.tif` | USGS Astrogeology | Obsoleto: en realidad es `ClrShade`; ya no se usa |
| Tierra | `earth/copernicus_90m/*.tif` | Copernicus GLO-90 (AWS, sin firma) | Parcial: 6,983 de 26,475 tiles; el resto en `run_download_missing.slurm` |
| Luna | `moon/diviner/dlre_prp_south.{tab,lbl,xml}` (577 MB, tabla ASCII de malla triangular 80–90°S) | NASA PDS Geosciences (LRO Diviner PRP) | `jobs/download_diviner.slurm` |
| Tierra | `earth/modis/ndvi/*.hdf` (MOD13C2 v061, 12 meses de 2023) | NASA Earthdata (LP DAAC) | OK |
| Tierra | `earth/modis/lst/*.hdf` (MOD11C3 v061, 12 meses de 2023) | NASA Earthdata (LP DAAC) | OK |
| Tierra | `earth/naturalearth/ne_10m_roads`, `ne_10m_airports` | Natural Earth | OK |
| Ambos | `nomenclature/MARS*.dbf`, `nomenclature/MOON*.dbf` | Gazetteer IAU/USGS | OK (descarga no registrada en los scripts) |

Los rasters no se suben al repo (ver `.gitignore`).

### Tipo, escala y nodata de cada mosaico

Revisado en Yuca el 2026-11-13 con rasterio. **Siempre aplicar `valor = crudo · scale + offset`**: `rasterio.read()` no lo hace solo.

| Archivo | dtype | scale | offset | nodata | Nota |
| --- | --- | --- | --- | --- | --- |
| `Mars_MGS_MOLA_DEM_mosaic_global_463m.tif` | int16 | 1.0 | 0.0 | −32768 | Metros |
| `Mars_ODY_THEMIS_IR_Day_Mosaic_100m.tif` | uint8 | 1.0 | 0.0 | 0 | Nivel de gris, no kelvin |
| `Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif` | uint8 | 1.0 | 0.0 | 0 | Nivel de gris, no kelvin |
| `Lunar_LRO_LOLA_Global_LDEM_118m.tif` | int16 | **0.5** | 0.0 | −32768 | **Medios metros**: la v1 no aplicó la escala y todas las métricas lunares salieron al doble |
| `Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif` | uint8 | 1.00395 | −0.00395 | 0 | Brillo relativo (≈ 1–256), no reflectancia absoluta; compararlo por rango dentro de la Luna |
| `Moon_IceFavorabilityIndex_{90N,90S}000E_591mp.tif` | float32 | 1.0 | 0.0 | −3.4e38 | Filtrar el nodata gigante |
| `Lunar_LRO_LOLA_Albedo_Global_128ppd.tif` | uint8 × 3 | 1.0 | 0.0 | 0 | Obsoleto (ClrShade RGB); mover a `_to_delete/` |

## Scripts

### `process_analogs.py`

- Recorre el DEM de cada cuerpo en ventanas de 256 px y toma hasta 4,500 ventanas espaciadas.
- Descarta ventanas con menos de 80 % de píxeles válidos.
- Por ventana calcula: elevación media, desviación estándar (rugosidad), pendiente media, pendiente p90 y desviación absoluta media respecto a la mediana (llamada `tri`).
- Muestrea capas auxiliares (THEMIS, capa lunar) con la mediana de un parche de 32 × 32.
- Normaliza con `StandardScaler`, agrupa con `MiniBatchKMeans` (40 clusters) y guarda la ventana más cercana a cada centroide como arquetipo.

### `enrich_nomenclature.py`

Asigna a cada arquetipo el rasgo IAU más cercano y el rasgo mayor (≥ 30 km) más cercano, con distancia haversine sobre el radio del cuerpo. Lee los `.dbf` sin dependencias externas.

### `match_earth_analogs.py`

- Recorre los tiles de Copernicus en ventanas de 512 px (en paralelo, 32 procesos).
- Descarta ventanas con < 85 % válidos, con > 30 % de píxeles cerca de 0 m (mar) o casi planas.
- Compara cada arquetipo contra todas las ventanas terrestres con distancia euclidiana sobre 4 rasgos normalizados: rugosidad, pendiente media, pendiente p90 y `tri`. La elevación no entra.
- Toma los 5 mejores, separados al menos 150 km entre sí.
- Puntaje: `100 / (1 + 0.35 · d)`.

## Corridas registradas

Logs en `logs/slurm/`.

| Job | Script | Resultado |
| --- | --- | --- |
| 2241770 | clustering | Primera prueba, sin conteos |
| 2241771 | clustering | 4,000 ventanas por cuerpo, 40 arquetipos |
| 2241773 | clustering | 4,500 ventanas por cuerpo, con capas auxiliares (versión actual) |
| 2241781 | matching | 3,643 tiles, 66,215 sitios |
| 2241782 | matching | 5,175 tiles, 98,465 sitios |
| 2241783 | matching | 6,983 tiles, 21,906 sitios (versión actual, con filtros de mar y planicie) |

## Explorar los datos

`jobs/explore_datasets.slurm` genera un reporte de todo lo descargado. Solo lee; no modifica `data/`.

```bash
cd /lustre/proyectos/p089/code && git pull && sbatch jobs/explore_datasets.slurm
```

Salida en `/lustre/proyectos/p089/runs/<JOBID>/exploracion/`: `index.html` (reporte con imágenes), `resumen.md` (tabla corta) y `resumen.json`. Para correr solo una parte: `sbatch jobs/explore_datasets.slurm --only planets` (o `copernicus`, `modis`, `vectors`).

## Recursos en Yuca

Consultado el 2026-11-13 con `sinfo` y `sacctmgr`.

| Partición | Nodos | Por nodo | Tiempo máximo | Estado ese día |
| --- | --- | --- | --- | --- |
| `cpu` (default) | 24 (`amdcpu-hpc-01..24`) | 64 CPUs, ~1 TB RAM | 7 días | 19 libres, 4 ocupados, 1 en drain (`24`) |
| `gpu` | 6 (`amdgpu-hpc-01..06`) | 48 CPUs, ~1 TB RAM, 2 × AMD MI210 (ROCm, no CUDA) | 7 días | 3 libres, 2 ocupados, 1 caído (`06`) |

Cuenta `p089`, QOS `qos089`. Usuarios: `owen` (pipeline), `aborquez`, `javier` (frontend; casi no usa el cluster) y `vmmn` (staff de ACARUS, no corre jobs). En la práctica los recursos son del equipo. Límites de `qos089`: **500 CPUs y 4 GPUs en total para el grupo**, 7 días por job. No hay límite de jobs simultáneos ni de jobs en cola, por usuario ni por cuenta; el único tope es la suma de recursos de todos los jobs del grupo.

## Cómo correrlo

En Yuca, con el entorno `spaceapps_2026`:

```bash
bash setup_and_download.sh
```

```bash
sbatch run_download_missing.slurm
```

`run_download_missing.slurm` reemplaza a `download_full_night.sh`: corre como job (no en el login) y usa las URLs corregidas.

Para ver espacio y archivos disponibles del proyecto:

```bash
lfs quota -h -g p089 /lustre
```

```bash
sbatch run_clustering.slurm
```

```bash
python3 enrich_nomenclature.py
```

```bash
sbatch run_earth_matching.slurm
```

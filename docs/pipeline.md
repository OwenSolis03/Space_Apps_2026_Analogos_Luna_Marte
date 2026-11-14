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
| Ambos | `nomenclature/MARS*.dbf`, `nomenclature/MOON*.dbf` | Gazetteer IAU/USGS | OK (descarga no registrada en los scripts) |

Los rasters no se suben al repo (ver `.gitignore`).

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

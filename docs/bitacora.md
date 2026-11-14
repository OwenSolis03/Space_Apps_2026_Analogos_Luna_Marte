# Bitácora

Registro de lo que se hace en el proyecto, de lo más reciente a lo más antiguo. Sirve también para la descripción de uso de IA de la entrega.

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

**Qué falta**

- Correr en Yuca la prueba `--limit 500` tras el arreglo y comparar mediana, p95 y máximo de `mean_slope_deg`, `relief_m` y `mean_elev_m` en la Luna entre la corrida `2242227` (antes) y la nueva corrida (después), además de verificar los `[META]` de todos los rasters (MOLA, THEMIS, LOLA, WAC, hielo).
- Una vez verificada la caída de la pendiente lunar (~a la mitad), lanzar el array completo `0-15` y `--merge` de T3 antes de pasar a T4.

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

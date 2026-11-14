# Pipeline de Detección de Análogos Planetarios (Tierra – Marte – Luna)

**Proyecto:** NASA Space Apps Challenge 2026  
**Infraestructura:** Clúster de Alto Rendimiento (HPC) Yuca (`p089`)  
**Directorio de trabajo:** `/lustre/proyectos/p089`  

---

## 1. Resumen Ejecutivo

Este documento describe la arquitectura, fundamentación matemática, algoritmos y flujos de ejecución desarrollados para identificar **análogos geomorfológicos terrestres** correspondientes a las regiones topográficas más representativas de **Marte** y la **Luna**.

A diferencia de enfoques basados en redes neuronales pre-entrenadas o selección manual, el sistema implementa un **pipeline propio de análisis geomorfométrico y aprendizaje no supervisado** que procesa modelos digitales de elevación (DEM) globales de alta resolución, extrae arquetipos planetarios mediante agrupamiento (*clustering*), asigna nomenclatura oficial de la Unión Astronómica Internacional (IAU) y ejecuta una búsqueda de vecinos más cercanos ($k$-NN) con restricciones geodésicas sobre toda la superficie continental terrestre.

---

## 2. Arquitectura y Estructura de Directorios

```text
/lustre/proyectos/p089/
├── data/
│   └── raw/
│       ├── earth/
│       │   ├── copernicus_90m/          # 26,475 tiles GeoTIFF (Copernicus DEM GLO-90)
│       │   ├── copernicus_90m_tileList.txt
│       │   └── copernicus_90m_urls.txt
│       ├── mars/
│       │   ├── Mars_MGS_MOLA_DEM_mosaic_global_463m.tif
│       │   ├── Mars_ODY_THEMIS_IR_Day_Mosaic_100m.tif
│       │   └── Mars_ODY_THEMIS_IR_Night_Mosaic_100m.tif
│       ├── moon/
│       │   ├── Lunar_LRO_LOLA_Global_LDEM_118m.tif
│       │   └── Lunar_LRO_LOLA_Albedo_Global_128ppd.tif
│       └── nomenclature/
│           ├── MARS_nomenclature_center_pts.*  # Shapefile/DBF oficial IAU
│           └── MOON_nomenclature_center_pts.*  # Shapefile/DBF oficial IAU
├── output/
│   ├── planetary_baselines.json         # 80 arquetipos (40 Marte + 40 Luna) con IAU
│   ├── analogs.json                     # Salida final Top-5 Tierra por arquetipo (Frontend)
│   ├── spaceapps_<JOBID>.log            # Logs de clustering planetario
│   └── earth_match_<JOBID>.log          # Logs de cruce terrestre paralelo
├── download_full_night.sh               # Descarga paralela multi-hilo con aria2c
├── process_analogs.py                   # Extracción de arquetipos planetarios (K-Means)
├── enrich_nomenclature.py               # Asignación de nombres oficiales IAU/USGS
├── match_earth_analogs.py               # Cruce geomorfológico paralelo Tierra-Planetas
├── run_clustering.slurm                 # Job Slurm para línea base planetaria
└── run_earth_matching.slurm             # Job Slurm para cruce global terrestre (32 cores)
```

---

## 3. Fundamentación Matemática y Algorítmica

El sistema no utiliza pesos pre-entrenados ni modelos de caja negra. Se compone de cuatro etapas deterministas y reproducibles:

### 3.1. Extracción de Características Geomorfométricas
Cada cuerpo celeste se divide en ventanas espaciales regulares ($256 \times 256\text{ px}$ en Luna/Marte; $512 \times 512\text{ px} \approx 46 \times 46\text{ km}$ en la Tierra). Para corregir la deformación cartográfica de las proyecciones equirectangulares, los diferenciales espaciales se escalan según el radio planetario $R$ y la latitud $\phi$:

$$\Delta x = |\Delta \lambda| \cdot \frac{\pi}{180} R \cos(\phi), \qquad \Delta y = |\Delta \phi| \cdot \frac{\pi}{180} R$$

Donde $R_{\text{Tierra}} = 6\,371.00\text{ km}$, $R_{\text{Marte}} = 3\,396.19\text{ km}$ y $R_{\text{Luna}} = 1\,737.40\text{ km}$.

Sobre la matriz de elevación $z(x, y)$ se calculan gradientes mediante diferencias finitas centrales y se extraen cuatro métricas invariantes al nivel medio del mar:

1. **Rugosidad macroscópica ($\sigma_z$):** Desviación estándar de la elevación dentro de la ventana:
   $$\sigma_z = \sqrt{\frac{1}{N}\sum_{i=1}^{N}(z_i - \bar{z})^2}$$
2. **Pendiente media ($\bar{\theta}$):** Promedio del ángulo de inclinación local:
   $$\theta_{i,j} = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right)$$
3. **Pendiente extrema ($P_{90}(\theta)$):** Percentil 90 de la distribución de pendientes, diseñado para capturar paredes de cráteres, escarpes tectónicos y flancos volcánicos abruptos.
4. **Índice de Irregularidad del Terreno ($\text{TRI}$):** Desviación absoluta media respecto a la mediana local $\tilde{z}$ (variante robusta de Riley et al., 1999):
   $$\text{TRI} = \frac{1}{N}\sum_{i=1}^{N}|z_i - \tilde{z}|$$

*(Adicionalmente, en Marte y la Luna se muestrean elevación media, reflectancia/albedo LOLA e infrarrojo térmico diurno/nocturno THEMIS como metadatos geofísicos).*

### 3.2. Descubrimiento de Arquetipos Planetarios (`process_analogs.py`)
Para sintetizar la diversidad topográfica global de Marte y la Luna sin sesgo manual:
1. Se estandarizan los vectores de características mediante transformación **Z-score** ($z = \frac{x - \mu}{\sigma}$).
2. Se ejecuta **Mini-Batch K-Means** (`k = 40` por planeta, `random_state = 42`, `batch_size = 1024`).
3. Para cada centroide calculado, se selecciona su **medoide** (la ventana real observada más cercana al centroide en el espacio normalizado), garantizando que las coordenadas y métricas correspondan a terrenos reales existentes.

### 3.3. Nomenclatura Oficial IAU (`enrich_nomenclature.py`)
Cada uno de los 80 arquetipos se cruza contra el *Gazetteer of Planetary Nomenclature* (USGS/IAU) mediante distancia geodésica **Haversine** sobre la esfera del planeta correspondiente:

$$d = 2R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)$$

El módulo asigna tanto el rasgo geológico puntual más cercano (*Crater*, *Mons*, *Vallis*, *Mensa*, *Fossa*) como el hito regional mayor ($\text{diámetro} \ge 30\text{ km}$).

### 3.4. Búsqueda de Análogos Terrestres y Diversidad Espacial (`match_earth_analogs.py`)
1. **Filtrado oceánico y de planicies sin relieve:** Se descartan ventanas terrestres con más de 15% de píxeles `NoData`, más de 30% de superficie a $0\text{ m}$ (océanos/lagos) o relieve nulo ($\sigma_z < 5\text{ m}$ y $\bar{\theta} < 0.3^\circ$).
2. **Normalización conjunta:** Se ajusta un `StandardScaler` sobre el espacio combinado de arquetipos planetarios y ventanas continentales terrestres utilizando el vector morfológico 4D $[\sigma_z, \bar{\theta}, P_{90}(\theta), \text{TRI}]$.
3. **Búsqueda $k$-NN con exclusión geodésica:** Se ordenan los sitios terrestres por distancia Euclidiana $d_{L2}$ al arquetipo y se seleccionan los **Top-5** exigiendo una separación mínima de **$150\text{ km}$** entre candidatos seleccionados, evitando repeticiones de ventanas adyacentes y asegurando diversidad geográfica global.
4. **Índice de Similitud:** La distancia normalizada se transforma a una escala porcentual interpretable mediante decaimiento hiperbólico:
   $$\text{Similarity Score} = \frac{100}{1 + 0.35 \, d_{L2}}$$

---

## 4. Guía de Operación en el Clúster HPC Yuca

### 4.1. Entorno Computacional
* **Partición Slurm:** `cpu`
* **Cuenta / QOS:** `--account=p089` (`qos089`)
* **Entorno Conda:** `spaceapps_2026` (`/apps/miniconda3/etc/profile.d/conda.sh`)
* **Recursos por job:** 1 nodo, 32 núcleos (`--cpus-per-task=32`), 64 GB RAM.

### 4.2. Comandos de Ejecución y Monitoreo

```bash
# 1. Verificar progreso de descarga global de Copernicus DEM 90m (26,475 tiles)
pgrep -af "aria2c" || echo "Descarga finalizada"
ls /lustre/proyectos/p089/data/raw/earth/copernicus_90m/*.tif | wc -l

# 2. Regenerar arquetipos planetarios y nombres IAU (si se modifican parámetros)
sbatch /lustre/proyectos/p089/run_clustering.slurm
python /lustre/proyectos/p089/enrich_nomenclature.py

# 3. Ejecutar el cruce geomorfológico global en paralelo (32 cores)
sbatch /lustre/proyectos/p089/run_earth_matching.slurm

# 4. Monitorear ejecución en Slurm
squeue -u owen
tail -f /lustre/proyectos/p089/output/earth_match_<JOBID>.log
```

---

## 5. Esquema del Archivo de Salida (`output/analogs.json`)

Este archivo es el contrato de datos consumido directamente por la interfaz web:

```json
{
  "generated_on": "Yuca HPC Cluster",
  "earth_sites_evaluated": 95000,
  "targets": {
    "Mars": [
      {
        "cluster_id": "mars-c00",
        "iau_nomenclature": {
          "nearest_feature": "Nirgal Vallis",
          "feature_type": "Vallis, valles",
          "distance_km": 77.4,
          "regional_landmark": "Nirgal Vallis",
          "regional_type": "Vallis, valles",
          "regional_distance_km": 77.4,
          "display_label": "Nirgal Vallis (Vallis, valles)"
        },
        "target_coords": { "lat": -27.0045, "lon": -40.997 },
        "target_metrics": {
          "mean_elev_m": 744.63,
          "roughness_std_m": 173.54,
          "mean_slope_deg": 1.24,
          "p90_slope_deg": 2.47,
          "tri": 127.38,
          "themis_ir_day": 124.0
        },
        "top_earth_analogs": [
          {
            "rank": 1,
            "similarity_score": 96.54,
            "distance": 0.1023,
            "lat": 38.7867,
            "lon": 94.64,
            "tile": "Copernicus_DSM_COG_30_N38_00_E094_00_DEM.tif",
            "metrics": {
              "mean_elev_m": 3118.2,
              "roughness_std_m": 185.07,
              "mean_slope_deg": 1.5,
              "p90_slope_deg": 2.5,
              "tri": 117.83
            }
          }
        ]
      }
    ],
    "Moon": [ "..." ]
  }
}
```

---

## 6. Interpretación Científica y Alcance

* **Validez operacional:** Las métricas seleccionadas capturan la estadística de pendientes, rugosidad vertical e irregularidad local a escala de decenas de kilómetros. Esto hace que los análogos identificados sean directamente relevantes para **pruebas de movilidad de rovers, validación de sensores LiDAR/radar de aterrizaje (TRN) y planificación de travesías**.
* **Limitación conocida:** Al tratarse de descriptores estadísticos escalares agregados por ventana, el modelo evalúa la **firma de relieve y pendiente**, pero no la **topología cerrada** (por ejemplo, un cráter lunar de paredes escarpadas puede emparejar con un cañón tectónico terrestre de igual desnivel y ángulo de talud, como ocurre entre el cráter *Stearns* y la Cordillera de Mérida).

---

## 7. Créditos de Datos y Herramientas Científicas

Para la documentación pública y presentación del proyecto, se reconocen las siguientes fuentes de datos abiertos y bibliotecas científicas:

* **NASA / USGS Astrogeology Science Center:**
  * *Mars Global Surveyor (MGS) MOLA Global DEM (463 m).*
  * *Mars Odyssey THEMIS Infrared Day & Night Global Mosaics (100 m).*
  * *Lunar Reconnaissance Orbiter (LRO) LOLA Global LDEM (118 m) & Albedo/Shaded Relief.*
* **International Astronomical Union (IAU) / USGS:**
  * *Gazetteer of Planetary Nomenclature* (catálogos oficiales de rasgos superficiales de Marte y la Luna).
* **European Space Agency (ESA) / Copernicus:**
  * *Copernicus DEM GLO-90 (90 m)*, distribuido a través del *AWS Open Data Registry*.
* **Ecosistema Open-Source en Python:**
  * `scikit-learn` (Pedregosa et al., 2011) — Implementación de `StandardScaler` y `MiniBatchKMeans` (Sculley, 2010).
  * `Rasterio` / `GDAL`, `NumPy`, `SciPy` y `PyProj`.
# Planetary Analog Finder (PAF)
## NASA Space Apps Challenge 2026 — Blueprint Operativo y Metodológico (v2.0 Blindado)

---

## 1. Resumen Ejecutivo y Propósito
El objetivo del proyecto es construir una plataforma web interactiva orientada a ingenieros de misión y geólogos planetarios para identificar, caracterizar y rankear **sitios análogos terrestres** comparados con ubicaciones estratégicas de aterrizaje o bases permanentes en la **Luna (Programa Artemis)** y **Marte**.

A diferencia de catálogos estáticos, selecciones manuales o comparaciones visuales arbitrarias, la herramienta evalúa la correspondencia mediante un **Índice de Similitud de Misión (MSI)** multidimensional basado en **Kernels Radiales Gaussianos (RBF)** e índices de viabilidad logística, derivados de datos satelitales abiertos de NASA, USGS, ESA y JAXA. El sistema descubre **nuevos análogos no catalogados** ejecutando un pipeline de teselación espacial (**Uber H3**) y clustering no supervisado (**HDBSCAN**) en la **supercomputadora Yuca**, contrastando tanto **análogos morfológicos/estáticos** como **análogos de procesos dinámicos/estacionales** (ej. tormentas de polvo), e integrando de manera obligatoria la sección de **"Límites del análogo"** (discrepancias físicas insalvables como gravedad, radiación y atmósfera).

---

## 2. Decisiones de Alcance y Mitigación de Riesgos (48 Horas)

| Factor | Decisión de Alcance | Justificación Técnica y Operativa |
| :--- | :--- | :--- |
| **Exploración Global y Teselación** | Máscara booleana de superficie expuesta (~12% del globo) pre-alineada en Google Earth Engine (GEE) y agrupada en celdas hexagonales **Uber H3 (Resolución 6, $\sim 36\text{ km}^2$)**. | Evita cuellos de botella de I/O y reproyección de TBs de GeoTIFFs crudos. Reduce $2.2 \times 10^9$ píxeles a $\sim 1.8 \times 10^5$ vectores estadísticos manejables en RAM sin diluir rasgos geológicos. |
| **Rol de Supercómputo (Yuca)** | Procesamiento por lotes fuera de línea (*Offline Batch Job via Slurm*) sobre la malla H3 para extracción estadística, HDBSCAN y evaluación de Kernels RBF. | Cero dependencia en vivo durante la presentación; la web consume el artefacto estático exportado (`analogs_universe.json`). |
| **Resolución del Problema de Escala (Rugosidad)** | Separación formal entre **Macro-topografía** (pendiente regional) y **Micro-rugosidad** mediante variables proxy antes del *downsampling* (TRI en GLO-30 + SAR Sentinel-1 vs. Inercia Térmica THEMIS / LOLA Hurst). | Resuelve la imposibilidad física de medir obstáculos sub-métricos para rovers a partir de DEMs globales de $90\text{--}200\text{ m/px}$. |
| **Tipología de Análogos** | Bimodal: **Estáticos** (terreno, rugosidad proxy, ratios espectrales) y **Dinámicos** (procesos eólicos estacionales y aerosoles). | Responde a la directriz de NASA de analizar *procesos* además de *lugares*. |
| **Viabilidad Logística** | Inclusión de distancia a red vial pavimentada y aeropuertos cercanos (`logistics_score`). | Permite demostrar por qué un candidato nuevo (ej. Sonora) supera operativamente a sitios remotos clásicos (Antártida / Devon Island) en costo-beneficio. |
| **Lógica en el Cliente y Mapas** | Recálculo de pesos en memoria ($<1\text{ ms}$) y *Dual Viewer* pragmático (Mapbox en Tierra + NASA Trek WMTS / Leaflet para Luna y Marte). | Interactividad inmediata sin bloqueos de proyecciones planetarias ni fallas de CORS al exportar reportes. |

---

## 3. Arquitectura del Sistema y Pipeline HPC (Yuca)

```
[Pre-agregación Cloud (GEE / STAC) + Catálogo PDS (Luna / Marte)]
                                │
                                ▼
         ┌──────────────────────────────────────────────┐
         │    PIPELINE HPC BATCH (SUPERCOMPUTADORA YUCA)│
         │                                              │
         │  1. Máscara Booleana y Teselación H3 (Res 6):│
         │     Descarte: Océanos, NDVI > 0.20, Urbano   │
         │  2. Extracción de Estadísticos por Celda H3: │
         │     [Slope_μ, TRI_proxy, Fe_Ratio, Clay_Ratio│
         │      Albedo, Aridity_Idx, MODIS_AOD, Dist_Rd]│
         │  3. Clustering No Supervisado (HDBSCAN)      │
         │  4. Scoring Gaussiano (RBF) vs. Targets      │
         └──────────────────────┬───────────────────────┘
                                │
                                ▼
              [Artefacto Estático: analogs_universe.json]
                                │
                                ▼
         ┌──────────────────────────────────────────────┐
         │             FRONTEND WEB REACT + VITE        │
         │                                              │
         │  • Dual Viewer (Mapbox Tierra + NASA WMTS)   │
         │  • Presets Operativos + Sliders en memoria   │
         │  • Radar Charts + Filtro de Viabilidad (Km)  │
         │  • Panel Crítico: "Límites del Análogo"      │
         └──────────────────────────────────────────────┘
```

### Protocolo de Ejecución en Yuca
1. **Ingesta Pre-alineada (H+0 a H+6):** Extracción de bandas reducidas por celda H3 desde Google Earth Engine / STAC APIs hacia Yuca, eliminando la descarga de rasters crudos masivos.
2. **Prueba piloto (H+6 a H+12):** Validación del script de Python (`h3`, `numpy`, `scipy`, `scikit-learn`, `hdbscan`) sobre el cuadrante del Desierto de Sonora / Suroeste de EE. UU.
3. **Batch global (H+18 a H+26):** Corrida nocturna en la cola Slurm procesando las celdas H3 de zonas áridas globales contra el vector de sitios objetivo de Marte y la Luna.
4. **Exportación (H+26):** Generación del archivo `analogs_universe.json` con los mejores 50 a 100 clusters agrupados, enriquecidos con metadatos logísticos y mineralógicos.
5. **Plan de contingencia:** Si la cola de Slurm experimenta demoras, el frontend opera de forma transparente con el dataset validado en la prueba piloto más el catálogo curado de referencia.

---

## 4. Contrato de Datos Estático (`analogs_universe.json`)

El esquema desacopla los **presets operativos** (`mission_presets`) de los **sitios candidatos** (`analogs`). De esta forma, el frontend calcula el `MSI` dinámicamente en tiempo real ($<1\text{ ms}$) en función de los sliders del usuario sin depender de un índice estático pre-fijado:

```json
{
  "metadata": {
    "version": "2.0.0",
    "grid_system": "Uber H3 Resolution 6 (~36 km2)",
    "hpc_node": "Yuca Supercomputer (UNISON) - Slurm Batch",
    "generated_at": "2026-11-15T04:00:00Z"
  },
  "mission_presets": {
    "mobility_and_traction": {
      "label": "Movilidad y Tracción de Rovers",
      "weights": { "topography": 0.40, "roughness": 0.40, "spectral": 0.10, "environmental": 0.10 }
    },
    "isru_and_mining": {
      "label": "ISRU y Extracción de Recursos",
      "weights": { "topography": 0.15, "roughness": 0.15, "spectral": 0.55, "environmental": 0.15 }
    },
    "dust_and_atmospheric": {
      "label": "Abrasión Eólica y Mitigación de Polvo",
      "weights": { "topography": 0.10, "roughness": 0.15, "spectral": 0.15, "environmental": 0.60 }
    }
  },
  "analogs": [
    {
      "id": "pinacate-crater-elegante",
      "h3_index": "8648a9327ffffff",
      "name": "Cráter El Elegante, Campo Volcánico El Pinacate",
      "location": {
        "lat": 31.848,
        "lon": -113.390,
        "country": "México",
        "region_type": "Volcanic / Maar Crater"
      },
      "classification": "NEW_CANDIDATE",
      "analog_type": "STATIC_GEOLOGY",
      "target_body": "Mars",
      "target_site": {
        "id": "mars-jezero-floor",
        "name": "Jezero Crater Floor",
        "lat": 18.38,
        "lon": 77.58,
        "wmts_layer": "Mars_MRO_CTX_Mosaic",
        "description": "Terreno volcánico y sedimentario con basaltos y piroclastos."
      },
      "sub_scores": {
        "topography": 0.92,
        "roughness": 0.88,
        "spectral": 0.84,
        "environmental": 0.86
      },
      "logistics": {
        "accessibility_score": 0.91,
        "nearest_paved_road_km": 14.5,
        "nearest_airport_code": "PPE",
        "nearest_airport_km": 92.0,
        "permits_required": "CONANP / Reserva de la Biosfera"
      },
      "metrics_comparison": {
        "mean_slope_deg": { "earth": 14.2, "target": 12.8, "sigma_tol": 5.0 },
        "tri_roughness_index": { "earth": 0.42, "target": 0.39, "sigma_tol": 0.15, "note": "Normalizado: GLO-30 TRI + SAR vs. THEMIS Thermal Inertia Proxy" },
        "ferrous_iron_index": { "earth": 1.38, "target": 1.44, "sigma_tol": 0.25, "note": "Sentinel-2 SWIR1/NIR vs. MRO CRISM Mafic Index" },
        "inferred_minerals": {
          "earth": ["Olivine", "Plagioclase Basalt", "Pyroxene"],
          "target": ["Basaltic Sands", "Augite", "Olivine-rich units"]
        }
      },
      "breakdown_limits": {
        "atmospheric_pressure": "Tierra: ~1013 hPa vs. Marte: ~6 hPa. El arrastre aerodinámico y la sustentación eólica son incomparables.",
        "gravity": "Tierra: 1.0g vs. Marte: 0.38g. El ángulo de reposo dinámico y el hundimiento de rueda (sinkage) varían por menor compactación gravitatoria.",
        "radiation": "La magnetosfera terrestre bloquea radiación GCR y eventos de partículas solares (SPE).",
        "thermal_cycle": "Tierra: oscilación diurna ~20°C vs. Marte: oscilación extrema de ~80°C a ~100°C."
      },
      "test_protocol": "Pruebas de tracción en taludes basálticos sueltos, evaluación de desgaste de bandas de rodadura y calibración de odometría visual (SLAM).",
      "datasets": [
        { "name": "Copernicus DEM GLO-30 & Sentinel-1 SAR", "source": "ESA / OpenTopography" },
        { "name": "Sentinel-2 L2A Multispectral (SWIR/NIR)", "source": "Copernicus Data Space" },
        { "name": "MOLA-HRSC Blended DEM 200m & THEMIS TI", "source": "NASA PDS Geosciences Node" },
        { "name": "MRO CRISM Summary Products", "source": "NASA Mars Trek" }
      ]
    },
    {
      "id": "sahara-bodele-depression",
      "h3_index": "86534e26fffffff",
      "name": "Depresión de Bodélé, Chad",
      "location": {
        "lat": 17.000,
        "lon": 18.000,
        "country": "Chad",
        "region_type": "Hyper-arid Basin / Dust Source"
      },
      "classification": "NEW_CANDIDATE",
      "analog_type": "DYNAMIC_PROCESS",
      "target_body": "Mars",
      "target_site": {
        "id": "mars-amazonis-dust",
        "name": "Global Dust Storm Activity (Amazonis / Chryse)",
        "lat": 20.00,
        "lon": -40.00,
        "wmts_layer": "Mars_Viking_MDIM21_ClrMosaic",
        "description": "Zonas de movilización de partículas finas durante tormentas globales marcianas."
      },
      "sub_scores": {
        "topography": 0.72,
        "roughness": 0.75,
        "spectral": 0.81,
        "environmental": 0.96
      },
      "logistics": {
        "accessibility_score": 0.28,
        "nearest_paved_road_km": 410.0,
        "nearest_airport_code": "NDJ",
        "nearest_airport_km": 580.0,
        "permits_required": "Expedición militar / Especial"
      },
      "metrics_comparison": {
        "mean_slope_deg": { "earth": 1.8, "target": 1.2, "sigma_tol": 5.0 },
        "tri_roughness_index": { "earth": 0.12, "target": 0.15, "sigma_tol": 0.15, "note": "Llanura sedimentaria fina" },
        "aerosol_optical_depth": { "earth": 0.92, "target": 0.95, "sigma_tol": 0.20, "note": "MODIS Deep Blue AOD vs. MCS Dust Opacity Normalizada" },
        "inferred_minerals": {
          "earth": ["Diatomite", "Quartz Silt", "Illite/Kaolinite"],
          "target": ["Ferric Oxides", "Basaltic Fines", "Perchlorate-bearing Dust"]
        }
      },
      "breakdown_limits": {
        "atmospheric_pressure": "Presión terrestre de 1013 hPa frente a 6 hPa marcianos. En Marte, el umbral de fricción eólica (límite de Bagnold) exige velocidades de viento mucho mayores para iniciar la saltación.",
        "composition": "Partículas ricas en diatomeas y cuarzo abrasivo en la Tierra vs. silicatos basálticos finos enriquecidos con percloratos y óxidos férricos en Marte.",
        "electrostatics": "La ausencia de humedad relativa en Marte intensifica la carga triboeléctrica del polvo, elevando la adherencia en ópticas y paneles solares."
      },
      "test_protocol": "Ensayos de sellado mecánico rotativo, resistencia a la abrasión en articulaciones y evaluación de mitigación electrostática de polvo en celdas solares.",
      "datasets": [
        { "name": "MODIS Deep Blue Aerosol Optical Depth", "source": "NASA Earthdata" },
        { "name": "Mars Climate Sounder Dust Profiles", "source": "NASA PDS Geosciences Node" }
      ]
    }
  ]
}
```

---

## 5. Metodología: Índice de Similitud de Misión (MSI)

Para evitar las distorsiones de escala propias de la similitud coseno y la inestabilidad numérica de las divisiones por valores cercanos a cero en llanuras suaves, cada dimensión geofísica $k \in \{\text{topo}, \text{rough}, \text{spect}, \text{env}\}$ se evalúa mediante un **Kernel Radial Gaussiano (RBF)** calibrado con la tolerancia física de ingeniería $\sigma_k$:

$$
S_k(x_{\text{Earth}}, x_{\text{Target}}) = \exp\left( - \frac{(x_{k,\text{Earth}} - x_{k,\text{Target}})^2}{2\sigma_k^2} \right)
$$

Este operador garantiza que:
* $S_k \in (0, 1]$ sea estrictamente acotado, continuo y diferenciable.
* Diferencias milimétricas en terrenos planos ($\approx 0^\circ$) produzcan similitudes cercanas a $1.0$ sin penalizaciones artificiales.
* Desviaciones que superen el umbral de tolerancia operativa $\sigma_k$ decaigan exponencialmente.

### Cálculo Dinámico en Memoria (Cliente Web)
El **Índice de Similitud de Misión (MSI)** se computa de forma reactiva en el navegador combinando el vector de pesos seleccionado por el ingeniero de misión:

$$
\text{MSI} = \sum_{k} w_k \cdot S_k \quad \text{sujeto a} \quad \sum_{k} w_k = 1.0, \quad w_k \ge 0
$$

De manera opcional en la interfaz, el usuario puede activar el **Índice Ajustado por Logística ($\text{MSI}_{\text{log}}$)** para priorizar sitios accesibles para campañas de campo de bajo costo:

$$
\text{MSI}_{\text{log}} = \text{MSI} \cdot \left(1 - \lambda + \lambda \cdot A_{\text{log}}\right)
$$

donde $\lambda \in [0, 0.3]$ es el factor de importancia logística y $A_{\text{log}} = \exp(-d_{\text{road}} / 100\text{ km})$ mide la accesibilidad vial terrestre.

### Definición de Subíndices Geofísicos ($S_k$)
1. **$S_{\text{topo}}$ (Macro-Topografía y Pendientes):**
   Evalúa la distribución de pendientes ($\mu_\theta$ y percentil $P_{90}$) calculada sobre modelos de elevación digital a escala regional ($\sigma_{\text{topo}} = 5.0^\circ$).
2. **$S_{\text{rough}}$ (Rugosidad Superficial por Proxy Termofísico/Topográfico):**
   Dado que los DEMs globales ($30\text{--}200\text{ m/px}$) no resuelven obstáculos sub-métricos a escala de chasis de rover, $S_{\text{rough}}$ cruza variables proxy normalizadas en $[0,1]$ antes del *downsampling*:
   * **Tierra:** Índice de Rugosidad del Terreno (*TRI*, desviación local de elevación en ventana de $3\times3$ sobre GLO-30) combinado con retrodispersión radar SAR (Sentinel-1 VV/VH) sensible a rugosidad centimétrica.
   * **Marte / Luna:** Inercia Térmica de Mars Odyssey THEMIS (que cuantifica tamaño de grano y abundancia de rocas superficiales) y mapas de rugosidad bidireccional LRO LOLA (Exponente de Hurst) para la Luna.
3. **$S_{\text{spect}}$ (Afinidad Mineralógica y Espectral):**
   Compara índices espectrales continuos de reflectancia multiespectral (Sentinel-2 / Landsat 8-9 en Tierra vs. MRO CRISM / Chandrayaan-1 $M^3$):
   * **Índice de Minerales Máficos / Ferrosos ($R_{\text{Fe}}$):** Ratio $\text{SWIR}_1 / \text{NIR}$ para presencia de olivinos y piroxenos en basaltos.
   * **Índice de Óxidos Férricos ($R_{\text{Ox}}$):** Ratio $\text{Red} / \text{Blue}$ para regolito oxidado.
   * **Índice de Filosilicatos / Arcillas ($R_{\text{Clay}}$):** Ratio $\text{SWIR}_1 / \text{SWIR}_2$ para alteración acuosa e ISRU.
   *(La catalogación mineralógica específica en texto se asigna por enriquecimiento semántico sobre los Top 100 clusters generados en Yuca)*.
4. **$S_{\text{env}}$ (Condiciones Ambientales y Procesos Dinámicos):**
   * **Modo Estático:** Índice de hiper-aridez derivado de la inversión de vegetación ($\text{NDVI} < 0.15$) y humedad superficial (NDWI).
   * **Modo Dinámico:** Frecuencia estacional de eventos de polvo medida mediante Profundidad Óptica de Aerosoles (MODIS Deep Blue AOD a $550\text{ nm}$) contrastada con perfiles de opacidad de polvo atmosférico de *Mars Climate Sounder* (MCS).

---

## 6. Datasets Oficiales (NASA, USGS, ESA, JAXA)

| Cuerpo | Dimensión | Sensor / Misión | Producto Específico |
| :--- | :--- | :--- | :--- |
| **Luna** | Topografía y Pendiente | LRO LOLA | Global Lunar DTM 118m / Polar SLDEM 20–60m |
| **Luna** | Rugosidad de Superficie | LRO LOLA Roughness | Lunar Surface Roughness Maps (Hurst Exponent) |
| **Luna** | Composición / Mineralogía | Chandrayaan-1 / $M^3$ | Reflectancia espectral / Diviner Christiansen Feature |
| **Luna** | Temperaturas Extremas | LRO Diviner | Mapas térmicos de regiones en sombra permanente (PSRs) |
| **Marte** | Topografía Global | MGS MOLA + MEX HRSC | Blended Global DEM (200 m/px) |
| **Marte** | Topografía Local | MRO HiRISE | DTMs de sitios de aterrizaje a 1 m/px |
| **Marte** | Termofísica / Rugosidad Proxy | Mars Odyssey THEMIS | Thermal Inertia Global Map (tamaño de grano/roca) |
| **Marte** | Dinámica Atmosférica | Mars Climate Sounder | Registros de perfiles de polvo atmosférico global |
| **Tierra** | Topografía y Rugosidad Proxy | Copernicus GLO-30 + Sentinel-1 | Global DEM (TRI 30m) + Backscatter Radar SAR |
| **Tierra** | Índices Espectrales y Suelo | Sentinel-2 / Landsat 8/9 | Ratios $\text{SWIR}_1/\text{NIR}$ (Hierro), $\text{SWIR}_1/\text{SWIR}_2$ (Arcillas) y NDVI |
| **Tierra** | Dinámica Eólica y Aerosoles | Terra/Aqua MODIS | Deep Blue Aerosol Optical Depth (AOD 550 nm) |
| **Tierra** | Accesibilidad Logística | OpenStreetMap / Natural Earth | Red vial pavimentada global y aeródromos (Cálculo de distancia) |

---

## 7. Flujo de Navegación del Usuario (Frontend)

```
[1. Definición del Escenario]
       │
       ▼
   • Selector de Cuerpo: Luna (Artemis) | Marte
   • Tipo de Análogo: Terreno / Geología Estática | Proceso Dinámico (Polvo / Viento)
   • Caso Operativo (Preset de Pesos): Movilidad | ISRU & Hielo | Abrasión de Polvo
       │
       ▼
[2. Ponderación de Pesos y Filtro Logístico en Memoria]
   • Sliders reactivos de dimensiones geofísicas + Toggle de "Prioridad Logística (Km)"
       │
       ▼
[3. Exploración Dual en Pantalla]
   • Vista Terrestre (Mapbox GL): Hexágonos H3 y marcadores clasificados por afinidad
   • Vista Planetaria (Leaflet + NASA Trek WMTS): Contexto orbital de Marte / Luna
   • Barra de Resultados: Tarjetas comparativas con score MSI en vivo
       │
       ▼
[4. Ficha Técnica e Inspección Científica]
   • Radar Chart de 4 ejes + Indicador de Accesibilidad Vial
   • PANEL CRÍTICO: "Límites del Análogo" (Gravedad, Presión, Radiación)
   • Protocolo de prueba sugerido para ingeniería de campo
   • Enlaces directos de procedencia a datasets de NASA / PDS
       │
       ▼
[5. Comparación y Exportación]
   • Vista comparativa "Versus" lado a lado entre dos sitios (ej. Clásico vs. Nuevo Candidato)
   • Exportación limpia de ficha técnica en JSON / Markdown (y vista de impresión CSS)
```

---

## 8. Distribución del Equipo (6 Personas)

```
                              ┌────────────────────────┐
                              │  COORDINACIÓN GENERAL  │
                              └───────────┬────────────┘
                                          │
            ┌─────────────────────────────┴─────────────────────────────┐
            ▼                                                           ▼
 ┌──────────────────────┐                                    ┌──────────────────────┐
 │   EQUIPO CÓDIGO (2)  │                                    │ EQUIPO DATOS, CIENCIA│
 │                      │                                    │   Y PRESENTACIÓN (4) │
 └──────────┬───────────┘                                    └──────────┬───────────┘
            │                                                           │
   ┌────────┴────────┐                                         ┌────────┴────────┐
   ▼                 ▼                                         ▼                 ▼
[Dev 1]           [Dev 2]                                   [P1: Pitch]       [P2: Data/GEE]
Frontend, UI      Pipeline Yuca,                            Orador principal, Pre-agregación GEE,
y Dual Map        H3/HDBSCAN y JSON                         guion y defensa   targets y JSON curado
                                                                                │
                                                            [P3: Science]     [P4: Media/Deck]
                                                            Límites físicos,  Diapositivas y
                                                            docs oficiales    video demo respaldo
```

### Funciones Específicas
* **Dev 1 (Frontend):** Construir la interfaz reactiva (Vite + React + Tailwind + Mapbox GL para Tierra + Leaflet/NASA WMTS para planeta objetivo + Recharts) y la vista comparativa "Versus".
* **Dev 2 (Pipeline HPC & Despliegue):** Programar el script en Yuca sobre la malla H3 (cálculo vectorial RBF + clustering HDBSCAN), ensamblar `analogs_universe.json` y desplegar en Vercel/Netlify.
* **Persona 1 (Lead Pitch & Orador):** Redactar y memorizar el guion cronometrado para los jueces; liderar la defensa técnica en la sesión de preguntas y respuestas.
* **Persona 2 (Ingeniería de Datos Satelitales & Enlace GEE):** Ejecutar el script en Google Earth Engine desde la Hora 0 para exportar la tabla de celdas H3 pre-alineada hacia Yuca y estructurar en código los metadatos de sitios *Target* (liberando a Dev 2 de tareas de limpieza manual).
* **Persona 3 (Física Planetaria & Documentación):** Redactar las justificaciones cuantitativas de "Límites del análogo", protocolos de prueba de campo, responder el formulario de NASA Space Apps y documentar el uso de IA.
* **Persona 4 (Deck & Demo de Respaldo):** Diseñar diapositivas de alto impacto visual y grabar el video de navegación de la web funcional para respaldar la presentación ante fallas de red.

---

## 9. Cronograma de Ejecución (48 Horas)

| Fase Temporal | Hito: Equipo de Código + Data Lead (Dev 1, Dev 2, P2) | Hito: Equipo de Ciencia y Presentación (P1, P3, P4) |
| :--- | :--- | :--- |
| **H00 – H06** | **Dev 1:** Setup Vite + React + Tailwind y mock de `analogs_universe.json`.<br>**P2 + Dev 2:** Extracción de malla H3 en GEE y vectores de sitios objetivo (Luna/Marte). | Selección de casos de misión, redacción de límites físicos base (gravedad, presión, radiación) y estructura narrativa del pitch. |
| **H06 – H14** | **Dev 1:** Montaje del Dual Map Viewer y sliders reactivos con cálculo RBF en memoria.<br>**Dev 2:** Prueba piloto del script HDBSCAN + RBF en Yuca (cuadrante Sonora/SW USA). | Redacción de protocolos de prueba de ingeniería para los sitios clave y diseño visual de las primeras láminas del deck. |
| **H14 – H24** | **Dev 2:** Ejecución del batch global en la cola Slurm de Yuca.<br>**Dev 1 + P2:** Conexión del frontend con el dataset piloto e integración del filtro logístico. | Enriquecimiento semántico de los mejores clusters (mineralogía inferida, permisos) y cierre de textos del proyecto en NASA Space Apps. |
| **H24 – H36** | **Dev 1 + Dev 2:** Ingesta del `analogs_universe.json` definitivo de Yuca, Radar Charts, panel de "Límites del Análogo" y vista "Versus". | Primeros ensayos de pitch cronometrados usando la aplicación real desplegada; preparación de láminas de arquitectura y metodología matemática. |
| **H36 – H42** | **Code Freeze.** Pulido de interfaz, pruebas de rendimiento (<16 ms por frame) y corrección de detalles visuales. | Grabación del video demo de respaldo (1080p) y entrenamiento adversarial de preguntas y respuestas con el banco de objeciones del jurado. |
| **H42 – H48** | Publicación y documentación del repositorio abierto en GitHub (incluyendo scripts de Slurm/Yuca). | Ensayo general cronometrado y envío final en la plataforma oficial de NASA Space Apps. |
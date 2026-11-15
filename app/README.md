# PROTOTERRA — Frontend Web Application

The interactive, client-side planetary exploration console for **PROTOTERRA**. Built with **Vue 3**, **TypeScript**, and the **RETÍCULA Design System**, designed for real-time mission analysis, dynamic multi-dimensional similarity ranking, and planetary-scale cartographic visualization.

Deployed live on Firebase Hosting: **[https://prototerra.web.app](https://prototerra.web.app)**

---

## Architecture & Technology Stack

PROTOTERRA's frontend is engineered as a zero-backend, zero-latency reactive Single Page Application (SPA). Once the bundled client-side data contract (`analogs_universe.json`, ~7.5 MB gzip-compressed) is loaded into memory, all similarity re-calculations, spatial filtering, and telemetry inspections execute purely on the client CPU in <50 ms.

| Domain | Technology / Library | Application |
| :--- | :--- | :--- |
| **Reactive Core** | **Vue 3 (Composition API)** | State management, reactive filters, declarative UI components |
| **Type Safety** | **TypeScript 5.6** | Strict end-to-end typing for planetary targets, analog pairs, and telemetry |
| **Build & Tooling** | **Vite 8 & Rolldown** | Lightning-fast HMR, ES module bundling, tree-shaking |
| **Design System** | **RETÍCULA (SCSS)** | Telemetry console aesthetic, high-contrast dark mode, chamfered panels |
| **Cartography & GIS** | **Leaflet 1.9** | Interactive Earth analog mapping, satellite tiles, vector layers |
| **3D Visualization** | **Three.js 0.187** | Interactive 3D celestial orbit selectors for Moon and Mars targets |
| **Micro-Interactions**| **Anime.js 4.5** | Smooth orbital transitions and planetary navigation animation engine |
| **Formula Rendering** | **KaTeX 0.19** | Client-side LaTeX rendering for algorithmic explainability |
| **Code Highlighting**| **Highlight.js 11.12** | Syntax highlighting for embedded JSON schemas and data contracts |

---

## Directory Layout

```text
app/
├── public/                       # Static public assets served at root
│   ├── data/
│   │   └── analogs_universe.json # Pre-computed universe (76 targets, 5,010 analog pairs)
│   ├── diagrams/                 # Interactive Archify system blueprints
│   ├── figures/                  # 10 High-resolution scientific EDA control maps
│   └── favicon.ico               # Application favicon
├── src/
│   ├── assets/                   # Local fonts, team portraits, and branding icons
│   ├── components/               # Reusable RETÍCULA UI components
│   │   ├── explorer/             # Explorer & Site Sheet components
│   │   │   ├── ScenarioPanel.vue # Preset picker, weight sliders, animated InfoButtons
│   │   │   ├── SiteMap.vue       # Tactical Leaflet maps (selective opacity & beacon focus)
│   │   │   ├── RankList.vue      # Filtered & sorted target list with MSI bars
│   │   │   ├── SiteDossier.vue   # Deep site sheet: target vs. analog feature comparison
│   │   │   ├── MineralogyPanel.vue # Orbital mineralogy context (Kaguya MI, TES, EMIT)
│   │   │   ├── RadarChart.vue    # 7-Dimensional similarity radar profile
│   │   │   ├── InfoButton.vue    # Rotating 45° (+) to (×) explanation toggle
│   │   │   └── InfoPanel.vue     # Full-width explanation callout panels
│   │   ├── charts/               # Reactive SVG data visualization components
│   │   │   ├── BarChart.vue      # Top countries by unique analog candidate count
│   │   │   ├── StripPlot.vue     # MSI distribution strip plot for Moon and Mars
│   │   │   ├── FunnelChart.vue   # EDA candidate retention funnel visualization
│   │   │   └── SimilarityMatrix.vue # Target-analog correlation heatmap
│   │   ├── home/                 # Interactive 3D home components (SolarSystem, SectionRail)
│   │   ├── how/                  # 6-Stage interactive pipeline walkthrough stages
│   │   ├── layout/               # Header, Footer, Hero, SectionBlock, DataTable, FigureSlot
│   │   └── reticula/             # RETÍCULA design tokens (RButton, RTag, RGlyph, RReadout, RPanel...)
│   ├── composables/              # Vue 3 reactive composables (useUniverse, useExplorer, useReducedMotion)
│   ├── content/                  # Text copy, explainability formulas, and team bios
│   ├── lib/                      # Core mathematical & client-side algorithms (msi.ts, content.ts, stats.ts)
│   ├── styles/                   # RETÍCULA design tokens, typography, and SCSS modules
│   ├── views/                    # 7 Route Views (Home, Results, Challenge, HowItWorks, Algorithm, Data, About)
│   ├── App.vue                   # Root application shell
│   ├── main.ts                   # Application bootstrap and plugin initialization
│   └── router/                   # Vue Router hash-mode configuration
├── package.json                  # Dependencies, scripts, and package metadata
├── tsconfig.json                 # TypeScript compiler configuration
└── vite.config.ts                # Vite bundler configuration
```

---

## Key Features

1. **Interactive 3D Celestial Selector:**
   Seamlessly switch between the **Moon (Artemis III polar zones & equatorial maria)** and **Mars (Perseverance Jezero, Gale, Valles Marineris)** with 3D coordinate anchoring.
2. **Real-Time Client-Side Multi-Dimensional Scoring (MSI):**
   Drag weights across 7 physical dimensions (*Topography*, *Roughness*, *Aridity*, *Thermal*, *Geology*, *Dust*, *Ice*). The client re-sorts all 5,010 candidates on-the-fly in <50 ms without server round-trips.
3. **Mission Presets:**
   One-click presets calibrated in `scripts/pipeline/match.py` for specific aerospace testing goals:
   - 🚗 **Rover mobility and traction** (`mobility_and_traction`): Focuses on slope hazards, roughness, and terrain ruggedness (Moon & Mars).
   - 🏗 **Base construction and landing** (`construction_and_base`): Emphasizes low-relief topography, landing stability, and foundation substrates (Moon & Mars).
   - 🪨 **Geology and surface materials** (`geology_and_materials`): Heavy weight on lithologic and stratigraphic compatibility (Moon & Mars).
   - 🌪 **Dust storms and seasons** (`dust_and_seasons`): Focuses on atmospheric aerosols, aeolian saltation, and thermal swings (Mars only).
   - 🧊 **Water ice and cold traps (ISRU)** (`isru_and_ice`): Prioritizes volatiles stability, cryospheric permafrost, and permanently shadowed regions (Moon & Mars).
4. **Orbital Mineralogy & Composition Context (`CONTEXT · NOT SCORED`):**
   Renders JAXA Kaguya MI (Moon) and MGS TES (Mars) rock-forming silicate abundances alongside NASA EMIT L3 (Earth) secondary weathering mineralogy directly on each site dossier without unscientifically mixing them into the physical similarity score.
5. **Logistics & Fieldwork Grounding:**
   Calculates travel distances to the nearest paved road and commercial/cargo airport for all candidate Earth sites using global vector networks (Natural Earth).
6. **"Where the Analogy Breaks":**
   Explicit warning badges indicating physical non-substitutable barriers (1/6th gravity, hard vacuum, cosmic ionizing radiation) so engineers and scientists never make false assumptions.

---

## Quick Start & Local Development

### Prerequisites
- **Node.js**: v18.0.0 or later (v20+ recommended)
- **npm**: v9.0.0 or later

### Installation

```bash
# Navigate to the app directory
cd app

# Install dependencies
npm install
```

### Development Server

```bash
npm run dev
```
Starts the local development server with Vite HMR at `http://localhost:5173`.

### Production Build & Type Checking

```bash
# Type-check TypeScript and build optimized production bundle
npm run build
```
Generates production-ready distribution files in `app/dist/`.

### Preview Production Build

```bash
npm run preview
```
Spins up a local HTTP server serving the contents of `app/dist/` to verify production behavior.

---

## Deployment

The application is configured for deployment to **Firebase Hosting**:

```bash
# Build frontend
npm run build

# Deploy hosting target from project root
firebase deploy --only hosting:prototerra
```

Live Production URL: **[https://prototerra.web.app](https://prototerra.web.app)**

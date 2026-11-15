// The Algorithm page: eleven steps, each with its formulas, its parameters and the real source it runs.
// Code comes from the pipeline files through ?raw imports and lib/extract.ts, so the page cannot drift
// from the code. Parameter values are read from the same sources with `constOf`.

import planetFeaturesPy from "../../../scripts/pipeline/planet_features.py?raw";
import geoPy from "../../../scripts/pipeline/geo.py?raw";
import featuresPy from "../../../scripts/pipeline/features.py?raw";
import targetsPy from "../../../scripts/pipeline/targets.py?raw";
import earthFeaturesPy from "../../../scripts/pipeline/earth_features.py?raw";
import matchPy from "../../../scripts/pipeline/match.py?raw";
import dustPy from "../../../scripts/pipeline/dust.py?raw";
import icePy from "../../../scripts/pipeline/ice.py?raw";
import geologyRulesPy from "../../../scripts/pipeline/geology_rules.py?raw";
import configPy from "../../../scripts/pipeline/config.py?raw";
import msiTs from "../lib/msi.ts?raw";
import { extractBetween, extractBlock } from "../lib/extract";

/** One row of a parameter readout. */
export interface ReadoutItem {
  label: string;
  value: string;
}

export const REPO_URL = "https://github.com/OwenSolis03/prototerra";

/** Value of a module-level constant, as written in the source (for example "0.25" or "16.0"). */
export function constOf(source: string, name: string): string {
  const m = source.match(new RegExp(`^${name}\\s*(?::[^=\\n]+)?=\\s*([^\\n#]+?)\\s*(?:#.*)?$`, "m"));
  if (!m) throw new Error(`constOf: ${name} not found`);
  return m[1]!.trim();
}

/** A list constant written over several lines, returned as its items. */
function listOf(source: string, name: string): string[] {
  const m = source.match(new RegExp(`^${name}[^=\\n]*=\\s*(\\[[\\s\\S]*?\\])`, "m"));
  if (!m) throw new Error(`listOf: ${name} not found`);
  return [...m[1]!.matchAll(/["']([^"']+)["']/g)].map((x) => x[1]!);
}

/** Body radius from config.py, in metres. */
const radiusM = (body: string): number => {
  const m = configPy.match(new RegExp(`"${body}":\\s*([0-9.]+)`));
  if (!m) throw new Error(`radiusM: ${body} not found`);
  return Number(m[1]);
};
const radiusOf = (body: string): string => radiusM(body).toLocaleString("en-US");

export interface Snippet {
  file: string;
  lang: "python" | "typescript";
  code: string;
}

/** A table that is read from the universe JSON when the page renders. */
export type LiveTable = "normalization" | "presets" | "geology" | "limits-moon" | "limits-mars" | "funnel";

export interface Step {
  code: string;
  title: string;
  summary: string;
  formulas: string[];
  params: ReadoutItem[];
  notes?: string[];
  live?: LiveTable[];
  snippets: Snippet[];
  /** Optional call to action at the end of the step. */
  cta?: { label: string; to: string };
}

const param = (label: string, value: string): ReadoutItem => ({ label, value });

export const STEPS: Step[] = [
  {
    code: "STEP.01",
    title: "ONE GRID FOR EVERY BODY",
    summary:
      "The three bodies are swept with an almost equal-area mesh of patch centres between −88° and 88°. The longitude step widens with latitude, so every patch covers the same area.",
    formulas: [
      String.raw`\Delta\varphi=\frac{180}{\pi}\cdot\frac{L}{R},\qquad \Delta\lambda(\varphi)=\frac{\Delta\varphi}{\cos\varphi},\qquad L=32\ \text{km}`,
    ],
    params: [
      param("R EARTH", `${radiusOf("Earth")} m`),
      param("R MOON", `${radiusOf("Moon")} m`),
      param("R MARS", `${radiusOf("Mars")} m`),
      param("PATCH L", `${constOf(configPy, "PATCH_SIZE_KM")} km`),
    ],
    snippets: [{ file: "scripts/pipeline/planet_features.py", lang: "python", code: extractBlock(planetFeaturesPy, "def generate_grid(") }],
  },
  {
    code: "STEP.02",
    title: "THE SAME 32 KM PATCH EVERYWHERE",
    summary:
      "Each patch is reprojected to a local azimuthal equidistant projection centred on itself and resampled to 500 m per pixel (64 × 64). Nodata is masked first, then scale and offset are applied. Patches with less than 90 % valid pixels, and patches that cross ±180°, are dropped, so slope and roughness are comparable across bodies and latitudes.",
    formulas: [
      String.raw`N=\frac{L}{r}=\frac{32\,000\ \text{m}}{500\ \text{m}}=64,\qquad z=\text{raw}\cdot s+o,\qquad \frac{\#\{\text{valid pixels}\}}{N^{2}}\ \ge\ 0.90`,
      String.raw`x=R\,c\,\sin\alpha,\quad y=R\,c\,\cos\alpha,\qquad \cos c=\sin\varphi_0\sin\varphi+\cos\varphi_0\cos\varphi\cos(\lambda-\lambda_0)`,
    ],
    params: [
      param("PATCH SIZE", `${constOf(configPy, "PATCH_SIZE_KM")} km`),
      param("RESOLUTION", `${constOf(configPy, "PATCH_RES_M")} m/px`),
      param("PIXELS", `${constOf(configPy, "PATCH_PIXELS")} × ${constOf(configPy, "PATCH_PIXELS")}`),
      param("MIN VALID", constOf(configPy, "MIN_VALID_FRAC")),
    ],
    notes: ["c is the angular distance to the patch centre and α the azimuth."],
    snippets: [
      { file: "scripts/pipeline/geo.py", lang: "python", code: extractBlock(geoPy, "def extract_patch(") },
      { file: "scripts/pipeline/geo.py", lang: "python", code: extractBlock(geoPy, "def _clean_nodata(") },
    ],
  },
  {
    code: "STEP.03",
    title: "SIX TERRAIN FEATURES",
    summary:
      "One function computes the same six terrain features for Earth, the Moon and Mars: mean and 90th-percentile slope, relief, hypsometric integral, detrended roughness and terrain ruggedness. Mean elevation is stored but never compared, because the vertical datums differ.",
    formulas: [
      String.raw`s_{ij}=\arctan\sqrt{\left(\frac{\partial z}{\partial x}\right)^{2}+\left(\frac{\partial z}{\partial y}\right)^{2}},\qquad \bar{s}=\operatorname{mean}(s),\qquad s_{90}=P_{90}(s)`,
      String.raw`\text{relief}=P_{95}(z)-P_{5}(z),\qquad HI=\frac{\bar{z}-z_{\min}}{z_{\max}-z_{\min}}`,
      String.raw`\hat{z}=ax+by+c\ \ (\text{least squares}),\qquad \sigma_d=\operatorname{std}\!\left(z-\hat{z}\right)`,
      String.raw`TRI=\operatorname*{mean}_{(i,j)}\sqrt{\sum_{k\in N_8(i,j)}\left(z_k-z_{ij}\right)^{2}}`,
    ],
    params: [
      param("FEATURES", "6"),
      param("SLOPE", "MEAN · P90"),
      param("ROUGHNESS", "σd · TRI"),
      param("SHAPE", "RELIEF · HI"),
    ],
    snippets: [{ file: "scripts/pipeline/features.py", lang: "python", code: extractBlock(featuresPy, "def compute_features(") }],
  },
  {
    code: "STEP.04",
    title: "TARGETS ON THE MOON AND MARS",
    summary:
      "There are 16 curated targets: 8 lunar candidate regions for Artemis III, anchored on the IAU feature of the same name, plus the rim of Shackleton; and 8 Martian sites, the landing sites and the shallow-ice region of Arcadia. Each body also has 30 terrain archetypes. A point anchor averages 5 patches (centre plus 4 neighbours, at least 3 valid). A rim anchor averages 8 patches around the rim every 45° (at least 5 valid). Archetypes are k-means clusters on standardised features, and the representative is the real patch nearest the centroid.",
    formulas: [
      String.raw`\mathbf{f}_T=\frac{1}{n}\sum_{p=1}^{n}\mathbf{f}_p,\qquad \min_{\mu,\,c}\ \sum_i\left\lVert \mathbf{x}_i-\mu_{c(i)}\right\rVert^{2},\qquad k=30`,
    ],
    params: [
      param("NEIGHBOUR OFFSET", `${constOf(targetsPy, "NEIGHBOR_OFFSET_KM")} km`),
      param("CLUSTERS N", constOf(targetsPy, "N_CLUSTERS")),
      param("KMEANS SEED", constOf(targetsPy, "KMEANS_SEED")),
      param("CLUSTER FEATURES", listOf(targetsPy, "CLUSTER_FEATURES").join(" · ")),
    ],
    snippets: [
      { file: "scripts/pipeline/targets.py", lang: "python", code: extractBlock(targetsPy, "def anchor_points(") },
      { file: "scripts/pipeline/targets.py", lang: "python", code: extractBlock(targetsPy, "def build_clusters(") },
    ],
  },
  {
    code: "STEP.05",
    title: "EARTH: ONLY BARE GROUND",
    summary:
      "Of 497,818 grid points, 179,663 have a land tile. Vegetated ones are dropped when their annual maximum NDVI is above 0.25. Points without NDVI (permanent ice and snow) pass only if they have a daytime surface temperature. That leaves 44,375 candidates and 40,244 valid patches (90.69 %). Each site also gets its distance to the nearest road and airport, its country, and a label: KNOWN_ANALOG if it falls in one of the 12 analog regions already studied, NEW_CANDIDATE otherwise.",
    formulas: [
      String.raw`\text{keep}\iff \mathrm{NDVI}_{\max}\le 0.25\ \ \lor\ \ \left(\mathrm{NDVI}_{\max}=\varnothing\ \land\ \mathrm{LST}_{\text{day}}\neq\varnothing\right)`,
    ],
    params: [
      param("NDVI PREFILTER", `≤ ${constOf(earthFeaturesPy, "NDVI_PREFILTER_MAX")}`),
      param("MIN VALID", constOf(configPy, "MIN_VALID_FRAC")),
      param("VALID PATCHES", "40,244 (90.69 %)"),
    ],
    live: ["funnel"],
    snippets: [
      { file: "scripts/pipeline/earth_features.py", lang: "python", code: extractBlock(earthFeaturesPy, "def _compute_prefilter_masks(") },
    ],
  },
  {
    code: "STEP.06",
    title: "ROBUST NORMALISATION IN EARTH UNITS",
    summary:
      "Features are expressed in Earth standard deviations. Each one is centred on its Earth median and scaled by Earth's median absolute deviation (MAD), after log1p on the long-tailed features. A z of 2 means two Earth deviations steeper than typical bare Earth ground.",
    formulas: [
      String.raw`x'=\ln(1+x)\ \ \text{for relief},\ \sigma_d,\ TRI;\qquad z_k=\frac{x'_k-\operatorname{med}_E(x'_k)}{1.4826\cdot\operatorname{MAD}_E(x'_k)},\qquad \operatorname{MAD}=\operatorname{med}\left|x'-\operatorname{med}(x')\right|`,
    ],
    params: [
      param("LOG1P FEATURES", listOf(matchPy, "LOG_FEATURES").join(" · ")),
      param("MAD → σ", constOf(matchPy, "MAD_TO_SIGMA")),
      param("MAD FLOOR", constOf(matchPy, "MAD_FLOOR")),
    ],
    live: ["normalization"],
    snippets: [{ file: "scripts/pipeline/match.py", lang: "python", code: extractBlock(matchPy, "class Normalizer") }],
  },
  {
    code: "STEP.07",
    title: "SEVEN SIMILARITY DIMENSIONS",
    summary:
      "Each dimension gives a similarity between 0 and 1 through a Gaussian kernel. Dimensions that cannot be compared in absolute units (thermal, dust, cold traps) compare percentile ranks within each planet: how extreme the site is at home.",
    formulas: [
      String.raw`d_{\text{topo}}=\sqrt{\tfrac{1}{4}\sum_{k\in\mathcal{T}}\left(z^{E}_k-z^{T}_k\right)^{2}},\qquad S_{\text{topo}}=\exp\!\left(-\frac{d_{\text{topo}}^{2}}{2\sigma^{2}}\right),\quad \sigma=1`,
      String.raw`d_{\text{rough}}=\sqrt{\tfrac{1}{2}\sum_{k\in\mathcal{R}}\left(z^{E}_k-z^{T}_k\right)^{2}},\qquad S_{\text{rough}}=\exp\!\left(-\frac{d_{\text{rough}}^{2}}{2\sigma^{2}}\right)`,
      String.raw`S_{\text{env}}=\exp\!\left(-\frac{\max\!\left(0,\ \mathrm{NDVI}_{\max}-0.10\right)^{2}}{2\,(0.10)^{2}}\right)`,
      String.raw`r=\frac{\operatorname{rank}(x)}{n}\ \ (\text{within its own planet}),\qquad S_{\text{thermal}}=\exp\!\left(-\frac{1}{2}\left(\frac{r_E-r_T}{0.15}\right)^{2}\right)`,
      String.raw`S_{\text{geo}}=M\!\left[c_T,\ c_E\right]\quad(\text{8-class similarity matrix})`,
      String.raw`S_{\text{dust}}=\exp\!\left(-\frac{d_L^{2}+d_S^{2}+d_\phi^{2}}{6}\right),\quad d_L=\frac{\left|r^{L}_E-r^{L}_T\right|}{0.15},\quad d_S=\frac{\left|r^{S}_E-r^{S}_T\right|}{0.15},\quad d_\phi=\frac{\Delta_\circ(\phi_E,\phi_T)}{60^\circ}`,
      String.raw`\text{seasonality}=\frac{\max_b\tau_b-\min_b\tau_b}{\bar{\tau}+\varepsilon},\qquad L_s^{E}=\left(\frac{\text{doy}-79.5}{365.2422}\cdot 360^\circ\right)\bmod 360^\circ`,
      String.raw`S_{\text{ice}}^{\text{Moon}}=\exp\!\left(-\frac{d^{2}}{2}\right),\quad d=\sqrt{\frac{d_c^{2}+d_i^{2}}{2}},\quad d_c=\frac{r^{c}_E-r^{c}_T}{0.15},\quad d_i=\frac{I_E-I_T}{0.5};\qquad S_{\text{ice}}^{\text{Mars}}=\exp\!\left(-\frac{d_i^{2}}{2}\right)\ \ (I_T>0)`,
    ],
    params: [
      param("NDVI FREE", constOf(matchPy, "NDVI_FREE")),
      param("NDVI SCALE", constOf(matchPy, "NDVI_SCALE")),
      param("THERMAL UNIT", constOf(matchPy, "THERMAL_UNIT")),
      param("DUST RANK σ", constOf(dustPy, "DUST_RANK_SIGMA")),
      param("DUST PHASE σ", `${constOf(dustPy, "DUST_PHASE_SIGMA_DEG")}°`),
      param("TROPICAL BAND", `${constOf(dustPy, "TROPICAL_LAT_DEG")}°`),
      param("COLD RANK σ", constOf(icePy, "COLD_RANK_SIGMA")),
      param("ICE LEVEL σ", constOf(icePy, "ICE_LEVEL_SIGMA")),
    ],
    notes: [
      "Topography uses mean slope, p90 slope, relief and the hypsometric integral (set 𝒯). Roughness uses σd and TRI (set ℛ).",
      "Missing NDVI (ice) counts as bare ground, so S_env = 1. Thermal and dust apply only to Mars.",
      "Near the equator (|latitude| < 15°, on the Earth patch or the target) the phase term is dropped and the divisor goes from 6 to 4. The dust phase is shifted by 180° in the southern hemisphere to align the seasons.",
      "I_E is 1 for an ice layer, 0.5 for frozen ground (daytime LST below 0 °C) and 0 otherwise.",
    ],
    live: ["geology"],
    snippets: [
      { file: "scripts/pipeline/match.py", lang: "python", code: extractBlock(matchPy, "def dimension_scores(") },
      { file: "scripts/pipeline/match.py", lang: "python", code: extractBlock(matchPy, "def geology_scores(") },
      { file: "scripts/pipeline/dust.py", lang: "python", code: extractBlock(dustPy, "def S_dust(") },
      { file: "scripts/pipeline/ice.py", lang: "python", code: extractBlock(icePy, "def S_ice(") },
      { file: "scripts/pipeline/geology_rules.py", lang: "python", code: extractBetween(geologyRulesPy, "_OFF_DIAGONAL_SIMILARITIES", "class SimilarityMatrix") },
    ],
  },
  {
    code: "STEP.08",
    title: "MISSION SIMILARITY INDEX AND MISSING DATA",
    summary:
      "The MSI is the weighted mean of the dimensions. Five mission presets fix the weights, and you can change them. Missing data has three cases. (A) The dimension does not apply to the body: it is ignored. (B) It is missing on the target: it is ignored, but if the remaining weight falls below 0.6 the target is not ranked for that preset. (C) The target has it and the Earth patch does not: it counts as 0, because there is no evidence and no credit. Before this rule the dust preset sent Martian targets to Antarctica, which has no dust data, and that 40 % of weight vanished.",
    formulas: [
      String.raw`\mathrm{MSI}=\frac{\sum_{d\in\mathcal{D}_T}w_d\,\tilde{S}_d}{\sum_{d\in\mathcal{D}_T}w_d},\qquad \tilde{S}_d=\begin{cases}S_d&\text{if measured on Earth}\\[2pt]0&\text{otherwise}\end{cases}`,
      String.raw`\text{coverage}=\frac{\sum_{d\in\mathcal{D}_T}w_d}{\sum_{d\in\mathcal{A}_b}w_d}\ \ge\ 0.6`,
    ],
    params: [
      param("EARTH MISSING", constOf(matchPy, "EARTH_MISSING_SCORE")),
      param("MIN COVERAGE", constOf(matchPy, "MIN_PRESET_COVERAGE")),
      param("ICE-CAP EXEMPT", "isru_and_ice"),
    ],
    live: ["presets"],
    notes: ["The scoring rules below are copied from metadata.scoring_policy in the exported file."],
    snippets: [
      { file: "scripts/pipeline/match.py", lang: "python", code: extractBlock(matchPy, "def msi(") },
      { file: "scripts/pipeline/match.py", lang: "python", code: extractBlock(matchPy, "def preset_status(") },
      { file: "scripts/pipeline/match.py", lang: "python", code: extractBlock(matchPy, "def available_dims(") },
    ],
  },
  {
    code: "STEP.09",
    title: "DIVERSE TOP 30",
    summary:
      "Every Earth patch is scored against each target, and the list is walked from the highest MSI down. A site is accepted only if it is at least 150 km from every site already accepted, up to 30 per preset. At most 3 ice-surface sites appear in a list, except in the ice preset.",
    formulas: [
      String.raw`d=2R\arcsin\sqrt{\sin^{2}\frac{\Delta\varphi}{2}+\cos\varphi_1\cos\varphi_2\,\sin^{2}\frac{\Delta\lambda}{2}},\qquad \min_j d(i,j)\ \ge\ 150\ \text{km}`,
    ],
    params: [
      param("TOP N", constOf(matchPy, "TOP_N")),
      param("MIN SEPARATION", `${constOf(matchPy, "MIN_SEP_KM")} km`),
      param("ICE SURFACE MAX", constOf(matchPy, "MAX_ICE_SURFACE_PER_PRESET")),
      param("EARTH RADIUS", `${(radiusM("Earth") / 1000).toLocaleString("en-US")} km`),
    ],
    snippets: [
      { file: "scripts/pipeline/match.py", lang: "python", code: extractBlock(matchPy, "def haversine_km(") },
      { file: "scripts/pipeline/match.py", lang: "python", code: extractBlock(matchPy, "def select_diverse(") },
      { file: "scripts/pipeline/match.py", lang: "python", code: extractBlock(matchPy, "def select_by_preset(") },
    ],
  },
  {
    code: "STEP.10",
    title: "WHERE THE ANALOGY BREAKS",
    summary:
      "Each pair lists the features that do not match, in physical units, and the fixed physical limits of each body. No terrestrial site reproduces those limits: gravity, atmosphere, pressure and radiation.",
    formulas: [
      String.raw`\left|z^{E}_k-z^{T}_k\right|>1.5,\qquad \left|r_E-r_T\right|>0.30,\qquad \Delta_\circ(\phi_E,\phi_T)>90^\circ,\qquad c_E\neq c_T`,
    ],
    params: [
      param("MISMATCH z", constOf(matchPy, "MISMATCH_Z")),
      param("MISMATCH RANK", constOf(matchPy, "MISMATCH_RANK")),
      param("MISMATCH PHASE", `${constOf(matchPy, "MISMATCH_PHASE_DEG")}°`),
    ],
    live: ["limits-moon", "limits-mars"],
    snippets: [
      { file: "scripts/pipeline/match.py", lang: "python", code: extractBlock(matchPy, "def mismatches(") },
      { file: "scripts/pipeline/match.py", lang: "python", code: extractBlock(matchPy, "def layer_mismatches(") },
    ],
  },
  {
    code: "STEP.11",
    title: "RE-WEIGHTING IN THE BROWSER",
    summary:
      "The exported JSON keeps the sub-scores, so the app recalculates the MSI when a slider moves. An optional road-distance factor, controlled by λ, lowers the score of sites far from a road.",
    formulas: [
      String.raw`\mathrm{MSI}_{\lambda}=\mathrm{MSI}\cdot\left(1-\lambda+\lambda\,e^{-d_{\text{road}}/100\ \text{km}}\right),\qquad \lambda\in[0,\ 0.3]`,
    ],
    params: [
      param("λ RANGE", "0 to 0.30"),
      param("ROAD SCALE", "100 km"),
      param("DEFAULT λ", "0 (off)"),
    ],
    snippets: [
      { file: "app/src/lib/msi.ts", lang: "typescript", code: extractBetween(msiTs, "export function msi(", "/** Logistics-adjusted MSI") },
      { file: "app/src/lib/msi.ts", lang: "typescript", code: extractBetween(msiTs, "/** Logistics-adjusted MSI", "export interface RankedTarget") },
    ],
    cta: { label: "TRY IT IN RESULTS", to: "/results" },
  },
];

/** Parameters at a glance, shown at the end of the page. */
export const GLANCE: ReadoutItem[] = [
  param("PATCH", `${constOf(configPy, "PATCH_SIZE_KM")} km`),
  param("RESOLUTION", `${constOf(configPy, "PATCH_RES_M")} m/px`),
  param("GRID", `${constOf(configPy, "PATCH_PIXELS")} × ${constOf(configPy, "PATCH_PIXELS")}`),
  param("VALID", `≥ ${constOf(configPy, "MIN_VALID_FRAC")}`),
  param("RBF σ", "1"),
  param("NDVI FREE", constOf(matchPy, "NDVI_FREE")),
  param("NDVI SCALE", constOf(matchPy, "NDVI_SCALE")),
  param("NDVI PREFILTER", constOf(earthFeaturesPy, "NDVI_PREFILTER_MAX")),
  param("THERMAL UNIT", constOf(matchPy, "THERMAL_UNIT")),
  param("DUST RANK σ", constOf(dustPy, "DUST_RANK_SIGMA")),
  param("DUST PHASE σ", `${constOf(dustPy, "DUST_PHASE_SIGMA_DEG")}°`),
  param("TROPICAL BAND", `${constOf(dustPy, "TROPICAL_LAT_DEG")}°`),
  param("COLD RANK σ", constOf(icePy, "COLD_RANK_SIGMA")),
  param("ICE LEVEL σ", constOf(icePy, "ICE_LEVEL_SIGMA")),
  param("EARTH-MISSING SCORE", constOf(matchPy, "EARTH_MISSING_SCORE")),
  param("MIN PRESET COVERAGE", constOf(matchPy, "MIN_PRESET_COVERAGE")),
  param("TOP N", constOf(matchPy, "TOP_N")),
  param("MIN SEPARATION", `${constOf(matchPy, "MIN_SEP_KM")} km`),
  param("MAX ICE-SURFACE SITES", constOf(matchPy, "MAX_ICE_SURFACE_PER_PRESET")),
  param("MISMATCH z", constOf(matchPy, "MISMATCH_Z")),
  param("MISMATCH RANK", constOf(matchPy, "MISMATCH_RANK")),
  param("MISMATCH PHASE", `${constOf(matchPy, "MISMATCH_PHASE_DEG")}°`),
  param("MAD → σ", constOf(matchPy, "MAD_TO_SIGMA")),
];

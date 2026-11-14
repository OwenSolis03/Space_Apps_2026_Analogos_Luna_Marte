import type { Body, Dimension } from "./types";

export const BODY_LABEL: Record<Body, { name: string; adj: string }> = {
  Mars: { name: "Mars", adj: "Martian" },
  Moon: { name: "the Moon", adj: "lunar" },
};

/** Short labels for sliders and radar axes; the long description comes from metadata.dimensions. */
export const DIM_LABEL: Record<Dimension, { label: string; hint: string }> = {
  topography: { label: "Topography", hint: "slope and shape of the land" },
  roughness: { label: "Roughness", hint: "how bumpy the ground is" },
  environment: { label: "Aridity", hint: "no plants" },
  thermal: { label: "Thermal", hint: "day vs night temperature swing" },
  geology: { label: "Geology", hint: "type of rock" },
  dust: { label: "Dust", hint: "dust in the air and its seasons" },
  ice: { label: "Ice", hint: "water ice and very cold spots" },
};

export const FEATURE_LABEL: Record<string, { label: string; unit: string; dim: Dimension | null }> = {
  mean_slope_deg: { label: "Mean slope", unit: "°", dim: "topography" },
  p90_slope_deg: { label: "P90 slope", unit: "°", dim: "topography" },
  detrended_std_m: { label: "Elevation σ", unit: "m", dim: "roughness" },
  tri_m: { label: "TRI", unit: "m", dim: "roughness" },
  relief_m: { label: "Relief", unit: "m", dim: "topography" },
  hypsometric_integral: { label: "Hypsometric integral", unit: "", dim: "topography" },
  mean_elev_m: { label: "Mean elevation", unit: "m", dim: null },
  geo_class: { label: "Rock class", unit: "", dim: "geology" },
  thermal_rank: { label: "Thermal contrast rank", unit: "", dim: "thermal" },
  dust_level_rank: { label: "Dust level rank", unit: "", dim: "dust" },
  dust_seasonality_rank: { label: "Dust seasonality rank", unit: "", dim: "dust" },
  dust_peak_phase_deg: { label: "Dust peak season", unit: "°", dim: "dust" },
  cold_rank: { label: "Cold-trap rank", unit: "", dim: "ice" },
};

export const GEO_CLASS_LABEL: Record<string, string> = {
  VOLCANIC_BASIC: "basaltic volcanic",
  VOLCANIC_OTHER: "other volcanic",
  PYROCLASTIC: "pyroclastic",
  SEDIMENTARY: "sedimentary",
  EVAPORITE: "evaporite",
  CRYSTALLINE: "crystalline",
  IMPACT: "impact",
  ICE: "ice",
};

export const fmtValue = (v: number | string | null | undefined, unit = ""): string => {
  if (v == null) return "n/a";
  if (typeof v === "string") return GEO_CLASS_LABEL[v] ?? v.toLowerCase();
  const s = Math.abs(v) >= 100 ? Math.round(v).toLocaleString("en-US") : v.toFixed(2);
  return unit ? `${s} ${unit}` : s;
};

export const LIMIT_LABEL: Record<string, string> = {
  gravity: "Gravity",
  atmosphere: "Atmosphere",
  pressure: "Pressure",
  radiation: "Radiation",
  thermal_cycle: "Thermal cycle",
  thermal_extremes: "Thermal extremes",
  polar_lighting: "Polar lighting",
  polar_illumination: "Polar illumination",
  regolith_and_dust: "Regolith and dust",
  atmospheric_pressure: "Atmospheric pressure",
  dust_storms: "Dust storms",
  perchlorates_and_soil_chemistry: "Soil chemistry",
  elevation_datum: "Elevation",
};

/** Readable fallback for any new limit key: "some_new_factor" -> "Some new factor". */
export const limitLabel = (factor: string) =>
  LIMIT_LABEL[factor] ?? factor.charAt(0).toUpperCase() + factor.slice(1).replace(/_/g, " ");

// Capas base verificadas en docs/plan_implementacion.md (T10).
export const TILES = {
  Earth: {
    url: "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg",
    maxNativeZoom: 8,
    attribution: "NASA GIBS · Blue Marble",
  },
  Mars: {
    url: "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
    maxNativeZoom: 6,
    attribution: "NASA Mars Trek · MOLA",
  },
  Moon: {
    url: "https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
    maxNativeZoom: 7,
    attribution: "NASA Moon Trek · LROC WAC",
  },
} as const;

/** Suggested field use from the target's terrain features (simple rule on slope and TRI). */
export function suggestedUses(f: Record<string, number>, body: Body, lat: number): string[] {
  const out: string[] = [];
  const p90 = f.p90_slope_deg ?? 0;
  const tri = f.tri_m ?? 0;
  if (p90 < 5) out.push(`Landing and plains navigation tests (P90 slope ${p90.toFixed(1)}°).`);
  else if (p90 < 15) out.push(`Rover traverses on moderate slopes (P90 ${p90.toFixed(1)}°): traction and power use.`);
  else out.push(`Steep terrain (P90 ${p90.toFixed(1)}°): route planning, hazards and teleoperation.`);
  if (tri > 600) out.push(`High roughness (TRI ${Math.round(tri)} m): obstacle detection and visual odometry.`);
  else out.push(`Low to moderate roughness (TRI ${Math.round(tri)} m): odometry and long-distance tests.`);
  if (body === "Moon" && Math.abs(lat) > 70) out.push("Polar latitude: relevant to Artemis candidate regions.");
  return out;
}

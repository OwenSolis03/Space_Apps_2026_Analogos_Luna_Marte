import type { Body, Dimension } from "./types";

export const BODY_LABEL: Record<Body, { name: string; adj: string }> = {
  Mars: { name: "Mars", adj: "Martian" },
  Moon: { name: "the Moon", adj: "lunar" },
};

export const DIM_LABEL: Record<Dimension, { label: string; hint: string; pending: string }> = {
  topography: { label: "Slope", hint: "mean slope and P90", pending: "" },
  roughness: { label: "Roughness", hint: "elevation σ and TRI", pending: "" },
  environment: { label: "Environment", hint: "aridity, dust", pending: "arrives with T5/T6" },
  thermal: { label: "Thermal", hint: "daily amplitude", pending: "arrives with T7" },
};

export const FEATURE_LABEL: Record<string, { label: string; unit: string; dim: Dimension | null }> = {
  mean_slope_deg: { label: "Mean slope", unit: "°", dim: "topography" },
  p90_slope_deg: { label: "P90 slope", unit: "°", dim: "topography" },
  detrended_std_m: { label: "Elevation σ", unit: "m", dim: "roughness" },
  tri_m: { label: "TRI", unit: "m", dim: "roughness" },
  relief_m: { label: "Relief", unit: "m", dim: "topography" },
  hypsometric_integral: { label: "Hypsometric integral", unit: "", dim: "topography" },
  mean_elev_m: { label: "Mean elevation", unit: "m", dim: null },
};

export const LIMIT_LABEL: Record<string, string> = {
  gravity: "Gravity",
  atmosphere: "Atmosphere",
  pressure: "Pressure",
  radiation: "Radiation",
  thermal_cycle: "Thermal cycle",
  polar_lighting: "Polar lighting",
  elevation_datum: "Elevation",
};

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

/** Uso de campo sugerido a partir de los rasgos del blanco (regla simple, provisional hasta T11). */
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

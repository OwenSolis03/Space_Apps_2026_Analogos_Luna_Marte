// Fixed numbers from the project documents. Used by Home, How It Works and the Data page.
// Sources: docs/handoff.md §1 and §3; docs/logbook.md (prefilter_stats.json table).
// Computed figures that come from the universe JSON live in lib/stats.ts, not here.

export const EARTH_PATCHES = 40244; // valid 32 km patches on Earth (90.69 % of candidates)
export const MARS_PATCHES = 140916; // Mars patches, 99.61 % valid
export const MOON_PATCHES = 36741; // Moon patches, 99.26 % valid
export const TARGETS = 76; // mission target sites (Moon and Mars)
export const CURATED_TARGETS = 16;
export const PAIRS = 4944; // target-analog pairs scored
export const RUN_ID = "2242506";
export const PATCH_KM = 32;
export const PATCH_RES_M = 500;
export const PATCH_PX = 64;
export const COPERNICUS_TILES = 26475;
export const RAW_VOLUME = "≈ 80 GB";

// Earth prefilter funnel (docs/logbook.md, prefilter_stats.json)
export const GRID = 497818;
export const WITH_TILE = 179663;
export const VEGETATED = 113935;
export const NO_LAND_DATA = 21353;
export const KEPT = 44375;
export const VALID = 40244;

export const fmt = (n: number) => n.toLocaleString("en-US");

/** Readout items for the Home page. */
export const HOME_FACTS = [
  { label: "EARTH PATCHES", value: fmt(EARTH_PATCHES) },
  { label: "MARS PATCHES", value: fmt(MARS_PATCHES) },
  { label: "MOON PATCHES", value: fmt(MOON_PATCHES) },
  { label: "TARGETS", value: String(TARGETS) },
  { label: "PAIRS SCORED", value: fmt(PAIRS) },
  { label: "RUN", value: RUN_ID },
];

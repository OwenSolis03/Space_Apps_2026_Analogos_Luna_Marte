// Exploratory data analysis for the Data page. Sources: docs/pipeline.md (file table, recorded runs),
// docs/HISTORY.md §2 and §6, docs/logbook.md (T5 entry), docs/plan_t16_missing_data.md §0 and §1.

export interface EdaFinding {
  code: string;
  title: string;
  text: string;
  consequence: string;
}

export const EDA_FINDINGS: EdaFinding[] = [
  {
    code: "EDA.01",
    title: "LOLA STORES HALF-METRES",
    text: "The lunar DEM has scale = 0.5, so every lunar vertical metric was doubled. After the fix the median lunar slope went from 13.24° to 6.93°.",
    consequence: "Every value is read as raw · scale + offset before any feature is computed.",
  },
  {
    code: "EDA.02",
    title: "MODIS USES OPPOSITE CONVENTIONS",
    text: "NDVI is raw ÷ 10000, while LST is raw × 0.02 − 273.15.",
    consequence: "Each MODIS product gets its own conversion; one rule does not fit both.",
  },
  {
    code: "EDA.03",
    title: "COPERNICUS HAS NO NODATA VALUE",
    text: "GLO-90 has no nodata value, and the sea is exactly 0.0. The mosaic treats 0 as nodata.",
    consequence: "The VRT treats 0 as nodata, so the sea is excluded from the mosaic.",
  },
  {
    code: "EDA.04",
    title: "THE \"ALBEDO\" FILE WAS RELIEF",
    text: "The file named lunar albedo was a colour-shaded relief. It was discarded and replaced by LROC WAC.",
    consequence: "LROC WAC is the lunar brightness layer.",
  },
  {
    code: "EDA.05",
    title: "THEMIS AND WAC ARE NOT ABSOLUTE",
    text: "THEMIS mosaics are grey levels, not kelvin, and LROC WAC is relative brightness.",
    consequence: "Both are compared as percentile ranks within each planet.",
  },
  {
    code: "EDA.06",
    title: "MISSING DATA AT THE POLES",
    text: "MODIS NDVI has no data south of 59.45°S, and Deep Blue AOD has no retrievals over snow and ice.",
    consequence: "The missing-data policy (STEP.08) decides how each missing value scores.",
  },
  {
    code: "EDA.07",
    title: "ONE PATCH SIZE FOR ALL BODIES",
    text: "Version 1 compared windows of different size per body: about 118 km on Mars, about 30 km on the Moon and about 46 km on Earth.",
    consequence: "One 32 km patch at 500 m per pixel is used for all three bodies.",
  },
  {
    code: "EDA.08",
    title: "EARTH IS FLAT AT THIS SCALE",
    text: "The median mean slope of bare-ground Earth patches is 0.46°, against a 6.93° median on the Moon.",
    consequence: "Earth's bare ground is nearly flat at this scale. The Moon is not.",
  },
];

/** Columns of the file table: type, scale, offset, nodata and a note, as checked on Yuca (docs/pipeline.md). */
export interface FileRow {
  file: string;
  dtype: string;
  scale: string;
  offset: string;
  nodata: string;
  note: string;
}

export const FILE_TABLE: FileRow[] = [
  { file: "Mars_MGS_MOLA_DEM_mosaic_global_463m.tif", dtype: "int16", scale: "1.0", offset: "0.0", nodata: "−32768", note: "Metres" },
  { file: "Mars_ODY_THEMIS_IR_Day_Mosaic_100m.tif", dtype: "uint8", scale: "1.0", offset: "0.0", nodata: "0", note: "Grey level, not kelvin" },
  { file: "Mars_MO_THEMIS-IR-Night_mosaic_60N60S_100m_v14.tif", dtype: "uint8", scale: "1.0", offset: "0.0", nodata: "0", note: "Grey level, not kelvin" },
  { file: "Lunar_LRO_LOLA_Global_LDEM_118m.tif", dtype: "int16", scale: "0.5", offset: "0.0", nodata: "−32768", note: "Half-metres. v1 did not apply the scale, so every lunar vertical metric came out doubled" },
  { file: "Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif", dtype: "uint8", scale: "1.00395", offset: "−0.00395", nodata: "0", note: "Relative brightness (≈ 1–256), not absolute reflectance; compared by percentile within the Moon" },
  { file: "Moon_IceFavorabilityIndex_{90N,90S}000E_591mp.tif", dtype: "float32", scale: "1.0", offset: "0.0", nodata: "−3.4e38", note: "Filter the huge nodata value" },
  { file: "Lunar_LRO_LOLA_Albedo_Global_128ppd.tif", dtype: "uint8 × 3", scale: "1.0", offset: "0.0", nodata: "0", note: "Obsolete (colour-shaded RGB); not used" },
  { file: "MOD13C2.A2023*.hdf (CMG 0.05 Deg Monthly NDVI)", dtype: "int16", scale: "÷ 10000", offset: "0.0", nodata: "−3000", note: "Opposite MODIS VI convention: divide by 10000, do not multiply. Values below −0.3 become NaN. No data south of 59.45°S" },
  { file: "MOD11C3.A2023*.hdf (LST_Day_CMG, LST_Night_CMG)", dtype: "uint16", scale: "× 0.02", offset: "−273.15 (to °C)", nodata: "0", note: "Here it is multiplied: °C = raw × 0.02 − 273.15. Covers Antarctica" },
  { file: "MOD08_M3.A2019..2023*.hdf (Deep Blue AOD 550 land mean)", dtype: "int16", scale: "× 0.001", offset: "0.0", nodata: "−9999", note: "(raw − add_offset) × scale_factor. No retrievals over snow and ice (NaN)" },
  { file: "dustscenario_MY{24..36}_v2-*.nc (cdod610)", dtype: "float32", scale: "1.0", offset: "0.0", nodata: "—", note: "NetCDF3 classic read with xarray (engine scipy). cdod610 is IR absorption CDOD normalised to 610 Pa" },
  { file: "glim_wgs84_0point5deg.txt.asc", dtype: "int (1..16)", scale: "—", offset: "—", nodata: "−9999", note: "ESRI ASCII, 720 × 360 (0.5°). Coastline cells mapped from wb via a valid 3×3 neighbourhood" },
  { file: "Copernicus GLO-90 tiles", dtype: "float32", scale: "1.0", offset: "0.0", nodata: "none", note: "Sea inside coastal tiles is exactly 0.0. Tile width shrinks with latitude. The VRT treats 0 as nodata" },
];

/** Figures from the control maps. They live on Yuca; drop the PNG into public/figures/ and set `src`. */
export interface FigureSlot {
  code: string;
  file: string;
  run: string;
  caption: string;
  alt: string;
  src?: string;
}

export const FIGURES: FigureSlot[] = [
  { code: "FIG.001", file: "map_earth_mean_slope_deg.png", run: "2242438", caption: "FIG.001 Earth mean slope, bare-ground patches", alt: "Map of mean slope over Earth's bare ground" },
  { code: "FIG.002", file: "map_earth_classification.png", run: "2242438", caption: "FIG.002 Earth classification: missing NDVI, known analog, new candidate", alt: "Map of Earth's classification of candidate sites" },
  { code: "FIG.003", file: "map_targets_mars.png", run: "2242423", caption: "FIG.003 Mars targets", alt: "Map of the Mars targets" },
  { code: "FIG.004", file: "map_targets_moon.png", run: "2242423", caption: "FIG.004 Moon targets", alt: "Map of the Moon targets" },
  { code: "FIG.005", file: "map_dust_level_*.png", run: "2242484", caption: "FIG.005 Mars dust level", alt: "Map of Mars dust level" },
];

/** Stage counts of the Earth prefilter (docs/logbook.md, prefilter_stats.json). */
export const PREFILTER_COUNTS: { stage: string; count: number; note: string }[] = [
  { stage: "grid", count: 497818, note: "All Earth grid points" },
  { stage: "no_tile", count: 318155, note: "Without a land tile (with_tile = 179,663)" },
  { stage: "vegetated", count: 113935, note: "Annual maximum NDVI above 0.25" },
  { stage: "no_land_data", count: 21353, note: "South of −60: 1,878 · −60 to 60: 17,573 · north of 60: 1,902" },
  { stage: "ndvi_missing", count: 14130, note: "South of −60: 13,081 · −60 to 60: 837 · north of 60: 212" },
  { stage: "kept", count: 44375, note: "NEW_CANDIDATE 43,596 · KNOWN_ANALOG 779" },
];

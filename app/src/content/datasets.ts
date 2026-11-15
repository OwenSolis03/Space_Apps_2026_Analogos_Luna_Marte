// Data page sources. Rows come from the README "Data" table and from docs/pipeline.md (§Data).
// `feeds` names the similarity dimension each source feeds, or the role it plays when no dimension applies.

export interface DatasetRow {
  body: "MARS" | "MOON" | "EARTH" | "MOON · MARS";
  dataset: string;
  use: string;
  source: string;
  url?: string;
  feeds: string[];
}

export const DATASETS: DatasetRow[] = [
  { body: "MARS", dataset: "MGS MOLA DEM, 463 m", use: "Terrain features", source: "USGS Astrogeology (from NASA PDS)", url: "https://astrogeology.usgs.gov/search", feeds: ["TOPOGRAPHY", "ROUGHNESS"] },
  { body: "MARS", dataset: "Mars Odyssey THEMIS IR day and night, 100 m", use: "Relative thermal contrast", source: "USGS Astrogeology", feeds: ["THERMAL"] },
  { body: "MARS", dataset: "MGS TES surface mineralogy, 3 km (Bandfield 2002)", use: "Primary rock-forming silicates (olivine, plagioclase, pyroxenes) orbital context", source: "NASA PDS / ASU (Bandfield 2002)", url: "https://tes.asu.edu/", feeds: ["MINERALOGY", "CONTEXT"] },
  { body: "MARS", dataset: "SIM 3292 global geology, 1:20M (Tanaka et al. 2014)", use: "Regional geology and units", source: "USGS SIM 3292", feeds: ["GEOLOGY"] },
  { body: "MARS", dataset: "Montabone CDOD v2 dust scenarios, MY24–36 (kriged, 2015/2020)", use: "Dust level and seasons", source: "Montabone et al. 2015/2020", feeds: ["DUST"] },
  { body: "MOON", dataset: "LRO LOLA LDEM, 118 m", use: "Terrain features", source: "USGS Astrogeology", feeds: ["TOPOGRAPHY", "ROUGHNESS"] },
  { body: "MOON", dataset: "LRO LROC WAC mosaic, 100 m", use: "Relative brightness (percentile within the Moon)", source: "USGS Astrogeology", feeds: ["CONTEXT"] },
  { body: "MOON", dataset: "LRO Diviner Polar Resource Product (south)", use: "Mean and max temperature, ice stability depth", source: "NASA PDS Geosciences", url: "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/", feeds: ["THERMAL", "ICE"] },
  { body: "MOON", dataset: "JAXA SELENE / Kaguya Multiband Imager (MI) mineral map, 500 m", use: "FeO wt%, plagioclase, olivine, pyroxenes & maturity index (OMAT) context", source: "JAXA / DARTS (SELENE Data Archive)", url: "https://www.darts.isas.jaxa.jp/planet/pdap/selene/", feeds: ["MINERALOGY", "CONTEXT"] },
  { body: "MOON", dataset: "Lunar ice favorability index", use: "Polar ice context", source: "USGS Astrogeology", feeds: ["ICE"] },
  { body: "MOON", dataset: "Unified Geologic Map of the Moon v2, 1:5M (Fortezzo et al. 2020)", use: "Regional geology and units", source: "USGS", feeds: ["GEOLOGY"] },
  { body: "EARTH", dataset: "Copernicus DEM GLO-90 (26,475 tiles)", use: "Terrain features", source: "ESA Copernicus, AWS open data", url: "https://registry.opendata.aws/copernicus-dem/", feeds: ["TOPOGRAPHY", "ROUGHNESS"] },
  { body: "EARTH", dataset: "MODIS MOD13C2 (NDVI) and MOD11C3 (land surface temperature), 2023", use: "Vegetation mask, thermal amplitude", source: "NASA Earthdata", url: "https://doi.org/10.5067/MODIS/MOD13C2.061", feeds: ["ENVIRONMENT", "THERMAL"] },
  { body: "EARTH", dataset: "MODIS MOD08_M3 Deep Blue aerosol optical depth, 2019–2023", use: "Aerosol proxy for the dust comparison", source: "NASA Earthdata (LAADS)", feeds: ["DUST"] },
  { body: "EARTH", dataset: "NASA EMIT L3 Aggregated Mineral Abundance, 60 m / 0.5° (EMITL3ASA)", use: "Secondary alteration minerals in arid swaths (clays, carbonates, sulfates, hematite)", source: "NASA LP DAAC / JPL", url: "https://lpdaac.usgs.gov/products/emitl3asa_mineralv001/", feeds: ["MINERALOGY", "CONTEXT"] },
  { body: "EARTH", dataset: "GLiM 0.5° global lithology (Hartmann & Moosdorf 2012)", use: "Rock type of each Earth patch", source: "PANGAEA", feeds: ["GEOLOGY"] },
  { body: "EARTH", dataset: "Natural Earth roads, airports, countries", use: "Logistics and country", source: "Natural Earth", url: "https://www.naturalearthdata.com/", feeds: ["LOGISTICS"] },
  { body: "MOON · MARS", dataset: "Gazetteer of Planetary Nomenclature", use: "Target anchors and names", source: "USGS / IAU", url: "https://planetarynames.wr.usgs.gov/", feeds: ["NAMES"] },
];

/** The official challenge resources table (docs/implementation_plan.md §2), copied as written. */
export const OFFICIAL_RESOURCES: { resource: string; used: string; product: string }[] = [
  { resource: "NASA Planetary Data System (PDS)", used: "Yes", product: "MOLA DEM 463 m, THEMIS IR Day/Night 100 m, LOLA LDEM 118 m, LROC WAC 100 m, MGS TES mineralogy (Bandfield 2002)" },
  { resource: "NASA Lunar Reconnaissance Orbiter (LRO)", used: "Yes", product: "LOLA (topography), LROC WAC (brightness)" },
  { resource: "NASA LRO Diviner Lunar Data", used: "Yes", product: "Diviner Polar Resource Product (PDS LRO-L-DLRE-5-PRP-V2.0, file DLRE_PRP_SOUTH.TAB): annual mean and maximum temperature, and ice stability depth, 80–90°S" },
  { resource: "NASA Earthdata Search", used: "Yes", product: "MODIS MOD13C2 (monthly NDVI), MOD11C3 (day/night land surface temperature), 0.05°, and NASA EMIT L3 mineral maps" },
  { resource: "NASA Worldview", used: "In the app", product: "NASA GIBS base layers (the technology behind Worldview) for the Earth map" },
  { resource: "Copernicus Data Space Ecosystem (ESA)", used: "Yes", product: "Copernicus DEM GLO-90" },
  { resource: "ESA Open Science Catalog", used: "No", product: "Optional: adds nothing we do not already have" },
  { resource: "CSA RADARSAT / SAR tutorial", used: "No (out of scope)", product: "Mention as future work: centimetre-scale roughness from radar" },
  { resource: "JAXA G-Portal / DARTS", used: "Yes", product: "JAXA SELENE / Kaguya Multiband Imager (MI) global FeO, plagioclase, olivine, and pyroxene mineral maps (500 m)" },
];

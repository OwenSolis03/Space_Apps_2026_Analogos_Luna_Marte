// Schema of analogs_universe.json as exported by pipeline/export.py (T8/T15).
export type Body = "Moon" | "Mars";
export type Dimension = "topography" | "roughness" | "environment" | "thermal" | "geology" | "dust" | "ice";
export const DIMENSIONS: Dimension[] = ["topography", "roughness", "environment", "thermal", "geology", "dust", "ice"];

export type Weights = Record<Dimension, number>;

export const ZERO_WEIGHTS: Weights = { topography: 0, roughness: 0, environment: 0, thermal: 0, geology: 0, dust: 0, ice: 0 };

/** Fills missing dimensions with 0 so older presets or partial weights never break the sliders. */
export const fullWeights = (w: Partial<Weights>): Weights => ({ ...ZERO_WEIGHTS, ...w });

export interface Preset {
  label: string;
  weights: Partial<Weights>;
  applies_to?: Body[];
}

export interface Limit {
  factor: string;
  earth: string;
  target: string;
  consequence: string;
  source: string;
}

export interface Mismatch {
  feature: string;
  earth: number | string;
  target: number | string;
  z_diff: number | null;
}

export interface Logistics {
  dist_road_km: number | null;
  dist_airport_km: number | null;
  nearest_airport_iata?: string | null;
  nearest_airport_name?: string | null;
}

export interface Analog {
  id: string;
  lat: number;
  lon: number;
  country: string | null;
  classification: "NEW_CANDIDATE" | "KNOWN_ANALOG";
  known_region: string | null;
  sub_scores: Partial<Record<Dimension, number | null>>;
  msi_by_preset: Record<string, number | null>;
  selected_by?: string[];
  features: Record<string, number>;
  earth_env: { ndvi_max?: number | null; lst_day_c?: number | null; lst_night_c?: number | null; lst_amplitude_c?: number | null } | null;
  logistics: Logistics | null;
  geology?: { glim_code?: string; geo_class?: string; lava_tube_terrain?: boolean; ice_surface?: boolean } | null;
  dust?: { level_rank?: number; seasonality_rank?: number; peak_phase_deg?: number } | null;
  ice?: { cold_rank?: number; ice_E?: number } | null;
  polar_cold?: boolean;
  subsurface_note?: string | null;
  mismatches: Mismatch[];
  earth_missing_dims?: Dimension[];
}

export interface Target {
  id: string;
  type: "CURATED" | "CLUSTER";
  body: Body;
  name: string;
  lat: number;
  lon: number;
  category: string | null;
  why: string | null;
  source_url: string | null;
  coord_source_url?: string | null;
  anchor_note?: string | null;
  iau_label: string | null;
  features: Record<string, number>;
  aux: Record<string, number | null>;
  available_dims?: Dimension[];
  preset_status?: Record<
    string,
    {
      status: "ok" | "not_applicable_body" | "insufficient_target_data";
      coverage: number;
      missing_dims: Dimension[];
    }
  >;
  geology?: { unit?: string; geo_class?: string; geo_class_share?: number } | null;
  dust?: { level_rank?: number; seasonality_rank?: number; peak_phase_deg?: number } | null;
  ice?: { cold_rank?: number; ice_T?: number; ice_source?: string } | null;
  analogs: Analog[];
}

export interface DimensionInfo {
  key: Dimension;
  label: string;
  description: string;
  bodies: Body[];
  source: string;
}

export interface Universe {
  metadata: {
    version: string;
    generated_at: string;
    source?: string;
    slurm_job_id?: string;
    earth_patches_evaluated: number | null;
    patch?: { size_km: number; res_m: number; projection: string };
    dimensions?: DimensionInfo[];
    not_modelled?: { item: string; note: string }[];
    citations?: string[];
    datasets?: { name: string; source: string; url: string | null }[];
    scoring_policy?: {
      earth_missing_score: number;
      min_preset_coverage: number;
      rules: string[];
    };
    preset_status_summary?: Record<string, Record<string, Record<string, number>>>;
  };
  mission_presets: Record<string, Preset>;
  limits: Record<Body, Limit[]>;
  targets: Target[];
}

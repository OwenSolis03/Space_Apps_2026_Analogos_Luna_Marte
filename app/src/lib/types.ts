// Esquema v2 de analogs_universe.json (docs/plan_implementacion.md, seccion 5).
export type Body = "Moon" | "Mars";
export type Dimension = "topography" | "roughness" | "environment" | "thermal";
export const DIMENSIONS: Dimension[] = ["topography", "roughness", "environment", "thermal"];

export type Weights = Record<Dimension, number>;

export interface Preset {
  label: string;
  weights: Weights;
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
  earth: number;
  target: number;
  z_diff: number;
}

export interface Analog {
  id: string;
  lat: number;
  lon: number;
  country: string | null;
  classification: "NEW_CANDIDATE" | "KNOWN_ANALOG";
  known_region: string | null;
  v1_similarity?: number;
  sub_scores: Record<Dimension, number | null>;
  msi_by_preset: Record<string, number>;
  features: Record<string, number>;
  earth_env: Record<string, number> | null;
  logistics: { dist_road_km: number; dist_airport_km: number } | null;
  mismatches: Mismatch[];
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
  iau_label: string | null;
  features: Record<string, number>;
  aux: Record<string, number | null>;
  analogs: Analog[];
}

export interface Universe {
  metadata: {
    version: string;
    generated_at: string;
    source?: string;
    earth_patches_evaluated: number | null;
    datasets: { name: string; source: string; url: string }[];
  };
  mission_presets: Record<string, Preset>;
  limits: Record<Body, Limit[]>;
  targets: Target[];
}

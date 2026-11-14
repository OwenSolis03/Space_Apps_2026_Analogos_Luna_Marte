import type { Analog, Body, Dimension, Target, Weights } from "./types";
import { DIMENSIONS } from "./types";

export const DIMENSION_BODIES: Record<Dimension, Body[]> = {
  topography: ["Moon", "Mars"],
  roughness: ["Moon", "Mars"],
  environment: ["Moon", "Mars"],
  thermal: ["Mars"],
  geology: ["Moon", "Mars"],
  dust: ["Mars"],
  ice: ["Moon", "Mars"],
};

/**
 * MSI = sum(w * S) / sum(w) over the applicable non-missing dimensions (0-1).
 * When targetDims is provided, Case C applies: dimensions in targetDims with
 * null Earth sub-score receive earthMissing (default 0).
 */
export function msi(
  a: Analog,
  w: Weights,
  targetDims?: Set<Dimension> | Dimension[],
  earthMissing = 0,
): number {
  const tSet = targetDims ? (targetDims instanceof Set ? targetDims : new Set(targetDims)) : undefined;
  let num = 0;
  let den = 0;
  for (const d of DIMENSIONS) {
    if (w[d] <= 0) continue;
    if (tSet !== undefined && !tSet.has(d)) continue;
    const s = a.sub_scores[d];
    if (tSet === undefined) {
      if (s == null) continue;
      num += w[d] * s;
      den += w[d];
    } else {
      const val = s != null ? s : earthMissing;
      num += w[d] * val;
      den += w[d];
    }
  }
  return den > 0 ? num / den : 0;
}

/** Logistics-adjusted MSI: MSI * (1 - λ + λ * exp(-road_km / 100)), λ in [0, 0.3]. */
export function msiLog(
  a: Analog,
  w: Weights,
  lambda: number,
  targetDims?: Set<Dimension> | Dimension[],
  earthMissing = 0,
): number {
  const base = msi(a, w, targetDims, earthMissing);
  const road = a.logistics?.dist_road_km;
  if (lambda <= 0 || road == null) return base;
  return base * (1 - lambda + lambda * Math.exp(-road / 100));
}

export interface RankedTarget {
  target: Target;
  analogs: { analog: Analog; score: number }[]; // highest first
  best: number;
}

export interface UnrankedTarget {
  target: Target;
  missingDims: Dimension[];
}

export interface RankingResult {
  ranked: RankedTarget[];
  unranked: UnrankedTarget[];
}

export function rankTargets(
  targets: Target[],
  w: Weights,
  minScore = 0,
  lambda = 0,
  newOnly = false,
  earthMissing = 0,
  minPresetCoverage = 0.6,
): RankingResult {
  const ranked: RankedTarget[] = [];
  const unranked: UnrankedTarget[] = [];

  for (const target of targets) {
    const tdims = target.available_dims ? new Set(target.available_dims) : undefined;

    if (tdims !== undefined) {
      let applicableW = 0;
      let availableW = 0;
      const missingDims: Dimension[] = [];
      for (const d of DIMENSIONS) {
        if (w[d] > 0 && DIMENSION_BODIES[d].includes(target.body)) {
          applicableW += w[d];
          if (tdims.has(d)) {
            availableW += w[d];
          } else {
            missingDims.push(d);
          }
        }
      }
      const coverage = applicableW > 0 ? availableW / applicableW : 1.0;
      if (coverage < minPresetCoverage) {
        unranked.push({ target, missingDims });
        continue;
      }
    }

    const analogs = target.analogs
      .filter((analog) => !newOnly || analog.classification === "NEW_CANDIDATE")
      .map((analog) => ({
        analog,
        score: msiLog(analog, w, lambda, tdims, earthMissing),
      }))
      .sort((x, y) => y.score - x.score);

    if (analogs.length > 0 && (analogs[0]?.score ?? 0) >= minScore) {
      ranked.push({ target, analogs, best: analogs[0]?.score ?? 0 });
    }
  }

  ranked.sort((x, y) => y.best - x.best);
  return { ranked, unranked };
}

/** Dimensions with data for at least one analog of these targets; the rest are shown disabled. */
export function availableDimensions(targets: Target[]): Set<Dimension> {
  const has = new Set<Dimension>();
  for (const t of targets) for (const a of t.analogs) for (const d of DIMENSIONS) if (a.sub_scores[d] != null) has.add(d);
  return has;
}

export const fmtLat = (v: number) => `${Math.abs(v).toFixed(2)}° ${v >= 0 ? "N" : "S"}`;
export const fmtLon = (v: number) => `${Math.abs(v).toFixed(2)}° ${v >= 0 ? "E" : "W"}`;
export const fmtNum = (v: number) =>
  Math.abs(v) >= 100 ? Math.round(v).toLocaleString("en-US") : v.toFixed(2);
export const pct = (v: number) => (v * 100).toFixed(1);

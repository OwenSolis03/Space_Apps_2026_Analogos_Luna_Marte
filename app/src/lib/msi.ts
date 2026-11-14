import type { Analog, Dimension, Target, Weights } from "./types";
import { DIMENSIONS } from "./types";

/**
 * MSI = sum(w * S) / sum(w) over the dimensions that have a sub-score (0-1).
 * Same formula as pipeline/match.py: it reproduces msi_by_preset to within 0.001.
 */
export function msi(a: Analog, w: Weights): number {
  let num = 0;
  let den = 0;
  for (const d of DIMENSIONS) {
    const s = a.sub_scores[d];
    if (s == null || w[d] <= 0) continue;
    num += w[d] * s;
    den += w[d];
  }
  return den > 0 ? num / den : 0;
}

/** Logistics-adjusted MSI: MSI * (1 - λ + λ * exp(-road_km / 100)), λ in [0, 0.3] (implementation plan, T7). */
export function msiLog(a: Analog, w: Weights, lambda: number): number {
  const base = msi(a, w);
  const road = a.logistics?.dist_road_km;
  if (lambda <= 0 || road == null) return base;
  return base * (1 - lambda + lambda * Math.exp(-road / 100));
}

export interface RankedTarget {
  target: Target;
  analogs: { analog: Analog; score: number }[]; // highest first
  best: number;
}

export function rankTargets(targets: Target[], w: Weights, minScore = 0, lambda = 0, newOnly = false): RankedTarget[] {
  return targets
    .map((target) => {
      const analogs = target.analogs
        .filter((analog) => !newOnly || analog.classification === "NEW_CANDIDATE")
        .map((analog) => ({ analog, score: msiLog(analog, w, lambda) }))
        .sort((x, y) => y.score - x.score);
      return { target, analogs, best: analogs[0]?.score ?? 0 };
    })
    .filter((r) => r.analogs.length > 0 && r.best >= minScore)
    .sort((x, y) => y.best - x.best);
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

import type { Analog, Target, Weights } from "./types";
import { DIMENSIONS } from "./types";

/** MSI = sum(w * S) / sum(w), solo con las dimensiones que tienen sub_score. Rango 0-1. */
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

export interface RankedTarget {
  target: Target;
  analogs: { analog: Analog; score: number }[]; // ordenados de mayor a menor
  best: number;
}

export function rankTargets(targets: Target[], w: Weights, minScore = 0): RankedTarget[] {
  return targets
    .map((target) => {
      const analogs = target.analogs
        .map((analog) => ({ analog, score: msi(analog, w) }))
        .sort((x, y) => y.score - x.score);
      return { target, analogs, best: analogs[0]?.score ?? 0 };
    })
    .filter((r) => r.best >= minScore)
    .sort((x, y) => y.best - x.best);
}

/** Dimensiones con datos en al menos un analogo: las demas se muestran deshabilitadas. */
export function availableDimensions(targets: Target[]) {
  const has = new Set<string>();
  for (const t of targets) for (const a of t.analogs) for (const d of DIMENSIONS) if (a.sub_scores[d] != null) has.add(d);
  return has;
}

export const fmtLat = (v: number) => `${Math.abs(v).toFixed(2)}° ${v >= 0 ? "N" : "S"}`;
export const fmtLon = (v: number) => `${Math.abs(v).toFixed(2)}° ${v >= 0 ? "E" : "W"}`;
export const fmtNum = (v: number) =>
  Math.abs(v) >= 100 ? Math.round(v).toLocaleString("en-US") : v.toFixed(2);
export const pct = (v: number) => (v * 100).toFixed(1);

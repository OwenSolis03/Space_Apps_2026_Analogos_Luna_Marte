// Pure functions over the exported universe, for the Results overview, How It Works and Data pages.
// Every number shown on the site is computed here from analogs_universe.json, or comes from content/facts.ts.
import type { Analog, Body, Target, Universe } from "./types";

export interface Summary {
  earthPatches: number;
  targets: number;
  curated: number;
  pairs: number;
  uniqueSites: number;
  newSites: number;
  knownSites: number;
  runId: string;
  generatedAt: string;
}

/** Headline counts for the Results hero. Unique sites are counted by analog id across all targets. */
export function summary(u: Universe): Summary {
  const all = new Set<string>();
  const fresh = new Set<string>();
  const known = new Set<string>();
  let pairs = 0;
  for (const t of u.targets) {
    for (const a of t.analogs) {
      pairs += 1;
      all.add(a.id);
      (a.classification === "NEW_CANDIDATE" ? fresh : known).add(a.id);
    }
  }
  return {
    earthPatches: u.metadata.earth_patches_evaluated ?? 0,
    targets: u.targets.length,
    curated: u.targets.filter((t) => t.type === "CURATED").length,
    pairs,
    uniqueSites: all.size,
    newSites: fresh.size,
    knownSites: known.size,
    runId: u.metadata.slurm_job_id ?? "n/a",
    generatedAt: u.metadata.generated_at,
  };
}

export interface BestPick {
  target: Target;
  /** Null when the preset does not apply to this body or no analog has a score for it. */
  analog: Analog | null;
  msi: number | null;
}

/** Best analog of each curated mission site for one preset, using the exported msi_by_preset values. */
export function bestPerTarget(u: Universe, presetKey: string): BestPick[] {
  return u.targets
    .filter((t) => t.type === "CURATED")
    .map((target) => {
      let analog: Analog | null = null;
      let best = -Infinity;
      for (const a of target.analogs) {
        const v = a.msi_by_preset[presetKey];
        if (v != null && v > best) {
          best = v;
          analog = a;
        }
      }
      return { target, analog, msi: analog ? best : null };
    });
}

/** Unique analog sites per country, largest first. */
export function sitesByCountry(u: Universe, n: number): { country: string; count: number }[] {
  const seen = new Set<string>();
  const counts = new Map<string, number>();
  for (const t of u.targets) {
    for (const a of t.analogs) {
      if (seen.has(a.id)) continue;
      seen.add(a.id);
      const country = a.country ?? "Unknown";
      counts.set(country, (counts.get(country) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .map(([country, count]) => ({ country, count }))
    .sort((x, y) => y.count - x.count)
    .slice(0, n);
}

/** Best MSI per curated target, split by body. Missing values are dropped. */
export function bestMsiByBody(u: Universe, presetKey: string): Record<Body, { name: string; msi: number }[]> {
  const out: Record<Body, { name: string; msi: number }[]> = { Moon: [], Mars: [] };
  for (const pick of bestPerTarget(u, presetKey)) {
    if (pick.msi != null) out[pick.target.body].push({ name: pick.target.name, msi: pick.msi });
  }
  return out;
}

/** Count of target geology classes per body (targets with a geology record only). */
export function geoClassCounts(u: Universe): Record<Body, Record<string, number>> {
  const out: Record<Body, Record<string, number>> = { Moon: {}, Mars: {} };
  for (const t of u.targets) {
    const cls = t.geology?.geo_class;
    if (!cls) continue;
    out[t.body][cls] = (out[t.body][cls] ?? 0) + 1;
  }
  return out;
}

export function median(values: number[]): number {
  if (values.length === 0) return NaN;
  const s = [...values].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid]! : (s[mid - 1]! + s[mid]!) / 2;
}

// State of the Results explorer: mission body, preset, weights, filters and the selected target and analog.
// Port of the React App state (docs/plan_t18_website.md §5.2). Ranking itself comes unchanged from lib/msi.ts.
import { computed, ref, watch, type ComputedRef } from "vue";
import type { Body, Dimension, DimensionInfo, Universe, Weights } from "@/lib/types";
import { ZERO_WEIGHTS, fullWeights } from "@/lib/types";
import {
  availableDimensions,
  fmtLat,
  fmtLon,
  pct,
  rankTargets,
  type RankedTarget,
  type UnrankedTarget,
} from "@/lib/msi";
import type { Target } from "@/lib/types";

/** A point on a map: a target (Moon or Mars) or an Earth analog. */
export interface MapPoint {
  id: string;
  lat: number;
  lon: number;
  label: string;
  selected: boolean;
  /** 0 to 1; drives the marker radius. */
  weight: number;
}

export function useExplorer(universe: ComputedRef<Universe | null>) {
  const body = ref<Body>("Mars");
  const presetId = ref<string | null>(null);
  const weights = ref<Weights>({ ...ZERO_WEIGHTS, topography: 0.5, roughness: 0.5 });
  const minScore = ref(0);
  const lambda = ref(0);
  const newOnly = ref(false);
  const targetId = ref<string | null>(null);
  const analogIndex = ref(0);

  // Start from the first mission preset as soon as the data arrives.
  let initialised = false;
  watch(
    universe,
    (data) => {
      if (!data || initialised) return;
      initialised = true;
      const first = Object.keys(data.mission_presets)[0];
      if (first) {
        presetId.value = first;
        weights.value = fullWeights(data.mission_presets[first]!.weights);
      }
    },
    { immediate: true },
  );

  const bodyTargets = computed<Target[]>(
    () => universe.value?.targets.filter((t) => t.body === body.value) ?? [],
  );
  const available = computed(() => availableDimensions(bodyTargets.value));
  const dimInfo = computed(() => {
    const out: Partial<Record<Dimension, DimensionInfo>> = {};
    for (const d of universe.value?.metadata.dimensions ?? []) out[d.key] = d;
    return out;
  });
  const earthMissing = computed(() => universe.value?.metadata.scoring_policy?.earth_missing_score ?? 0);
  const minCoverage = computed(() => universe.value?.metadata.scoring_policy?.min_preset_coverage ?? 0.6);

  const ranking = computed(() =>
    rankTargets(
      bodyTargets.value,
      weights.value,
      minScore.value,
      lambda.value,
      newOnly.value,
      earthMissing.value,
      minCoverage.value,
    ),
  );
  const ranked = computed(() => ranking.value.ranked);
  const unranked = computed<UnrankedTarget[]>(() => ranking.value.unranked);

  const selected = computed<RankedTarget | null>(
    () => ranked.value.find((r) => r.target.id === targetId.value) ?? ranked.value[0] ?? null,
  );
  const safeAnalog = computed(() =>
    selected.value && analogIndex.value < selected.value.analogs.length ? analogIndex.value : 0,
  );

  const targetPoints = computed<MapPoint[]>(() =>
    ranked.value.map((r) => ({
      id: r.target.id,
      lat: r.target.lat,
      lon: r.target.lon,
      label: `${r.target.name} · MSI ${pct(r.best)}`,
      selected: r.target.id === selected.value?.target.id,
      weight: r.best,
    })),
  );
  const earthPoints = computed<MapPoint[]>(() =>
    (selected.value?.analogs ?? []).map((x, i) => ({
      id: String(i),
      lat: x.analog.lat,
      lon: x.analog.lon,
      label: `#${i + 1} · ${fmtLat(x.analog.lat)}, ${fmtLon(x.analog.lon)} · MSI ${pct(x.score)}`,
      selected: i === safeAnalog.value,
      weight: x.score,
    })),
  );

  function selectTarget(id: string) {
    targetId.value = id;
    analogIndex.value = 0;
  }

  function setAnalogIndex(i: number) {
    analogIndex.value = i;
  }

  /** Switching body resets the selection, and switches to a preset that applies to the new body. */
  function changeBody(b: Body) {
    body.value = b;
    targetId.value = null;
    analogIndex.value = 0;
    const data = universe.value;
    if (!data || !presetId.value) return;
    const current = data.mission_presets[presetId.value];
    if (current?.applies_to && !current.applies_to.includes(b)) {
      const first = Object.entries(data.mission_presets).find(
        ([, p]) => !p.applies_to || p.applies_to.includes(b),
      );
      if (first) {
        presetId.value = first[0];
        weights.value = fullWeights(first[1].weights);
      }
    }
  }

  /** Moving a slider leaves the preset: the weights no longer match it. */
  function changeWeight(d: Dimension, v: number) {
    weights.value = { ...weights.value, [d]: v };
    presetId.value = null;
  }

  function choosePreset(id: string) {
    const data = universe.value;
    if (!data) return;
    presetId.value = id;
    weights.value = fullWeights(data.mission_presets[id]!.weights);
  }

  return {
    body,
    presetId,
    weights,
    minScore,
    lambda,
    newOnly,
    targetId,
    analogIndex,
    bodyTargets,
    available,
    dimInfo,
    ranked,
    unranked,
    selected,
    safeAnalog,
    targetPoints,
    earthPoints,
    selectTarget,
    setAnalogIndex,
    changeBody,
    changeWeight,
    choosePreset,
  };
}

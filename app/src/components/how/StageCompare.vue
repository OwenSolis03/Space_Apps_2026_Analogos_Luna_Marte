<script setup lang="ts">
// 05 COMPARE: a real example. Jezero crater against its best Earth analog for the rover mobility preset.
// The similarity profile grows from the centre and the MSI counts up. While the export loads, a skeleton shows.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { animate, createScope } from "animejs";
import { useUniverse } from "@/composables/useUniverse";
import { useInView } from "@/composables/useInView";
import { useReducedMotion } from "@/composables/useReducedMotion";
import { DIMENSIONS, type Analog, type Target, type Universe } from "@/lib/types";
import { DIM_LABEL } from "@/lib/content";
import { pct } from "@/lib/msi";

const EXAMPLE_TARGET = "mars-jezero-perseverance";
const EXAMPLE_PRESET = "mobility_and_traction";

const load = useUniverse();
const reduced = useReducedMotion();
const root = ref<HTMLElement | null>(null);
const counter = ref<HTMLElement | null>(null);

const universe = computed<Universe | null>(() => (load.value.state === "ready" ? load.value.data : null));
const example = computed<{ target: Target; analog: Analog; msi: number } | null>(() => {
  const u = universe.value;
  if (!u) return null;
  const target = u.targets.find((t) => t.id === EXAMPLE_TARGET);
  if (!target) return null;
  let best: Analog | null = null;
  let bestVal = -Infinity;
  for (const a of target.analogs) {
    const v = a.msi_by_preset[EXAMPLE_PRESET];
    if (v != null && v > bestVal) {
      bestVal = v;
      best = a;
    }
  }
  return best ? { target, analog: best, msi: bestVal } : null;
});

const CX = 180;
const CY = 150;
const R = 110;
const point = (i: number, r: number): [number, number] => [
  CX + r * Math.sin((i / DIMENSIONS.length) * 2 * Math.PI),
  CY - r * Math.cos((i / DIMENSIONS.length) * 2 * Math.PI),
];
const polygon = computed(() => {
  const ex = example.value;
  if (!ex) return "";
  return DIMENSIONS.map((d, i) => point(i, R * (ex.analog.sub_scores[d] ?? 0)).join(",")).join(" ");
});
const axes = DIMENSIONS.map((d, i) => ({ key: d, label: DIM_LABEL[d].label, end: point(i, R + 26) }));

let scope: ReturnType<typeof createScope> | undefined;
let run: (() => void) | undefined;

function prepare() {
  const ex = example.value;
  if (!ex || !root.value || !counter.value) return;
  const el = counter.value;
  const scale = { s: 0 };
  const msi = { v: 0 };
  scope = createScope({ root: root.value }).add(() => {
    run = () => {
      if (reduced.value) {
        scale.s = 1;
        msi.v = ex.msi;
        el.textContent = pct(ex.msi);
        return;
      }
      animate(scale, { s: 1, duration: 1200, ease: "outQuad", onUpdate: () => applyScale(scale.s) });
      animate(msi, { v: ex.msi, duration: 1400, ease: "outQuad", onUpdate: () => (el.textContent = pct(msi.v)) });
    };
    applyScale(0);
    el.textContent = pct(0);
  });
}

function applyScale(s: number) {
  root.value?.querySelector<SVGGElement>(".compare__shape")?.setAttribute("transform", `translate(${CX} ${CY}) scale(${s}) translate(${-CX} ${-CY})`);
}

onMounted(prepare);
watch(
  example,
  () => {
    scope?.revert();
    prepare();
  },
  { flush: "post" },
);
useInView(root, () => run?.());
onBeforeUnmount(() => scope?.revert());
</script>

<template>
  <div ref="root" class="compare">
    <template v-if="example">
      <svg viewBox="0 0 360 340" class="compare__svg" role="img" :aria-label="`Similarity by dimension between ${example.target.name} and ${example.analog.known_region ?? example.analog.country ?? 'its best analog'}`">
        <g class="compare__grid">
          <polygon v-for="f in [0.25, 0.5, 0.75, 1]" :key="f" :points="DIMENSIONS.map((_, i) => point(i, R * f).join(',')).join(' ')" />
        </g>
        <g class="compare__axes">
          <line v-for="(d, i) in DIMENSIONS" :key="d" :x1="CX" :y1="CY" :x2="point(i, R)[0]" :y2="point(i, R)[1]" />
        </g>
        <g class="compare__shape">
          <polygon :points="polygon" />
        </g>
        <text v-for="a in axes" :key="a.key" class="label compare__label" :x="a.end[0]" :y="a.end[1]" text-anchor="middle">{{ a.label }}</text>
      </svg>
      <div class="compare__msi">
        <p class="label">MSI · {{ example.target.name }} vs {{ example.analog.known_region ?? example.analog.country ?? "Earth analog" }}</p>
        <p ref="counter" class="compare__value num">0.0</p>
      </div>
    </template>
    <div v-else class="skeleton" aria-busy="true" aria-label="Loading the example">
      <span class="skeleton__bar" />
      <span class="skeleton__bar skeleton__bar--short" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.compare {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}

.compare__svg {
  width: 100%;
  max-width: 420px;
  height: auto;
  overflow: visible;
}

.compare__grid polygon {
  fill: none;
  stroke: var(--line-faint);
  stroke-width: var(--stroke-hairline);
}

.compare__axes line {
  stroke: var(--line);
  stroke-width: var(--stroke-hairline);
}

.compare__shape polygon {
  fill: var(--signal-tint);
  stroke: var(--ink);
  stroke-width: var(--stroke-line);
  stroke-linejoin: round;
}

.compare__label {
  fill: var(--ink-muted);
}

.compare__msi {
  display: grid;
  gap: var(--space-1);

  p {
    margin: 0;
  }
}

.compare__value {
  font-family: var(--font-display);
  font-size: clamp(40px, 6vw, 72px);
  line-height: 1;
  font-weight: 300;
  color: var(--ink);
}

.skeleton {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-5);
  background: var(--surface-raised);
  border: var(--stroke-hairline) solid var(--line-faint);
}

.skeleton__bar {
  display: block;
  height: var(--space-5);
  background: var(--surface-sunken);
}

.skeleton__bar--short {
  width: 60%;
}
</style>

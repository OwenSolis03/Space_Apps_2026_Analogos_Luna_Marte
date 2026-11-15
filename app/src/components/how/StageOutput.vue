<script setup lang="ts">
// 06 OUTPUT: three cards from the real example (ranking, where it breaks, logistics), entering one after another.
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { animate, createScope, stagger } from "animejs";
import { useUniverse } from "@/composables/useUniverse";
import { useInView } from "@/composables/useInView";
import { useReducedMotion } from "@/composables/useReducedMotion";
import { FEATURE_LABEL } from "@/lib/content";
import { pct, fmtLat, fmtLon } from "@/lib/msi";
import RButton from "@/components/reticula/RButton.vue";
import RTag from "@/components/reticula/RTag.vue";
import type { Analog, Target } from "@/lib/types";

const TARGET_ID = "mars-jezero-perseverance";
const PRESET_ID = "mobility_and_traction";

const load = useUniverse();
const reduced = useReducedMotion();
const root = ref<HTMLElement | null>(null);

const example = computed<{ target: Target; analog: Analog; msi: number } | null>(() => {
  if (load.value.state !== "ready") return null;
  const target = load.value.data.targets.find((t) => t.id === TARGET_ID);
  if (!target) return null;
  let best: Analog | null = null;
  let bestVal = -Infinity;
  for (const a of target.analogs) {
    const v = a.msi_by_preset[PRESET_ID];
    if (v != null && v > bestVal) {
      bestVal = v;
      best = a;
    }
  }
  return best ? { target, analog: best, msi: bestVal } : null;
});

const place = computed(() => {
  const a = example.value?.analog;
  if (!a) return "";
  return a.known_region ? `${a.known_region}${a.country ? `, ${a.country}` : ""}` : (a.country ?? "Copernicus DEM cell");
});

let scope: ReturnType<typeof createScope> | undefined;
let run: (() => void) | undefined;

function prepare() {
  if (!root.value) return;
  const el = root.value;
  scope = createScope({ root: el }).add(() => {
    if (reduced.value) return;
    run = () => {
      animate(el.querySelectorAll(".out-card"), {
        opacity: [0, 1],
        translateY: [16, 0],
        duration: 500,
        ease: "outQuad",
        delay: stagger(180),
      });
    };
    // Hide the cards until the stage is in view.
    el.querySelectorAll<HTMLElement>(".out-card").forEach((c) => (c.style.opacity = "0"));
  });
}

onMounted(prepare);
useInView(root, () => {
  root.value?.querySelectorAll<HTMLElement>(".out-card").forEach((c) => (c.style.opacity = ""));
  run?.();
});
onBeforeUnmount(() => scope?.revert());
const fmtLatLon = computed(() => (example.value ? `${fmtLat(example.value.analog.lat)}, ${fmtLon(example.value.analog.lon)}` : ""));
const mismatches = computed(() => (example.value?.analog.mismatches ?? []).slice(0, 2));
</script>

<template>
  <div ref="root" class="out">
    <template v-if="example">
      <article class="out-card">
        <p class="label">01 · RANKING</p>
        <p class="headline out-card__title">{{ place }}</p>
        <p class="num footnote">{{ fmtLatLon }}</p>
        <p class="out-card__score"><span class="label">MSI</span> <span class="num">{{ pct(example.msi) }}</span></p>
        <RTag tone="signal" bracket>{{ example.analog.classification === "NEW_CANDIDATE" ? "NEW CANDIDATE" : "KNOWN ANALOG" }}</RTag>
      </article>
      <article class="out-card">
        <p class="label">02 · WHERE IT BREAKS</p>
        <ul class="out-card__list body">
          <li v-for="m in mismatches" :key="m.feature">
            {{ (FEATURE_LABEL[m.feature]?.label ?? m.feature) }}:
            <span class="num">{{ typeof m.earth === "number" ? m.earth.toFixed(2) : m.earth }}</span> on Earth,
            <span class="num">{{ typeof m.target === "number" ? m.target.toFixed(2) : m.target }}</span> on Mars
          </li>
        </ul>
      </article>
      <article class="out-card">
        <p class="label">03 · LOGISTICS</p>
        <p class="body">
          <span class="num">{{ example.analog.logistics?.dist_road_km != null ? example.analog.logistics.dist_road_km.toFixed(1) : "n/a" }} km</span> to the nearest road
        </p>
        <p class="body">
          <span class="num">{{ example.analog.logistics?.dist_airport_km != null ? Math.round(example.analog.logistics.dist_airport_km).toLocaleString("en-US") : "n/a" }} km</span> to the nearest airport
        </p>
      </article>
      <RButton variant="primary" arrow to="/results" class="out__cta">OPEN RESULTS</RButton>
    </template>
    <div v-else class="skeleton" aria-busy="true" aria-label="Loading the example">
      <span class="skeleton__bar" />
      <span class="skeleton__bar skeleton__bar--short" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.out {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}

.out-card {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--surface-raised);
  border: var(--stroke-hairline) solid var(--line-faint);
  min-width: 0;

  p {
    margin: 0;
  }
}

.out-card > .tm-tag {
  justify-self: start;
}

.out-card__title {
  font-weight: 500;
  overflow-wrap: anywhere;
}

.out-card__score {
  display: flex;
  gap: var(--space-3);
  align-items: baseline;
}

.out-card__list {
  margin: 0;
  padding-left: var(--space-5);
  display: grid;
  gap: var(--space-1);
}

.out__cta {
  justify-self: start;
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

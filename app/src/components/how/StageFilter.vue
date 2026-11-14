<script setup lang="ts">
// 04 FILTER: two counters run from the full grid down to the valid patches, next to the funnel.
import { onBeforeUnmount, onMounted, ref } from "vue";
import { animate, createScope } from "animejs";
import FunnelChart from "@/components/charts/FunnelChart.vue";
import { FACTS_FUNNEL, GRID, VALID } from "@/content/facts";
import { useInView } from "@/composables/useInView";
import { useReducedMotion } from "@/composables/useReducedMotion";

const root = ref<HTMLElement | null>(null);
const counter = ref<HTMLElement | null>(null);
const reduced = useReducedMotion();
const fmt = (n: number) => Math.round(n).toLocaleString("en-US");

let scope: ReturnType<typeof createScope> | undefined;
let run: (() => void) | undefined;

onMounted(() => {
  if (!root.value || !counter.value) return;
  scope = createScope({ root: root.value }).add(() => {
    const value = { v: GRID };
    const el = counter.value!;
    run = () =>
      animate(value, {
        v: VALID,
        duration: reduced.value ? 0 : 2200,
        ease: "inOutQuad",
        onUpdate: () => (el.textContent = fmt(value.v)),
      });
    if (reduced.value) {
      el.textContent = fmt(VALID);
    } else {
      el.textContent = fmt(GRID);
    }
  });
});

useInView(root, () => run?.());
onBeforeUnmount(() => scope?.revert());
</script>

<template>
  <div ref="root" class="filter">
    <div class="filter__counter">
      <p class="label">GRID POINTS → VALID PATCHES</p>
      <p ref="counter" class="filter__value num" aria-live="off">{{ fmt(GRID) }}</p>
    </div>
    <FunnelChart label="Earth prefilter funnel: each stage with its share of the previous stage" :stages="FACTS_FUNNEL" />
  </div>
</template>

<style lang="scss" scoped>
.filter {
  display: grid;
  gap: var(--space-5);
}

.filter__counter {
  display: grid;
  gap: var(--space-2);

  p {
    margin: 0;
  }
}

.filter__value {
  font-family: var(--font-display);
  font-size: clamp(40px, 6vw, 72px);
  line-height: 1;
  font-weight: 300;
  color: var(--ink);
}
</style>

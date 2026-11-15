<script setup lang="ts">
// Earth prefilter funnel: each stage is a decreasing bar. The last bar (valid patches) is --signal.
import { computed } from "vue";

export interface FunnelStage {
  label: string;
  value: number;
}

const props = defineProps<{
  stages: FunnelStage[];
  label: string;
}>();

const ROW = 30;
const LABEL_W = 170;
const BAR_W = 300;
const VALUE_W = 150;
const W = LABEL_W + BAR_W + VALUE_W;

const first = computed(() => props.stages[0]?.value ?? 1);
const height = computed(() => props.stages.length * ROW + 6);
const fmt = (n: number) => n.toLocaleString("en-US");
const summary = computed(() =>
  props.stages
    .map((s, i) => {
      const prev = i === 0 ? null : props.stages[i - 1]!.value;
      const share = prev ? ` (${((s.value / prev) * 100).toFixed(2)} % of the previous stage)` : "";
      return `${s.label} ${fmt(s.value)}${share}`;
    })
    .join("; "),
);

const pctOfPrev = (i: number) => {
  if (i === 0) return "";
  const prev = props.stages[i - 1]!.value;
  return `${((props.stages[i]!.value / prev) * 100).toFixed(2)} %`;
};
</script>

<template>
  <figure class="funnel">
    <svg
      role="img"
      :aria-label="`${label}. ${summary}`"
      :viewBox="`0 0 ${W} ${height}`"
      preserveAspectRatio="xMinYMin meet"
      class="funnel__svg"
    >
      <g v-for="(s, i) in stages" :key="s.label" :transform="`translate(0 ${i * ROW + 3})`">
        <text class="label funnel__name" x="0" y="11" dominant-baseline="middle">{{ s.label }}</text>
        <rect
          :class="i === stages.length - 1 ? 'funnel__bar is-last' : 'funnel__bar'"
          :x="LABEL_W"
          y="2"
          :width="Math.max(2, (s.value / first) * BAR_W)"
          height="16"
        />
        <text class="label funnel__value num" :x="LABEL_W + BAR_W + 8" y="11" dominant-baseline="middle">
          {{ fmt(s.value) }}
          <tspan v-if="i > 0" class="funnel__share"> · {{ pctOfPrev(i) }}</tspan>
        </text>
      </g>
    </svg>
  </figure>
</template>

<style lang="scss" scoped>
.funnel {
  margin: 0;
  min-width: 0;
}

.funnel__svg {
  width: 100%;
  height: auto;
  overflow: visible;
}

.funnel__name {
  fill: var(--ink);
}

.funnel__value {
  fill: var(--ink);
}

.funnel__share {
  fill: var(--ink-muted);
}

.funnel__bar {
  fill: var(--graphite);
}

.funnel__bar.is-last {
  fill: var(--signal);
}
</style>

<script setup lang="ts">
// Horizontal bars with the value written at the end of each bar. One ink: bars in --graphite, highlight in --signal.
import { computed } from "vue";

export interface BarRow {
  label: string;
  value: number;
  highlight?: boolean;
}

const props = withDefaults(
  defineProps<{
    rows: BarRow[];
    /** Summary for screen readers, e.g. "Sites per country, top 15". */
    label: string;
    /** Formats the number written at the end of each bar. */
    format?: (v: number) => string;
  }>(),
  { format: (v: number) => v.toLocaleString("en-US") },
);

const ROW = 26;
const LABEL_W = 160;
const BAR_W = 300;
const VALUE_W = 80;

const max = computed(() => Math.max(1, ...props.rows.map((r) => r.value)));
const height = computed(() => props.rows.length * ROW + 8);
const width = LABEL_W + BAR_W + VALUE_W;
const summary = computed(() => props.rows.map((r) => `${r.label} ${props.format(r.value)}`).join(", "));
</script>

<template>
  <figure class="bars">
    <svg
      role="img"
      :aria-label="`${label}. ${summary}`"
      :viewBox="`0 0 ${width} ${height}`"
      preserveAspectRatio="xMinYMin meet"
      class="bars__svg"
    >
      <g v-for="(r, i) in rows" :key="r.label" :transform="`translate(0 ${i * ROW + 4})`">
        <text class="label bars__name" x="0" y="13" dominant-baseline="middle">{{ r.label }}</text>
        <rect
          :class="r.highlight ? 'bars__bar is-highlight' : 'bars__bar'"
          :x="LABEL_W"
          y="4"
          :width="(r.value / max) * BAR_W"
          height="14"
        />
        <text class="label bars__value num" :x="LABEL_W + BAR_W + 8" y="13" dominant-baseline="middle">
          {{ format(r.value) }}
        </text>
      </g>
      <line class="bars__axis" :x1="LABEL_W" :x2="LABEL_W" y1="0" :y2="height" />
    </svg>
  </figure>
</template>

<style lang="scss" scoped>
.bars {
  margin: 0;
  min-width: 0;
}

.bars__svg {
  width: 100%;
  height: auto;
  overflow: visible;
}

.bars__name {
  fill: var(--ink);
}

.bars__value {
  fill: var(--ink-muted);
}

.bars__bar {
  fill: var(--graphite);
}

.bars__bar.is-highlight {
  fill: var(--signal);
}

.bars__axis {
  stroke: var(--line);
  stroke-width: var(--stroke-hairline);
}
</style>

<script setup lang="ts">
// Square similarity table (0 to 1). Cells carry their value as text; the fill steps through three tones,
// so the value is never shown by colour alone.
import { computed } from "vue";

const props = defineProps<{
  /** Row and column labels, in order. */
  labels: string[];
  /** values[row][col] in 0..1. */
  values: number[][];
  label: string;
}>();

const N = computed(() => props.labels.length);
const CELL = 56;
const HEAD = 150;
const size = computed(() => HEAD + N.value * CELL);

const tone = (v: number) => (v >= 0.999 ? "is-full" : v <= 0.001 ? "is-zero" : "is-mid");
const cell = (v: number) => v.toFixed(2);
const summary = computed(() => `${N.value} classes, values from 0 to 1`);
</script>

<template>
  <figure class="matrix">
    <svg
      role="img"
      :aria-label="`${label}. ${summary}`"
      :viewBox="`0 0 ${size} ${size}`"
      preserveAspectRatio="xMinYMin meet"
      class="matrix__svg"
    >
      <g v-for="(rowLabel, r) in labels" :key="`row-${r}`">
        <text class="label matrix__label" x="0" :y="HEAD + r * CELL + CELL / 2" dominant-baseline="middle">{{ rowLabel }}</text>
        <g v-for="(colLabel, c) in labels" :key="`cell-${r}-${c}`">
          <rect
            :class="['matrix__cell', tone(values[r]?.[c] ?? 0)]"
            :x="HEAD + c * CELL"
            :y="HEAD + r * CELL"
            :width="CELL"
            :height="CELL"
          />
          <text
            class="num matrix__value"
            :x="HEAD + c * CELL + CELL / 2"
            :y="HEAD + r * CELL + CELL / 2"
            text-anchor="middle"
            dominant-baseline="middle"
          >{{ cell(values[r]?.[c] ?? 0) }}</text>
          <title>{{ rowLabel }} vs {{ colLabel }}: {{ cell(values[r]?.[c] ?? 0) }}</title>
        </g>
      </g>
      <g v-for="(colLabel, c) in labels" :key="`col-${c}`">
        <text class="label matrix__label" :x="HEAD + c * CELL + CELL / 2" :y="HEAD - 8" text-anchor="start" :transform="`rotate(-45 ${HEAD + c * CELL + CELL / 2} ${HEAD - 8})`">{{ colLabel }}</text>
      </g>
    </svg>
  </figure>
</template>

<style lang="scss" scoped>
.matrix {
  margin: 0;
  min-width: 0;
  overflow-x: auto;
}

.matrix__svg {
  width: 100%;
  min-width: 620px;
  height: auto;
}

.matrix__label {
  fill: var(--ink-muted);
}

.matrix__value {
  fill: var(--ink);
}

.matrix__cell {
  stroke: var(--line-faint);
  stroke-width: var(--stroke-hairline);

  &.is-zero {
    fill: var(--surface-raised);
  }

  &.is-mid {
    fill: var(--signal-tint);
  }

  &.is-full {
    fill: var(--signal);
  }
}
</style>

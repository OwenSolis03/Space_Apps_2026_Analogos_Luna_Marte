<script setup lang="ts">
// One row per body: every curated target as a dot on a 0 to 1 axis, with the median marked in --signal.
import { computed } from "vue";

export interface StripRow {
  label: string;
  points: { name: string; value: number }[];
}

const props = defineProps<{
  rows: StripRow[];
  label: string;
}>();

const W = 520;
const LEFT = 90;
const RIGHT = 24;
const ROW = 64;
const AXIS_Y_PAD = 28;

const plotW = W - LEFT - RIGHT;
const x = (v: number) => LEFT + Math.max(0, Math.min(1, v)) * plotW;
const height = computed(() => props.rows.length * ROW + AXIS_Y_PAD + 16);

function median(values: number[]): number {
  if (values.length === 0) return NaN;
  const s = [...values].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid]! : (s[mid - 1]! + s[mid]!) / 2;
}

const medians = computed(() => props.rows.map((r) => median(r.points.map((p) => p.value))));
const summary = computed(() =>
  props.rows
    .map((r, i) => `${r.label}: ${r.points.length} targets, median ${(medians.value[i]! * 100).toFixed(1)}`)
    .join("; "),
);
const ticks = [0, 0.25, 0.5, 0.75, 1];
</script>

<template>
  <figure class="strip">
    <svg
      role="img"
      :aria-label="`${label}. ${summary}`"
      :viewBox="`0 0 ${W} ${height}`"
      preserveAspectRatio="xMinYMin meet"
      class="strip__svg"
    >
      <g v-for="(r, i) in rows" :key="r.label" :transform="`translate(0 ${i * ROW})`">
        <text class="label strip__name" x="0" :y="ROW / 2 - 4" dominant-baseline="middle">{{ r.label }}</text>
        <line class="strip__track" :x1="LEFT" :x2="LEFT + plotW" :y1="ROW / 2" :y2="ROW / 2" />
        <circle
          v-for="(p, j) in r.points"
          :key="`${r.label}-${j}`"
          class="strip__dot"
          :cx="x(p.value)"
          :cy="ROW / 2"
          r="4"
        >
          <title>{{ p.name }}: {{ (p.value * 100).toFixed(1) }}</title>
        </circle>
        <line
          v-if="!Number.isNaN(medians[i])"
          class="strip__median"
          :x1="x(medians[i]!)"
          :x2="x(medians[i]!)"
          :y1="ROW / 2 - 16"
          :y2="ROW / 2 + 16"
        />
        <text
          v-if="!Number.isNaN(medians[i])"
          class="label strip__median-text"
          :x="x(medians[i]!)"
          :y="ROW / 2 - 20"
          :text-anchor="x(medians[i]!) > LEFT + plotW * 0.8 ? 'end' : 'middle'"
        >
          MEDIAN {{ (medians[i]! * 100).toFixed(1) }}
        </text>
      </g>
      <g :transform="`translate(0 ${rows.length * ROW})`">
        <line class="strip__axis" :x1="LEFT" :x2="LEFT + plotW" y1="0" y2="0" />
        <g v-for="t in ticks" :key="t">
          <line class="strip__axis" :x1="x(t)" :x2="x(t)" y1="0" y2="6" />
          <text class="label strip__tick" :x="x(t)" y="20" text-anchor="middle">{{ (t * 100).toFixed(0) }}</text>
        </g>
      </g>
    </svg>
  </figure>
</template>

<style lang="scss" scoped>
.strip {
  margin: 0;
  min-width: 0;
}

.strip__svg {
  width: 100%;
  height: auto;
  overflow: visible;
}

.strip__name,
.strip__tick {
  fill: var(--ink-muted);
}

.strip__median-text {
  fill: var(--ink);
}

.strip__track,
.strip__axis {
  stroke: var(--line);
  stroke-width: var(--stroke-hairline);
}

.strip__dot {
  fill: var(--graphite);
}

.strip__median {
  stroke: var(--signal);
  stroke-width: var(--stroke-bar);
}
</style>

<script setup lang="ts">
// Radar over the seven similarity dimensions (0 to 1). Port of components/Radar.tsx.
// Dashed axes: not applicable to this body. Hollow marker at the centre: no Earth data (scored 0).
import { computed } from "vue";
import type { Dimension } from "@/lib/types";
import { DIMENSIONS } from "@/lib/types";
import { DIM_LABEL } from "@/lib/content";

const props = defineProps<{
  values: Partial<Record<Dimension, number | null>>;
  availableDims?: Dimension[];
  earthMissingDims?: Dimension[];
}>();

const CX = 150;
const CY = 120;
const R = 82;
const N = DIMENSIONS.length;

const point = (i: number, r: number): [number, number] => [
  CX + r * Math.sin((i / N) * 2 * Math.PI),
  CY - r * Math.cos((i / N) * 2 * Math.PI),
];

const value = (d: Dimension) => props.values[d] ?? null;
const poly = computed(() =>
  DIMENSIONS.map((d, i) => point(i, R * (value(d) ?? 0)).join(",")).join(" "),
);

const summary = computed(() =>
  DIMENSIONS.map((d) => {
    if (props.earthMissingDims?.includes(d)) return `${DIM_LABEL[d].label}: no Earth data (0.00)`;
    const v = value(d);
    return `${DIM_LABEL[d].label}: ${v == null ? "not applicable" : v.toFixed(2)}`;
  }).join(", "),
);

const isOff = (d: Dimension) => (props.availableDims ? !props.availableDims.includes(d) : value(d) == null);
</script>

<template>
  <figure class="radar-wrap">
  <svg viewBox="-40 0 380 252" class="radar" role="img" :aria-label="`Similarity by dimension. ${summary}`">
    <polygon
      v-for="f in [0.25, 0.5, 0.75, 1]"
      :key="f"
      class="radar__grid"
      :points="DIMENSIONS.map((_, i) => point(i, R * f).join(',')).join(' ')"
    />
    <g v-for="(d, i) in DIMENSIONS" :key="d">
      <line
        class="radar__axis"
        :class="{ 'is-off': isOff(d) }"
        :x1="CX"
        :y1="CY"
        :x2="point(i, R)[0]"
        :y2="point(i, R)[1]"
      />
      <text
        class="label radar__label"
        :class="{ 'is-off': isOff(d) }"
        :x="point(i, R + 22)[0]"
        :y="point(i, R + 22)[1] + (earthMissingDims?.includes(d) ? 0 : 4)"
        text-anchor="middle"
      >
        <tspan :x="point(i, R + 22)[0]">{{ DIM_LABEL[d].label }}</tspan>
        <tspan v-if="earthMissingDims?.includes(d)" :x="point(i, R + 22)[0]" dy="14" class="radar__missing">
          no Earth data
        </tspan>
      </text>
    </g>
    <polygon class="radar__shape" :points="poly" />
    <template v-for="(d, i) in DIMENSIONS" :key="`dot-${d}`">
      <circle
        v-if="value(d) != null"
        class="radar__dot"
        :cx="point(i, R * (value(d) ?? 0))[0]"
        :cy="point(i, R * (value(d) ?? 0))[1]"
        r="3.5"
      />
      <circle
        v-else-if="earthMissingDims?.includes(d)"
        class="radar__hollow"
        :cx="point(i, 0)[0]"
        :cy="point(i, 0)[1]"
        r="4.5"
      />
    </template>
  </svg>
  <figcaption class="footnote radar__legend">DASHED AXES: NOT APPLICABLE · HOLLOW CIRCLE: NO EARTH DATA (0)</figcaption>
  </figure>
</template>

<style lang="scss" scoped>
.radar {
  display: block;
  width: 100%;
  max-width: 24rem;
  margin-inline: auto;
  overflow: visible;
}

.radar__grid {
  fill: none;
  stroke: var(--line-faint);
  stroke-width: var(--stroke-hairline);
}

.radar__axis {
  stroke: var(--line);
  stroke-width: var(--stroke-hairline);

  &.is-off {
    stroke-dasharray: 3 3;
    stroke: var(--line-faint);
  }
}

.radar__label {
  fill: var(--ink-muted);

  &.is-off {
    fill: var(--ink-muted);
  }
}

.radar__missing {
  fill: var(--signal-ink);
}

.radar__shape {
  fill: var(--signal-tint);
  fill-opacity: 0.8;
  stroke: var(--ink);
  stroke-width: var(--stroke-line);
  stroke-linejoin: round;
}

.radar__dot {
  fill: var(--ink);
}

.radar__hollow {
  fill: var(--surface-raised);
  stroke: var(--ink);
  stroke-width: var(--stroke-hairline);
}

.radar-wrap {
  margin: 0;
  min-width: 0;
}

.radar__legend {
  margin-top: var(--space-2);
  color: var(--ink-muted);
  text-align: center;
}
</style>

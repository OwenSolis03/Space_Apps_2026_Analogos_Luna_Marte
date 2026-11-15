<script setup lang="ts">
// RETÍCULA DotGrid: decorative dot matrix on a 16-unit pitch. Optional orange lead bar.
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    cols?: number;
    rows?: number;
    tone?: "graphite" | "faint" | "signal";
    lead?: boolean;
  }>(),
  { cols: 12, rows: 3, tone: "graphite", lead: false },
);

const PITCH = 16;
const DOT = 4;

const width = computed(() => props.cols * PITCH - (PITCH - DOT));
const height = computed(() => props.rows * PITCH - (PITCH - DOT));

const path = computed(() => {
  let d = "";
  for (let r = 0; r < props.rows; r++) {
    for (let c = 0; c < props.cols; c++) {
      d += `M${c * PITCH} ${r * PITCH}h${DOT}v${DOT}h-${DOT}z`;
    }
  }
  return d;
});
</script>

<template>
  <div class="tm-dotgrid" aria-hidden="true">
    <span v-if="lead" class="tm-dotgrid__lead" />
    <svg
      class="tm-dotgrid__svg"
      :class="`tm-dotgrid--${tone}`"
      :width="width"
      :height="height"
      :viewBox="`0 0 ${width} ${height}`"
      focusable="false"
    >
      <path :d="path" fill="currentColor" />
    </svg>
  </div>
</template>

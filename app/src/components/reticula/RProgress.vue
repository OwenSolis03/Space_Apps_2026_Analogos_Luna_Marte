<script setup lang="ts">
// RETÍCULA Progress: labelled bar with a percentage readout and an optional hazard tail.
import { computed } from "vue";
import RHazard from "./RHazard.vue";

const props = withDefaults(
  defineProps<{
    label: string;
    /** Between 0 and 1. */
    value: number;
    hazard?: boolean;
  }>(),
  { hazard: true },
);

const clamped = computed(() => Math.max(0, Math.min(1, props.value || 0)));
const pct = computed(() => Math.round(clamped.value * 100));
</script>

<template>
  <div class="tm-progress">
    <div class="tm-progress__row label">
      <span>{{ label }}</span>
      <span class="tm-progress__pct">{{ pct }}%</span>
    </div>
    <div class="tm-progress__bar">
      <div
        class="tm-progress__track"
        role="progressbar"
        :aria-label="label"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-valuenow="pct"
      >
        <span class="tm-progress__fill" :style="{ width: `calc((100% - 4px) * ${clamped})` }" />
      </div>
      <RHazard v-if="hazard" class="tm-progress__hazard" />
    </div>
  </div>
</template>

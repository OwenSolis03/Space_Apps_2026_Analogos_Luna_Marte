<script setup lang="ts">
// RETÍCULA Barcode: modular 24px bar with uneven segments. Ornament only; it encodes no data.
import { computed } from "vue";

const DEFAULT_SEGMENTS = [10, 3, 3, 3, 2, 5, 2, 2, 6, 2, 3, 8, 2, 2, 4, 3, 12, 2, 2, 3, 6, 2, 3, 3, 2];

const props = withDefaults(
  defineProps<{
    segments?: number[];
    tone?: "signal" | "ink" | "graphite";
  }>(),
  { segments: undefined, tone: "signal" },
);

const widths = computed(() => props.segments ?? DEFAULT_SEGMENTS);
</script>

<template>
  <div class="tm-barcode" :class="`tm-barcode--${tone}`" aria-hidden="true">
    <i
      v-for="(w, i) in widths"
      :key="i"
      :class="{ on: i % 2 === 0 }"
      :style="{ flexGrow: w }"
    />
  </div>
</template>

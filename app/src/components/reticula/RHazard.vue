<script setup lang="ts">
// RETÍCULA Hazard: diagonal hazard stripes. Ornament only; use one per composition.
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    tone?: "graphite" | "signal";
    height?: number | string;
    width?: number | string;
  }>(),
  { tone: "graphite", height: undefined, width: undefined },
);

const style = computed(() => ({
  ...(props.height !== undefined ? { height: typeof props.height === "number" ? `${props.height}px` : props.height } : {}),
  ...(props.width !== undefined ? { width: typeof props.width === "number" ? `${props.width}px` : props.width } : {}),
}));
</script>

<template>
  <div
    class="tm-hazard"
    :class="{ 'tm-hazard--signal': tone === 'signal' }"
    :style="style"
    aria-hidden="true"
  />
</template>

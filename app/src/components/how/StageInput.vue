<script setup lang="ts">
// 01 INPUT: three planet discs are drawn in, and the layers arrive as tags underneath.
import { onBeforeUnmount, onMounted, ref } from "vue";
import { createScope, createTimeline, stagger, svg } from "animejs";
import RTag from "@/components/reticula/RTag.vue";
import { useInView } from "@/composables/useInView";
import { useReducedMotion } from "@/composables/useReducedMotion";

const root = ref<HTMLElement | null>(null);
const reduced = useReducedMotion();
const LAYERS = ["ELEVATION", "VEGETATION", "TEMPERATURE", "ROCK TYPE", "DUST", "ICE"];
const DISCS = [
  { x: 90, label: "MOON" },
  { x: 240, label: "MARS" },
  { x: 390, label: "EARTH" },
];

let scope: ReturnType<typeof createScope> | undefined;
let timeline: ReturnType<typeof createTimeline> | undefined;

onMounted(() => {
  if (!root.value || reduced.value) return;
  scope = createScope({ root: root.value }).add(() => {
    timeline = createTimeline({ autoplay: false, defaults: { ease: "outQuad" } })
      .add(svg.createDrawable(".in-disc"), { draw: ["0 0", "0 1"], duration: 900, delay: stagger(200) })
      .add(".in-label, .in-layer", { opacity: [0, 1], duration: 400, delay: stagger(90) }, 500);
    timeline.seek(0);
  });
});

useInView(root, () => timeline?.play());
onBeforeUnmount(() => scope?.revert());
</script>

<template>
  <div ref="root" class="input">
    <svg viewBox="0 0 480 240" class="input__svg" role="img" aria-label="Three planet discs labelled Moon, Mars and Earth">
      <circle
        v-for="d in DISCS"
        :key="d.label"
        class="in-disc"
        :cx="d.x"
        cy="100"
        r="60"
        fill="none"
      />
      <text
        v-for="d in DISCS"
        :key="`l-${d.label}`"
        class="label in-label"
        :x="d.x"
        y="194"
        text-anchor="middle"
      >{{ d.label }}</text>
    </svg>
    <div class="input__layers">
      <RTag v-for="l in LAYERS" :key="l" class="in-layer" tone="outline">{{ l }}</RTag>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.input {
  display: grid;
  gap: var(--space-5);
}

.input__svg {
  width: 100%;
  height: auto;
  overflow: visible;
}

.in-disc {
  stroke: var(--ink);
  stroke-width: var(--stroke-line);
}

.in-label {
  fill: var(--ink);
}

.input__layers {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>

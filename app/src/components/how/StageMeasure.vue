<script setup lang="ts">
// 03 MEASURE: a terrain profile is drawn, then six bars (the footprint) grow from zero, labelled with the feature names.
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { createScope, createTimeline, stagger, svg } from "animejs";
import { useInView } from "@/composables/useInView";
import { useReducedMotion } from "@/composables/useReducedMotion";
import { FEATURE_LABEL } from "@/lib/content";

const root = ref<HTMLElement | null>(null);
const reduced = useReducedMotion();
const FEATURES = ["mean_slope_deg", "p90_slope_deg", "relief_m", "hypsometric_integral", "detrended_std_m", "tri_m"];
// Bar heights are decorative: they show the shape of a footprint, not any value.
const HEIGHTS = [70, 96, 52, 84, 60, 40];
const names = computed(() => FEATURES.map((f) => (FEATURE_LABEL[f]?.label ?? f).toUpperCase()));
const profile = "M0 150 C 40 110, 70 130, 110 90 S 180 60, 220 100 S 300 40, 340 80 S 420 70, 480 40";

let scope: ReturnType<typeof createScope> | undefined;
let timeline: ReturnType<typeof createTimeline> | undefined;

onMounted(() => {
  if (!root.value || reduced.value) return;
  scope = createScope({ root: root.value }).add(() => {
    timeline = createTimeline({ autoplay: false, defaults: { ease: "outQuad" } })
      .add(svg.createDrawable(".profile"), { draw: ["0 0", "0 1"], duration: 1000 })
      .add(".footprint-bar", { scaleY: [0, 1], duration: 600, delay: stagger(90) }, 700)
      .add(".footprint-name", { opacity: [0, 1], duration: 300, delay: stagger(90) }, 900);
    timeline.seek(0);
  });
});

useInView(root, () => timeline?.play());
onBeforeUnmount(() => scope?.revert());
</script>

<template>
  <div ref="root" class="measure">
    <svg viewBox="0 0 480 300" class="measure__svg" role="img" aria-label="A terrain profile and six footprint bars labelled with the six terrain features">
      <line x1="0" y1="160" x2="480" y2="160" class="measure__ground" />
      <path :d="profile" class="profile" fill="none" />
      <g v-for="(h, i) in HEIGHTS" :key="i" :transform="`translate(${i * 80 + 20} 0)`">
        <rect class="footprint-bar" x="0" :y="250 - h" width="40" :height="h" />
        <text class="label footprint-name" x="0" y="278">{{ names[i] }}</text>
      </g>
    </svg>
  </div>
</template>

<style lang="scss" scoped>
.measure__svg {
  width: 100%;
  height: auto;
  overflow: visible;
}

.measure__ground {
  stroke: var(--line-faint);
  stroke-width: var(--stroke-hairline);
}

.profile {
  stroke: var(--ink);
  stroke-width: var(--stroke-line);
}

.footprint-bar {
  fill: var(--graphite);
  transform-box: fill-box;
  transform-origin: bottom;
}

.footprint-name {
  fill: var(--ink-muted);
}
</style>

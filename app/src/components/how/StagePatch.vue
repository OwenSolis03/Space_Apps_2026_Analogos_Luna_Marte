<script setup lang="ts">
// 02 SAME SQUARE: a 16 by 16 dot grid (standing for the 64 by 64 patch) fills from the centre, once per body.
import { onBeforeUnmount, onMounted, ref } from "vue";
import { createScope, createTimeline, stagger } from "animejs";
import { useInView } from "@/composables/useInView";
import { useReducedMotion } from "@/composables/useReducedMotion";

const root = ref<HTMLElement | null>(null);
const reduced = useReducedMotion();
const N = 16;
const PITCH = 14;
const GAP = 40;
const SIZE = N * PITCH;
const BODIES = ["MOON", "MARS", "EARTH"];
const dots = Array.from({ length: N * N }, (_, i) => ({ x: (i % N) * PITCH, y: Math.floor(i / N) * PITCH }));
const groupX = (g: number) => g * (SIZE + GAP);
const viewW = BODIES.length * SIZE + (BODIES.length - 1) * GAP;

let scope: ReturnType<typeof createScope> | undefined;
let timeline: ReturnType<typeof createTimeline> | undefined;

onMounted(() => {
  if (!root.value || reduced.value) return;
  scope = createScope({ root: root.value }).add(() => {
    timeline = createTimeline({ autoplay: false });
    // One grid per body, each filling from its centre.
    root.value!.querySelectorAll<SVGGElement>(".patch").forEach((group) => {
      timeline!.add(
        group.querySelectorAll(".patch-dot"),
        { opacity: [0, 1], scale: [0, 1], duration: 300, delay: stagger(14, { grid: [N, N], from: "center" }) },
        0,
      );
    });
    timeline.seek(0);
  });
});

useInView(root, () => timeline?.play());
onBeforeUnmount(() => scope?.revert());
</script>

<template>
  <div ref="root" class="patch-figure">
    <svg :viewBox="`-8 -8 ${viewW + 16} ${SIZE + 64}`" class="patch-figure__svg" role="img" aria-label="Three 16 by 16 dot grids, one per body, each marked as 32 kilometres">
      <g v-for="(b, g) in BODIES" :key="b" class="patch" :transform="`translate(${groupX(g)} 0)`">
        <rect class="patch-frame" x="-4" y="-4" :width="SIZE + 8" :height="SIZE + 8" fill="none" />
        <rect
          v-for="(d, i) in dots"
          :key="`${b}-${i}`"
          class="patch-dot"
          :x="d.x"
          :y="d.y"
          width="4"
          height="4"
        />
        <text class="label patch-name" :x="0" :y="SIZE + 22">{{ b }} · 32 KM</text>
      </g>
    </svg>
  </div>
</template>

<style lang="scss" scoped>
.patch-figure__svg {
  width: 100%;
  height: auto;
}

.patch-frame {
  stroke: var(--line);
  stroke-width: var(--stroke-hairline);
}

.patch-dot {
  fill: var(--graphite);
  transform-box: fill-box;
  transform-origin: center;
}

.patch-name {
  fill: var(--ink-muted);
}
</style>

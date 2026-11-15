<script setup lang="ts">
// 01 INPUT: the Moon, Mars and Earth as spinning 3D bodies (same three.js style as the Home planets,
// three colours each), and the layers arriving as tags underneath. Without WebGL the flat line discs remain.
import { onBeforeUnmount, onMounted, ref } from "vue";
import { createScope, createTimeline, stagger } from "animejs";
import RTag from "@/components/reticula/RTag.vue";
import { useInView } from "@/composables/useInView";
import { useReducedMotion } from "@/composables/useReducedMotion";
import type { PlanetScene } from "@/components/home/planets3d";
import type { PlanetBody } from "@/content/sections";

const root = ref<HTMLElement | null>(null);
const svgEl = ref<SVGSVGElement | null>(null);
const canvas = ref<HTMLCanvasElement | null>(null);
const reduced = useReducedMotion();
const webgl = ref(true);

const VIEW = { x: 0, y: 0, w: 480, h: 240 };
const LAYERS = ["ELEVATION", "VEGETATION", "TEMPERATURE", "ROCK TYPE", "DUST", "ICE"];
const BODIES: { x: number; label: string; body: PlanetBody; tilt: number; spin: number }[] = [
  { x: 90, label: "MOON", body: "moon", tilt: 7, spin: 2.5 },
  { x: 240, label: "MARS", body: "mars", tilt: 25, spin: 5 },
  { x: 390, label: "EARTH", body: "earth", tilt: -23, spin: 6 },
];

let scope: ReturnType<typeof createScope> | undefined;
let timeline: ReturnType<typeof createTimeline> | undefined;
let bodies: PlanetScene | undefined;
let resizeObserver: ResizeObserver | undefined;
let unmounted = false;

function fit() {
  if (!bodies || !svgEl.value) return;
  const box = svgEl.value.getBoundingClientRect();
  bodies.resize(box.width, box.height, VIEW);
}

// three.js is loaded on demand, as on the Home page.
async function setupBodies() {
  if (!canvas.value) return;
  try {
    const { createPlanetScene } = await import("@/components/home/planets3d");
    if (!canvas.value || unmounted) return;
    bodies = createPlanetScene(
      canvas.value,
      BODIES.map((b) => ({ name: b.label, body: b.body, x: b.x, y: 100, tilt: b.tilt, spin: b.spin })),
      // Light from the upper left, in front of the bodies; y points up in the scene.
      { radius: 60, satellite: false, threeColour: true, lightAt: [-200, 260, 520], ambient: 0.9, light: 1.6 },
    );
  } catch {
    webgl.value = false;
    return;
  }
  fit();
  resizeObserver = new ResizeObserver(fit);
  if (svgEl.value) resizeObserver.observe(svgEl.value);
  bodies.start(reduced.value);
}

onMounted(() => {
  setupBodies();
  if (!root.value || reduced.value) return;
  scope = createScope({ root: root.value }).add(() => {
    timeline = createTimeline({ autoplay: false, defaults: { ease: "outQuad" } })
      .add(".input__canvas, .in-disc", { opacity: [0, 1], duration: 700 })
      .add(".in-label, .in-layer", { opacity: [0, 1], duration: 400, delay: stagger(90) }, 400);
    timeline.seek(0);
  });
});

useInView(root, () => timeline?.play());
onBeforeUnmount(() => {
  unmounted = true;
  scope?.revert();
  resizeObserver?.disconnect();
  bodies?.dispose();
});
</script>

<template>
  <div ref="root" class="input">
    <div class="input__scene">
      <svg ref="svgEl" viewBox="0 0 480 240" class="input__svg" role="img" aria-label="The Moon, Mars and Earth, spinning, with their names">
        <template v-if="!webgl">
          <circle v-for="d in BODIES" :key="d.label" class="in-disc" :cx="d.x" cy="100" r="60" fill="none" />
        </template>
        <text
          v-for="d in BODIES"
          :key="`l-${d.label}`"
          class="label in-label"
          :x="d.x"
          y="194"
          text-anchor="middle"
        >{{ d.label }}</text>
      </svg>
      <canvas v-show="webgl" ref="canvas" class="input__canvas" aria-hidden="true" />
    </div>
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

.input__scene {
  position: relative;
}

.input__canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
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

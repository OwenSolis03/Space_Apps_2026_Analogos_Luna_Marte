<script setup lang="ts">
// The Home navigation: a solar system. The sun opens RESULTS; each planet opens one section.
// Three layers share one viewBox: a back SVG (orbits and sun), a WebGL canvas with the 3D planets
// (three.js, RETÍCULA style), and a front SVG with the planet links, leaders and labels.
// Planets stay in place and spin on their own axis at different speeds. Without WebGL the flat SVG
// planets are drawn instead. Under prefers-reduced-motion a single still frame is drawn.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { animate, createScope, createTimeline, stagger, svg } from "animejs";
import { SECTIONS, sectionByName, type OrbitSpec, type SiteSection } from "@/content/sections";
import { useMediaQuery } from "@/composables/useMediaQuery";
import { useReducedMotion } from "@/composables/useReducedMotion";
import type { PlanetScene } from "./planets3d";

interface Planet extends SiteSection {
  orbit: OrbitSpec;
}

const root = ref<HTMLDivElement | null>(null);
const back = ref<SVGSVGElement | null>(null);
const canvas = ref<HTMLCanvasElement | null>(null);
const reduced = useReducedMotion();
const narrow = useMediaQuery("(max-width: 767px)");
/** False when WebGL is unavailable: the flat SVG planets are shown instead. */
const webgl = ref(true);

const sun = sectionByName("results");
const planets: Planet[] = SECTIONS.filter((s): s is Planet => s.orbit !== undefined);

// On phones only the first three orbits fit the drawing (Earth, Mars, Moon); the rest stay in the section list.
const shownPlanets = computed(() => (narrow.value ? planets.filter((p) => p.orbit.rx <= 400) : planets));

/** Every planet has the same radius (design units), in the SVG and in the 3D scene. */
const R = 34;
const HIT_R = 46;
const MERIDIANS = 4;
const meridians = Array.from({ length: MERIDIANS }, (_, k) => ({
  k,
  rx: R * Math.abs(Math.sin((k * Math.PI) / MERIDIANS)),
}));
const parallelOffsets = (n: number) =>
  Array.from({ length: n }, (_, i) => ((i - (n - 1) / 2) * (2 * R)) / (n + 1));

/** Earth and Mars are the bodies of the project: their orbits and rings are drawn stronger. */
const featured = (p: Planet) => p.orbit.body === "earth" || p.orbit.body === "mars";
const dashFor = (p: Planet) => (featured(p) ? "10 6" : "3 6");
// Earth's label sits higher so it clears the sun's tag.
const lift = (p: Planet) => (p.orbit.body === "earth" ? 26 : 0);

// Label boxes are sized from the text length (monospace label face).
const labelWidth = (text: string) => Math.round(text.length * 8.2 + 16);

const view = computed(() => (narrow.value ? { x: -420, y: -240, w: 840, h: 480 } : { x: -640, y: -360, w: 1280, h: 720 }));
const viewBox = computed(() => `${view.value.x} ${view.value.y} ${view.value.w} ${view.value.h}`);
const sunLabel = `${sun.code} / ${sun.label}`;

let scope: ReturnType<typeof createScope> | undefined;
let planetScene: PlanetScene | undefined;
let resizeObserver: ResizeObserver | undefined;
let unmounted = false;

// Restores each orbit's dash pattern once the intro has drawn the orbits.
function restoreOrbitDash() {
  root.value?.querySelectorAll<SVGEllipseElement>(".orbit").forEach((orbit) => {
    orbit.removeAttribute("pathLength");
    orbit.setAttribute("stroke-dasharray", orbit.dataset.dash ?? "3 6");
  });
}

function fitCanvas() {
  if (!planetScene || !back.value) return;
  const box = back.value.getBoundingClientRect();
  planetScene.resize(box.width, box.height, view.value);
}

// three.js is loaded on demand so it stays out of the main bundle.
async function setupPlanets() {
  if (!canvas.value) return;
  try {
    const { createPlanetScene } = await import("./planets3d");
    if (!canvas.value || unmounted) return;
    planetScene = createPlanetScene(
      canvas.value,
      planets.map((p) => ({ name: p.name, body: p.orbit.body, x: p.orbit.x, y: p.orbit.y, tilt: p.orbit.tilt, spin: p.orbit.spin })),
    );
  } catch {
    webgl.value = false;
    return;
  }
  planetScene.setVisible(new Set(shownPlanets.value.map((p) => p.name)));
  fitCanvas();
  resizeObserver = new ResizeObserver(fitCanvas);
  if (back.value) resizeObserver.observe(back.value);
  planetScene.start(reduced.value);
  // Exposed for checks in the browser console.
  (window as unknown as { __planets?: PlanetScene }).__planets = planetScene;
}

watch([shownPlanets, view], () => {
  planetScene?.setVisible(new Set(shownPlanets.value.map((p) => p.name)));
  fitCanvas();
});
watch(reduced, (r) => planetScene?.start(r));

onMounted(() => {
  setupPlanets();
  if (!root.value || reduced.value) return; // final state is already in the markup

  scope = createScope({ root: root.value }).add(() => {
    // Sun: frames counter-rotate, tick ring turns, pulse ring breathes.
    animate(".sun__frame", {
      rotate: (_el: unknown, i?: number) => ((i ?? 0) % 2 ? -360 : 360),
      duration: (_el: unknown, i?: number) => 70000 + (i ?? 0) * 25000,
      ease: "linear",
      loop: true,
    });
    animate(".sun__ticks", { rotate: 360, duration: 90000, ease: "linear", loop: true });
    animate(".sun__pulse", { scale: [1, 1.22], opacity: [0.7, 0], duration: 2600, ease: "outQuad", loop: true });

    // Orbits: the dash pattern drifts, the planets stay put.
    animate(".orbit", { strokeDashoffset: [0, -64], duration: 9000, ease: "linear", loop: true });

    // Flat fallback only: meridians follow |sin| so the SVG planets seem to spin.
    if (!webgl.value) {
      root.value!.querySelectorAll<SVGGElement>(".planet").forEach((planet, i) => {
        const ellipses = [...planet.querySelectorAll<SVGEllipseElement>(".planet__meridian")];
        const spin = { t: 0 };
        animate(spin, {
          t: Math.PI,
          duration: 12000 + i * 2500,
          ease: "linear",
          loop: true,
          onUpdate: () =>
            ellipses.forEach((m, k) =>
              m.setAttribute("rx", String(R * Math.abs(Math.sin(spin.t + (k * Math.PI) / ellipses.length)))),
            ),
        });
      });
    }

    // One-off intro: orbits draw, sun grows, planets and labels arrive.
    // createDrawable rewrites the orbits' dash settings (pathLength, dasharray), so each pattern
    // is restored when the intro ends.
    createTimeline({ defaults: { ease: "outQuad" }, onComplete: restoreOrbitDash })
      .add(svg.createDrawable(".orbit"), { draw: ["0 0", "0 1"], duration: 900, delay: stagger(80) })
      .add(".sun", { scale: [0.6, 1], opacity: [0, 1], duration: 500 }, 200)
      .add(webgl.value ? ".solar__canvas, .planet__ring" : ".planet__body", { opacity: [0, 1], duration: 600, delay: stagger(90) }, 500)
      .add(".leader, .planet__tag", { opacity: [0, 1], duration: 300, delay: stagger(60) }, 900);
  });
});

onBeforeUnmount(() => {
  unmounted = true;
  scope?.revert();
  resizeObserver?.disconnect();
  planetScene?.dispose();
  planetScene = undefined;
});
</script>

<template>
  <div ref="root" class="solar-wrap">
    <!-- Back layer: orbits and the sun -->
    <svg
      ref="back"
      class="solar"
      role="group"
      aria-label="Solar system navigation"
      :viewBox="viewBox"
      preserveAspectRatio="xMidYMid meet"
    >
      <g class="solar__orbits">
        <ellipse
          v-for="p in shownPlanets"
          :key="`orbit-${p.name}`"
          class="orbit"
          :class="{ 'orbit--featured': featured(p) }"
          :data-orbit="p.name"
          :data-dash="dashFor(p)"
          cx="0"
          cy="0"
          :rx="p.orbit.rx"
          :ry="p.orbit.ry"
          fill="none"
          :stroke-dasharray="dashFor(p)"
        />
      </g>

      <!-- Sun: RESULTS -->
      <a class="sun" :href="`#${sun.path}`" :aria-label="`Go to ${sun.label}`">
        <g transform="rotate(45)">
          <rect class="sun__frame" x="-115" y="-115" width="230" height="230" fill="none" stroke-width="1" />
          <rect class="sun__frame" x="-135" y="-135" width="270" height="270" fill="none" stroke-width="1" />
          <rect class="sun__frame" x="-155" y="-155" width="310" height="310" fill="none" stroke-width="1" />
        </g>
        <circle class="sun__ticks" r="108" fill="none" stroke-width="6" stroke-dasharray="1 11" />
        <circle class="sun__pulse" r="92" fill="none" stroke-width="2" />
        <circle class="sun__disc" r="92" />
        <!-- Scaled down so the name keeps a clear margin inside the disc -->
        <g transform="scale(0.82)">
          <text class="label sun__code" x="0" y="-14" text-anchor="middle">{{ sun.code }}</text>
          <text class="headline sun__name" x="0" y="20" text-anchor="middle">{{ sun.label }}</text>
        </g>
      </a>

      <!-- Sun leader and its orange tag (desktop only) -->
      <g v-if="!narrow" class="sun__tag-group">
        <line class="leader" x1="0" y1="-116" x2="0" y2="-164" stroke-width="1" />
        <rect class="sun__tag" :x="-labelWidth(sunLabel) / 2" y="-175" :width="labelWidth(sunLabel)" height="22" />
        <text class="label sun__tag-text" x="0" y="-164" text-anchor="middle" dominant-baseline="central">{{ sunLabel }}</text>
      </g>
    </svg>

    <!-- Middle layer: 3D planets -->
    <canvas v-show="webgl" ref="canvas" class="solar__canvas" aria-hidden="true" />

    <!-- Front layer: planet links, leaders and labels -->
    <svg class="solar solar--front" :viewBox="viewBox" preserveAspectRatio="xMidYMid meet" aria-hidden="false">
      <defs>
        <clipPath v-for="p in shownPlanets" :id="`clip-${p.name}`" :key="`clip-${p.name}`">
          <circle :r="R" />
        </clipPath>
      </defs>
      <g
        v-for="p in shownPlanets"
        :key="p.name"
        class="body"
        :transform="`translate(${p.orbit.x} ${p.orbit.y})`"
      >
        <a
          class="planet"
          :class="{ 'planet--featured': featured(p) }"
          :data-body="p.name"
          :href="`#${p.path}`"
          :aria-label="`Go to ${p.label}`"
        >
          <!-- Larger invisible target so a planet is a reasonable touch target (about 44px on phones) -->
          <circle class="planet__hit" :r="HIT_R" fill="transparent" />
          <g v-if="!webgl" class="planet__body">
            <circle class="planet__disc" :r="R" stroke-width="2" />
            <g :transform="`rotate(${p.orbit.tilt})`" :clip-path="`url(#clip-${p.name})`">
              <line
                v-for="(y, i) in parallelOffsets(p.orbit.parallels)"
                :key="`par-${i}`"
                class="planet__parallel"
                :x1="-R"
                :x2="R"
                :y1="y"
                :y2="y"
                stroke-width="1"
              />
              <ellipse
                v-for="m in meridians"
                :key="`mer-${m.k}`"
                class="planet__meridian"
                cx="0"
                cy="0"
                :rx="m.rx"
                :ry="R"
                fill="none"
                stroke-width="1"
              />
            </g>
          </g>
          <circle v-if="featured(p)" class="planet__ring" :r="R + 5" fill="none" />
          <circle class="planet__focus" :r="R + 10" fill="none" stroke-width="2" />
          <template v-if="!narrow">
            <line class="leader" x1="0" :y1="-(R + 8)" :x2="0" :y2="-80 - lift(p)" />
            <rect class="leader__cap" x="-2" :y="-82 - lift(p)" width="4" height="4" />
            <g class="planet__tag" :transform="`translate(0 ${-lift(p)})`">
              <rect :x="-labelWidth(`${p.code} / ${p.label}`) / 2" y="-105" :width="labelWidth(`${p.code} / ${p.label}`)" height="22" />
              <text class="label" x="0" y="-94" text-anchor="middle" dominant-baseline="central">{{ p.code }} / {{ p.label }}</text>
            </g>
          </template>
        </a>
      </g>
    </svg>
  </div>
</template>

<style lang="scss" scoped>
// Shapes are flat: stroke and fill come from tokens only. Hover and focus change state instantly.
.solar-wrap {
  position: relative;
}

.solar__canvas,
.solar--front {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.solar__canvas {
  pointer-events: none;
}

// Only the planet links take pointer events; the rest of the front layer lets clicks through to the sun.
.solar--front {
  pointer-events: none;

  .planet {
    pointer-events: auto;
  }
}

.solar {
  width: 100%;
  height: calc(100dvh - var(--space-9));
  min-height: 480px;
  display: block;
  overflow: visible;
}

// Phones: the drawing keeps its aspect ratio instead of filling the viewport.
@media (max-width: 767px) {
  .solar {
    height: auto;
    min-height: 0;
    aspect-ratio: 840 / 480;
    overflow: hidden;
  }
}

// Rotations and scales pivot on each element's own centre.
.sun__frame,
.sun__ticks,
.sun__pulse,
.sun,
.planet__body {
  transform-box: fill-box;
  transform-origin: center;
}

.orbit {
  stroke: var(--line);
  stroke-width: var(--stroke-line);
}

.orbit--featured {
  stroke: var(--graphite);
}

.solar-wrap:has([data-body="challenge"]:hover) [data-orbit="challenge"],
.solar-wrap:has([data-body="how-it-works"]:hover) [data-orbit="how-it-works"],
.solar-wrap:has([data-body="algorithm"]:hover) [data-orbit="algorithm"],
.solar-wrap:has([data-body="data"]:hover) [data-orbit="data"],
.solar-wrap:has([data-body="about"]:hover) [data-orbit="about"],
.solar-wrap:has([data-body="challenge"]:focus-visible) [data-orbit="challenge"],
.solar-wrap:has([data-body="how-it-works"]:focus-visible) [data-orbit="how-it-works"],
.solar-wrap:has([data-body="algorithm"]:focus-visible) [data-orbit="algorithm"],
.solar-wrap:has([data-body="data"]:focus-visible) [data-orbit="data"],
.solar-wrap:has([data-body="about"]:focus-visible) [data-orbit="about"] {
  stroke: var(--ink);
}

.sun {
  cursor: pointer;
  outline: none;
  text-decoration: none;
}

.sun__frame {
  stroke: var(--line);
}

.sun__ticks {
  stroke: var(--graphite);
}

.sun__pulse {
  stroke: var(--signal);
}

.sun__disc {
  fill: var(--signal);
}

.sun__code,
.sun__name {
  fill: var(--on-signal);
}

.sun__tag {
  fill: var(--signal);
}

.sun__tag-text {
  fill: var(--on-signal);
}

.sun:hover .sun__frame,
.sun:focus-visible .sun__frame {
  stroke: var(--ink);
}

.sun:focus-visible .sun__disc {
  stroke: var(--focus);
  stroke-width: var(--stroke-line);
}

.leader {
  stroke: var(--line);
  stroke-width: var(--stroke-hairline);
}

.planet--featured .leader {
  stroke: var(--graphite);
  stroke-width: var(--stroke-line);
}

.planet__ring {
  stroke: var(--signal);
  stroke-width: var(--stroke-line);
}

.planet {
  cursor: pointer;
  outline: none;
  text-decoration: none;
}

.planet__disc {
  fill: var(--surface-raised);
  stroke: var(--line);
}

.planet__parallel,
.planet__meridian {
  stroke: var(--graphite);
}

.planet__tag rect {
  fill: var(--surface);
}

.planet__tag text {
  fill: var(--ink);
}

.planet__focus {
  stroke: var(--focus);
  opacity: 0;
}

.leader__cap {
  fill: var(--line);
}

.planet:hover .planet__disc,
.planet:focus-visible .planet__disc {
  stroke: var(--ink);
}

.planet:hover .leader,
.planet:focus-visible .leader,
.planet:hover .leader__cap,
.planet:focus-visible .leader__cap {
  stroke: var(--ink);
  fill: var(--ink);
}

.planet:hover .planet__tag rect,
.planet:focus-visible .planet__tag rect {
  fill: var(--ink);
}

.planet:hover .planet__tag text,
.planet:focus-visible .planet__tag text {
  fill: var(--surface);
}

.planet:focus-visible .planet__focus {
  opacity: 1;
}

.sun:hover ~ .sun__tag-group .sun__tag,
.sun:focus-visible ~ .sun__tag-group .sun__tag {
  fill: var(--ink);
}

.sun:hover ~ .sun__tag-group .sun__tag-text,
.sun:focus-visible ~ .sun__tag-group .sun__tag-text {
  fill: var(--surface);
}
</style>

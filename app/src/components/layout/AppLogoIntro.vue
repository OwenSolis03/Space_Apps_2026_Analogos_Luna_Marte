<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, useId } from "vue";
import { createTimeline, utils } from "animejs";
import { EARTH_DOTS } from "./earthDots";
import { useReducedMotion } from "@/composables/useReducedMotion";

const props = withDefaults(
  defineProps<{
    targetSelector?: string;
  }>(),
  {
    targetSelector: "#home-resting-logo",
  },
);

const emit = defineEmits<{
  (e: "complete"): void;
}>();

const uid = useId();
const reduced = useReducedMotion();

const overlayRef = ref<HTMLDivElement | null>(null);
const stageRef = ref<HTMLDivElement | null>(null);
const iconRef = ref<SVGSVGElement | null>(null);
const ringRef = ref<SVGCircleElement | null>(null);
const markerRef = ref<SVGRectElement | null>(null);
const ticksRef = ref<SVGPathElement | null>(null);
const baseRef = ref<SVGCircleElement | null>(null);
const patternRef = ref<SVGRectElement | null>(null);
const landRef = ref<SVGPathElement | null>(null);
const moonRef = ref<SVGGElement | null>(null);
const marsRef = ref<SVGGElement | null>(null);
const barRef = ref<HTMLDivElement | null>(null);
const nameRef = ref<HTMLDivElement | null>(null);
const dotsGroupRef = ref<SVGGElement | null>(null);

let mainTl: any = null;
let dockTl: any = null;
let isFinished = false;

function skip() {
  if (isFinished) return;
  isFinished = true;
  if (mainTl) {
    try {
      mainTl.revert();
    } catch {}
  }
  if (dockTl) {
    try {
      dockTl.revert();
    } catch {}
  }
  emit("complete");
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === "Escape" || e.key === " " || e.key === "Enter") {
    skip();
  }
}

function dockToTarget() {
  if (isFinished) return;
  isFinished = true;

  if (props.targetSelector) {
    const targetEl = document.querySelector(props.targetSelector) as HTMLElement | null;
    if (targetEl && stageRef.value && overlayRef.value) {
      const tRect = targetEl.getBoundingClientRect();
      const sRect = stageRef.value.getBoundingClientRect();

      if (tRect.width > 0 && tRect.height > 0 && sRect.width > 0 && sRect.height > 0) {
        const scale = tRect.width / sRect.width;
        const tCenterX = tRect.left + tRect.width / 2;
        const tCenterY = tRect.top + tRect.height / 2;
        const sCenterX = sRect.left + sRect.width / 2;
        const sCenterY = sRect.top + sRect.height / 2;

        const dx = tCenterX - sCenterX;
        const dy = tCenterY - sCenterY;

        dockTl = createTimeline({
          onComplete: () => {
            emit("complete");
          },
        });

        dockTl.add(
          stageRef.value,
          {
            translateX: dx,
            translateY: dy,
            scale: scale,
            duration: 650,
            ease: "inOutQuart",
          },
          0,
        );

        dockTl.add(
          overlayRef.value,
          {
            opacity: 0,
            duration: 600,
            ease: "linear",
          },
          50,
        );

        return;
      }
    }
  }

  // Fallback if target element not ready or unmeasured
  if (overlayRef.value) {
    dockTl = createTimeline({
      onComplete: () => emit("complete"),
    }).add(overlayRef.value, {
      opacity: 0,
      duration: 400,
      ease: "linear",
    });
  } else {
    emit("complete");
  }
}

onMounted(() => {
  if (reduced.value) {
    emit("complete");
    return;
  }

  window.addEventListener("keydown", handleKeyDown);

  const stage = stageRef.value;
  const icon = iconRef.value;
  const ring = ringRef.value;
  const marker = markerRef.value;
  const ticks = ticksRef.value;
  const base = baseRef.value;
  const pattern = patternRef.value;
  const land = landRef.value;
  const moon = moonRef.value;
  const mars = marsRef.value;
  const bar = barRef.value;
  const name = nameRef.value;
  const dotsGroup = dotsGroupRef.value;

  if (
    !stage ||
    !icon ||
    !ring ||
    !marker ||
    !ticks ||
    !base ||
    !pattern ||
    !land ||
    !moon ||
    !mars ||
    !bar ||
    !name ||
    !dotsGroup
  ) {
    emit("complete");
    return;
  }

  const dots = Array.from(dotsGroup.querySelectorAll("rect"));

  // Initial state setup
  const C = 2 * Math.PI * 128;
  ring.style.strokeDasharray = String(C);
  ring.style.transformBox = "fill-box";
  ring.style.transformOrigin = "center";
  ring.style.transform = "rotate(-90deg)";
  utils.set(ring, { strokeDashoffset: C });
  utils.set([marker, ticks, base, pattern, land, moon, mars, bar, name], { opacity: 0 });
  utils.set(dots, { opacity: 0 });

  const off = dots.map(() => {
    const a = Math.random() * Math.PI * 2;
    const rx = 360 + Math.random() * 520;
    const ry = 160 + Math.random() * 220;
    return [Math.cos(a) * rx, Math.sin(a) * ry];
  });
  const lag = dots.map(() => Math.random() * 260);

  const startAnimation = () => {
    if (isFinished) return;

    // Center icon in the stage before typography enters
    const iconRect = icon.getBoundingClientRect();
    const stageRect = stage.getBoundingClientRect();
    const shift = stageRect.width / 2 - (iconRect.left - stageRect.left + iconRect.width / 2);
    (utils as any).set(icon, { translateX: shift });

    const tl: any = createTimeline({
      defaults: { ease: "outQuart" },
      onComplete: () => {
        dockToTarget();
      },
    });
    mainTl = tl;

    // 1 · Earth formation from star dots
    tl.add(
      dots,
      {
        translateX: { from: (_el: any, i: number) => off[i][0], to: 0 },
        translateY: { from: (_el: any, i: number) => off[i][1], to: 0 },
        opacity: { from: 0, to: 1, duration: 260, ease: "linear" },
        duration: 800,
        delay: (_el: any, i: number) => lag[i],
      },
      0,
    );
    tl.add(base, { opacity: { from: 0, to: 1 }, duration: 420, ease: "linear" }, 650);
    tl.add(pattern, { opacity: { from: 0, to: 1 }, duration: 240, ease: "linear" }, 940);
    tl.add(dots, { opacity: { from: 1, to: 0 }, duration: 240, ease: "linear" }, 960);
    tl.add(land, { opacity: { from: 0, to: 1 }, duration: 520, ease: "inOutQuad" }, 1000);

    // Orbit: starts at orange marker and draws around
    tl.add(marker, { opacity: { from: 0, to: 1 }, scale: { from: 0.2, to: 1 }, duration: 380 }, 820);
    tl.add(ring, { strokeDashoffset: { from: C, to: 0 }, duration: 800, ease: "inOutQuad" }, 900);
    tl.add(ticks, { opacity: { from: 0, to: 1 }, duration: 300, ease: "linear" }, 1500);

    // 2 · Mars enters from the left
    tl.add(
      mars,
      {
        translateX: { from: -1150, to: 0 },
        scale: { from: 0.6, to: 1 },
        opacity: { from: 0, to: 1, duration: 200, ease: "linear" },
        duration: 800,
      },
      1100,
    );

    // 3 · Moon enters from the left
    tl.add(
      moon,
      {
        translateX: { from: -900, to: 0 },
        scale: { from: 0.6, to: 1 },
        opacity: { from: 0, to: 1, duration: 200, ease: "linear" },
        duration: 800,
      },
      1650,
    );

    // 4 · Icon slides left to final position and name appears
    tl.add(icon, { translateX: { from: shift, to: 0 }, duration: 750, ease: "inOutQuart" }, 2150);
    tl.add(
      bar,
      {
        opacity: { from: 0, to: 1, duration: 150, ease: "linear" },
        clipPath: { from: "inset(0% 100% 0% 0%)", to: "inset(0% 0% 0% 0%)" },
        duration: 450,
        ease: "outCubic",
      },
      2250,
    );
    tl.add(
      name,
      {
        opacity: { from: 0, to: 1, duration: 300, ease: "linear" },
        translateX: { from: -22, to: 0 },
        clipPath: { from: "inset(-20% 100% -20% 0%)", to: "inset(-20% -6% -20% 0%)" },
        duration: 700,
        ease: "outQuart",
      },
      2350,
    );
  };

  const fontsReady = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
  Promise.race([fontsReady, new Promise((r) => setTimeout(r, 400))]).then(startAnimation);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleKeyDown);
  if (mainTl) {
    try {
      mainTl.revert();
    } catch {}
  }
  if (dockTl) {
    try {
      dockTl.revert();
    } catch {}
  }
});
</script>

<template>
  <div
    ref="overlayRef"
    class="logo-intro"
    role="dialog"
    aria-label="PROTOTERRA Animation"
    @click="skip"
  >
    <div
      ref="stageRef"
      class="logo-intro__stage"
      role="img"
      aria-label="PROTOTERRA: imagotipo con la Luna y Marte delante de la Tierra"
    >
      <svg
        ref="iconRef"
        class="logo-intro__icon"
        viewBox="0 -32 560 304"
        aria-hidden="true"
      >
        <defs>
          <pattern :id="`ih-odots-${uid}`" width="16" height="16" patternUnits="userSpaceOnUse" x="6" y="6">
            <rect width="4" height="4" fill="#5f95c6" />
          </pattern>
          <pattern :id="`ih-mdots-${uid}`" width="16" height="16" patternUnits="userSpaceOnUse" x="6" y="6">
            <rect width="4" height="4" fill="#716f70" />
          </pattern>
          <pattern :id="`ih-hatch-${uid}`" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="3" height="12" fill="#8c3418" />
          </pattern>
          <clipPath :id="`ih-earth-${uid}`">
            <circle cx="280" cy="120" r="104" />
          </clipPath>
        </defs>

        <!-- Orbit Ring -->
        <circle ref="ringRef" cx="280" cy="120" r="128" fill="none" stroke="#716f70" stroke-width="1.5" />
        <rect ref="markerRef" x="276" y="-12" width="8" height="8" fill="#ff8500" />
        <path ref="ticksRef" d="M280 236 L280 241 M280 247 L280 252 M272 244 L277 244 M283 244 L288 244" stroke="#716f70" stroke-width="1.5" fill="none" />

        <!-- Earth Base & Pattern -->
        <circle ref="baseRef" cx="280" cy="120" r="104" fill="#3f7cb5" />
        <rect ref="patternRef" x="176" y="16" width="208" height="208" :fill="`url(#ih-odots-${uid})`" :clip-path="`url(#ih-earth-${uid})`" />

        <!-- Star Dots -->
        <g ref="dotsGroupRef" fill="#5f95c6" aria-hidden="true">
          <rect v-for="(p, i) in EARTH_DOTS" :key="i" :x="p.x" :y="p.y" width="4" height="4" />
        </g>

        <!-- Continents (Land) -->
        <path
          ref="landRef"
          d="M232 22 L300 18 L318 34 L300 48 L292 62 L280 70 L272 84 L262 96 L268 104 L276 118 L284 128 L296 132 L318 140 L330 152 L326 172 L312 190 L302 210 L296 224 L290 214 L288 190 L282 168 L276 150 L270 138 L262 124 L254 110 L246 96 L236 78 L226 60 L220 40 Z"
          fill="#3f8f4f"
          :clip-path="`url(#ih-earth-${uid})`"
        />

        <!-- Moon -->
        <g ref="moonRef" style="transform-box: fill-box; transform-origin: center">
          <circle cx="152" cy="120" r="110" class="logo-intro__halo" />
          <circle cx="152" cy="120" r="104" fill="#8f8d8e" />
          <circle cx="152" cy="120" r="102" :fill="`url(#ih-mdots-${uid})`" />
        </g>

        <!-- Mars -->
        <g ref="marsRef" style="transform-box: fill-box; transform-origin: center">
          <circle cx="408" cy="120" r="110" class="logo-intro__halo" />
          <circle cx="408" cy="120" r="104" fill="#a8401f" />
          <circle cx="408" cy="120" r="102" :fill="`url(#ih-hatch-${uid})`" />
        </g>
      </svg>

      <div ref="barRef" class="logo-intro__bar" />
      <div ref="nameRef" class="logo-intro__name">
        <p class="logo-intro__name-text">PROTOTERRA</p>
      </div>
    </div>

    <button
      class="logo-intro__skip label"
      type="button"
      @click.stop="skip"
    >
      SKIP [ESC]
    </button>
  </div>
</template>

<style lang="scss" scoped>
.logo-intro {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: var(--surface, #dfdfdf);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
}

.logo-intro__stage {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: clamp(10px, 1.5vw, 24px);
  position: relative;
  transform-origin: center center;
  pointer-events: none;
  max-width: min(94vw, 1100px);
}

.logo-intro__icon {
  width: clamp(240px, 32vw, 400px);
  height: auto;
  overflow: visible;
  flex-shrink: 0;
}

.logo-intro__halo {
  fill: var(--surface, #dfdfdf);
}

.logo-intro__bar {
  width: clamp(3px, 0.4vw, 4px);
  height: clamp(48px, 6vw, 64px);
  background: var(--signal, #ff8500);
  border-radius: 0;
  flex-shrink: 0;
}

.logo-intro__name {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.logo-intro__name-text {
  margin: 0;
  font-family: var(--font-display, "Martian Mono", monospace);
  font-size: clamp(36px, 5vw, 64px);
  line-height: 1;
  font-weight: 300;
  letter-spacing: 0.12em;
  color: var(--ink, #121212);
  white-space: nowrap;
}

.logo-intro__skip {
  position: absolute;
  bottom: var(--space-6, 32px);
  right: var(--space-6, 32px);
  background: transparent;
  border: var(--stroke-hairline) solid var(--line-faint, #bfbfbf);
  color: var(--ink-muted, #716f70);
  padding: 6px 12px;
  font-size: 11px;
  letter-spacing: 0.14em;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    color: var(--ink, #121212);
    border-color: var(--ink, #121212);
    background: var(--surface-raised, #ffffff);
  }
}
</style>

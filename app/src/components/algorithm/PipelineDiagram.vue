<script setup lang="ts">
// Static map of the pipeline stages. Each box links to the step that explains it.
// Boxes are chamfered (top right) and joined by straight rules.

interface Box {
  id: string;
  x: number;
  y: number;
  title: string;
  sub: string;
  href: string;
}

const W = 200;
const H = 68;
const C = 16; // chamfer in user units (matches --chamfer-md)

const boxes: Box[] = [
  { id: "t3", x: 0, y: 0, title: "T3 · GRID", sub: "32 KM PATCHES", href: "#step-01" },
  { id: "t4", x: 260, y: 0, title: "T4 · TARGETS", sub: "16 CURATED + 30 ARCHETYPES", href: "#step-04" },
  { id: "t6", x: 0, y: 110, title: "T6 · EARTH LAYERS", sub: "NDVI · LST · ROADS", href: "#step-07" },
  { id: "t5", x: 260, y: 110, title: "T5 · EARTH", sub: "BARE GROUND ONLY", href: "#step-05" },
  { id: "t12", x: 0, y: 220, title: "T12 · T13 · T14", sub: "LAYER STAGES", href: "#step-07" },
  { id: "t7", x: 520, y: 110, title: "T7 · MATCHING", sub: "7 DIMENSIONS · MSI", href: "#step-08" },
  { id: "t8", x: 780, y: 110, title: "T8 · EXPORT", sub: "JSON EXPORT", href: "#step-11" },
  { id: "app", x: 1040, y: 110, title: "APP", sub: "RESULTS · DATA", href: "#step-11" },
];

const byId = (id: string) => boxes.find((b) => b.id === id)!;

/** Chamfered rectangle as a polygon (top-right corner cut). */
const outline = (b: Box) =>
  [
    [b.x, b.y],
    [b.x + W - C, b.y],
    [b.x + W, b.y + C],
    [b.x + W, b.y + H],
    [b.x, b.y + H],
  ]
    .map((p) => p.join(","))
    .join(" ");

// Straight rules between boxes (from → to), drawn in the middle of the connecting edge.
const links: [string, string, "h" | "v"][] = [
  ["t3", "t4", "h"],
  ["t6", "t5", "h"],
  ["t5", "t7", "h"],
  ["t7", "t8", "h"],
  ["t8", "app", "h"],
];

const edge = (from: string, to: string) => {
  const a = byId(from);
  const b = byId(to);
  const y = a.y + H / 2;
  const x1 = a.x + W;
  const x2 = b.x;
  return { x1, y1: y, x2, y2: y };
};
</script>

<template>
  <figure class="pipeline">
    <svg
      class="pipeline__svg"
      role="img"
      aria-label="Pipeline stages: grid, targets, Earth layers, Earth bare ground, extra layers, matching, export and the app"
      viewBox="0 0 1240 290"
      preserveAspectRatio="xMinYMin meet"
    >
      <g class="pipeline__links">
        <line
          v-for="[from, to] in links"
          :key="`${from}-${to}`"
          :x1="edge(from, to).x1"
          :y1="edge(from, to).y1"
          :x2="edge(from, to).x2"
          :y2="edge(from, to).y2"
        />
      </g>
      <a v-for="b in boxes" :key="b.id" :href="b.href" class="pipeline__box">
        <polygon :points="outline(b)" />
        <text class="label pipeline__title" :x="b.x + 16" :y="b.y + 26">{{ b.title }}</text>
        <text class="label pipeline__sub" :x="b.x + 16" :y="b.y + 48">{{ b.sub }}</text>
      </a>
    </svg>
    <figcaption class="footnote">
      Adapted from the pipeline section of the README. Each box links to the step that explains it.
    </figcaption>
  </figure>
</template>

<style lang="scss" scoped>
.pipeline {
  margin: 0;
  min-width: 0;
  padding: var(--space-4);
  background: var(--surface-raised);
  border: var(--stroke-hairline) solid var(--line-faint);
}

.pipeline__svg {
  width: 100%;
  height: auto;
  min-width: 720px;
}

.pipeline__links line {
  stroke: var(--line);
  stroke-width: var(--stroke-line);
}

.pipeline__box polygon {
  fill: var(--surface);
  stroke: var(--line);
  stroke-width: var(--stroke-line);
}

.pipeline__box:hover polygon,
.pipeline__box:focus-visible polygon {
  stroke: var(--ink);
  fill: var(--surface-raised);
}

.pipeline__box:focus-visible {
  outline: none;
}

.pipeline__title {
  fill: var(--ink);
}

.pipeline__sub {
  fill: var(--ink-muted);
}

.pipeline {
  overflow-x: auto;
}
</style>

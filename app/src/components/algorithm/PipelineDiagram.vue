<script setup lang="ts">
// Static map of the pipeline stages. Boxes are chamfered (top right), sized to their text,
// and joined by straight rules. They are not interactive.

interface BoxDef {
  id: string;
  row: number;
  col: number;
  title: string;
  sub: string;
}

interface Box extends BoxDef {
  x: number;
  y: number;
  w: number;
}

const H = 68;
const C = 16; // chamfer in user units (matches --chamfer-md)
const GAP_X = 56;
const ROW_Y = 110;
const PAD = 16;
// Label style: 11px Martian Mono with 0.1em tracking, measured at 8.8 units per character.
const CHAR_W = 8.8;

const defs: BoxDef[] = [
  { id: "t3", row: 0, col: 0, title: "T3 · GRID", sub: "32 KM PATCHES" },
  { id: "t4", row: 0, col: 1, title: "T4 · TARGETS", sub: "16 CURATED + 30 ARCHETYPES" },
  { id: "t6", row: 1, col: 0, title: "T6 · EARTH LAYERS", sub: "NDVI · LST · ROADS" },
  { id: "t5", row: 1, col: 1, title: "T5 · EARTH", sub: "BARE GROUND ONLY" },
  { id: "t12", row: 2, col: 0, title: "T12 · T13 · T14", sub: "LAYER STAGES" },
  { id: "t7", row: 1, col: 2, title: "T7 · MATCHING", sub: "SEVEN DIMENSIONS · MSI" },
  { id: "t8", row: 1, col: 3, title: "T8 · EXPORT", sub: "analogs_universe.json" },
  { id: "app", row: 1, col: 4, title: "APP", sub: "RESULTS · DATA" },
];

const textW = (d: BoxDef) => Math.ceil(Math.max(d.title.length, d.sub.length) * CHAR_W) + PAD * 2 + C / 2;

// Every column is as wide as its widest box, so boxes in a column line up and nothing overflows.
const cols = Math.max(...defs.map((d) => d.col)) + 1;
const colW = Array.from({ length: cols }, (_, c) => Math.max(...defs.filter((d) => d.col === c).map(textW)));
const colX = colW.map((_, c) => colW.slice(0, c).reduce((s, w) => s + w + GAP_X, 0));

const boxes: Box[] = defs.map((d) => ({ ...d, x: colX[d.col]!, y: d.row * ROW_Y, w: colW[d.col]! }));
const viewW = colX[cols - 1]! + colW[cols - 1]!;
const viewH = 2 * ROW_Y + H;
const byId = (id: string) => boxes.find((b) => b.id === id)!;

/** Chamfered rectangle as a polygon (top-right corner cut). */
const outline = (b: Box) =>
  [
    [b.x, b.y],
    [b.x + b.w - C, b.y],
    [b.x + b.w, b.y + C],
    [b.x + b.w, b.y + H],
    [b.x, b.y + H],
  ]
    .map((p) => p.join(","))
    .join(" ");

// Straight rules between boxes on the same row.
const links: [string, string][] = [
  ["t3", "t4"],
  ["t6", "t5"],
  ["t5", "t7"],
  ["t7", "t8"],
  ["t8", "app"],
];

const edge = (from: string, to: string) => {
  const a = byId(from);
  const b = byId(to);
  const y = a.y + H / 2;
  return { x1: a.x + a.w, y1: y, x2: b.x, y2: y };
};
</script>

<template>
  <figure class="pipeline">
    <svg
      class="pipeline__svg"
      role="img"
      aria-label="Pipeline stages: grid, targets, Earth layers, Earth bare ground, extra layers, matching, export and the app"
      :viewBox="`-2 -2 ${viewW + 4} ${viewH + 4}`"
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
      <g v-for="b in boxes" :key="b.id" class="pipeline__box">
        <polygon :points="outline(b)" />
        <text class="label pipeline__title" :x="b.x + PAD" :y="b.y + 26">{{ b.title }}</text>
        <text class="label pipeline__sub" :x="b.x + PAD" :y="b.y + 48">{{ b.sub }}</text>
      </g>
    </svg>
    <figcaption class="footnote">Adapted from the pipeline section of the README.</figcaption>
  </figure>
</template>

<style lang="scss" scoped>
.pipeline {
  margin: 0;
  min-width: 0;
  padding: var(--space-4);
  background: var(--surface-raised);
  border: var(--stroke-hairline) solid var(--line-faint);
  overflow-x: auto;
}

.pipeline__svg {
  width: 100%;
  height: auto;
  min-width: 760px;
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

.pipeline__title {
  fill: var(--ink);
}

.pipeline__sub {
  fill: var(--ink-muted);
  text-transform: none;
}
</style>

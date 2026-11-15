<script setup lang="ts">
// RETÍCULA Glyph: instrument marks on a 24-unit grid. Port of components/bundle.js (Glyph).
import { computed } from "vue";

export type GlyphName =
  | "plus" | "close" | "tick-left" | "tick-right" | "bracket" | "corner"
  | "slash" | "slash-pair" | "chevron-down" | "chevron-right" | "dots" | "dot";

interface GlyphDef {
  p?: string[];
  r?: number[][];
  w?: number;
}

const GLYPHS: Record<GlyphName, GlyphDef> = {
  plus: { p: ["M12 3V9M12 15V21M3 12H9M15 12H21"], w: 1.5 },
  close: { p: ["M6 6L10 10M14 14L18 18M18 6L14 10M10 14L6 18"], w: 1.5 },
  "tick-left": { p: ["M5 3V21M5 12H20"], w: 1.5 },
  "tick-right": { p: ["M19 3V21M19 12H4"], w: 1.5 },
  bracket: { p: ["M3 9V3H9M15 3H21V9M21 15V21H15M9 21H3V15"], w: 2 },
  corner: { p: ["M4 21V9L9 4H21"], w: 1.5 },
  slash: { p: ["M4 20L20 4"], w: 3.5 },
  "slash-pair": { p: ["M2 16L14 4M10 20L22 8"], w: 3.5 },
  "chevron-down": { p: ["M4 8L12 16L20 8"], w: 3 },
  "chevron-right": { p: ["M8 4L16 12L8 20"], w: 3 },
  dots: { r: [[3, 11, 2], [11, 11, 2], [19, 11, 2]] },
  dot: { r: [[10, 10, 4]] },
};

const props = withDefaults(
  defineProps<{
    name: GlyphName;
    size?: number;
    tone?: "ink" | "muted" | "graphite" | "signal";
    /** With a label the glyph is an image; without one it is decorative. */
    label?: string;
  }>(),
  { size: 24, tone: "ink", label: undefined },
);

const def = computed<GlyphDef>(() => GLYPHS[props.name] ?? GLYPHS.plus);
</script>

<template>
  <svg
    class="tm-glyph"
    :class="`tm-tone-${tone}`"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    :role="label ? 'img' : undefined"
    :aria-label="label"
    :aria-hidden="label ? undefined : 'true'"
    focusable="false"
  >
    <path
      v-for="(d, i) in def.p ?? []"
      :key="`p${i}`"
      :d="d"
      fill="none"
      stroke="currentColor"
      :stroke-width="def.w"
      stroke-linecap="butt"
      stroke-linejoin="miter"
    />
    <rect
      v-for="(r, i) in def.r ?? []"
      :key="`r${i}`"
      :x="r[0]"
      :y="r[1]"
      :width="r[2]"
      :height="r[2]"
      fill="currentColor"
    />
  </svg>
</template>

<style lang="scss" scoped>
.tm-glyph {
  display: inline-block;
  vertical-align: middle;
  flex: none;
}
</style>

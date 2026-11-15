<script setup lang="ts">
// RETÍCULA Button: rectangular action with uppercase text.
// Renders a router link with `to`, an external link with `href`, otherwise a <button>.
import { computed } from "vue";
import { RouterLink, type RouteLocationRaw } from "vue-router";
import RGlyph from "./RGlyph.vue";

const props = withDefaults(
  defineProps<{
    variant?: "primary" | "secondary";
    arrow?: boolean;
    disabled?: boolean;
    type?: "button" | "submit" | "reset";
    to?: RouteLocationRaw;
    href?: string;
  }>(),
  { variant: "primary", arrow: false, disabled: false, type: "button", to: undefined, href: undefined },
);

const classes = computed(() => ["tm-btn", `tm-btn--${props.variant}`, "tm-focusable"]);
</script>

<template>
  <RouterLink v-if="to" :to="to" :class="classes">
    <slot />
    <RGlyph v-if="arrow" name="chevron-right" :size="16" />
  </RouterLink>
  <a v-else-if="href" :href="href" target="_blank" rel="noreferrer" :class="classes">
    <slot />
    <RGlyph v-if="arrow" name="chevron-right" :size="16" />
  </a>
  <button v-else :type="type" :disabled="disabled" :class="classes">
    <slot />
    <RGlyph v-if="arrow" name="chevron-right" :size="16" />
  </button>
</template>

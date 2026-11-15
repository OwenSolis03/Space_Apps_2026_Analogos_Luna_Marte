<script setup lang="ts">
// RETÍCULA Headline: signal rule, kicker, display title, subtitle and byline.
// size lg = display-a, md = display-c, sm = headline.
withDefaults(
  defineProps<{
    title?: string;
    kicker?: string;
    subtitle?: string;
    by?: string;
    size?: "lg" | "md" | "sm";
    rule?: "signal" | "graphite";
    as?: "h1" | "h2" | "h3" | "h4";
  }>(),
  { title: "", kicker: undefined, subtitle: undefined, by: undefined, size: "md", rule: "signal", as: "h2" },
);

const sizeClass = { lg: "display-a", md: "display-c", sm: "headline" } as const;
</script>

<template>
  <header class="tm-headline">
    <span class="tm-headline__rule" :class="{ 'tm-headline__rule--graphite': rule === 'graphite' }" aria-hidden="true" />
    <p v-if="kicker" class="label tm-headline__kicker">{{ kicker }}</p>
    <component :is="as" class="tm-headline__title" :class="sizeClass[size]">
      <slot name="title">{{ title }}</slot>
    </component>
    <p v-if="subtitle" class="byline tm-headline__subtitle">{{ subtitle }}</p>
    <p v-if="by" class="byline tm-headline__by">{{ by }}</p>
  </header>
</template>

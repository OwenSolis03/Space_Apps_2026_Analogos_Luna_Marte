<script setup lang="ts">
// A figure from the analysis. Shown in full scientific color when the image exists; otherwise a pending frame.
import RFrame from "@/components/reticula/RFrame.vue";

const props = defineProps<{
  /** Path relative to the site root, for example "figures/map_targets_moon.png". */
  src?: string;
  caption: string;
  alt: string;
}>();

const url = (src: string) => `${import.meta.env.BASE_URL}${src}`;
</script>

<template>
  <figure class="figure">
    <img v-if="props.src" class="figure__img" :src="url(src ?? '')" :alt="alt" loading="lazy" />
    <RFrame v-else ratio="4 / 3" :caption="caption" :label="alt" />
    <figcaption v-if="props.src" class="footnote figure__caption">{{ caption }}</figcaption>
  </figure>
</template>

<style lang="scss" scoped>
.figure {
  margin: 0;
  min-width: 0;
  display: grid;
  gap: var(--space-2);
}

.figure__img {
  width: 100%;
  height: auto;
  border: var(--stroke-hairline) solid var(--line);
  display: block;
}
</style>

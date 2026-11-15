<script setup lang="ts">
// RETÍCULA Frame: placeholder for an image that is still pending. Cross-hatched box with a figure caption.
withDefaults(
  defineProps<{
    ratio?: string;
    caption?: string;
    /** Accessible description of the image that will go here. */
    label?: string;
  }>(),
  { ratio: "16 / 9", caption: undefined, label: "Pending image" },
);
</script>

<template>
  <figure class="tm-frame">
    <div class="tm-frame__box" role="img" :aria-label="label" :style="{ aspectRatio: ratio }">
      <svg class="tm-frame__x" viewBox="0 0 100 100" preserveAspectRatio="none" focusable="false" aria-hidden="true">
        <path d="M0 0L100 100M100 0L0 100" fill="none" stroke="currentColor" stroke-width="1" vector-effect="non-scaling-stroke" />
      </svg>
    </div>
    <figcaption v-if="caption" class="label tm-frame__caption">{{ caption }}</figcaption>
  </figure>
</template>

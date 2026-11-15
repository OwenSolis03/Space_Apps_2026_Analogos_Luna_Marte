<script setup lang="ts">
// RETÍCULA IconButton: circular icon-only button. `label` is required because there is no visible text.
import RGlyph, { type GlyphName } from "./RGlyph.vue";

withDefaults(
  defineProps<{
    label: string;
    glyph?: GlyphName;
    /** Active state: ring in --ink plus an orange tick mark. Leave undefined for a plain button. */
    pressed?: boolean;
    disabled?: boolean;
  }>(),
  { glyph: "plus", pressed: undefined, disabled: false },
);

defineEmits<{ click: [event: MouseEvent] }>();
</script>

<template>
  <span v-if="pressed" class="tm-ibtn-wrap">
    <button
      type="button"
      class="tm-ibtn tm-focusable"
      :aria-label="label"
      aria-pressed="true"
      :disabled="disabled"
      @click="$emit('click', $event)"
    >
      <RGlyph :name="glyph" :size="20" />
    </button>
    <RGlyph name="tick-left" :size="16" tone="signal" />
  </span>
  <button
    v-else
    type="button"
    class="tm-ibtn tm-focusable"
    :aria-label="label"
    :aria-pressed="pressed === undefined ? undefined : 'false'"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <RGlyph :name="glyph" :size="20" />
  </button>
</template>

<style lang="scss" scoped>
.tm-ibtn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  padding: 0;
  margin: 0;

  :deep(.tm-glyph),
  svg {
    display: block;
    margin: auto;
    flex: none;
  }
}

.tm-ibtn-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
</style>

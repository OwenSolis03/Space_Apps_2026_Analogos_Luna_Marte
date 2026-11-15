<script setup lang="ts">
// "What does X mean?" toggle. Sits next to a control's label, never inside the <label>.
import RGlyph from "@/components/reticula/RGlyph.vue";

const props = defineProps<{
  /** Unique id, e.g. "dim-topography". The panel it controls is `exp-<id>`. */
  id: string;
  /** Used in the accessible name, e.g. "Topography". */
  title: string;
  open: boolean;
}>();

defineEmits<{ toggle: [] }>();
</script>

<template>
  <button
    type="button"
    class="info-btn tm-focusable"
    :aria-expanded="open"
    :aria-controls="`exp-${props.id}`"
    :aria-label="`What does ${props.title} mean?`"
    @click="$emit('toggle')"
  >
    <RGlyph :name="open ? 'close' : 'plus'" :size="16" />
  </button>
</template>

<style lang="scss" scoped>
.info-btn {
  display: inline-grid;
  place-items: center;
  flex: none;
  width: 32px;
  height: 32px;
  padding: 0;
  border: var(--stroke-hairline) solid var(--line);
  background: transparent;
  color: var(--ink);
  cursor: pointer;

  &:hover,
  &[aria-expanded="true"] {
    border-color: var(--ink);
  }
}
</style>

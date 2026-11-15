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
    :class="{ 'is-open': open }"
    :aria-expanded="open"
    :aria-controls="`exp-${props.id}`"
    :aria-label="`What does ${props.title} mean?`"
    @click="$emit('toggle')"
  >
    <span class="info-btn__icon" :class="{ 'is-open': open }">
      <RGlyph name="plus" :size="16" />
    </span>
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
  transition: border-color 0.15s ease, background-color 0.15s ease;

  &:hover,
  &[aria-expanded="true"],
  &.is-open {
    border-color: var(--ink);
  }

  &[aria-expanded="true"],
  &.is-open {
    background: var(--surface-ghost);
  }
}

.info-btn__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  transition: transform 0.22s cubic-bezier(0.2, 0.8, 0.2, 1);
  transform-origin: center center;

  &.is-open {
    transform: rotate(45deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .info-btn__icon {
    transition: none;
  }
}
</style>

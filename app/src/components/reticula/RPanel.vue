<script setup lang="ts">
// RETÍCULA Panel: chamfered tile with optional label, note, big code and corner marks.
withDefaults(
  defineProps<{
    tone?: "raised" | "signal" | "tint" | "graphite" | "sunken" | "outline";
    chamfer?: boolean;
    label?: string;
    note?: string;
    code?: string;
    marks?: boolean;
  }>(),
  { tone: "raised", chamfer: true, label: undefined, note: undefined, code: undefined, marks: false },
);
</script>

<template>
  <section
    class="tm-panel"
    :class="[`tm-panel--${tone}`, { 'tm-panel--chamfer': chamfer }]"
  >
    <header v-if="label || note" class="tm-panel__head">
      <p v-if="label" class="label tm-panel__label">{{ label }}</p>
      <p v-if="note" class="label tm-panel__note">{{ note }}</p>
    </header>
    <div v-if="$slots.default" class="tm-panel__body">
      <slot />
    </div>
    <footer v-if="code || marks" class="tm-panel__foot">
      <p v-if="code" class="code tm-panel__code">{{ code }}</p>
      <span v-else />
      <svg
        v-if="marks"
        class="tm-panel__marks"
        width="36"
        height="20"
        viewBox="0 0 36 20"
        aria-hidden="true"
        focusable="false"
      >
        <rect x="0" y="0" width="4" height="4" fill="currentColor" />
        <rect x="16" y="0" width="4" height="4" fill="currentColor" />
        <rect x="0" y="16" width="4" height="4" fill="currentColor" />
        <rect x="32" y="16" width="4" height="4" fill="currentColor" />
      </svg>
    </footer>
  </section>
</template>

<script setup lang="ts">
// Site footer: project and team identity, event line, and the ornamental barcode.
import RBarcode from "@/components/reticula/RBarcode.vue";
import { REPOSITORY_URL } from "@/content/sections";
</script>

<template>
  <footer class="app-footer">
    <div class="page app-footer__inner">
      <div class="stack stack--tight">
        <p class="headline">ENDURANCE CXXV</p>
        <p class="label">FROM DATA TO ACTION</p>
      </div>
      <div class="stack stack--tight">
        <a class="label" :href="REPOSITORY_URL" target="_blank" rel="noreferrer">REPOSITORY</a>
        <p class="label">NASA SPACE APPS CHALLENGE 2026 · SONORA</p>
        <p class="label">COMPUTED ON YUCA · ACARUS · UNIVERSIDAD DE SONORA</p>
      </div>
      <RBarcode class="app-footer__barcode" tone="graphite" />
    </div>
  </footer>
</template>

<style lang="scss" scoped>
.app-footer {
  border-top: var(--stroke-hairline) solid var(--line);
  background: var(--surface);
}

.app-footer__inner {
  display: grid;
  gap: var(--space-6);
  padding-block: var(--space-7);
}

.app-footer__barcode {
  width: min(320px, 100%);
}

.app-footer a {
  color: var(--ink);
}

@media (min-width: 900px) {
  .app-footer__inner {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr);
    align-items: end;
  }
}
</style>

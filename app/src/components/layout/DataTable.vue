<script setup lang="ts">
// Plain data table in RETÍCULA style. Header cells use the label style; numbers align right (class "num").
defineProps<{
  /** Screen-reader caption that describes the table. */
  caption: string;
}>();
</script>

<template>
  <div class="data-table">
    <table class="dtable body">
      <caption class="sr-only">{{ caption }}</caption>
      <slot />
    </table>
  </div>
</template>

<style lang="scss" scoped>
.data-table {
  overflow-x: auto;
  min-width: 0;
}

.dtable {
  width: 100%;
  min-width: 36rem;
  border-collapse: collapse;

  :deep(th),
  :deep(td) {
    padding: var(--space-2) var(--space-3);
    border-bottom: var(--stroke-hairline) solid var(--line-faint);
    text-align: left;
    vertical-align: top;
  }

  :deep(th) {
    color: var(--ink-muted);
    font-weight: 500;
  }

  :deep(.num) {
    text-align: right;
    white-space: nowrap;
  }
}
</style>

<script setup lang="ts">
// Hero of every page except Home: the only display-a of the view, with an optional aside (a Readout).
import RHeadline from "@/components/reticula/RHeadline.vue";

defineProps<{
  code: string;
  title: string;
  subtitle?: string;
}>();
</script>

<template>
  <section class="page-hero">
    <div class="page-hero__grid">
      <RHeadline size="lg" as="h1" :kicker="code" :title="title" :subtitle="subtitle" />
      <div v-if="$slots.aside" class="page-hero__aside">
        <slot name="aside" />
      </div>
    </div>
  </section>
</template>

<style lang="scss" scoped>
// The title can be wide (display-a), so the headline gets more room than the aside.
.page-hero__grid {
  display: grid;
  gap: var(--space-7);
  align-items: end;
}

@media (min-width: 900px) {
  .page-hero__grid {
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  }
}

.page-hero__aside {
  min-width: 0;
}
</style>

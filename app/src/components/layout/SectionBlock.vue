<script setup lang="ts">
// A titled block inside a view. Each block is an anchor target (#id) and uses a display-c heading.
import RHeadline from "@/components/reticula/RHeadline.vue";

defineProps<{
  id: string;
  code: string;
  title: string;
  subtitle?: string;
}>();
</script>

<template>
  <section :id="id" class="section">
    <RHeadline size="md" as="h2" :kicker="code" :title="title" :subtitle="subtitle" />
    <div class="section__body">
      <slot />
    </div>
  </section>
</template>

<style lang="scss" scoped>
.section__body {
  margin-top: var(--space-6);
}
</style>

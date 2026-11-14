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
    <div class="columns">
      <RHeadline size="lg" as="h1" :kicker="code" :title="title" :subtitle="subtitle" />
      <div v-if="$slots.aside" class="page-hero__aside">
        <slot name="aside" />
      </div>
    </div>
  </section>
</template>

<style lang="scss" scoped>
.page-hero__aside {
  align-self: end;
}
</style>

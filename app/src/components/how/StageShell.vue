<script setup lang="ts">
// One stage of How It Works: text on the left (narrow column), its animated figure on the right.
import RHeadline from "@/components/reticula/RHeadline.vue";

defineProps<{
  id: string;
  code: string;
  title: string;
  lead: string;
  body: string[];
}>();
</script>

<template>
  <section :id="id" class="stage" :aria-labelledby="`${id}-title`">
    <div class="stage__text">
      <p class="label stage__code">{{ code }}</p>
      <RHeadline size="md" as="h2" :title="title" />
      <p class="lead">{{ lead }}</p>
      <p v-for="(p, i) in body" :key="i" class="body">{{ p }}</p>
    </div>
    <div class="stage__figure">
      <slot />
    </div>
  </section>
</template>

<style lang="scss" scoped>
.stage {
  display: grid;
  gap: var(--space-6);
  align-items: center;
  min-height: 80dvh;
  padding-block: var(--space-8);
  border-bottom: var(--stroke-hairline) solid var(--line-faint);

  @media (min-width: 900px) {
    grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
    gap: var(--space-8);
  }
}

.stage__text {
  display: grid;
  gap: var(--space-4);
  max-width: 40ch;
  align-content: center;

  p {
    margin: 0;
  }
}

.stage__code {
  color: var(--ink-muted);
}

.stage__figure {
  min-width: 0;
}
</style>

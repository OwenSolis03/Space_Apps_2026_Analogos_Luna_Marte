<script setup lang="ts">
// RETÍCULA Readout: label/value pairs in mini mono, rendered as a description list.
import RTag from "./RTag.vue";

export interface ReadoutItem {
  label: string;
  value: string;
  /** Render the value as a Tag (status) instead of plain text. */
  status?: boolean;
  tone?: "graphite" | "signal" | "outline";
}

withDefaults(
  defineProps<{
    title?: string;
    items: ReadoutItem[];
  }>(),
  { title: undefined },
);
</script>

<template>
  <div class="tm-readout">
    <p v-if="title" class="label tm-readout__title">{{ title }}</p>
    <dl class="tm-readout__list">
      <div v-for="(it, i) in items" :key="i" class="tm-readout__row">
        <dt class="label">{{ it.label }}</dt>
        <dd class="label">
          <RTag v-if="it.status" :tone="it.tone ?? 'graphite'">{{ it.value }}</RTag>
          <template v-else>{{ it.value }}</template>
        </dd>
      </div>
    </dl>
  </div>
</template>

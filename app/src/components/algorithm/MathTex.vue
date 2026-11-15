<script setup lang="ts">
// Renders a LaTeX formula with KaTeX. Parse errors show as text, never as a blank page.
import { computed } from "vue";
import katex from "katex";
import "katex/dist/katex.min.css";

const props = withDefaults(defineProps<{ tex: string; block?: boolean }>(), { block: true });

const html = computed(() =>
  katex.renderToString(props.tex, { displayMode: props.block, throwOnError: false, output: "htmlAndMathml" }),
);
</script>

<template>
  <div v-if="block" class="math math--block" v-html="html" />
  <span v-else class="math" v-html="html" />
</template>

<style lang="scss" scoped>
.math--block {
  overflow-x: auto;
  padding: var(--space-2) 0;
}

.math {
  color: var(--ink);
}
</style>

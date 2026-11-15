<script setup lang="ts">
// Source listing: syntax highlighting for Python, TypeScript and bash only; long listings collapse.
import { computed, onBeforeUnmount, ref } from "vue";
import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import typescript from "highlight.js/lib/languages/typescript";
import bash from "highlight.js/lib/languages/bash";
import RButton from "@/components/reticula/RButton.vue";

hljs.registerLanguage("python", python);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("bash", bash);

const props = withDefaults(
  defineProps<{
    code: string;
    lang: "python" | "typescript" | "bash";
    file?: string;
    collapsedLines?: number;
  }>(),
  { file: undefined, collapsedLines: 36 },
);

const lines = computed(() => props.code.split("\n"));
const long = computed(() => lines.value.length > props.collapsedLines);
const expanded = ref(false);

const shown = computed(() => (long.value && !expanded.value ? lines.value.slice(0, props.collapsedLines).join("\n") : props.code));
const highlighted = computed(() => hljs.highlight(shown.value, { language: props.lang, ignoreIllegals: true }).value);

const copied = ref(false);
let copyTimer: number | undefined;

async function copy() {
  try {
    await navigator.clipboard.writeText(props.code);
    copied.value = true;
    window.clearTimeout(copyTimer);
    copyTimer = window.setTimeout(() => (copied.value = false), 1500);
  } catch {
    // clipboard blocked: the listing is still selectable on the page
  }
}

onBeforeUnmount(() => window.clearTimeout(copyTimer));
</script>

<template>
  <figure class="listing">
    <figcaption v-if="file" class="listing__head">
      <span class="label listing__file">{{ file }}</span>
      <button type="button" class="listing__copy label tm-focusable" @click="copy">
        {{ copied ? "COPIED" : "COPY" }}
      </button>
    </figcaption>
    <div class="listing__scroll">
      <pre class="listing__pre"><code class="hljs" v-html="highlighted" /></pre>
    </div>
    <div v-if="long" class="listing__foot">
      <RButton variant="secondary" @click="expanded = !expanded">
        {{ expanded ? "COLLAPSE" : `SHOW FULL FUNCTION (${lines.length} LINES)` }}
      </RButton>
    </div>
  </figure>
</template>

<style lang="scss" scoped>
.listing {
  margin: 0;
  min-width: 0;
  background: var(--surface-raised);
  border: var(--stroke-hairline) solid var(--line);
  clip-path: polygon(
    0 0,
    calc(100% - var(--chamfer-md)) 0,
    100% var(--chamfer-md),
    100% 100%,
    0 100%
  );
}

.listing__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-bottom: var(--stroke-hairline) solid var(--line-faint);
}

.listing__file {
  color: var(--ink-muted);
  overflow-wrap: anywhere;
}

.listing__copy {
  border: var(--stroke-hairline) solid var(--line);
  background: transparent;
  color: var(--ink);
  padding: var(--space-1) var(--space-2);
  cursor: pointer;
  white-space: nowrap;

  &:hover {
    border-color: var(--ink);
  }
}

.listing__scroll {
  overflow-x: auto;
  padding: var(--space-3);
}

.listing__pre {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--size-code);
  line-height: var(--leading-code);
  color: var(--ink);
  white-space: pre;
}

.listing__pre code {
  font-family: inherit;
}

.listing__foot {
  padding: 0 var(--space-3) var(--space-3);
}
</style>

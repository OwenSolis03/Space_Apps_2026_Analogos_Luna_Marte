<script setup lang="ts">
// The four-part explanation of a control. Placed right below the control; hidden when closed.
import { EXPLANATION_HEADINGS, type Explanation } from "@/lib/explanations";

const props = withDefaults(
  defineProps<{
    id: string;
    title: string;
    open: boolean;
    explanation: Explanation;
    actionHeading?: string;
  }>(),
  { actionHeading: EXPLANATION_HEADINGS.slider },
);
</script>

<template>
  <div
    :id="`exp-${props.id}`"
    class="info-panel"
    role="region"
    :aria-label="`${title}: explanation`"
    :hidden="!open"
  >
    <div>
      <h4 class="label">{{ EXPLANATION_HEADINGS.what }}</h4>
      <p>{{ explanation.what }}</p>
    </div>
    <div>
      <h4 class="label">{{ EXPLANATION_HEADINGS.measure }}</h4>
      <p>{{ explanation.measure }}</p>
    </div>
    <div>
      <h4 class="label">{{ actionHeading }}</h4>
      <p>{{ explanation.slider }}</p>
    </div>
    <div>
      <h4 class="label">{{ EXPLANATION_HEADINGS.why }}</h4>
      <p>{{ explanation.why }}</p>
    </div>
    <p v-if="explanation.note" class="info-panel__note">{{ explanation.note }}</p>
  </div>
</template>

<style lang="scss" scoped>
.info-panel {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--surface);
  border-left: var(--stroke-bar) solid var(--graphite);
  font-size: 14px;
  line-height: 20px;
  color: var(--ink);

  &[hidden] {
    display: none;
  }

  h4 {
    margin: 0 0 var(--space-1);
    color: var(--ink-muted);
  }

  p {
    margin: 0;
  }
}

.info-panel__note {
  color: var(--ink-muted);
}
</style>

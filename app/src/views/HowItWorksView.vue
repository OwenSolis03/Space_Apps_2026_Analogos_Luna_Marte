<script setup lang="ts">
// How It Works (SEC.03): six stages from input to output, each with an animated figure.
// Plain language, no formulas and no code. The progress strip follows the stage in view.
import { onBeforeUnmount, onMounted, ref } from "vue";
import { STAGES, CLOSING } from "@/content/howItWorks";
import PageHero from "@/components/layout/PageHero.vue";
import RButton from "@/components/reticula/RButton.vue";
import RPanel from "@/components/reticula/RPanel.vue";
import RGlyph from "@/components/reticula/RGlyph.vue";
import StageShell from "@/components/how/StageShell.vue";
import StageInput from "@/components/how/StageInput.vue";
import StagePatch from "@/components/how/StagePatch.vue";
import StageMeasure from "@/components/how/StageMeasure.vue";
import StageFilter from "@/components/how/StageFilter.vue";
import StageCompare from "@/components/how/StageCompare.vue";
import StageOutput from "@/components/how/StageOutput.vue";

const current = ref(1);
let observer: IntersectionObserver | undefined;

onMounted(() => {
  if (typeof IntersectionObserver === "undefined") return;
  observer = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) current.value = Number(e.target.id.replace("stage-", ""));
      }
    },
    { rootMargin: "-40% 0px -50% 0px" },
  );
  document.querySelectorAll<HTMLElement>(".stage").forEach((el) => observer!.observe(el));
});

onBeforeUnmount(() => observer?.disconnect());

const idOf = (i: number) => `stage-${String(i + 1).padStart(2, "0")}`;
</script>

<template>
  <main class="page how">
    <PageHero code="SEC.03" title="HOW IT WORKS" subtitle="WHAT GOES IN, WHAT COMES OUT" />

    <nav class="progress" aria-label="Stages">
      <ol class="progress__list">
        <li v-for="(s, i) in STAGES" :key="s.code">
          <a :href="`#${idOf(i)}`" class="label progress__link" :aria-current="current === i + 1 ? 'step' : undefined">
            <RGlyph v-if="current === i + 1" name="tick-left" tone="signal" :size="16" />
            {{ String(i + 1).padStart(2, "0") }} {{ s.title }}
          </a>
        </li>
      </ol>
    </nav>

    <StageShell
      :id="idOf(0)"
      :code="STAGES[0]!.code"
      :title="STAGES[0]!.title"
      :lead="STAGES[0]!.lead"
      :body="STAGES[0]!.body"
    >
      <StageInput />
    </StageShell>

    <StageShell
      :id="idOf(1)"
      :code="STAGES[1]!.code"
      :title="STAGES[1]!.title"
      :lead="STAGES[1]!.lead"
      :body="STAGES[1]!.body"
    >
      <StagePatch />
    </StageShell>

    <StageShell
      :id="idOf(2)"
      :code="STAGES[2]!.code"
      :title="STAGES[2]!.title"
      :lead="STAGES[2]!.lead"
      :body="STAGES[2]!.body"
    >
      <StageMeasure />
    </StageShell>

    <StageShell
      :id="idOf(3)"
      :code="STAGES[3]!.code"
      :title="STAGES[3]!.title"
      :lead="STAGES[3]!.lead"
      :body="STAGES[3]!.body"
    >
      <StageFilter />
    </StageShell>

    <StageShell
      :id="idOf(4)"
      :code="STAGES[4]!.code"
      :title="STAGES[4]!.title"
      :lead="STAGES[4]!.lead"
      :body="STAGES[4]!.body"
    >
      <StageCompare />
    </StageShell>

    <StageShell
      :id="idOf(5)"
      :code="STAGES[5]!.code"
      :title="STAGES[5]!.title"
      :lead="STAGES[5]!.lead"
      :body="STAGES[5]!.body"
    >
      <StageOutput />
    </StageShell>

    <section class="closing" aria-labelledby="closing-h">
      <RPanel tone="graphite" class="closing__panel">
        <p id="closing-h" class="headline closing__title">{{ CLOSING.title }}</p>
        <p class="body">{{ CLOSING.text }}</p>
        <RButton variant="secondary" to="/results#limits" arrow>SEE THE LIMITS</RButton>
      </RPanel>
    </section>
  </main>
</template>

<style lang="scss" scoped>
.progress {
  position: sticky;
  top: 64px;
  z-index: 5;
  background: var(--surface);
  border-bottom: var(--stroke-hairline) solid var(--line-faint);
}

.progress__list {
  list-style: none;
  margin: 0;
  padding: 0 var(--space-4);
  display: flex;
  gap: var(--space-4);
  overflow-x: auto;
  max-width: 1280px;
  margin-inline: auto;
}

.progress__link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  min-height: 44px;
  color: var(--ink-muted);
  text-decoration: none;
  white-space: nowrap;

  &[aria-current="step"] {
    color: var(--ink);
  }
}

.closing {
  padding-block: var(--space-9) var(--space-7);
}

.closing__panel {
  min-height: 0;
  padding: var(--space-6);
  display: grid;
  gap: var(--space-4);
  justify-items: start;
}

.closing__title {
  font-weight: 500;
  color: var(--on-graphite);
}

.closing__panel p {
  margin: 0;
}
</style>

<script setup lang="ts">
// Algorithm (SEC.04): the pipeline in eleven steps, with its formulas and the real source of each step.
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useUniverse } from "@/composables/useUniverse";
import { GLANCE, REPO_URL, STEPS } from "@/content/algorithm";
import PageHero from "@/components/layout/PageHero.vue";
import RPanel from "@/components/reticula/RPanel.vue";
import RButton from "@/components/reticula/RButton.vue";
import RReadout from "@/components/reticula/RReadout.vue";
import RGlyph from "@/components/reticula/RGlyph.vue";
import CodeBlock from "@/components/algorithm/CodeBlock.vue";
import PipelineDiagram from "@/components/algorithm/PipelineDiagram.vue";
import StepCard from "@/components/algorithm/StepCard.vue";

const load = useUniverse();
const universe = computed(() => (load.value.state === "ready" ? load.value.data : null));

const current = ref(0);
let observer: IntersectionObserver | undefined;

onMounted(() => {
  if (typeof IntersectionObserver === "undefined") return;
  // The step nearest the upper third of the viewport is the current one.
  observer = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) {
          const n = Number(e.target.id.replace("step-", ""));
          if (!Number.isNaN(n)) current.value = n;
        }
      }
    },
    { rootMargin: "-30% 0px -60% 0px" },
  );
  document.querySelectorAll<HTMLElement>(".step").forEach((el) => observer!.observe(el));
});

onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
  <main class="page">
    <PageHero code="SEC.04" title="ALGORITHM" subtitle="FROM RAW ELEVATION TO A RANKED, EXPLAINABLE ANALOG" />

    <section class="section" aria-labelledby="repo-h">
      <RPanel tone="raised" label="SOURCE CODE" class="repo">
        <p class="body repo__text">
          The whole pipeline is in the repository. The excerpts on this page are read from the same files that run the analysis.
        </p>
        <RButton variant="primary" arrow :href="REPO_URL">OPEN REPOSITORY</RButton>
        <CodeBlock
          lang="bash"
          code="git clone https://github.com/OwenSolis03/Space_Apps_2026_Analogos_Luna_Marte.git"
        />
      </RPanel>
    </section>

    <section class="section" aria-labelledby="pipeline-h">
      <p id="pipeline-h" class="label section__label">PIPELINE</p>
      <PipelineDiagram />
    </section>

    <section class="section steps" aria-labelledby="steps-h">
      <p id="steps-h" class="label section__label">ELEVEN STEPS</p>
      <div class="steps__layout">
        <nav class="index" aria-label="Algorithm steps">
          <ol class="index__list">
            <li v-for="(s, i) in STEPS" :key="s.code">
              <a :href="`#step-${String(i + 1).padStart(2, '0')}`" class="label index__link" :aria-current="current === i + 1 ? 'step' : undefined">
                <RGlyph v-if="current === i + 1" name="tick-left" tone="signal" :size="16" />
                {{ s.code }}
              </a>
            </li>
          </ol>
        </nav>
        <div class="steps__cards">
          <StepCard v-for="s in STEPS" :key="s.code" :step="s" :universe="universe" />
        </div>
      </div>
    </section>

    <section class="section" aria-labelledby="glance-h">
      <p id="glance-h" class="label section__label">PARAMETERS AT A GLANCE</p>
      <p class="footnote">Read from pipeline/config.py, match.py, dust.py, ice.py and earth_features.py.</p>
      <RReadout :items="GLANCE" />
    </section>
  </main>
</template>

<style lang="scss" scoped>
.section {
  padding-block: var(--space-9) 0;
}

.section__label {
  margin-bottom: var(--space-5);
  color: var(--ink-muted);
}

.repo {
  min-height: 0;
  padding: var(--space-5);
}

.repo__text {
  margin: 0;
  color: var(--ink);
}

.steps__layout {
  display: grid;
  gap: var(--space-7);

  @media (min-width: 1024px) {
    grid-template-columns: minmax(0, 14rem) minmax(0, 1fr);
    align-items: start;
  }
}

.index {
  @media (min-width: 1024px) {
    position: sticky;
    top: 96px;
  }
}

.index__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-1);
}

.index__link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 40px;
  color: var(--ink-muted);
  text-decoration: none;

  &[aria-current="step"] {
    color: var(--ink);
  }

  &:hover {
    color: var(--ink);
  }
}

.steps__cards {
  display: grid;
  gap: var(--space-7);
  min-width: 0;
}
</style>

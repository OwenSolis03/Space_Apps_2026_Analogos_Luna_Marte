<script setup lang="ts">
// One step of the Algorithm page: summary, formulas, parameters, live tables, and the real source.
import { computed } from "vue";
import type { Universe } from "@/lib/types";
import { DIMENSIONS } from "@/lib/types";
import { GEO_CLASS_LABEL, limitLabel } from "@/lib/content";
import { REPO_URL, type Step } from "@/content/algorithm";
import { FACTS_FUNNEL } from "@/content/facts";
import RHeadline from "@/components/reticula/RHeadline.vue";
import RReadout from "@/components/reticula/RReadout.vue";
import RButton from "@/components/reticula/RButton.vue";
import RGlyph from "@/components/reticula/RGlyph.vue";
import DataTable from "@/components/layout/DataTable.vue";
import MathTex from "./MathTex.vue";
import CodeBlock from "./CodeBlock.vue";
import FunnelChart from "@/components/charts/FunnelChart.vue";
import SimilarityMatrix from "@/components/charts/SimilarityMatrix.vue";

const props = defineProps<{
  step: Step;
  universe: Universe | null;
}>();

/** Fields of metadata that the shared Universe type does not declare but the export contains. */
interface ExtraMeta {
  normalization?: { median: Record<string, number>; scale: Record<string, number>; log1p?: string[] | Record<string, boolean> };
  geology_classes?: string[];
  geology_similarity: Record<string, Record<string, number>>;
}
const extra = computed(() => props.universe?.metadata as unknown as ExtraMeta | undefined);

const fmt4 = (v: number) => v.toFixed(4);
const weight = (v: number | undefined) => (v && v > 0 ? v.toFixed(2) : "—");

const normalizationRows = computed(() => {
  const n = extra.value?.normalization;
  if (!n) return [];
  return Object.keys(n.median).map((k) => ({
    key: k,
    median: n.median[k]!,
    scale: n.scale[k],
    log1p: Array.isArray(n.log1p) ? n.log1p.includes(k) : Boolean(n.log1p?.[k]),
  }));
});

const presetRows = computed(() => {
  const presets = props.universe?.mission_presets ?? {};
  return Object.entries(presets).map(([id, p]) => ({
    id,
    label: p.label,
    bodies: p.applies_to ? p.applies_to.join(" · ") : "MOON · MARS",
    weights: DIMENSIONS.map((d) => p.weights[d]),
  }));
});

const geology = computed(() => {
  const m = extra.value;
  if (!m) return null;
  const classes = m.geology_classes ?? Object.keys(m.geology_similarity);
  const values = classes.map((a) => classes.map((b) => m.geology_similarity[a]?.[b] ?? 0));
  return { labels: classes.map((c) => (GEO_CLASS_LABEL[c] ?? c).toUpperCase()), values };
});

const limitsFor = (body: "Moon" | "Mars") => props.universe?.limits[body] ?? [];
</script>

<template>
  <article :id="`step-${step.code.slice(-2)}`" class="step">
    <header class="step__head">
      <p class="label step__code">{{ step.code }}</p>
      <RHeadline size="sm" as="h3" :title="step.title" />
    </header>

    <p class="prose">{{ step.summary }}</p>

    <div v-for="(f, i) in step.formulas" :key="i" class="formula">
      <MathTex :tex="f" />
    </div>

    <p v-for="(n, i) in step.notes ?? []" :key="`n-${i}`" class="body note">{{ n }}</p>

    <RReadout title="PARAMETERS" :items="step.params" />

    <template v-if="step.live?.includes('normalization') && normalizationRows.length">
      <p class="label live__title">FEATURE NORMALISATION · FROM THE EXPORT</p>
      <DataTable caption="Earth median, scale and log1p flag for every feature">
        <thead>
          <tr>
            <th class="label" scope="col">FEATURE</th>
            <th class="label num" scope="col">MEDIAN</th>
            <th class="label num" scope="col">SCALE (σ)</th>
            <th class="label" scope="col">LOG1P</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in normalizationRows" :key="r.key">
            <td>{{ r.key }}</td>
            <td class="num">{{ fmt4(r.median) }}</td>
            <td class="num">{{ r.scale != null ? fmt4(r.scale) : "—" }}</td>
            <td>{{ r.log1p ? "YES" : "NO" }}</td>
          </tr>
        </tbody>
      </DataTable>
    </template>

    <template v-if="step.live?.includes('presets') && presetRows.length">
      <p class="label live__title">MISSION PRESETS · WEIGHTS PER DIMENSION · FROM THE EXPORT</p>
      <DataTable caption="Weights of each mission preset per dimension, with the bodies it applies to">
        <thead>
          <tr>
            <th class="label" scope="col">PRESET</th>
            <th class="label" scope="col">BODIES</th>
            <th v-for="d in DIMENSIONS" :key="d" class="label num" scope="col">{{ d.toUpperCase() }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in presetRows" :key="p.id">
            <td>{{ p.label }}</td>
            <td class="label">{{ p.bodies }}</td>
            <td v-for="(w, i) in p.weights" :key="i" class="num">{{ weight(w) }}</td>
          </tr>
        </tbody>
      </DataTable>
      <p class="label live__title">SCORING RULES · metadata.scoring_policy.rules</p>
      <ol class="rules body">
        <li v-for="(r, i) in universe?.metadata.scoring_policy?.rules ?? []" :key="i">{{ r }}</li>
      </ol>
    </template>

    <template v-if="step.live?.includes('geology') && geology">
      <p class="label live__title">GEOLOGY SIMILARITY MATRIX · metadata.geology_similarity</p>
      <SimilarityMatrix
        label="Geology similarity between regional rock classes"
        :labels="geology.labels"
        :values="geology.values"
      />
    </template>

    <template v-if="step.live?.includes('limits-moon')">
      <p class="label live__title">PHYSICAL LIMITS · MOON · limits.Moon</p>
      <DataTable caption="Fixed physical limits of the Moon that no Earth site reproduces">
        <thead>
          <tr>
            <th class="label" scope="col">FACTOR</th>
            <th class="label" scope="col">EARTH</th>
            <th class="label" scope="col">MOON</th>
            <th class="label" scope="col">CONSEQUENCE</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="l in limitsFor('Moon')" :key="l.factor">
            <td>{{ limitLabel(l.factor) }}</td>
            <td>{{ l.earth }}</td>
            <td>{{ l.target }}</td>
            <td class="body">{{ l.consequence }}</td>
          </tr>
        </tbody>
      </DataTable>
    </template>

    <template v-if="step.live?.includes('limits-mars')">
      <p class="label live__title">PHYSICAL LIMITS · MARS · limits.Mars</p>
      <DataTable caption="Fixed physical limits of Mars that no Earth site reproduces">
        <thead>
          <tr>
            <th class="label" scope="col">FACTOR</th>
            <th class="label" scope="col">EARTH</th>
            <th class="label" scope="col">MARS</th>
            <th class="label" scope="col">CONSEQUENCE</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="l in limitsFor('Mars')" :key="l.factor">
            <td>{{ limitLabel(l.factor) }}</td>
            <td>{{ l.earth }}</td>
            <td>{{ l.target }}</td>
            <td class="body">{{ l.consequence }}</td>
          </tr>
        </tbody>
      </DataTable>
    </template>

    <template v-if="step.live?.includes('funnel')">
      <p class="label live__title">EARTH PREFILTER · STAGE COUNTS</p>
      <FunnelChart label="Earth prefilter funnel, from grid points to valid patches" :stages="FACTS_FUNNEL" />
    </template>

    <div v-for="(s, i) in step.snippets" :key="`s-${i}`" class="snippet">
      <a class="label snippet__link" :href="`${REPO_URL}/blob/main/${s.file}`" target="_blank" rel="noreferrer">
        VIEW ON GITHUB <RGlyph name="chevron-right" :size="14" />
      </a>
      <CodeBlock :code="s.code" :lang="s.lang" :file="s.file" />
    </div>

    <RButton v-if="step.cta" :to="step.cta.to" arrow>{{ step.cta.label }}</RButton>
  </article>
</template>

<style lang="scss" scoped>
.step {
  display: grid;
  gap: var(--space-5);
  min-width: 0;
  padding-bottom: var(--space-7);
  border-bottom: var(--stroke-hairline) solid var(--line-faint);
}

.step__head {
  display: grid;
  gap: var(--space-2);
}

.step__code {
  color: var(--ink-muted);
}

.note {
  margin: 0;
}

.formula {
  padding: var(--space-3) var(--space-4);
  background: var(--surface-raised);
  border-left: var(--stroke-bar) solid var(--graphite);
  overflow-x: auto;
}

.live__title {
  margin-top: var(--space-3);
  color: var(--ink-muted);
}

.rules {
  margin: 0;
  padding-left: var(--space-5);
  display: grid;
  gap: var(--space-1);
}

.snippet {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.snippet__link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  justify-self: start;
  color: var(--ink);
}
</style>

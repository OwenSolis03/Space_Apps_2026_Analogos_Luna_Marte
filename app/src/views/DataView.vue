<script setup lang="ts">
// Data (SEC.05): the sources, the exploratory analysis that shaped the pipeline, and live charts from the export.
import { computed } from "vue";
import { useUniverse } from "@/composables/useUniverse";
import { DATASETS, OFFICIAL_RESOURCES, type DatasetRow } from "@/content/datasets";
import { EDA_FINDINGS, FIGURES, FILE_TABLE, PREFILTER_COUNTS } from "@/content/eda";
import { COPERNICUS_TILES, EARTH_PATCHES, MARS_PATCHES, MOON_PATCHES } from "@/content/facts";
import { DIM_LABEL, GEO_CLASS_LABEL } from "@/lib/content";
import { geoClassCounts } from "@/lib/stats";
import { DIMENSIONS } from "@/lib/types";
import PageHero from "@/components/layout/PageHero.vue";
import SectionBlock from "@/components/layout/SectionBlock.vue";
import DataTable from "@/components/layout/DataTable.vue";
import FigureSlot from "@/components/layout/FigureSlot.vue";
import RReadout from "@/components/reticula/RReadout.vue";
import RTag from "@/components/reticula/RTag.vue";
import RPanel from "@/components/reticula/RPanel.vue";
import StripPlot from "@/components/charts/StripPlot.vue";
import BarChart from "@/components/charts/BarChart.vue";

const load = useUniverse();
const universe = computed(() => (load.value.state === "ready" ? load.value.data : null));

const groups: { body: DatasetRow["body"]; label: string }[] = [
  { body: "MARS", label: "MARS" },
  { body: "MOON", label: "MOON" },
  { body: "EARTH", label: "EARTH" },
  { body: "MOON · MARS", label: "MOON AND MARS" },
];
const rowsOf = (body: DatasetRow["body"]) => DATASETS.filter((d) => d.body === body);

const readout = computed(() => [
  { label: "RAW VOLUME", value: "≈ 80 GB" },
  { label: "DATASETS", value: String(DATASETS.length) },
  { label: "COPERNICUS TILES", value: COPERNICUS_TILES.toLocaleString("en-US") },
  { label: "BODIES", value: "3" },
]);

const fmt = (n: number) => n.toLocaleString("en-US");
const dimLabel = (key: string) => {
  const d = DIMENSIONS.find((x) => x.toUpperCase() === key);
  return d ? DIM_LABEL[d].label : key;
};

// Slopes of the Moon and Mars targets, from the export (degrees).
const slopeStrip = computed(() => {
  const u = universe.value;
  if (!u) return [];
  const pick = (body: "Moon" | "Mars") =>
    u.targets.filter((t) => t.body === body).map((t) => ({ name: t.name, value: t.features.mean_slope_deg ?? NaN }))
      .filter((p) => !Number.isNaN(p.value));
  return [
    { label: "MOON", points: pick("Moon") },
    { label: "MARS", points: pick("Mars") },
  ];
});

const geoBars = computed(() => {
  const u = universe.value;
  if (!u) return { Moon: [], Mars: [] } as Record<"Moon" | "Mars", { label: string; value: number }[]>;
  const counts = geoClassCounts(u);
  const toRows = (c: Record<string, number>) =>
    Object.entries(c)
      .map(([cls, n]) => ({ label: (GEO_CLASS_LABEL[cls] ?? cls).toUpperCase(), value: n }))
      .sort((a, b) => b.value - a.value);
  return { Moon: toRows(counts.Moon), Mars: toRows(counts.Mars) };
});

interface ExtraMeta {
  normalization?: { median: Record<string, number>; scale: Record<string, number> };
}
const normRows = computed(() => {
  const n = (universe.value?.metadata as unknown as ExtraMeta | undefined)?.normalization;
  if (!n) return [];
  return Object.keys(n.median).map((k) => ({ key: k, median: n.median[k]!, scale: n.scale[k] }));
});
</script>

<template>
  <main class="page">
    <PageHero code="SEC.05" title="DATA" subtitle="OPEN DATASETS AND WHAT THEY TAUGHT US">
      <template #aside>
        <RReadout :items="readout" />
      </template>
    </PageHero>

    <SectionBlock id="datasets" code="SEC.05" title="DATASETS" subtitle="WHICH OPEN SOURCE FEEDS WHICH PART OF THE SCORE">
      <div class="groups">
        <div v-for="g in groups" :key="g.body" class="group">
          <p class="label group__label">{{ g.label }}</p>
          <DataTable :caption="`Datasets for ${g.label.toLowerCase()}`">
            <thead>
              <tr>
                <th class="label" scope="col">DATASET</th>
                <th class="label" scope="col">USE</th>
                <th class="label" scope="col">SOURCE</th>
                <th class="label" scope="col">FEEDS</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in rowsOf(g.body)" :key="r.dataset">
                <td>{{ r.dataset }}</td>
                <td class="body">{{ r.use }}</td>
                <td>
                  <a v-if="r.url" :href="r.url" target="_blank" rel="noreferrer" class="source-link">{{ r.source }}</a>
                  <template v-else>{{ r.source }}</template>
                </td>
                <td>
                  <span class="tags">
                    <RTag v-for="f in r.feeds" :key="f" tone="graphite">{{ dimLabel(f) }}</RTag>
                  </span>
                </td>
              </tr>
            </tbody>
          </DataTable>
        </div>
      </div>

      <div class="block">
        <p class="label group__label">OFFICIAL CHALLENGE RESOURCES</p>
        <p class="footnote">Source: the challenge's Resources tab, checked on 2026-11-13.</p>
        <DataTable caption="Official challenge resources and how the project uses them">
          <thead>
            <tr>
              <th class="label" scope="col">OFFICIAL RESOURCE</th>
              <th class="label" scope="col">USED?</th>
              <th class="label" scope="col">PRODUCT</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in OFFICIAL_RESOURCES" :key="r.resource">
              <td>{{ r.resource }}</td>
              <td class="label">{{ r.used }}</td>
              <td class="body">{{ r.product }}</td>
            </tr>
          </tbody>
        </DataTable>
      </div>

      <div class="block">
        <p class="label group__label">REFERENCES</p>
        <ol v-if="universe?.metadata.citations?.length" class="refs footnote">
          <li v-for="c in universe.metadata.citations" :key="c">{{ c }}</li>
        </ol>
        <ul v-if="universe?.metadata.datasets?.length" class="refs footnote">
          <li v-for="d in universe.metadata.datasets" :key="d.name">
            <a v-if="d.url" :href="d.url" target="_blank" rel="noreferrer" class="source-link">{{ d.name }}</a>
            <template v-else>{{ d.name }}</template>
            · {{ d.source }}
          </li>
        </ul>
        <p v-if="universe" class="footnote">
          {{ universe.metadata.source }}. Version {{ universe.metadata.version }}, generated {{ universe.metadata.generated_at.slice(0, 10) }}.
        </p>
      </div>
    </SectionBlock>

    <SectionBlock id="eda" code="SEC.05" title="EXPLORATORY DATA ANALYSIS" subtitle="WHAT WAS CHECKED BEFORE THE PIPELINE WAS TRUSTED">
      <div class="block">
        <p class="label group__label">WHAT IS INSIDE EVERY FILE</p>
        <RPanel tone="tint" class="rule">
          <p class="label">ALWAYS APPLY value = raw · scale + offset</p>
        </RPanel>
        <DataTable caption="Type, scale, offset and nodata of every raster, checked on Yuca">
          <thead>
            <tr>
              <th class="label" scope="col">FILE</th>
              <th class="label" scope="col">TYPE</th>
              <th class="label num" scope="col">SCALE</th>
              <th class="label num" scope="col">OFFSET</th>
              <th class="label num" scope="col">NODATA</th>
              <th class="label" scope="col">NOTE</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in FILE_TABLE" :key="r.file">
              <td>{{ r.file }}</td>
              <td class="label">{{ r.dtype }}</td>
              <td class="num">{{ r.scale }}</td>
              <td class="num">{{ r.offset }}</td>
              <td class="num">{{ r.nodata }}</td>
              <td class="body">{{ r.note }}</td>
            </tr>
          </tbody>
        </DataTable>
      </div>

      <div class="block">
        <p class="label group__label">FINDINGS</p>
        <div class="findings">
          <RPanel v-for="f in EDA_FINDINGS" :key="f.code" tone="raised" :label="f.code" class="finding">
            <p class="headline finding__title">{{ f.title }}</p>
            <p class="body">{{ f.text }}</p>
            <p class="footnote finding__consequence">{{ f.consequence }}</p>
          </RPanel>
        </div>
      </div>

      <div class="block">
        <p class="label group__label">COVERAGE</p>
        <DataTable caption="Valid patches per body and the Earth prefilter stages">
          <thead>
            <tr>
              <th class="label" scope="col">BODY</th>
              <th class="label num" scope="col">VALID PATCHES</th>
              <th class="label num" scope="col">OF CANDIDATES</th>
              <th class="label num" scope="col">SHARE</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>MARS</td>
              <td class="num">{{ fmt(MARS_PATCHES) }}</td>
              <td class="num">141,472</td>
              <td class="num">99.61 %</td>
            </tr>
            <tr>
              <td>MOON</td>
              <td class="num">{{ fmt(MOON_PATCHES) }}</td>
              <td class="num">37,014</td>
              <td class="num">99.26 %</td>
            </tr>
            <tr>
              <td>EARTH</td>
              <td class="num">{{ fmt(EARTH_PATCHES) }}</td>
              <td class="num">44,375</td>
              <td class="num">90.69 %</td>
            </tr>
          </tbody>
        </DataTable>
        <DataTable caption="Earth prefilter stage counts">
          <thead>
            <tr>
              <th class="label" scope="col">STAGE</th>
              <th class="label num" scope="col">COUNT</th>
              <th class="label" scope="col">NOTE</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in PREFILTER_COUNTS" :key="p.stage">
              <td class="label">{{ p.stage }}</td>
              <td class="num">{{ fmt(p.count) }}</td>
              <td class="body">{{ p.note }}</td>
            </tr>
          </tbody>
        </DataTable>
      </div>

      <div v-if="universe" class="block">
        <p class="label group__label">LIVE FROM THE EXPORT</p>
        <div class="charts">
          <figure class="chart">
            <p class="label">TARGET MEAN SLOPE · DEGREES</p>
            <StripPlot label="Mean slope of each target, Moon and Mars" :rows="slopeStrip" :axis-max="30" :format="(v: number) => `${v.toFixed(1)}°`" />
          </figure>
          <figure class="chart">
            <p class="label">GEOLOGY CLASSES OF THE MOON TARGETS</p>
            <BarChart label="Moon target count per geology class" :rows="geoBars.Moon" />
          </figure>
          <figure class="chart">
            <p class="label">GEOLOGY CLASSES OF THE MARS TARGETS</p>
            <BarChart label="Mars target count per geology class" :rows="geoBars.Mars" />
          </figure>
        </div>
        <p class="label group__label">NORMALISATION · metadata.normalization</p>
        <DataTable caption="Earth median and scale used to normalise every feature">
          <thead>
            <tr>
              <th class="label" scope="col">FEATURE</th>
              <th class="label num" scope="col">MEDIAN</th>
              <th class="label num" scope="col">SCALE</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in normRows" :key="r.key">
              <td>{{ r.key }}</td>
              <td class="num">{{ r.median.toFixed(4) }}</td>
              <td class="num">{{ r.scale.toFixed(4) }}</td>
            </tr>
          </tbody>
        </DataTable>
      </div>

      <div class="block">
        <p class="label group__label">FIGURES</p>
        <p class="footnote">Exploratory data analysis (EDA) and planetary control maps produced during Slurm batch runs on the Yuca supercomputer (ACARUS).</p>
        <div class="figures">
          <FigureSlot v-for="f in FIGURES" :key="f.code" :src="f.src" :caption="f.caption" :alt="f.alt" />
        </div>
      </div>
    </SectionBlock>
  </main>
</template>

<style lang="scss" scoped>
.block {
  display: grid;
  gap: var(--space-4);
  margin-top: var(--space-7);
  min-width: 0;
}

.group__label {
  color: var(--ink-muted);
}

.groups,
.findings,
.figures {
  display: grid;
  gap: var(--space-6);
}

.group {
  display: grid;
  gap: var(--space-3);
  min-width: 0;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.source-link {
  color: var(--ink);
  text-decoration: underline;
  text-decoration-thickness: var(--stroke-hairline);
  text-underline-offset: 3px;
}

.refs {
  margin: 0;
  padding-left: var(--space-5);
  display: grid;
  gap: var(--space-1);
}

.rule {
  min-height: 0;
  padding: var(--space-4);
}

.rule p {
  margin: 0;
}

.finding {
  min-height: 0;
}

.finding__title {
  margin-top: var(--space-2);
  font-weight: 500;
}

.finding__consequence {
  margin-top: var(--space-2);
}

.charts {
  display: grid;
  gap: var(--space-5);

  @media (min-width: 900px) {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.chart {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: var(--space-4);
  background: var(--surface-raised);
  border: var(--stroke-hairline) solid var(--line-faint);
  min-width: 0;

  p {
    margin: 0;
  }
}

.figures {
  @media (min-width: 900px) {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>

<script setup lang="ts">
// Results (SEC.01): best analog per mission site, the explorer (ported from the React app),
// the site sheet, overview charts, and what the analysis does not claim.
import { computed, nextTick, ref, watch } from "vue";
import { useUniverse } from "@/composables/useUniverse";
import { useExplorer } from "@/composables/useExplorer";
import { useReducedMotion } from "@/composables/useReducedMotion";
import { bestMsiByBody, bestPerTarget, sitesByCountry, summary } from "@/lib/stats";
import { BODY_LABEL, TILES } from "@/lib/content";
import { fmtLat, fmtLon, pct } from "@/lib/msi";
import type { Body } from "@/lib/types";
import { NOT_TO_CLAIM } from "@/content/results";
import PageHero from "@/components/layout/PageHero.vue";
import SectionBlock from "@/components/layout/SectionBlock.vue";
import DataTable from "@/components/layout/DataTable.vue";
import RReadout from "@/components/reticula/RReadout.vue";
import RTag from "@/components/reticula/RTag.vue";
import ScenarioPanel from "@/components/explorer/ScenarioPanel.vue";
import SiteMap from "@/components/explorer/SiteMap.vue";
import RankList from "@/components/explorer/RankList.vue";
import SiteDossier from "@/components/explorer/SiteDossier.vue";
import BarChart from "@/components/charts/BarChart.vue";
import StripPlot from "@/components/charts/StripPlot.vue";

const reduced = useReducedMotion();
const load = useUniverse();
const universe = computed(() => (load.value.state === "ready" ? load.value.data : null));

const {
  body,
  presetId,
  weights,
  minScore,
  lambda,
  newOnly,
  bodyTargets,
  available,
  dimInfo,
  ranked,
  unranked,
  selected,
  safeAnalog,
  targetPoints,
  earthPoints,
  selectTarget,
  setAnalogIndex,
  changeBody,
  changeWeight,
  choosePreset,
} = useExplorer(universe);

const stats = computed(() => (universe.value ? summary(universe.value) : null));
const B = computed(() => BODY_LABEL[body.value]);
const fmt = (n: number) => n.toLocaleString("en-US");

// Preset for the table and the overview charts. The explorer keeps its own preset.
const tablePreset = ref("");
watch(
  universe,
  (u) => {
    if (u && !tablePreset.value) tablePreset.value = Object.keys(u.mission_presets)[0] ?? "";
  },
  { immediate: true },
);
const presets = computed(() => (universe.value ? Object.entries(universe.value.mission_presets) : []));
const picks = computed(() => (universe.value && tablePreset.value ? bestPerTarget(universe.value, tablePreset.value) : []));
const countries = computed(() => (universe.value ? sitesByCountry(universe.value, 15) : []));
const strip = computed(() => {
  if (!universe.value || !tablePreset.value) return [];
  const by = bestMsiByBody(universe.value, tablePreset.value);
  return [
    { label: "MOON", points: by.Moon.map((p) => ({ name: p.name, value: p.msi })) },
    { label: "MARS", points: by.Mars.map((p) => ({ name: p.name, value: p.msi })) },
  ];
});

const readout = computed(() => {
  const s = stats.value;
  if (!s) return [];
  return [
    { label: "EARTH PATCHES EVALUATED", value: fmt(s.earthPatches) },
    { label: "TARGETS (MISSION SITES)", value: `${s.targets} (${s.curated} CURATED)` },
    { label: "TARGET-ANALOG PAIRS", value: fmt(s.pairs) },
    { label: "UNIQUE EARTH SITES", value: fmt(s.uniqueSites) },
    { label: "NEW CANDIDATES", value: fmt(s.newSites), status: true, tone: "signal" as const },
    { label: "KNOWN ANALOG SITES", value: fmt(s.knownSites) },
    { label: "RUN", value: s.runId },
  ];
});

const split = computed(() => {
  const s = stats.value;
  if (!s || s.uniqueSites === 0) return null;
  return {
    newPct: (s.newSites / s.uniqueSites) * 100,
    knownPct: (s.knownSites / s.uniqueSites) * 100,
    newSites: s.newSites,
    knownSites: s.knownSites,
  };
});

/** A row in the table opens that target in the explorer, switching body if needed, then scrolls there. */
async function openFromTable(id: string, targetBody: Body) {
  if (body.value !== targetBody) changeBody(targetBody);
  selectTarget(id);
  await nextTick();
  document.getElementById("explorer")?.scrollIntoView({
    behavior: reduced.value ? "auto" : "smooth",
    block: "start",
  });
}
</script>

<template>
  <main class="page">
    <PageHero code="SEC.01" title="RESULTS" subtitle="WHAT THE GLOBAL SEARCH FOUND">
      <template #aside>
        <RReadout v-if="readout.length" :items="readout" />
        <p v-else-if="load.state === 'loading'" class="body" role="status">LOADING ANALOG DATA…</p>
      </template>
    </PageHero>

    <div v-if="load.state === 'error'" role="alert" class="alert">
      <p class="label">THE ANALOG DATA COULD NOT BE LOADED.</p>
      <p class="footnote">{{ load.message }}. Check that the file app/public/data/analogs_universe.json exists.</p>
    </div>

    <template v-if="universe">
      <SectionBlock
        id="explorer"
        code="SEC.01"
        title="EXPLORER"
        subtitle="PICK A MISSION CASE AND ADJUST THE WEIGHTS. THE RANKING IS RECALCULATED IN YOUR BROWSER."
      >
        <div class="chips" role="group" aria-label="Target body">
          <button type="button" class="tm-chip" :aria-pressed="body === 'Mars'" @click="changeBody('Mars')">MARS</button>
          <button type="button" class="tm-chip" :aria-pressed="body === 'Moon'" @click="changeBody('Moon')">MOON</button>
          <span class="footnote explorer__count">{{ bodyTargets.length }} TARGETS FOR {{ B.name.toUpperCase() }}</span>
        </div>

        <div class="explorer">
          <ScenarioPanel
            class="explorer__scenario"
            :body="body"
            :presets="universe.mission_presets"
            :preset-id="presetId"
            :weights="weights"
            :available="available"
            :dim-info="dimInfo"
            :body-name="B.name"
            :min-score="minScore"
            :lambda="lambda"
            :new-only="newOnly"
            @preset="choosePreset"
            @weight="changeWeight"
            @min-score="(v: number) => (minScore = v)"
            @lambda="(v: number) => (lambda = v)"
            @new-only="(v: boolean) => (newOnly = v)"
          />

          <div class="explorer__maps">
            <SiteMap
              :key="`targets-${body}`"
              :title="`${B.name} · terrain targets`"
              kind="target"
              :tiles="TILES[body]"
              :geographic="true"
              :points="targetPoints"
              note="CLICK A POINT TO OPEN ITS SHEET"
              @select="selectTarget"
            />
            <SiteMap
              title="EARTH · ANALOGS OF THE SELECTED TARGET"
              kind="earth"
              :tiles="TILES.Earth"
              :geographic="false"
              :points="earthPoints"
              @select="(id: string) => setAnalogIndex(Number(id))"
            />
          </div>

          <RankList
            class="explorer__rank"
            :ranked="ranked"
            :unranked="unranked"
            :total="bodyTargets.length"
            :selected-id="selected?.target.id ?? null"
            @select="selectTarget"
          />
        </div>
      </SectionBlock>

      <SectionBlock id="site" code="SEC.01" title="SITE SHEET" subtitle="HOW CLOSE EACH ANALOG IS, FEATURE BY FEATURE, AND WHAT EARTH CANNOT REPRODUCE">
        <SiteDossier
          v-if="selected"
          :ranked="selected"
          :analog-index="safeAnalog"
          :limits="universe.limits[body]"
          @analog="setAnalogIndex"
        />
        <p v-else class="body">SELECT A TARGET IN THE RANKING OR ON THE MAP TO SEE ITS SHEET.</p>
      </SectionBlock>

      <SectionBlock
        id="headline"
        code="SEC.01"
        title="BEST ANALOG PER MISSION SITE"
        subtitle="ONE ROW PER CURATED TARGET · MSI FOR THE SELECTED PRESET"
      >
        <div class="chips" role="group" aria-label="Mission preset for this table">
          <button
            v-for="[id, p] in presets"
            :key="id"
            type="button"
            class="tm-chip"
            :aria-pressed="tablePreset === id"
            @click="tablePreset = id"
          >
            {{ p.label }}
          </button>
        </div>

        <DataTable caption="Best Earth analog for each curated Moon and Mars target, for the selected preset">
          <thead>
            <tr>
              <th class="label" scope="col">SITE</th>
              <th class="label" scope="col">BODY</th>
              <th class="label" scope="col">CATEGORY</th>
              <th class="label" scope="col">BEST ANALOG</th>
              <th class="label num" scope="col">MSI</th>
              <th class="label" scope="col">STATUS</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in picks" :key="p.target.id">
              <td>
                <button type="button" class="row-link tm-focusable" @click="openFromTable(p.target.id, p.target.body)">
                  {{ p.target.name }}
                </button>
              </td>
              <td class="label">{{ p.target.body.toUpperCase() }}</td>
              <td>{{ p.target.category ?? "" }}</td>
              <td>
                <template v-if="p.analog">
                  {{ p.analog.known_region ?? p.analog.country ?? "Copernicus DEM cell" }}
                  <span class="num footnote block">{{ fmtLat(p.analog.lat) }}, {{ fmtLon(p.analog.lon) }}</span>
                </template>
                <span v-else class="footnote">NOT MODELLED FOR THIS PRESET</span>
              </td>
              <td class="num">{{ p.msi != null ? pct(p.msi) : "n/a" }}</td>
              <td>
                <RTag v-if="p.analog && p.analog.classification === 'NEW_CANDIDATE'" tone="signal" bracket>NEW CANDIDATE</RTag>
                <RTag v-else-if="p.analog" tone="outline" bracket>KNOWN ANALOG</RTag>
                <RTag v-else tone="outline" bracket>NOT MODELLED</RTag>
              </td>
            </tr>
          </tbody>
        </DataTable>
      </SectionBlock>

      <SectionBlock id="overview" code="SEC.01" title="THE BIG PICTURE" subtitle="THREE VIEWS OF THE WHOLE RUN">
        <div class="overview">
          <figure class="overview__card">
            <p class="label">SITES PER COUNTRY · TOP 15</p>
            <BarChart label="Unique Earth analog sites per country, top 15" :rows="countries.map((c) => ({ label: c.country.toUpperCase(), value: c.count }))" />
          </figure>

          <figure class="overview__card">
            <p class="label">BEST MSI PER MISSION SITE · {{ presets.find(([id]) => id === tablePreset)?.[1].label.toUpperCase() }}</p>
            <StripPlot label="Best MSI per curated target, Moon and Mars" :rows="strip" />
            <p class="footnote">
              Lunar scores are lower because Earth has very little arid terrain as rugged as the lunar south pole at this scale.
              That is a finding, not a bug.
            </p>
          </figure>

          <figure v-if="split" class="overview__card">
            <p class="label">NEW CANDIDATES AGAINST KNOWN ANALOG SITES</p>
            <div class="split" role="img" :aria-label="`${fmt(split.newSites)} new candidate sites and ${fmt(split.knownSites)} known analog sites`">
              <span class="split__new" :style="{ width: `${split.newPct}%` }" />
              <span class="split__known" :style="{ width: `${split.knownPct}%` }" />
            </div>
            <div class="split__legend">
              <span class="label">NEW CANDIDATE · {{ fmt(split.newSites) }}</span>
              <span class="label">KNOWN ANALOG · {{ fmt(split.knownSites) }}</span>
            </div>
          </figure>
        </div>
      </SectionBlock>

      <SectionBlock id="limits" code="SEC.01" title="WHAT THIS DOES NOT CLAIM" subtitle="MODEL LIMITS AND THE CLAIMS TO AVOID">
        <div class="limits">
          <div>
            <p class="label">NOT MODELLED</p>
            <ul class="list">
              <li v-for="n in universe.metadata.not_modelled ?? []" :key="n.item">
                <p class="label">{{ n.item }}</p>
                <p class="body">{{ n.note }}</p>
              </li>
            </ul>
          </div>
          <div>
            <p class="label">WHAT WE MUST NOT CLAIM</p>
            <ul class="list">
              <li v-for="c in NOT_TO_CLAIM" :key="c.lead">
                <p class="label">{{ c.lead }}</p>
                <p class="body">{{ c.body }}</p>
              </li>
            </ul>
          </div>
        </div>
      </SectionBlock>
    </template>
  </main>
</template>

<style lang="scss" scoped>
.alert {
  margin-top: var(--space-6);
  padding: var(--space-4);
  background: var(--surface-raised);
  border-left: var(--stroke-bar) solid var(--signal);
}

.alert p {
  margin: 0;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-5);
}

.explorer__count {
  margin-left: var(--space-2);
}

.row-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ink);
  font-weight: 500;
  text-align: left;
  text-decoration: underline;
  text-decoration-thickness: var(--stroke-hairline);
  text-underline-offset: 3px;
  cursor: pointer;

  &:hover {
    text-decoration-thickness: var(--stroke-line);
  }
}

.block {
  display: block;
}

.explorer {
  display: grid;
  gap: var(--space-4);
  align-items: start;

  @media (min-width: 1024px) {
    grid-template-columns: minmax(0, 1fr) 22rem;
  }
}

.explorer__scenario {
  grid-column: 1 / -1;
}

.explorer__maps {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
  align-content: start;
}



.overview {
  display: grid;
  gap: var(--space-5);

  @media (min-width: 900px) {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}

.overview__card {
  display: grid;
  align-content: start;
  gap: var(--space-3);
  margin: 0;
  padding: var(--space-4);
  background: var(--surface-raised);
  border: var(--stroke-hairline) solid var(--line-faint);
  min-width: 0;

  p {
    margin: 0;
  }
}

.split {
  display: flex;
  height: var(--space-5);
  border: var(--stroke-hairline) solid var(--line);
}

.split__new {
  display: block;
  background: var(--signal);
}

.split__known {
  display: block;
  background: var(--graphite);
}

.split__legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2);
}

.limits {
  display: grid;
  gap: var(--space-6);

  @media (min-width: 900px) {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}

.list {
  list-style: none;
  margin: var(--space-3) 0 0;
  padding: 0;
  display: grid;
  gap: var(--space-3);

  li {
    display: grid;
    gap: var(--space-1);
    padding-top: var(--space-3);
    border-top: var(--stroke-hairline) solid var(--line-faint);
  }

  p {
    margin: 0;
  }
}
</style>

<script setup lang="ts">
// Site sheet: the selected target against one of its Earth analogs. Port of components/Dossier.tsx.
// Every comparison is marked by a word and a glyph, never by colour alone.
import { computed } from "vue";
import type { Analog, Dimension, Limit, MineralogyMeta, Mismatch, Target } from "@/lib/types";
import type { RankedTarget } from "@/lib/msi";
import { fmtLat, fmtLon, fmtNum, pct } from "@/lib/msi";
import { BODY_LABEL, DIM_LABEL, FEATURE_LABEL, GEO_CLASS_LABEL, fmtValue, limitLabel, suggestedUses } from "@/lib/content";
import RGlyph from "@/components/reticula/RGlyph.vue";
import RTag from "@/components/reticula/RTag.vue";
import RadarChart from "./RadarChart.vue";
import MineralogyPanel from "./MineralogyPanel.vue";

const props = defineProps<{
  ranked: RankedTarget;
  analogIndex: number;
  limits: Limit[];
  mineralogyMeta?: MineralogyMeta;
}>();

const emit = defineEmits<{ analog: [i: number] }>();

interface Row {
  key: string;
  label: string;
  unit: string;
  target: number | string | null | undefined;
  earth: number | string | null | undefined;
}

/** Non-terrain comparisons (geology, dust, ice) built from the structured fields of the export. */
function processRows(t: Target, a: Analog): Row[] {
  const rows: Row[] = [];
  if (t.geology?.geo_class || a.geology?.geo_class) {
    rows.push({ key: "geo_class", label: "Rock class (regional)", unit: "", target: t.geology?.geo_class, earth: a.geology?.geo_class });
  }
  if (t.dust && a.dust) {
    rows.push({ key: "dust_level_rank", label: "Dust level rank", unit: "", target: t.dust.level_rank, earth: a.dust.level_rank });
    rows.push({ key: "dust_seasonality_rank", label: "Dust seasonality rank", unit: "", target: t.dust.seasonality_rank, earth: a.dust.seasonality_rank });
  }
  if (t.ice?.cold_rank != null || (a.sub_scores.ice != null && a.ice?.cold_rank != null)) {
    rows.push({ key: "cold_rank", label: "Cold-trap rank", unit: "", target: t.ice?.cold_rank, earth: a.ice?.cold_rank });
  }
  return rows;
}

const picked = computed(() => props.ranked.analogs[props.analogIndex] ?? props.ranked.analogs[0]!);
const t = computed(() => props.ranked.target);
const a = computed(() => picked.value.analog);
const score = computed(() => picked.value.score);
const body = computed(() => BODY_LABEL[t.value.body].name);

const mismatchByFeature = computed(() => new Map(a.value.mismatches.map((m) => [m.feature, m] as const)));
const terrain = computed(() =>
  Object.keys(t.value.features).filter((k) => k in a.value.features && k !== "mean_elev_m"),
);
const processList = computed(() => processRows(t.value, a.value));
const extra = computed<Row[]>(() => {
  const shown = new Set([...terrain.value, ...processList.value.map((r) => r.key)]);
  return a.value.mismatches
    .filter((m) => !shown.has(m.feature) && !m.feature.startsWith("no_earth_data:"))
    .map((m) => ({
      key: m.feature,
      label: FEATURE_LABEL[m.feature]?.label ?? m.feature,
      unit: FEATURE_LABEL[m.feature]?.unit ?? "",
      target: m.target,
      earth: m.earth,
    }));
});
const notes = computed(() =>
  [
    a.value.subsurface_note,
    a.value.polar_cold ? "Polar cold environment on Earth: useful for cold-trap and ice operations." : null,
    a.value.geology?.ice_surface ? "Ice-covered surface on Earth." : null,
  ].filter((n): n is string => Boolean(n)),
);
const uses = computed(() => [...suggestedUses(t.value.features, t.value.body, t.value.lat), ...notes.value]);

const breaks = computed(() =>
  a.value.mismatches.map((m) => {
    if (m.feature.startsWith("no_earth_data:")) {
      const dim = m.feature.split(":")[1] as Dimension;
      return `no Earth data for ${DIM_LABEL[dim]?.label.toLowerCase() ?? dim}`;
    }
    return m.feature === "geo_class"
      ? `rock class (${fmtValue(m.earth)} on Earth, ${fmtValue(m.target)} on ${body.value})`
      : (FEATURE_LABEL[m.feature]?.label ?? m.feature).toLowerCase();
  }),
);

const km = (v: number | null | undefined) => (v == null ? "n/a" : `${Math.round(v).toLocaleString("en-US")} km`);

/** Mismatch cell: a word plus a glyph. z is shown when the feature has a Z score. */
function matchKind(mm: Mismatch | undefined): { kind: "match" | "mismatch" | "differs"; z: number | null } {
  if (!mm) return { kind: "match", z: null };
  return mm.z_diff == null ? { kind: "differs", z: null } : { kind: "mismatch", z: mm.z_diff };
}
const signed = (z: number) => `${z > 0 ? "+" : ""}${z}`;
</script>

<template>
  <div class="dossier">
    <div class="dossier__main">
      <div class="pair">
        <article class="card card--target">
          <p class="label card__eyebrow">{{ body }} · {{ t.type === "CURATED" ? (t.category ?? "mission site") : "terrain archetype" }}</p>
          <p class="headline card__title">{{ t.name }}</p>
          <p class="num footnote">{{ fmtLat(t.lat) }}, {{ fmtLon(t.lon) }} · {{ t.id }}</p>
          <p v-if="t.why" class="body card__text">{{ t.why }}</p>
          <p v-if="t.geology?.geo_class" class="footnote">
            Regional geology: {{ GEO_CLASS_LABEL[t.geology.geo_class] ?? t.geology.geo_class }}
            <template v-if="t.geology.unit"> (unit {{ t.geology.unit }})</template>
          </p>
          <a v-if="t.source_url" class="label card__link" :href="t.source_url" target="_blank" rel="noreferrer">SOURCE</a>
        </article>

        <span class="label pair__versus">VERSUS</span>

        <article class="card card--earth">
          <p class="label card__eyebrow">
            Earth · analog #{{ analogIndex + 1 }} ·
            <RTag v-if="a.classification === 'KNOWN_ANALOG'" tone="outline" bracket>KNOWN ANALOG REGION</RTag>
            <RTag v-else tone="signal" bracket>NEW CANDIDATE</RTag>
          </p>
          <p class="headline card__title">
            {{ a.known_region ? `${a.known_region}${a.country ? `, ${a.country}` : ""}` : (a.country ?? "Copernicus DEM cell") }}
          </p>
          <p class="num footnote">{{ fmtLat(a.lat) }}, {{ fmtLon(a.lon) }}</p>
          <dl class="facts">
            <dt class="label">NEAREST ROAD</dt>
            <dd class="num">{{ km(a.logistics?.dist_road_km) }}</dd>
            <dt class="label">NEAREST AIRPORT</dt>
            <dd class="num">
              {{ km(a.logistics?.dist_airport_km) }}
              <template v-if="a.logistics?.nearest_airport_iata"> · {{ a.logistics.nearest_airport_iata }}</template>
            </dd>
            <template v-if="a.earth_env?.ndvi_max != null">
              <dt class="label">MAX NDVI</dt>
              <dd class="num">{{ a.earth_env.ndvi_max.toFixed(2) }}</dd>
            </template>
            <template v-if="a.earth_env?.lst_amplitude_c != null">
              <dt class="label">DAY-NIGHT ΔT</dt>
              <dd class="num">{{ a.earth_env.lst_amplitude_c.toFixed(1) }} °C</dd>
            </template>
          </dl>
        </article>
      </div>

      <div class="analogs">
        <div class="analogs__head">
          <span class="label">EARTH ANALOGS, BEST FIRST</span>
          <span class="label num">{{ ranked.analogs.length }} PLACES</span>
        </div>
        <div class="chip-row" role="group" aria-label="Analogs for this target">
          <button
            v-for="(x, i) in ranked.analogs"
            :key="x.analog.id"
            type="button"
            class="tm-chip num"
            :aria-pressed="i === analogIndex"
            @click="emit('analog', i)"
          >
            <RGlyph v-if="i === analogIndex" name="tick-left" tone="signal" :size="14" />
            #{{ i + 1 }} · {{ pct(x.score) }}
          </button>
        </div>
      </div>

      <div class="table-wrap">
        <table class="dtable body">
          <caption class="sr-only">Target features versus the Earth analog</caption>
          <thead>
            <tr>
              <th class="label" scope="col">FEATURE</th>
              <th class="label" scope="col">{{ body.toUpperCase() }}</th>
              <th class="label" scope="col">EARTH</th>
              <th class="label" scope="col">STATUS</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="k in terrain" :key="k">
              <td>{{ (FEATURE_LABEL[k] ?? { label: k }).label }}</td>
              <td class="num">{{ fmtNum(t.features[k]!) }} {{ FEATURE_LABEL[k]?.unit }}</td>
              <td class="num">{{ fmtNum(a.features[k]!) }} {{ FEATURE_LABEL[k]?.unit }}</td>
              <td>
                <template v-for="m in [matchKind(mismatchByFeature.get(k))]" :key="k">
                  <span v-if="m.kind === 'match'" class="status status--match"><RGlyph name="tick-right" :size="14" /> MATCH</span>
                  <span v-else class="status status--mismatch"><RGlyph name="close" :size="14" /> MISMATCH <span class="num">(z {{ signed(m.z!) }})</span></span>
                </template>
              </td>
            </tr>
            <tr v-for="r in [...processList, ...extra]" :key="r.key">
              <td>{{ r.label }}</td>
              <td class="num">{{ fmtValue(r.target, r.unit) }}</td>
              <td class="num">{{ fmtValue(r.earth, r.unit) }}</td>
              <td>
                <span v-if="r.target == null || r.earth == null" class="status status--none">NO DATA</span>
                <template v-else>
                  <span v-if="matchKind(mismatchByFeature.get(r.key)).kind === 'match'" class="status status--match"><RGlyph name="tick-right" :size="14" /> MATCH</span>
                  <span v-else-if="matchKind(mismatchByFeature.get(r.key)).kind === 'differs'" class="status status--mismatch"><RGlyph name="close" :size="14" /> DIFFERS</span>
                  <span v-else class="status status--mismatch"><RGlyph name="close" :size="14" /> MISMATCH <span class="num">(z {{ signed(matchKind(mismatchByFeature.get(r.key)).z!) }})</span></span>
                </template>
              </td>
            </tr>
            <tr v-for="dim in a.earth_missing_dims ?? []" :key="`missing-${dim}`">
              <td class="italic">{{ DIM_LABEL[dim]?.label ?? dim }}</td>
              <td class="num">measured</td>
              <td class="num">no Earth measurement, scored 0</td>
              <td><span class="status status--mismatch"><RGlyph name="close" :size="14" /> NO EARTH DATA</span></td>
            </tr>
            <tr class="dtable__muted">
              <td>Mean elevation</td>
              <td class="num">{{ fmtNum(t.features.mean_elev_m!) }} m</td>
              <td class="num">{{ fmtNum(a.features.mean_elev_m!) }} m</td>
              <td class="footnote">NOT COMPARABLE (DATUM)</td>
            </tr>
          </tbody>
        </table>
        <p class="footnote table-note">
          Ranks are percentiles within each planet (0 = lowest, 1 = highest), so they compare how extreme a site is at home, not absolute values.
        </p>
      </div>

      <div class="use">
        <p class="label">SUGGESTED FIELD USE</p>
        <ul class="use__list body">
          <li v-for="u in uses" :key="u">{{ u }}</li>
        </ul>
        <p class="footnote">Rule of thumb from slope and roughness, plus the site notes from the pipeline.</p>
      </div>

      <MineralogyPanel
        v-if="props.mineralogyMeta"
        :target="t"
        :analog="a"
        :meta="props.mineralogyMeta"
        :body-name="body"
      />
    </div>

    <div class="dossier__side">
      <section class="side-card">
        <div class="side-card__head">
          <h3 class="headline">SIMILARITY PROFILE</h3>
          <span class="label">MSI <span class="num">{{ pct(score) }}</span></span>
        </div>
        <RadarChart :values="a.sub_scores" :available-dims="t.available_dims" :earth-missing-dims="a.earth_missing_dims" />
      </section>

      <section class="side-card">
        <h3 class="headline">WHERE THE ANALOGY BREAKS</h3>
        <p v-if="breaks.length > 0" class="body side-card__text">At this site: {{ breaks.join("; ") }}.</p>
        <p v-else class="body side-card__text">At this site no measured feature is beyond 1.5 σ; the physical limits below still apply.</p>
        <ul class="limits">
          <li v-for="l in limits" :key="l.factor" class="limits__item">
            <div>
              <p class="label">{{ limitLabel(l.factor) }}</p>
              <p class="num footnote">{{ l.earth }} / {{ l.target }}</p>
            </div>
            <p class="body">
              {{ l.consequence }}
              <a v-if="l.source" class="footnote" :href="l.source" target="_blank" rel="noreferrer">SOURCE</a>
            </p>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.dossier {
  display: grid;
  gap: var(--space-6);
  min-width: 0;

  @media (min-width: 1100px) {
    grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr);
    align-items: start;
  }
}

.dossier__main,
.dossier__side {
  display: grid;
  gap: var(--space-5);
  align-content: start;
  min-width: 0;
}

.pair {
  display: grid;
  gap: var(--space-3);
  align-items: stretch;

  @media (min-width: 640px) {
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  }
}

.pair__versus {
  align-self: center;
  justify-self: center;
  color: var(--ink-muted);
}

.card {
  min-width: 0;
  display: grid;
  align-content: start;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--surface-raised);
  border: var(--stroke-line) solid var(--line);
}

.card--target {
  border-color: var(--ink);
}

.card__title {
  font-weight: 500;
  overflow-wrap: anywhere;
}

.card__text {
  margin-top: var(--space-1);
}

.card__link {
  justify-self: start;
  color: var(--ink);
}

.facts {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-1) var(--space-3);
  margin: 0;

  dt {
    color: var(--ink-muted);
  }

  dd {
    margin: 0;
  }
}

.analogs {
  display: grid;
  gap: var(--space-2);
}

.analogs__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--space-2);
}

.chip-row {
  display: flex;
  gap: var(--space-2);
  overflow-x: auto;
  padding-bottom: var(--space-2);
}

.chip-row .tm-chip {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.table-wrap {
  overflow-x: auto;
}

.dtable {
  width: 100%;
  min-width: 32rem;
  border-collapse: collapse;

  th,
  td {
    padding: var(--space-2);
    border-bottom: var(--stroke-hairline) solid var(--line-faint);
    text-align: left;
    vertical-align: top;
  }

  th {
    color: var(--ink-muted);
    font-weight: 500;
  }

  .num {
    text-align: right;
  }

  tr.dtable__muted td {
    color: var(--ink-muted);
  }
}

.italic {
  font-style: italic;
}

.status {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  white-space: nowrap;
}

.status--match {
  color: var(--ink);
}

.status--mismatch {
  color: var(--signal-ink);
}

.status--none {
  color: var(--ink-muted);
}

.table-note {
  margin-top: var(--space-2);
}

.use {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--surface);
  border: var(--stroke-hairline) solid var(--line-faint);
}

.use__list {
  margin: 0;
  padding-left: var(--space-5);
  display: grid;
  gap: var(--space-1);
}

.side-card {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--surface-raised);
  border: var(--stroke-hairline) solid var(--line-faint);
}

.side-card__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--space-2);
}

.side-card__text {
  margin: 0;
}

.limits {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-3);
}

.limits__item {
  display: grid;
  gap: var(--space-1);
  padding-top: var(--space-3);
  border-top: var(--stroke-hairline) dashed var(--line);

  @media (min-width: 640px) {
    grid-template-columns: 8rem minmax(0, 1fr);
    gap: var(--space-3);
  }

  p {
    margin: 0;
  }
}
</style>

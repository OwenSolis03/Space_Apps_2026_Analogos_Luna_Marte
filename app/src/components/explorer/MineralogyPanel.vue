<script setup lang="ts">
// Mineral context of the selected target and Earth analog.
// Display only: this layer provides scientific context and does NOT enter the MSI score.
import { computed } from "vue";
import type { Analog, MineralogyBlock, MineralogyMeta, MineralogySourceMeta, Target } from "@/lib/types";
import RTag from "@/components/reticula/RTag.vue";

const props = defineProps<{
  target: Target;
  analog: Analog;
  meta?: MineralogyMeta;
  bodyName: string;
}>();

const EARTH_SOURCE = "emit_l3asa";
const TINY = 0.05;

const order = (unit: string) => (unit === "wt%" ? 0 : unit === "index" ? 2 : 1);
const fmt = (v: number, unit: string) =>
  `${unit === "index" ? v.toFixed(2) : v.toFixed(1)}${unit === "%" ? " %" : unit === "index" ? "" : ` ${unit}`}`;

const targetSource = computed<MineralogySourceMeta | undefined>(() =>
  props.meta && props.target.mineralogy ? props.meta.sources[props.target.mineralogy.source] : undefined
);

const earthSource = computed<MineralogySourceMeta | undefined>(() =>
  props.meta ? props.meta.sources[EARTH_SOURCE] : undefined
);

const earthProcessed = computed(() => Boolean(props.analog.mineralogy));

function getRows(block: MineralogyBlock | null | undefined, source: MineralogySourceMeta | undefined) {
  if (block?.status !== "ok" || !block.values || !source) return [];
  return source.variables
    .map((v) => ({ v, value: block.values?.[v.key] }))
    .filter((r): r is { v: typeof r.v; value: number } => r.value != null && (r.v.unit === "index" || r.value >= TINY))
    .sort((a, b) => order(a.v.unit) - order(b.v.unit) || b.value - a.value);
}

const targetRows = computed(() => getRows(props.target.mineralogy, targetSource.value));
const earthRows = computed(() => getRows(props.analog.mineralogy, earthSource.value));
</script>

<template>
  <div v-if="props.meta" class="mineralogy-card">
    <div class="mineralogy-card__head">
      <div class="mineralogy-card__title-group">
        <h3 class="headline">MINERALOGY & COMPOSITION</h3>
        <span class="label mineralogy-badge">ORBITAL CONTEXT</span>
      </div>
      <RTag tone="outline">CONTEXT · NOT SCORED</RTag>
    </div>

    <p class="footnote mineralogy-note">
      Mineral distributions are informative context: planetary sensors measure primary igneous rock-forming silicates, while Earth EMIT observes secondary alteration minerals.
    </p>

    <div class="mineralogy-grid">
      <!-- Target Side -->
      <div class="mineralogy-side">
        <p class="label mineralogy-side__label">
          {{ props.bodyName.toUpperCase() }} TARGET
          <span v-if="targetSource" class="footnote">({{ targetSource.name.split(' (')[0] }})</span>
        </p>

        <p class="body mineralogy-summary">
          {{ props.target.mineralogy?.status === 'ok' ? props.target.mineralogy.summary : (props.target.mineralogy?.note ?? 'No mineral data available for this target.') }}
        </p>

        <dl v-if="targetRows.length > 0" class="mineralogy-list">
          <div v-for="{ v, value } in targetRows" :key="v.key" class="mineralogy-row">
            <dt class="label text-muted">{{ v.label }}</dt>
            <dd class="num font-semibold">{{ fmt(value, v.unit) }}</dd>
          </div>
        </dl>

        <details v-if="targetSource && targetSource.caveats.length > 0" class="mineralogy-details footnote">
          <summary class="cursor-pointer">Instrument limits & caveats</summary>
          <ul>
            <li v-for="c in targetSource.caveats" :key="c">{{ c }}</li>
          </ul>
        </details>
      </div>

      <!-- Earth Analog Side -->
      <div class="mineralogy-side">
        <p class="label mineralogy-side__label">
          EARTH ANALOG
          <span v-if="earthSource" class="footnote">(NASA EMIT L3)</span>
        </p>

        <p class="body mineralogy-summary">
          {{ earthProcessed ? props.analog.mineralogy?.summary : 'Earth orbital mineral data (EMIT) is optional context for arid swaths.' }}
        </p>

        <dl v-if="earthRows.length > 0" class="mineralogy-list">
          <div v-for="{ v, value } in earthRows" :key="v.key" class="mineralogy-row">
            <dt class="label text-muted">{{ v.label }}</dt>
            <dd class="num font-semibold">{{ fmt(value, v.unit) }}</dd>
          </div>
        </dl>

        <details v-if="earthSource && earthSource.caveats.length > 0" class="mineralogy-details footnote">
          <summary class="cursor-pointer">EMIT coverage & caveats</summary>
          <ul>
            <li v-for="c in earthSource.caveats" :key="c">{{ c }}</li>
          </ul>
        </details>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.mineralogy-card {
  padding: var(--space-4);
  background: var(--surface-raised);
  border: var(--stroke-hairline) solid var(--line-faint);
  display: grid;
  gap: var(--space-3);
}

.mineralogy-card__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.mineralogy-card__title-group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.mineralogy-badge {
  color: var(--signal);
}

.mineralogy-note {
  margin: 0;
  color: var(--ink-muted);
}

.mineralogy-grid {
  display: grid;
  gap: var(--space-4);

  @media (min-width: 640px) {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}

.mineralogy-side {
  padding: var(--space-3);
  background: var(--surface-sunken);
  border: var(--stroke-hairline) solid var(--line-faint);
  display: grid;
  gap: var(--space-2);
  align-content: start;
}

.mineralogy-side__label {
  color: var(--ink);
  margin: 0;
}

.mineralogy-summary {
  margin: 0;
  font-weight: 500;
  color: var(--ink);
  font-size: 13px;
  line-height: 1.4;
}

.mineralogy-list {
  margin: var(--space-2) 0 0;
  display: grid;
  gap: var(--space-1);
}

.mineralogy-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 2px;
  border-bottom: var(--stroke-hairline) solid var(--line-faint);
  font-size: 12px;
}

.text-muted {
  color: var(--ink-muted);
}

.mineralogy-details {
  margin-top: var(--space-2);
  color: var(--ink-muted);

  summary {
    cursor: pointer;
    font-weight: 500;
    color: var(--ink);

    &:hover {
      color: var(--signal);
    }
  }

  ul {
    margin: var(--space-1) 0 0;
    padding-left: var(--space-4);
    display: grid;
    gap: 4px;
  }
}
</style>

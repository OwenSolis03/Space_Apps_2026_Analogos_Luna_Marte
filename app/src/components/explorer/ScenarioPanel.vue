<script setup lang="ts">
// Scenario controls: mission case, weights per dimension, minimum MSI, road preference, new-only switch.
// Port of components/ScenarioPanel.tsx. Every explanation is one InfoButton + InfoPanel pair.
import { computed, ref } from "vue";
import type { Body, Dimension, DimensionInfo, Preset, Weights } from "@/lib/types";
import { DIMENSIONS } from "@/lib/types";
import { DIM_LABEL } from "@/lib/content";
import { CONTROL_EXPLANATION, DIM_EXPLANATION, EXPLANATION_HEADINGS, INTRO, PRESET_EXPLANATION } from "@/lib/explanations";
import InfoButton from "./InfoButton.vue";
import InfoPanel from "./InfoPanel.vue";

const props = defineProps<{
  body: Body;
  presets: Record<string, Preset>;
  presetId: string | null;
  weights: Weights;
  available: Set<Dimension>;
  dimInfo: Partial<Record<Dimension, DimensionInfo>>;
  bodyName: string;
  minScore: number;
  lambda: number;
  newOnly: boolean;
}>();

const emit = defineEmits<{
  preset: [id: string];
  weight: [d: Dimension, v: number];
  minScore: [v: number];
  lambda: [v: number];
  newOnly: [v: boolean];
}>();

// Keys of every explanation panel. "Show explanations" opens all of them.
const KEYS = [...DIMENSIONS.map((d) => `dim-${d}`), "min-score", "road", "new-only"];
const STORE_KEY = "paf.explanations";

// localStorage may be blocked (private mode, policies); the panel then just forgets the choice.
function readStored(): boolean {
  try {
    return localStorage.getItem(STORE_KEY) === "1";
  } catch {
    return false;
  }
}
function writeStored(on: boolean) {
  try {
    localStorage.setItem(STORE_KEY, on ? "1" : "0");
  } catch {
    // storage unavailable: nothing to remember
  }
}

const open = ref<Set<string>>(readStored() ? new Set(KEYS) : new Set());
const allOpen = computed(() => KEYS.every((k) => open.value.has(k)));

function toggle(key: string) {
  const next = new Set(open.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  open.value = next;
}

function toggleAll() {
  // Decide the next state first: reading the computed after the assignment would see the new state.
  const openAll = !allOpen.value;
  open.value = openAll ? new Set(KEYS) : new Set();
  writeStored(openAll);
}

const activeDims = computed(() => DIMENSIONS.filter((d) => props.available.has(d)));
const total = computed(() => activeDims.value.reduce((s, d) => s + props.weights[d], 0) || 1);
const presetText = computed(() => (props.presetId ? PRESET_EXPLANATION[props.presetId] : undefined));
const presetEntries = computed(() =>
  Object.entries(props.presets).filter(([, p]) => !p.applies_to || p.applies_to.includes(props.body)),
);

const share = (d: Dimension) =>
  props.available.has(d) ? `${Math.round((props.weights[d] / total.value) * 100)}%` : "n/a";
</script>

<template>
  <aside class="scenario" aria-label="Scenario">
    <div class="scenario__head">
      <h3 class="headline">Scenario</h3>
      <button
        type="button"
        class="switch tm-focusable"
        role="switch"
        :aria-checked="allOpen"
        aria-label="Show all explanations in this panel"
        @click="toggleAll"
      >
        <span class="switch__track" :class="{ 'is-on': allOpen }" aria-hidden="true">
          <span class="switch__thumb" />
        </span>
        <span class="label" aria-hidden="true">Show explanations</span>
      </button>
    </div>

    <fieldset class="group">
      <legend class="label group__legend">Mission case</legend>
      <p class="body">{{ INTRO }}</p>
      <div class="chips">
        <button
          v-for="[id, preset] in presetEntries"
          :key="id"
          type="button"
          class="tm-chip"
          :aria-pressed="presetId === id"
          @click="emit('preset', id)"
        >
          {{ preset.label }}
        </button>
      </div>
      <p v-if="presetText" class="body">{{ presetText }}</p>
    </fieldset>

    <div class="scenario__body">
    <fieldset class="group">
      <legend class="label group__legend">Weights by dimension</legend>
      <p class="body">{{ CONTROL_EXPLANATION.weightsShare }}</p>
      <div class="weights">
      <template v-for="d in DIMENSIONS" :key="d">
      <div class="control control--cell" :class="{ 'is-off': !available.has(d) }">
        <div class="control__row">
          <div class="control__label">
            <label :for="`w-${d}`" :title="dimInfo[d]?.description" class="label">
              {{ DIM_LABEL[d].label }}
              <span class="control__hint">· {{ DIM_LABEL[d].hint }}</span>
            </label>
            <InfoButton :id="`dim-${d}`" :title="DIM_LABEL[d].label" :open="open.has(`dim-${d}`)" @toggle="toggle(`dim-${d}`)" />
          </div>
          <output :for="`w-${d}`" class="label num">{{ share(d) }}</output>
        </div>
        <input
          :id="`w-${d}`"
          class="tm-range"
          type="range"
          min="0"
          max="100"
          step="5"
          :value="available.has(d) ? Math.round(weights[d] * 100) : 0"
          :disabled="!available.has(d)"
          @input="emit('weight', d, Number(($event.target as HTMLInputElement).value) / 100)"
        />
        <span v-if="!available.has(d)" class="tm-tag tm-tag--outline pending">NOT MODELLED FOR {{ bodyName.toUpperCase() }}</span>
      </div>
      <!-- The explanation spans the whole row, so an open panel never squeezes the columns. -->
      <InfoPanel class="weights__panel" :id="`dim-${d}`" :title="DIM_LABEL[d].label" :open="open.has(`dim-${d}`)" :explanation="DIM_EXPLANATION[d]" />
      </template>
      </div>
    </fieldset>

    <div class="filters">
    <div class="control">
      <div class="control__row">
        <div class="control__label">
          <label for="min-score" class="label">
            Minimum MSI: <span class="num">{{ Math.round(minScore * 100) }}</span>
          </label>
          <InfoButton id="min-score" title="Minimum MSI" :open="open.has('min-score')" @toggle="toggle('min-score')" />
        </div>
      </div>
      <input
        id="min-score"
        class="tm-range"
        type="range"
        min="0"
        max="95"
        step="5"
        :value="Math.round(minScore * 100)"
        @input="emit('minScore', Number(($event.target as HTMLInputElement).value) / 100)"
      />
      <InfoPanel id="min-score" title="Minimum MSI" :open="open.has('min-score')" :explanation="CONTROL_EXPLANATION.minScore" />
    </div>

    <fieldset class="group">
      <legend class="label group__legend">Logistics and novelty</legend>
      <div class="control">
        <div class="control__row">
          <div class="control__label">
            <label for="lambda" class="label">
              Prefer sites near a road <span class="num control__hint">λ = {{ lambda.toFixed(2) }} (0 = off)</span>
            </label>
            <InfoButton id="road" title="Prefer sites near a road" :open="open.has('road')" @toggle="toggle('road')" />
          </div>
        </div>
        <input
          id="lambda"
          class="tm-range"
          type="range"
          min="0"
          max="30"
          step="5"
          :value="Math.round(lambda * 100)"
          @input="emit('lambda', Number(($event.target as HTMLInputElement).value) / 100)"
        />
        <InfoPanel id="road" title="Prefer sites near a road" :open="open.has('road')" :explanation="CONTROL_EXPLANATION.road" />
      </div>

      <div class="control">
        <div class="control__row">
          <div class="control__label">
            <label class="check">
              <input
                type="checkbox"
                :checked="newOnly"
                @change="emit('newOnly', ($event.target as HTMLInputElement).checked)"
              />
              <span class="label">Only new candidates (hide well-known analog regions)</span>
            </label>
            <InfoButton id="new-only" title="Only new candidates" :open="open.has('new-only')" @toggle="toggle('new-only')" />
          </div>
        </div>
        <InfoPanel
          id="new-only"
          title="Only new candidates"
          :open="open.has('new-only')"
          :explanation="CONTROL_EXPLANATION.newOnly"
          :action-heading="EXPLANATION_HEADINGS.switch"
        />
      </div>
    </fieldset>
    </div>
    </div>
  </aside>
</template>

<style lang="scss" scoped>
.scenario {
  display: grid;
  align-content: start;
  gap: var(--space-5);
  padding: var(--space-4);
  background: var(--surface-raised);
  border: var(--stroke-hairline) solid var(--line-faint);
}

.scenario__body {
  display: grid;
  gap: var(--space-6);

  @media (min-width: 1024px) {
    grid-template-columns: minmax(0, 1fr) minmax(0, 20rem);
    align-items: start;
  }
}

.weights {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-4) var(--space-5);
}

.weights__panel {
  grid-column: 1 / -1;
}

.control--cell {
  align-content: start;
  padding-top: var(--space-3);
  border-top: var(--stroke-hairline) solid var(--line-faint);
}

.filters {
  display: grid;
  gap: var(--space-5);
  align-content: start;

  @media (min-width: 1024px) {
    padding-left: var(--space-5);
    border-left: var(--stroke-hairline) solid var(--line-faint);
  }
}

.scenario__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-3);
}

.switch {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 40px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ink-muted);
  cursor: pointer;

  &:hover {
    color: var(--ink);
  }
}

.switch__track {
  position: relative;
  width: 36px;
  height: 20px;
  border: var(--stroke-hairline) solid var(--line);
  background: var(--surface-sunken);

  &.is-on {
    background: var(--signal);
  }
}

.switch__thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  background: var(--ink);

  .is-on > & {
    transform: translateX(16px);
  }
}

.group {
  display: grid;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  border: 0;
  min-width: 0;
}

.group__legend {
  padding: 0;
  margin-bottom: var(--space-2);
  color: var(--ink-muted);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.control {
  display: grid;
  gap: var(--space-2);
  min-width: 0;

  &.is-off .label {
    color: var(--ink-muted);
  }
}

.control__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.control__label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.control__hint {
  color: var(--ink-muted);
}

.pending {
  justify-self: start;
}

.check {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;

  input {
    width: 16px;
    height: 16px;
    accent-color: var(--ink);
  }
}
</style>

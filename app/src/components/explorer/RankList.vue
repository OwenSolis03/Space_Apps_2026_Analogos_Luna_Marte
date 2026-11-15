<script setup lang="ts">
// Ranked targets for the current case. Port of components/RankList.tsx.
import { computed } from "vue";
import type { RankedTarget, UnrankedTarget } from "@/lib/msi";
import { fmtLat, fmtLon, pct } from "@/lib/msi";
import { DIM_LABEL } from "@/lib/content";
import RGlyph from "@/components/reticula/RGlyph.vue";

const props = defineProps<{
  ranked: RankedTarget[];
  unranked: UnrankedTarget[];
  total: number;
  selectedId: string | null;
}>();

const emit = defineEmits<{ select: [id: string] }>();

const missingNames = computed(() =>
  Array.from(new Set(props.unranked.flatMap((u) => u.missingDims))).map(
    (d) => DIM_LABEL[d]?.label.toLowerCase() ?? d,
  ),
);
</script>

<template>
  <section class="rank" aria-labelledby="rank-h">
    <header class="rank__head">
      <h3 id="rank-h" class="headline">Target ranking</h3>
      <span class="label num">{{ ranked.length }} / {{ total }}</span>
    </header>

    <p v-if="ranked.length === 0" class="rank__empty body">
      No target reaches that minimum MSI. Lower it to see results.
    </p>
    <ol v-else class="rank__list">
      <li v-for="(r, i) in ranked" :key="r.target.id">
        <button
          type="button"
          class="rank__item tm-focusable"
          :aria-current="r.target.id === selectedId ? 'true' : undefined"
          @click="emit('select', r.target.id)"
        >
          <span class="label num rank__index">{{ String(i + 1).padStart(2, "0") }}</span>
          <span class="rank__name">
            <span class="rank__title">{{ r.target.name }}</span>
            <span class="label num rank__meta">{{ r.target.id }} · {{ fmtLat(r.target.lat) }}, {{ fmtLon(r.target.lon) }}</span>
          </span>
          <span class="rank__score num">
            {{ pct(r.best) }}
            <span class="rank__unit label">MSI</span>
          </span>
          <RGlyph v-if="r.target.id === selectedId" class="rank__tick" name="tick-left" tone="signal" :size="16" />
        </button>
      </li>
    </ol>

    <footer v-if="unranked.length > 0" class="rank__foot">
      <p class="footnote">
        <strong>{{ unranked.length }} targets</strong> are not ranked for this case: no
        {{ missingNames.join(", ") }} data at these sites ({{ unranked.slice(0, 3).map((u) => u.target.name).join(", ") }}{{ unranked.length > 3 ? ", …" : "" }}).
      </p>
    </footer>
  </section>
</template>

<style lang="scss" scoped>
.rank {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--surface-raised);
  border: var(--stroke-hairline) solid var(--line-faint);
}

.rank__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
}

.rank__empty {
  padding: 0 var(--space-4) var(--space-4);
}

.rank__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 32rem;
  overflow: auto;
  border-top: var(--stroke-hairline) solid var(--line-faint);
}

.rank__item {
  position: relative;
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  min-height: 56px;
  padding: var(--space-2) var(--space-6) var(--space-2) var(--space-3);
  border: 0;
  border-bottom: var(--stroke-hairline) solid var(--line-faint);
  background: transparent;
  color: var(--ink);
  text-align: left;
  cursor: pointer;

  &:hover {
    background: var(--surface);
  }

  &[aria-current="true"] {
    background: var(--ink);
    color: var(--surface);

    .rank__meta,
    .rank__unit,
    .rank__index {
      color: var(--surface);
    }
  }
}

.rank__index,
.rank__unit,
.rank__meta {
  color: var(--ink-muted);
}

.rank__name {
  display: grid;
  min-width: 0;
}

.rank__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  text-transform: uppercase;
}

.rank__meta {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank__score {
  display: grid;
  justify-items: end;
  font-weight: 500;
}

.rank__tick {
  position: absolute;
  right: var(--space-2);
  top: 50%;
  transform: translateY(-50%);
}

.rank__foot {
  padding: var(--space-3) var(--space-4);
  border-top: var(--stroke-hairline) solid var(--line-faint);
  background: var(--surface);
  color: var(--ink-muted);
}
</style>

<script setup lang="ts">
// TEMPORARY component gallery for phase 2 (every RETÍCULA component in every variant).
// Remove this file, its route in router.ts, and the `/kit` link in phase 9.
import RGlyph, { type GlyphName } from "@/components/reticula/RGlyph.vue";
import RPanel from "@/components/reticula/RPanel.vue";
import RTag from "@/components/reticula/RTag.vue";
import RButton from "@/components/reticula/RButton.vue";
import RIconButton from "@/components/reticula/RIconButton.vue";
import RProgress from "@/components/reticula/RProgress.vue";
import RReadout from "@/components/reticula/RReadout.vue";
import RHeadline from "@/components/reticula/RHeadline.vue";
import RFrame from "@/components/reticula/RFrame.vue";
import RHazard from "@/components/reticula/RHazard.vue";
import RDotGrid from "@/components/reticula/RDotGrid.vue";
import RBarcode from "@/components/reticula/RBarcode.vue";

const glyphNames: GlyphName[] = [
  "plus", "close", "tick-left", "tick-right", "bracket", "corner",
  "slash", "slash-pair", "chevron-down", "chevron-right", "dots", "dot",
];
</script>

<template>
  <main class="page kit">
    <section class="kit__group">
      <p class="label">GLYPH</p>
      <div class="kit__glyphs">
        <div v-for="n in glyphNames" :key="n" class="kit__glyph">
          <RGlyph :name="n" :size="40" />
          <span class="label kit__muted">{{ n }}</span>
        </div>
      </div>
    </section>

    <section class="kit__group">
      <p class="label">PANEL</p>
      <div class="kit__row">
        <RPanel class="kit__cell" tone="signal" label="Encryption protocols" note="Load.4139.A64" code="A0." marks />
        <RPanel class="kit__cell" tone="tint" label="Set" note="Module 7" code="07" />
        <RPanel class="kit__cell" tone="graphite" label="Level" code="2.C" />
        <RPanel class="kit__cell" tone="raised" label="Verified" code="3.C" />
        <RPanel class="kit__cell" tone="sunken" label="Unassigned" note="Reserved" />
        <RPanel class="kit__cell" tone="outline" :chamfer="false" label="Outline" note="No chamfer" code="D1" />
      </div>
    </section>

    <section class="kit__group">
      <p class="label">TAG</p>
      <div class="kit__row">
        <RTag>Operational</RTag>
        <RTag tone="signal">Started</RTag>
        <RTag tone="outline">Verified</RTag>
        <RTag tone="outline" bracket>Crew safety</RTag>
        <RTag tone="graphite" bracket>System error</RTag>
      </div>
    </section>

    <section class="kit__group">
      <p class="label">BUTTON</p>
      <div class="kit__row">
        <RButton>Start load</RButton>
        <RButton arrow>Continue</RButton>
        <RButton variant="secondary">Cancel</RButton>
        <RButton disabled>Unavailable</RButton>
      </div>
    </section>

    <section class="kit__group">
      <p class="label">ICON BUTTON</p>
      <div class="kit__row">
        <RIconButton label="Add" glyph="plus" />
        <RIconButton label="Close" glyph="close" />
        <RIconButton label="More options" glyph="dots" />
        <RIconButton label="Selected" glyph="plus" :pressed="true" />
        <RIconButton label="Unavailable" glyph="plus" disabled />
      </div>
    </section>

    <section class="kit__group">
      <p class="label">PROGRESS</p>
      <div class="kit__col">
        <RProgress label="Calibration" :value="0.62" />
        <RProgress label="Load.4139" :value="0.18" />
        <RProgress label="Verification" :value="1" :hazard="false" />
      </div>
    </section>

    <section class="kit__group">
      <p class="label">READOUT</p>
      <div class="kit__narrow">
        <RReadout
          title="System check"
          :items="[
            { label: 'Ext', value: 'Operational', status: true },
            { label: 'Pos', value: '34.4-111' },
            { label: 'Crs', value: 'A to B v Del' },
            { label: 'Safety level', value: 'Started', status: true, tone: 'signal' },
            { label: 'Sys', value: '00x0000000005A' },
          ]"
        />
      </div>
    </section>

    <section class="kit__group">
      <p class="label">HEADLINE</p>
      <div class="kit__narrow kit__stack">
        <RHeadline size="lg" as="h1" kicker="Sector 45-A46AF" title="Console 07" subtitle="Surface mapping" by="By mapping team" />
        <RHeadline size="md" kicker="Chapter 2" title="Beyond" rule="graphite" />
        <RHeadline size="sm" title="Scheduled return to base" subtitle="Deadline: 2324" />
      </div>
    </section>

    <section class="kit__group">
      <p class="label">FRAME</p>
      <div class="kit__row">
        <div class="kit__frame-wide"><RFrame ratio="16 / 9" caption="FIG.003 Travel sector" label="Travel sector map" /></div>
        <div class="kit__frame-a"><RFrame ratio="3 / 4" caption="FIG-A" label="Portrait" /></div>
        <div class="kit__frame-b"><RFrame ratio="1 / 1" caption="FIG-2.5" label="Detail" /></div>
      </div>
    </section>

    <section class="kit__group">
      <p class="label">HAZARD</p>
      <div class="kit__narrow kit__stack">
        <div><p class="label kit__muted">Graphite</p><RHazard /></div>
        <div><p class="label kit__muted">Signal</p><RHazard tone="signal" :height="16" /></div>
      </div>
    </section>

    <section class="kit__group">
      <p class="label">DOT GRID</p>
      <div class="kit__stack">
        <div><p class="label kit__muted">Graphite with lead</p><RDotGrid :cols="24" :rows="3" lead /></div>
        <div><p class="label kit__muted">Faint</p><RDotGrid :cols="10" :rows="4" tone="faint" /></div>
        <div><p class="label kit__muted">Signal</p><RDotGrid :cols="6" :rows="2" tone="signal" /></div>
      </div>
    </section>

    <section class="kit__group">
      <p class="label">BARCODE</p>
      <div class="kit__narrow kit__stack">
        <RBarcode />
        <RBarcode tone="ink" :segments="[6, 6, 2, 2, 8, 2, 4, 4, 2, 10]" />
        <RBarcode tone="graphite" :segments="[14, 3, 3, 3, 3, 3, 8, 2, 2, 2]" />
      </div>
    </section>
  </main>
</template>

<style lang="scss" scoped>
.kit {
  display: grid;
  gap: var(--space-8);
}

.kit__group {
  display: grid;
  gap: var(--space-4);
}

.kit__row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-5);
  align-items: flex-start;
}

.kit__col,
.kit__stack {
  display: grid;
  gap: var(--space-5);
}

.kit__narrow {
  max-width: 420px;
}

.kit__cell {
  width: 232px;
}

.kit__glyphs {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
  gap: var(--space-5);
}

.kit__glyph {
  display: grid;
  justify-items: center;
  gap: var(--space-2);
}

.kit__muted {
  color: var(--ink-muted);
}

.kit__frame-wide {
  width: 420px;
}

.kit__frame-a {
  width: 140px;
}

.kit__frame-b {
  width: 180px;
}
</style>

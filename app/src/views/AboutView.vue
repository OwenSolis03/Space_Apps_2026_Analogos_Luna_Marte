<script setup lang="ts">
// About (SEC.06): the team, its track record, the crew, and the acknowledgements.
import PageHero from "@/components/layout/PageHero.vue";
import SectionBlock from "@/components/layout/SectionBlock.vue";
import RButton from "@/components/reticula/RButton.vue";
import RGlyph from "@/components/reticula/RGlyph.vue";
import RPanel from "@/components/reticula/RPanel.vue";
import RTag from "@/components/reticula/RTag.vue";
import { ACKNOWLEDGEMENTS, CREW, STORY, STORY_CLOSING, TRACK_RECORD } from "@/content/about";
import isotipo from "@/assets/Isotipo.svg";
</script>

<template>
  <main class="page">
    <PageHero code="SEC.06" title="ENDURANCE CXXV" subtitle="FROM DATA TO ACTION">
      <template #aside>
        <div class="logo">
          <img :src="isotipo" alt="Endurance CXXV logo" width="280" />
        </div>
      </template>
    </PageHero>

    <SectionBlock id="story" code="SEC.06" title="THE TEAM" subtitle="WHO WE ARE">
      <div class="story">
        <p v-for="(p, i) in STORY" :key="i" class="prose">{{ p }}</p>
        <p class="quote story__closing">{{ STORY_CLOSING }}</p>
      </div>
    </SectionBlock>

    <SectionBlock id="track-record" code="SEC.06" title="TRACK RECORD" subtitle="COMPETITIONS, EVENTS AND RESEARCH">
      <ol class="log">
        <li v-for="(t, i) in TRACK_RECORD" :key="i" class="log__row">
          <span class="label log__year">{{ t.year }}</span>
          <span class="log__event body">{{ t.event }}</span>
          <RTag v-if="t.award" :tone="t.tone ?? 'graphite'" bracket>{{ t.award }}</RTag>
        </li>
      </ol>
    </SectionBlock>

    <SectionBlock id="members" code="SEC.06" title="CREW" subtitle="SIX STUDENTS">
      <ul class="crew">
        <li v-for="(m, i) in CREW" :key="i" class="crew__item">
          <template v-if="m.photo">
            <figure class="portrait">
              <img class="portrait__img" :src="m.photo" :alt="`Portrait of ${m.name}`" loading="lazy" />
            </figure>
            <p class="label crew__code">CREW.0{{ i + 1 }}</p>
            <p class="headline crew__name">{{ m.name }}</p>
            <a
              class="label crew__link"
              :href="m.linkedin"
              target="_blank"
              rel="noreferrer"
              :aria-label="`LinkedIn profile of ${m.name}`"
            >
              LINKEDIN <RGlyph name="chevron-right" :size="14" />
            </a>
          </template>
        </li>
      </ul>
    </SectionBlock>

    <section id="acknowledgements" class="section" aria-labelledby="ack-h">
      <p id="ack-h" class="label section__label">ACKNOWLEDGEMENTS</p>
      <RPanel tone="graphite" label="ACARUS · UNIVERSIDAD DE SONORA" class="ack">
        <p class="body ack__text">{{ ACKNOWLEDGEMENTS }}</p>
        <RButton variant="secondary" href="https://acarus.unison.mx/" arrow>VISIT ACARUS</RButton>
      </RPanel>
    </section>
  </main>
</template>

<style lang="scss" scoped>
.logo {
  display: grid;
  place-items: center;
  padding: var(--space-5);
  background: var(--surface-raised);
  border: var(--stroke-hairline) solid var(--line-faint);

  img {
    width: 100%;
    max-width: 280px;
    height: auto;
  }
}

.story {
  display: grid;
  gap: var(--space-5);
  max-width: 64ch;
}

.story__closing {
  margin-top: var(--space-4);
  color: var(--ink);
}

.log {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  max-width: 64ch;
}

.log__row {
  display: grid;
  grid-template-columns: 4rem minmax(0, 1fr);
  align-items: center;
  gap: var(--space-2) var(--space-4);
  padding-block: var(--space-3);
  border-top: var(--stroke-hairline) solid var(--line-faint);

  .tm-tag {
    grid-column: 2;
    justify-self: start;
  }
}

.log__year {
  color: var(--ink-muted);
}

.log__event {
  color: var(--ink);
}

.crew {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-6) var(--space-4);
  grid-template-columns: repeat(2, minmax(0, 1fr));

  @media (min-width: 900px) {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.crew__item {
  display: grid;
  gap: var(--space-2);
  align-content: start;
  min-width: 0;
}

.portrait {
  margin: 0;
  aspect-ratio: 1 / 1;
  border: var(--stroke-hairline) solid var(--line);
  clip-path: polygon(0 0, calc(100% - var(--chamfer-md)) 0, 100% var(--chamfer-md), 100% 100%, 0 100%);
  overflow: hidden;
}

.portrait__img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.crew__code {
  color: var(--ink-muted);
}

.crew__name {
  font-weight: 500;
  overflow-wrap: anywhere;
}

.crew__link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  justify-self: start;
  min-height: 40px;
  color: var(--ink);
}

.section {
  padding-block: var(--space-9) 0;
}

.section__label {
  margin-bottom: var(--space-5);
  color: var(--ink-muted);
}

.ack {
  min-height: 0;
  padding: var(--space-6);
  display: grid;
  gap: var(--space-4);
  justify-items: start;
}

.ack :deep(.tm-btn--secondary) {
  color: var(--on-graphite);
  border-color: var(--on-graphite);
}

.ack__text {
  margin: 0;
  max-width: 64ch;
  color: var(--on-graphite);
}
</style>

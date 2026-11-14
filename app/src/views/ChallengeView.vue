<script setup lang="ts">
// Challenge (SEC.02): the hackathon, the challenge we answer, what it warns about, and what we do.
import PageHero from "@/components/layout/PageHero.vue";
import SectionBlock from "@/components/layout/SectionBlock.vue";
import DataTable from "@/components/layout/DataTable.vue";
import RButton from "@/components/reticula/RButton.vue";
import RPanel from "@/components/reticula/RPanel.vue";
import RReadout from "@/components/reticula/RReadout.vue";
import {
  CALENDAR,
  CHALLENGE_TITLE,
  DIFFERENTIATOR,
  HACKATHON_COPY,
  LOCAL_EVENT,
  NASA_ASKS_ROWS,
  OFFICIAL_URL,
  OUR_CHALLENGE,
  WARNINGS,
} from "@/content/challenge";

const calendarItems = CALENDAR.map((c) => ({ label: c.label, value: c.value }));
const eventName: string = LOCAL_EVENT.name;
const eventWhere: string = `${LOCAL_EVENT.place}, ${LOCAL_EVENT.dates}`;
const eventUrl: string = LOCAL_EVENT.url;
</script>

<template>
  <main class="page">
    <PageHero code="SEC.02" title="CHALLENGE" subtitle="NASA SPACE APPS CHALLENGE 2026" />

    <SectionBlock id="hackathon" code="SEC.02" title="THE HACKATHON" subtitle="A GLOBAL WEEKEND, HOSTED LOCALLY">
      <div class="two">
        <div class="stack">
          <p class="prose">{{ HACKATHON_COPY }}</p>
          <div>
            <RButton variant="secondary" href="https://www.spaceappschallenge.org" arrow>VISIT SPACE APPS</RButton>
          </div>
        </div>
        <div class="stack">
          <p class="label">OUR LOCAL EVENT</p>
          <p class="headline">{{ eventName }}</p>
          <p class="body">{{ eventWhere }}</p>
          <div>
            <RButton variant="secondary" :href="eventUrl" arrow>VISIT THE LOCAL EVENT</RButton>
          </div>
          <RReadout
            title="EVENT CALENDAR"
            :items="calendarItems"
          />
        </div>
      </div>
    </SectionBlock>

    <SectionBlock id="challenge" code="SEC.02" title="OUR CHALLENGE" subtitle="THE OFFICIAL TITLE, AND THE THREE THINGS EVERY TEAM HAS TO EXPLAIN">
      <div class="stack">
        <p class="lead challenge__title">{{ CHALLENGE_TITLE }}</p>
        <div>
          <RButton variant="secondary" :href="OFFICIAL_URL" arrow>READ THE OFFICIAL CHALLENGE</RButton>
        </div>
        <div class="threes">
          <RPanel v-for="c in OUR_CHALLENGE" :key="c.code" tone="raised" :label="c.code" class="three">
            <p class="headline">{{ c.title }}</p>
          </RPanel>
        </div>
      </div>
    </SectionBlock>

    <SectionBlock id="warnings" code="SEC.02" title="WHAT THE CHALLENGE WARNS ABOUT" subtitle="FOUR POINTS THAT SHAPE THE METHOD">
      <ol class="warnings body">
        <li v-for="(w, i) in WARNINGS" :key="i">{{ w }}</li>
      </ol>
    </SectionBlock>

    <SectionBlock id="ask" code="SEC.02" title="WHAT NASA ASKS · WHAT WE DO" subtitle="THE CHALLENGE'S QUESTIONS AND OUR ANSWER TO EACH">
      <DataTable caption="What NASA asks, what the project does, and why it is different">
        <thead>
          <tr>
            <th class="label" scope="col">WHAT NASA ASKS</th>
            <th class="label" scope="col">WHAT THE PROJECT DOES</th>
            <th class="label" scope="col">WHY IT IS DIFFERENT</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in NASA_ASKS_ROWS" :key="r.ask">
            <td>{{ r.ask }}</td>
            <td class="body">{{ r.does }}</td>
            <td class="body">{{ r.different }}</td>
          </tr>
        </tbody>
      </DataTable>
      <p class="quote differentiator">{{ DIFFERENTIATOR }}</p>
      <div>
        <RButton to="/how-it-works" arrow>SEE HOW IT WORKS</RButton>
      </div>
    </SectionBlock>
  </main>
</template>

<style lang="scss" scoped>
.two {
  display: grid;
  gap: var(--space-7);

  @media (min-width: 900px) {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}

.stack {
  display: grid;
  gap: var(--space-4);
  align-content: start;
  min-width: 0;

  p {
    margin: 0;
  }
}

.challenge__title {
  max-width: 40ch;
  color: var(--ink);
}

.threes {
  display: grid;
  gap: var(--space-4);

  @media (min-width: 900px) {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.three {
  min-height: 0;
  padding: var(--space-4);
}

.three p {
  margin: 0;
}

.warnings {
  margin: 0;
  padding-left: var(--space-5);
  display: grid;
  gap: var(--space-2);
  max-width: 64ch;
}

.differentiator {
  max-width: 64ch;
  margin: var(--space-5) 0 0;
  color: var(--ink);
}
</style>

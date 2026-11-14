<script setup lang="ts">
// Home: the solar system is the navigation. Results is the sun; each planet is one of the other sections.
import RHeadline from "@/components/reticula/RHeadline.vue";
import RReadout from "@/components/reticula/RReadout.vue";
import RDotGrid from "@/components/reticula/RDotGrid.vue";
import SolarSystem from "@/components/home/SolarSystem.vue";
import SectionRail from "@/components/home/SectionRail.vue";
import { HOME_FACTS } from "@/content/facts";
import { PROJECT_NAME } from "@/content/sections";
</script>

<template>
  <main class="home">
    <p class="sr-only">
      Navigation. The sun opens RESULTS. Each planet opens one section: CHALLENGE, HOW IT WORKS, ALGORITHM,
      DATA and ABOUT US. Press Tab to move between bodies and Enter to open one.
    </p>
    <a class="skip-link sr-only" href="#section-list">Skip to section list</a>

    <div class="home__scene">
      <div class="home__intro">
        <RHeadline
          size="sm"
          as="h1"
          kicker="NASA SPACE APPS CHALLENGE 2026 · ENDURANCE CXXV"
          :title="PROJECT_NAME"
          subtitle="EARTH SITES THAT STAND IN FOR THE MOON AND MARS"
        />
      </div>

      <SolarSystem class="home__solar" />

      <div class="home__facts">
        <RReadout :items="HOME_FACTS.map((f) => ({ label: f.label, value: f.value }))" />
      </div>

      <div class="home__cue">
        <RDotGrid :cols="6" :rows="2" tone="graphite" lead />
        <p class="label">SELECT A BODY TO NAVIGATE</p>
      </div>
    </div>

    <SectionRail />
  </main>
</template>

<style lang="scss" scoped>
.home__scene {
  position: relative;
  padding: var(--space-6);
}

.home__intro {
  max-width: 320px;
}

.home__facts {
  width: min(320px, 100%);
}

.home__cue {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

// Overlays sit in the corners of the scene on wide screens.
// The skip link targets the phone list, which is hidden on wide screens, so it is hidden too.
@media (min-width: 768px) {
  .skip-link {
    display: none;
  }

  .home__intro {
    position: absolute;
    top: var(--space-6);
    left: var(--space-6);
    z-index: 1;
  }

  .home__facts {
    position: absolute;
    left: var(--space-6);
    bottom: var(--space-6);
    z-index: 1;
  }

  .home__cue {
    position: absolute;
    right: var(--space-6);
    bottom: var(--space-6);
    z-index: 1;
  }

  // Keeps the top planet labels clear of the title block.
  .home__solar {
    margin-top: var(--space-7);
  }
}

// Phones: the scene stacks vertically, the solar system is a compact scene above the section list.
@media (max-width: 767px) {
  .home__scene {
    display: grid;
    gap: var(--space-5);
    padding: var(--space-5) var(--space-4);
  }

  .home__intro,
  .home__facts,
  .home__cue {
    order: 0;
  }

  .home__solar {
    order: 1;
  }

  .home__cue {
    order: 2;
  }
}
</style>

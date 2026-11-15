<script setup lang="ts">
// Home: the solar system is the navigation. Results is the sun; each planet opens one of the other sections.
import { ref } from "vue";
import RHeadline from "@/components/reticula/RHeadline.vue";
import RDotGrid from "@/components/reticula/RDotGrid.vue";
import SolarSystem from "@/components/home/SolarSystem.vue";
import SectionRail from "@/components/home/SectionRail.vue";
import AppLogo from "@/components/layout/AppLogo.vue";
import AppLogoIntro from "@/components/layout/AppLogoIntro.vue";
import { PROJECT_NAME, PROJECT_TAGLINE } from "@/content/sections";

const showIntro = ref(true);

function onIntroComplete() {
  showIntro.value = false;
}

function replayIntro() {
  showIntro.value = true;
}
</script>

<template>
  <main class="home">
    <!-- Center stage intro animation on Home load -->
    <AppLogoIntro
      v-if="showIntro"
      target-selector="#home-resting-logo"
      @complete="onIntroComplete"
    />

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
          :subtitle="PROJECT_TAGLINE"
        >
          <template #title>
            <div
              id="home-resting-logo"
              class="home__logo-anchor"
              :style="{ visibility: showIntro ? 'hidden' : 'visible' }"
              title="Replay intro animation"
              tabindex="0"
              role="button"
              :aria-label="`${PROJECT_NAME}, replay intro animation`"
              @click="replayIntro"
              @keydown.enter="replayIntro"
              @keydown.space.prevent="replayIntro"
            >
              <AppLogo size="md" layout="responsive" />
            </div>
          </template>
        </RHeadline>
      </div>

      <SolarSystem class="home__solar" />

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
  max-width: min(380px, 100%);
}

.home__logo-anchor {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  border-radius: var(--radius-0, 0);
  transition: opacity 0.2s ease;

  &:hover {
    opacity: 0.85;
  }

  &:focus-visible {
    outline: 2px solid var(--signal);
    outline-offset: 4px;
  }
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

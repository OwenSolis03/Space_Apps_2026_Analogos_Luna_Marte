<script setup lang="ts">
// Sticky header: project placeholder logo and the six section links.
import { computed, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import RGlyph from "@/components/reticula/RGlyph.vue";
import RIconButton from "@/components/reticula/RIconButton.vue";
import AppLogo from "@/components/layout/AppLogo.vue";
import { NAV_SECTIONS, PROJECT_NAME } from "@/content/sections";

const route = useRoute();
const open = ref(false);
const current = computed(() => route.name);
</script>

<template>
  <header class="app-header">
    <div class="page app-header__inner">
      <RouterLink to="/" class="app-header__brand" :aria-label="`${PROJECT_NAME}, home`">
        <AppLogo size="sm" />
      </RouterLink>

      <nav class="app-header__nav" :class="{ 'is-open': open }" aria-label="Sections">
        <ul>
          <li v-for="s in NAV_SECTIONS" :key="s.name">
            <RouterLink
              :to="{ name: s.name }"
              class="label"
              :class="{ 'is-current': current === s.name }"
              :aria-current="current === s.name ? 'page' : undefined"
              @click="open = false"
            >
              <RGlyph v-if="current === s.name" name="tick-left" tone="signal" :size="16" />
              {{ s.label }}
            </RouterLink>
          </li>
        </ul>
      </nav>

      <RIconButton
        class="app-header__toggle"
        label="Open navigation"
        glyph="dots"
        :pressed="open"
        @click="open = !open"
      />
    </div>
  </header>
</template>

<style lang="scss" scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--surface);
  border-bottom: var(--stroke-hairline) solid var(--line);
}

.app-header__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  min-height: 64px;
  padding-block: var(--space-3);
}

.app-header__brand {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  text-decoration: none;
}

.app-header__mark {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border: var(--stroke-hairline) solid var(--line);
}

.app-header__nav {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--surface);
  border-bottom: var(--stroke-hairline) solid var(--line);
  padding: var(--space-4);

  &.is-open {
    display: block;
  }

  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: var(--space-1);
  }

  a {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    min-height: 44px;
    color: var(--ink-muted);
    text-decoration: none;
  }

  a.is-current {
    color: var(--ink);
  }

  a:hover {
    color: var(--ink);
  }
}

.app-header__toggle {
  display: inline-flex;
}


@media (min-width: 900px) {
  .app-header__nav {
    display: block;
    position: static;
    background: transparent;
    border: 0;
    padding: 0;

    ul {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-4);
    }

    a {
      min-height: 0;
    }
  }

  .app-header__toggle {
    display: none;
  }
}
</style>

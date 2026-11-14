<script setup lang="ts">
// Mobile section list (below 768px): the same six sections as the solar system, as large touch rows.
import { RouterLink } from "vue-router";
import RGlyph from "@/components/reticula/RGlyph.vue";
import RPanel from "@/components/reticula/RPanel.vue";
import { NAV_SECTIONS } from "@/content/sections";
</script>

<template>
  <nav id="section-list" class="rail" aria-label="Section list">
    <ul class="rail__list">
      <li v-for="s in NAV_SECTIONS" :key="s.name">
        <RPanel :tone="s.name === 'results' ? 'signal' : 'raised'" class="rail__panel">
          <RouterLink :to="{ name: s.name }" class="rail__link">
            <span class="label">{{ s.code }}</span>
            <span class="headline">{{ s.label }}</span>
            <RGlyph name="chevron-right" :size="24" />
          </RouterLink>
        </RPanel>
      </li>
    </ul>
  </nav>
</template>

<style lang="scss" scoped>
.rail {
  display: none;
  padding: var(--space-5) var(--space-4) var(--space-7);
}

.rail__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-2);
}

.rail__panel {
  min-height: 0;
  padding: 0;
}

.rail__link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  min-height: 56px;
  padding: var(--space-3) var(--space-4);
  color: inherit;
  text-decoration: none;
}

// Shown on phones only; on larger screens the solar system is the navigation.
@media (max-width: 767px) {
  .rail {
    display: block;
  }
}
</style>

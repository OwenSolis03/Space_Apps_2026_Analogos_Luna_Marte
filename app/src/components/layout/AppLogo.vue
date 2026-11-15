<script setup lang="ts">
import { useId } from "vue";

withDefaults(
  defineProps<{
    size?: "xs" | "sm" | "md" | "lg" | "hero";
    iconOnly?: boolean;
    ariaLabel?: string;
  }>(),
  {
    size: "md",
    iconOnly: false,
    ariaLabel: "PROTOTERRA",
  },
);

const uid = useId();
</script>

<template>
  <div
    class="app-logo"
    :class="[`app-logo--${size}`, { 'app-logo--icon-only': iconOnly }]"
    role="img"
    :aria-label="ariaLabel"
  >
    <svg
      class="app-logo__icon"
      viewBox="0 -32 560 304"
      aria-hidden="true"
    >
      <defs>
        <pattern :id="`odots-${uid}`" width="16" height="16" patternUnits="userSpaceOnUse" x="6" y="6">
          <rect width="4" height="4" fill="#5f95c6" />
        </pattern>
        <pattern :id="`mdots-${uid}`" width="16" height="16" patternUnits="userSpaceOnUse" x="6" y="6">
          <rect width="4" height="4" fill="#716f70" />
        </pattern>
        <pattern :id="`hatch-${uid}`" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="3" height="12" fill="#8c3418" />
        </pattern>
        <clipPath :id="`earth-${uid}`">
          <circle cx="280" cy="120" r="104" />
        </clipPath>
      </defs>

      <!-- Orbit Ring and Markers -->
      <circle cx="280" cy="120" r="128" fill="none" stroke="#716f70" stroke-width="1.5" />
      <rect x="276" y="-12" width="8" height="8" fill="#ff8500" />
      <path d="M280 236 L280 241 M280 247 L280 252 M272 244 L277 244 M283 244 L288 244" stroke="#716f70" stroke-width="1.5" fill="none" />

      <!-- Earth Base and Ocean Pattern -->
      <circle cx="280" cy="120" r="104" fill="#3f7cb5" />
      <rect x="176" y="16" width="208" height="208" :fill="`url(#odots-${uid})`" :clip-path="`url(#earth-${uid})`" />

      <!-- Continents (Land) -->
      <path
        d="M232 22 L300 18 L318 34 L300 48 L292 62 L280 70 L272 84 L262 96 L268 104 L276 118 L284 128 L296 132 L318 140 L330 152 L326 172 L312 190 L302 210 L296 224 L290 214 L288 190 L282 168 L276 150 L270 138 L262 124 L254 110 L246 96 L236 78 L226 60 L220 40 Z"
        fill="#3f8f4f"
        :clip-path="`url(#earth-${uid})`"
      />

      <!-- Moon (halo cutout, body, pattern) -->
      <g>
        <circle cx="152" cy="120" r="110" class="app-logo__halo" />
        <circle cx="152" cy="120" r="104" fill="#8f8d8e" />
        <circle cx="152" cy="120" r="102" :fill="`url(#mdots-${uid})`" />
      </g>

      <!-- Mars (halo cutout, body, hatch) -->
      <g>
        <circle cx="408" cy="120" r="110" class="app-logo__halo" />
        <circle cx="408" cy="120" r="104" fill="#a8401f" />
        <circle cx="408" cy="120" r="102" :fill="`url(#hatch-${uid})`" />
      </g>
    </svg>

    <div v-if="!iconOnly" class="app-logo__bar" aria-hidden="true" />
    <span v-if="!iconOnly" class="app-logo__name">PROTOTERRA</span>
  </div>
</template>

<style lang="scss" scoped>
.app-logo {
  display: inline-flex;
  align-items: center;
  user-select: none;
  text-decoration: none;
  vertical-align: middle;
}

.app-logo__icon {
  display: block;
  flex-shrink: 0;
  overflow: visible;
  height: 1em;
  width: auto;
}

.app-logo__halo {
  fill: var(--surface, #dfdfdf);
}

.app-logo__bar {
  flex-shrink: 0;
  background: var(--signal, #ff8500);
}

.app-logo__name {
  font-family: var(--font-display);
  font-weight: 300;
  line-height: 1;
  letter-spacing: 0.12em;
  color: var(--ink);
  white-space: nowrap;
}

// Size variants
.app-logo--xs {
  font-size: 13px;
  gap: 6px;
  .app-logo__icon { height: 18px; }
  .app-logo__bar { width: 2px; height: 14px; }
}

.app-logo--sm {
  font-size: 15px;
  gap: 8px;
  .app-logo__icon { height: 26px; }
  .app-logo__bar { width: 2px; height: 20px; }
}

.app-logo--md {
  font-size: 24px;
  gap: 12px;
  .app-logo__icon { height: 38px; }
  .app-logo__bar { width: 3px; height: 28px; }
}

.app-logo--lg {
  font-size: 36px;
  gap: 16px;
  .app-logo__icon { height: 56px; }
  .app-logo__bar { width: 4px; height: 44px; }
}

.app-logo--hero {
  font-size: clamp(28px, 4.5vw, 64px);
  gap: clamp(8px, 1.2vw, 20px);
  .app-logo__icon { height: clamp(48px, 7.5vw, 108px); }
  .app-logo__bar { width: clamp(2.5px, 0.4vw, 5px); height: clamp(34px, 5.5vw, 76px); }
}
</style>

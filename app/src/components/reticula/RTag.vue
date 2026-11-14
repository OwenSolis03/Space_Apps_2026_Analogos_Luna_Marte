<script setup lang="ts">
// RETÍCULA Tag: status label, 1 to 3 words, optionally wrapped in [ brackets ].
withDefaults(
  defineProps<{
    tone?: "graphite" | "signal" | "outline";
    bracket?: boolean;
  }>(),
  { tone: "graphite", bracket: false },
);
</script>

<template>
  <span class="tm-tag" :class="`tm-tag--${tone}`"><template v-if="bracket">[ </template><slot /><template v-if="bracket"> ]</template></span>
</template>

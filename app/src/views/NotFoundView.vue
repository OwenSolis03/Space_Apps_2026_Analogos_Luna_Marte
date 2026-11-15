<script setup lang="ts">
// Catch-all route: unknown addresses land here with a way back to Home.
import RHeadline from "@/components/reticula/RHeadline.vue";
import RButton from "@/components/reticula/RButton.vue";
</script>

<template>
  <main class="page stack">
    <RHeadline size="md" as="h1" kicker="ERR.404" title="PAGE NOT FOUND" subtitle="THIS ADDRESS IS NOT PART OF THE SITE" />
    <div>
      <RButton to="/" arrow>RETURN HOME</RButton>
    </div>
  </main>
</template>

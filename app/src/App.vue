<script setup lang="ts">
// Application shell: the header is hidden on Home, where the solar system is the navigation.
import { useRoute, RouterView } from "vue-router";
import AppHeader from "@/components/layout/AppHeader.vue";
import AppFooter from "@/components/layout/AppFooter.vue";

const route = useRoute();
</script>

<template>
  <AppHeader v-if="route.name !== 'home'" />
  <RouterView />
  <AppFooter />
</template>

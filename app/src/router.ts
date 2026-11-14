import { createRouter, createWebHashHistory, type RouteRecordRaw } from "vue-router";
import HomeView from "@/views/HomeView.vue";

// Hash history: works under any static host and any sub-path (vite base is "./").
const routes: RouteRecordRaw[] = [
  { path: "/", name: "home", component: HomeView },
  { path: "/results", name: "results", component: () => import("@/views/ResultsView.vue") },
  { path: "/challenge", name: "challenge", component: () => import("@/views/ChallengeView.vue") },
  { path: "/how-it-works", name: "how-it-works", component: () => import("@/views/HowItWorksView.vue") },
  { path: "/algorithm", name: "algorithm", component: () => import("@/views/AlgorithmView.vue") },
  { path: "/data", name: "data", component: () => import("@/views/DataView.vue") },
  { path: "/about", name: "about", component: () => import("@/views/AboutView.vue") },
  { path: "/:pathMatch(.*)*", name: "not-found", component: () => import("@/views/NotFoundView.vue") },
];

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition;
    if (to.hash) return { el: to.hash };
    return { top: 0 };
  },
});

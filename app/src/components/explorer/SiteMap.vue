<script setup lang="ts">
// Leaflet map with circle markers. Port of components/SiteMap.tsx.
// The map and its layer are plain variables, not refs: Vue must not make Leaflet objects reactive.
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { MapPoint } from "@/composables/useExplorer";

const props = defineProps<{
  title: string;
  kind: "target" | "earth";
  tiles: { url: string; maxNativeZoom: number; attribution: string };
  /** true: EPSG:4326 (NASA Trek, Moon and Mars). false: Web Mercator (GIBS, Earth). */
  geographic: boolean;
  points: MapPoint[];
  note?: string;
}>();

const emit = defineEmits<{ select: [id: string] }>();

const el = ref<HTMLDivElement | null>(null);
let map: L.Map | null = null;
let layer: L.LayerGroup | null = null;
let resizeObserver: ResizeObserver | null = null;

function drawPoints(points: MapPoint[]) {
  if (!map || !layer) return;
  layer.clearLayers();
  // Selected points are drawn last so they sit on top.
  const ordered = [...points].sort((a, b) => Number(a.selected) - Number(b.selected));
  let sel: MapPoint | undefined;
  for (const p of ordered) {
    if (p.selected) sel = p;
    L.circleMarker([p.lat, p.lon], {
      radius: p.selected ? 9 : 4 + p.weight * 4,
      weight: 1.5,
      fillOpacity: 1,
      className: `mk-${props.kind}${p.selected ? " is-on" : ""}`,
    })
      .bindTooltip(p.label)
      .on("click", () => emit("select", p.id))
      .addTo(layer);
  }
  if (sel && props.kind === "earth") {
    map.flyTo([sel.lat, sel.lon], Math.max(map.getZoom(), 2), { duration: 0.6 });
  }
}

onMounted(() => {
  if (!el.value) return;
  map = L.map(el.value, {
    crs: props.geographic ? L.CRS.EPSG4326 : L.CRS.EPSG3857,
    center: [0, 0],
    zoom: props.geographic ? 0 : 1,
    minZoom: 0,
    maxZoom: 8,
    worldCopyJump: !props.geographic,
    attributionControl: true,
    zoomControl: true,
  });
  L.tileLayer(props.tiles.url, {
    maxNativeZoom: props.tiles.maxNativeZoom,
    attribution: props.tiles.attribution,
    noWrap: props.geographic,
  }).addTo(map);
  layer = L.layerGroup().addTo(map);
  resizeObserver = new ResizeObserver(() => map?.invalidateSize());
  resizeObserver.observe(el.value);
  drawPoints(props.points);
});

watch(
  () => props.points,
  (points) => drawPoints(points),
);

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  map?.remove();
  map = null;
  layer = null;
});
</script>

<template>
  <figure class="map">
    <figcaption class="map__caption">
      <span class="label">{{ title }}</span>
      <span v-if="note" class="footnote">{{ note }}</span>
    </figcaption>
    <div class="map__frame">
      <div ref="el" class="map__canvas" role="application" :aria-label="title" />
    </div>
  </figure>
</template>

<style lang="scss" scoped>
.map {
  margin: 0;
  background: var(--surface-raised);
  border: var(--stroke-hairline) solid var(--line-faint);
  min-width: 0;
}

.map__caption {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-bottom: var(--stroke-hairline) solid var(--line-faint);
}

.map__frame {
  position: relative;
}

.map__canvas {
  width: 100%;
  height: 288px;
}
</style>

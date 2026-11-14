import { useEffect, useRef } from "react";
import L from "leaflet";

export interface MapPoint {
  id: string;
  lat: number;
  lon: number;
  label: string;
  selected: boolean;
  weight: number; // 0-1, controls marker radius
}

interface Props {
  title: string;
  kind: "target" | "earth";
  tiles: { url: string; maxNativeZoom: number; attribution: string };
  geographic: boolean; // true: EPSG:4326 (NASA Trek); false: Web Mercator (GIBS)
  points: MapPoint[];
  onSelect: (id: string) => void;
  note?: string;
}

/** Leaflet map with circular markers. Recreated only if projection or base layer changes. */
export function SiteMap({ title, kind, tiles, geographic, points, onSelect, note }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const layer = useRef<L.LayerGroup | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!el.current) return;
    const m = L.map(el.current, {
      crs: geographic ? L.CRS.EPSG4326 : L.CRS.EPSG3857,
      center: [0, 0],
      zoom: geographic ? 0 : 1,
      minZoom: 0,
      maxZoom: 8,
      worldCopyJump: !geographic,
      attributionControl: true,
      zoomControl: true,
    });
    L.tileLayer(tiles.url, {
      maxNativeZoom: tiles.maxNativeZoom,
      attribution: tiles.attribution,
      noWrap: geographic,
    }).addTo(m);
    layer.current = L.layerGroup().addTo(m);
    map.current = m;
    const ro = new ResizeObserver(() => m.invalidateSize());
    ro.observe(el.current);
    return () => {
      ro.disconnect();
      m.remove();
      map.current = null;
    };
  }, [tiles.url, tiles.maxNativeZoom, tiles.attribution, geographic]);

  useEffect(() => {
    const g = layer.current;
    const m = map.current;
    if (!g || !m) return;
    g.clearLayers();
    let sel: MapPoint | undefined;
    // Selected markers are rendered last so they appear on top
    const ordered = [...points].sort((a, b) => Number(a.selected) - Number(b.selected));
    for (const p of ordered) {
      if (p.selected) sel = p;
      L.circleMarker([p.lat, p.lon], {
        radius: p.selected ? 9 : 4 + p.weight * 4,
        weight: 1.5,
        fillOpacity: p.selected ? 1 : 0.8,
        className: `mk-${kind}${p.selected ? " is-on" : ""}`,
      })
        .bindTooltip(p.label)
        .on("click", () => onSelectRef.current(p.id))
        .addTo(g);
    }
    if (sel && kind === "earth") m.flyTo([sel.lat, sel.lon], Math.max(m.getZoom(), 2), { duration: 0.6 });
  }, [points, kind]);

  return (
    <figure className="m-0 overflow-hidden rounded-panel border border-line bg-surface">
      <figcaption className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3 py-2">
        <span className="eyebrow">{title}</span>
        {note && <span className="text-xs text-muted">{note}</span>}
      </figcaption>
      <div className="map-frame">
        <div ref={el} className="h-64 w-full sm:h-72" role="application" aria-label={title} />
      </div>
    </figure>
  );
}

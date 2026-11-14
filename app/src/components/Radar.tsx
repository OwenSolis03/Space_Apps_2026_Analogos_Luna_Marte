import type { Dimension } from "../lib/types";
import { DIMENSIONS } from "../lib/types";
import { DIM_LABEL } from "../lib/content";

/** Radar de 4 ejes (0-1). Los ejes sin dato se dibujan punteados y sin punto. */
export function Radar({ values }: { values: Record<Dimension, number | null> }) {
  const cx = 150, cy = 120, R = 82, n = DIMENSIONS.length;
  const pt = (i: number, r: number): [number, number] => [cx + r * Math.sin((i / n) * 2 * Math.PI), cy - r * Math.cos((i / n) * 2 * Math.PI)];
  const poly = DIMENSIONS.map((d, i) => pt(i, R * (values[d] ?? 0)).join(",")).join(" ");
  const summary = DIMENSIONS.map((d) => `${DIM_LABEL[d].label}: ${values[d] == null ? "no data" : values[d]!.toFixed(2)}`).join(", ");

  return (
    <svg viewBox="-30 0 360 250" className="mx-auto w-full max-w-xs" role="img" aria-label={`Similarity by dimension. ${summary}`}>
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <polygon key={f} points={DIMENSIONS.map((_, i) => pt(i, R * f).join(",")).join(" ")} fill="none" stroke="var(--line)" />
      ))}
      {DIMENSIONS.map((d, i) => {
        const [x, y] = pt(i, R);
        const [lx, ly] = pt(i, R + 20);
        const off = values[d] == null;
        return (
          <g key={d}>
            <line x1={cx} y1={cy} x2={x} y2={y} stroke="var(--line)" strokeDasharray={off ? "3 3" : undefined} />
            <text x={lx} y={ly + 4} textAnchor="middle" fontSize="11" fill={off ? "var(--faint)" : "var(--muted)"}>
              {DIM_LABEL[d].label}
            </text>
          </g>
        );
      })}
      <polygon points={poly} fill="var(--earth)" fillOpacity={0.2} stroke="var(--earth)" strokeWidth={2} strokeLinejoin="round" />
      {DIMENSIONS.map((d, i) => {
        if (values[d] == null) return null;
        const [x, y] = pt(i, R * values[d]!);
        return <circle key={d} cx={x} cy={y} r={3.5} fill="var(--earth)" />;
      })}
      <text x={cx} y={244} textAnchor="middle" fontSize="10" fill="var(--faint)">
        dashed axes: no data yet
      </text>
    </svg>
  );
}

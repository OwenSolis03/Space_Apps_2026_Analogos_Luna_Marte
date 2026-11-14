import type { Dimension } from "../lib/types";
import { DIMENSIONS } from "../lib/types";
import { DIM_LABEL } from "../lib/content";

/** Radar over the seven dimensions (0-1). Axes without a sub-score are dashed and have no dot. */
export function Radar({ values }: { values: Partial<Record<Dimension, number | null>> }) {
  const cx = 150, cy = 120, R = 82, n = DIMENSIONS.length;
  const pt = (i: number, r: number): [number, number] => [cx + r * Math.sin((i / n) * 2 * Math.PI), cy - r * Math.cos((i / n) * 2 * Math.PI)];
  const v = (d: Dimension) => values[d] ?? null;
  const poly = DIMENSIONS.map((d, i) => pt(i, R * (v(d) ?? 0)).join(",")).join(" ");
  const summary = DIMENSIONS.map((d) => `${DIM_LABEL[d].label}: ${v(d) == null ? "not applicable" : v(d)!.toFixed(2)}`).join(", ");

  return (
    <svg viewBox="-40 0 380 252" className="mx-auto w-full max-w-sm" role="img" aria-label={`Similarity by dimension. ${summary}`}>
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <polygon key={f} points={DIMENSIONS.map((_, i) => pt(i, R * f).join(",")).join(" ")} fill="none" stroke="var(--line)" />
      ))}
      {DIMENSIONS.map((d, i) => {
        const [x, y] = pt(i, R);
        const [lx, ly] = pt(i, R + 22);
        const off = v(d) == null;
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
        const s = v(d);
        if (s == null) return null;
        const [x, y] = pt(i, R * s);
        return <circle key={d} cx={x} cy={y} r={3.5} fill="var(--earth)" />;
      })}
      <text x={cx} y={248} textAnchor="middle" fontSize="10" fill="var(--faint)">
        dashed axes: not applicable to this pair
      </text>
    </svg>
  );
}

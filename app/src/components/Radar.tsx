import type { Dimension } from "../lib/types";
import { DIMENSIONS } from "../lib/types";
import { DIM_LABEL } from "../lib/content";

interface Props {
  values: Partial<Record<Dimension, number | null>>;
  availableDims?: Dimension[];
  earthMissingDims?: Dimension[];
}

/** Radar over the seven dimensions (0-1). Axes without a sub-score are dashed; missing Earth data is drawn at 0 with hollow marker. */
export function Radar({ values, availableDims, earthMissingDims }: Props) {
  const cx = 150, cy = 120, R = 82, n = DIMENSIONS.length;
  const pt = (i: number, r: number): [number, number] => [cx + r * Math.sin((i / n) * 2 * Math.PI), cy - r * Math.cos((i / n) * 2 * Math.PI)];
  const v = (d: Dimension) => values[d] ?? null;
  const poly = DIMENSIONS.map((d, i) => pt(i, R * (v(d) ?? 0)).join(",")).join(" ");
  const summary = DIMENSIONS.map((d) => {
    if (earthMissingDims?.includes(d)) return `${DIM_LABEL[d].label}: no Earth data (0.00)`;
    return `${DIM_LABEL[d].label}: ${v(d) == null ? "not applicable" : v(d)!.toFixed(2)}`;
  }).join(", ");

  return (
    <svg viewBox="-40 0 380 252" className="mx-auto w-full max-w-sm font-display tracking-wider uppercase" role="img" aria-label={`Similarity by dimension. ${summary}`}>
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <polygon key={f} points={DIMENSIONS.map((_, i) => pt(i, R * f).join(",")).join(" ")} fill="none" stroke="var(--line-faint)" />
      ))}
      {DIMENSIONS.map((d, i) => {
        const [x, y] = pt(i, R);
        const [lx, ly] = pt(i, R + 22);
        const off = availableDims ? !availableDims.includes(d) : v(d) == null;
        const missing = earthMissingDims?.includes(d);
        return (
          <g key={d}>
            <line x1={cx} y1={cy} x2={x} y2={y} stroke="var(--line-faint)" strokeDasharray={off ? "3 3" : undefined} />
            <text x={lx} y={ly + (missing ? 0 : 4)} textAnchor="middle" fontSize="9" fill="var(--ink-muted)">
              <tspan x={lx}>{DIM_LABEL[d].label}</tspan>
              {missing && (
                <tspan x={lx} dy="10" fontSize="7" fill="var(--signal-ink)">
                  no Earth data
                </tspan>
              )}
            </text>
          </g>
        );
      })}
      <polygon points={poly} fill="var(--signal)" fillOpacity={0.35} stroke="var(--ink)" strokeWidth={2} strokeLinejoin="round" />
      {DIMENSIONS.map((d, i) => {
        const s = v(d);
        if (s != null) {
          const [x, y] = pt(i, R * s);
          return <circle key={d} cx={x} cy={y} r={3.5} fill="var(--ink)" />;
        }
        if (earthMissingDims?.includes(d)) {
          const [x, y] = pt(i, 0);
          return <circle key={d} cx={x} cy={y} r={4.5} fill="var(--surface-raised)" stroke="var(--signal-ink)" strokeWidth={1.5} />;
        }
        return null;
      })}
      <text x={cx} y={248} textAnchor="middle" fontSize="7" fill="var(--ink-muted)">
        dashed axes: not applicable · hollow circle: no Earth data (0)
      </text>
    </svg>
  );
}

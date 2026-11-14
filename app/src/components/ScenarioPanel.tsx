import type { Dimension, Preset, Weights } from "../lib/types";
import { DIMENSIONS } from "../lib/types";
import { DIM_LABEL } from "../lib/content";

interface Props {
  presets: Record<string, Preset>;
  presetId: string | null;
  onPreset: (id: string) => void;
  weights: Weights;
  onWeight: (d: Dimension, v: number) => void;
  available: Set<string>;
  minScore: number;
  onMinScore: (v: number) => void;
}

export function ScenarioPanel(p: Props) {
  const active = DIMENSIONS.filter((d) => p.available.has(d));
  const total = active.reduce((s, d) => s + p.weights[d], 0) || 1;

  return (
    <aside aria-label="Scenario" className="grid content-start gap-5 rounded-panel border border-line bg-surface p-4">
      <fieldset className="grid gap-2">
        <legend className="mb-2 text-sm font-semibold text-muted">Mission case</legend>
        <div className="flex flex-wrap gap-2">
          {Object.entries(p.presets).map(([id, preset]) => (
            <button key={id} type="button" className="chip text-left" aria-pressed={p.presetId === id} onClick={() => p.onPreset(id)}>
              {preset.label}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="grid gap-3">
        <legend className="mb-2 text-sm font-semibold text-muted">Weights by dimension</legend>
        {DIMENSIONS.map((d) => {
          const on = p.available.has(d);
          const id = `w-${d}`;
          return (
            <div key={d} className={`grid grid-cols-[1fr_auto] items-center gap-x-2 text-sm ${on ? "" : "opacity-60"}`}>
              <label htmlFor={id}>
                {DIM_LABEL[d].label} <span className="text-faint">· {DIM_LABEL[d].hint}</span>
              </label>
              <output htmlFor={id} className="num text-xs">
                {on ? `${Math.round((p.weights[d] / total) * 100)}%` : "no data"}
              </output>
              <input
                id={id}
                type="range"
                min={0}
                max={100}
                step={5}
                value={on ? Math.round(p.weights[d] * 100) : 0}
                disabled={!on}
                onChange={(e) => p.onWeight(d, Number(e.target.value) / 100)}
                className="col-span-2 w-full disabled:cursor-not-allowed"
              />
              {!on && <span className="pending col-span-2 w-fit">{DIM_LABEL[d].pending}</span>}
            </div>
          );
        })}
      </fieldset>

      <div className="grid gap-1 text-sm">
        <label htmlFor="min-score" className="font-semibold text-muted">
          Minimum MSI: <span className="num text-fg">{Math.round(p.minScore * 100)}</span>
        </label>
        <input id="min-score" type="range" min={0} max={95} step={5} value={Math.round(p.minScore * 100)} onChange={(e) => p.onMinScore(Number(e.target.value) / 100)} />
      </div>

      <div className="grid gap-1 text-sm">
        <span className="font-semibold text-muted">Logistics</span>
        <label className="flex items-center gap-2 opacity-60">
          <input type="checkbox" disabled /> Prefer sites near a road
        </label>
        <span className="pending w-fit">road distance arrives with T6</span>
      </div>
    </aside>
  );
}

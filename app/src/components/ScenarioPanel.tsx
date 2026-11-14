import { useState } from "react";
import type { Body, Dimension, DimensionInfo, Preset, Weights } from "../lib/types";
import { DIMENSIONS } from "../lib/types";
import { DIM_LABEL } from "../lib/content";
import { CONTROL_EXPLANATION, DIM_EXPLANATION, EXPLANATION_HEADINGS, INTRO, PRESET_EXPLANATION } from "../lib/explanations";
import { InfoButton, InfoPanel } from "./InfoToggle";

interface Props {
  body: Body;
  presets: Record<string, Preset>;
  presetId: string | null;
  onPreset: (id: string) => void;
  weights: Weights;
  onWeight: (d: Dimension, v: number) => void;
  available: Set<Dimension>;
  dimInfo: Partial<Record<Dimension, DimensionInfo>>;
  bodyName: string;
  minScore: number;
  onMinScore: (v: number) => void;
  lambda: number;
  onLambda: (v: number) => void;
  newOnly: boolean;
  onNewOnly: (v: boolean) => void;
}

const KEYS = [...DIMENSIONS.map((d) => `dim-${d}`), "min-score", "road", "new-only"];
const STORE_KEY = "paf.explanations";

function readStored(): boolean {
  try {
    return localStorage.getItem(STORE_KEY) === "1";
  } catch {
    return false;
  }
}
function writeStored(on: boolean) {
  try {
    localStorage.setItem(STORE_KEY, on ? "1" : "0");
  } catch {
    // storage blocked: the panel still works, it just forgets the choice
  }
}

export function ScenarioPanel(p: Props) {
  const active = DIMENSIONS.filter((d) => p.available.has(d));
  const total = active.reduce((s, d) => s + p.weights[d], 0) || 1;

  const [open, setOpen] = useState<Set<string>>(() => (readStored() ? new Set(KEYS) : new Set()));
  const allOpen = KEYS.every((k) => open.has(k));
  const toggle = (k: string) =>
    setOpen((s) => {
      const n = new Set(s);
      if (n.has(k)) n.delete(k);
      else n.add(k);
      return n;
    });
  const toggleAll = () => {
    setOpen(allOpen ? new Set() : new Set(KEYS));
    writeStored(!allOpen);
  };

  const presetText = p.presetId ? PRESET_EXPLANATION[p.presetId] : undefined;

  return (
    <aside aria-label="Scenario" className="grid content-start gap-5 self-start rounded-panel border border-line bg-surface p-4 md:sticky md:top-20 md:max-h-[calc(100dvh-6rem)] md:overflow-y-auto">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <h3 className="text-base font-semibold">Scenario</h3>
        <button
          type="button"
          role="switch"
          aria-checked={allOpen}
          aria-label="Show all explanations in this panel"
          onClick={toggleAll}
          className="inline-flex min-h-8 cursor-pointer items-center gap-2 rounded-full text-sm whitespace-nowrap text-muted transition-colors hover:text-fg"
        >
          <span aria-hidden="true" className={`relative h-5 w-9 rounded-full border border-line transition-colors ${allOpen ? "bg-accent" : "bg-surface-2"}`}>
            <span className={`absolute top-0.5 left-0.5 size-3.5 rounded-full bg-fg transition-transform ${allOpen ? "translate-x-4" : ""}`} />
          </span>
          <span aria-hidden="true">Show explanations</span>
        </button>
      </div>

      <fieldset className="grid gap-2">
        <legend className="mb-2 text-sm font-semibold text-muted">Mission case</legend>
        <p className="mb-1 text-sm">{INTRO}</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(p.presets)
            .filter(([, preset]) => !preset.applies_to || preset.applies_to.includes(p.body))
            .map(([id, preset]) => (
              <button key={id} type="button" className="chip text-left" aria-pressed={p.presetId === id} onClick={() => p.onPreset(id)}>
                {preset.label}
              </button>
            ))}
        </div>
        {presetText && <p className="text-sm text-muted">{presetText}</p>}
      </fieldset>

      <fieldset className="grid gap-3">
        <legend className="mb-2 text-sm font-semibold text-muted">Weights by dimension</legend>
        <p className="text-sm text-muted">{CONTROL_EXPLANATION.weightsShare}</p>
        {DIMENSIONS.map((d) => {
          const on = p.available.has(d);
          const id = `w-${d}`;
          const key = `dim-${d}`;
          const info = p.dimInfo[d];
          return (
            <div key={d} className="grid gap-y-1 text-sm">
              <div className="flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-1">
                  <label htmlFor={id} title={info?.description} className={on ? "" : "opacity-60"}>
                    {DIM_LABEL[d].label} <span className="text-faint">· {DIM_LABEL[d].hint}</span>
                  </label>
                  <InfoButton id={key} title={DIM_LABEL[d].label} open={open.has(key)} onToggle={() => toggle(key)} />
                </div>
                <output htmlFor={id} className={`num text-xs ${on ? "" : "opacity-60"}`}>
                  {on ? `${Math.round((p.weights[d] / total) * 100)}%` : "n/a"}
                </output>
              </div>
              <input
                id={id}
                type="range"
                min={0}
                max={100}
                step={5}
                value={on ? Math.round(p.weights[d] * 100) : 0}
                disabled={!on}
                onChange={(e) => p.onWeight(d, Number(e.target.value) / 100)}
                className="w-full disabled:cursor-not-allowed disabled:opacity-60"
              />
              {!on && <span className="pending w-fit">not modelled for {p.bodyName}</span>}
              <InfoPanel id={key} title={DIM_LABEL[d].label} open={open.has(key)} explanation={DIM_EXPLANATION[d]} />
            </div>
          );
        })}
      </fieldset>

      <div className="grid gap-1 text-sm">
        <div className="flex items-center gap-1">
          <label htmlFor="min-score" className="font-semibold text-muted">
            Minimum MSI: <span className="num text-fg">{Math.round(p.minScore * 100)}</span>
          </label>
          <InfoButton id="min-score" title="Minimum MSI" open={open.has("min-score")} onToggle={() => toggle("min-score")} />
        </div>
        <input id="min-score" type="range" min={0} max={95} step={5} value={Math.round(p.minScore * 100)} onChange={(e) => p.onMinScore(Number(e.target.value) / 100)} />
        <InfoPanel id="min-score" title="Minimum MSI" open={open.has("min-score")} explanation={CONTROL_EXPLANATION.minScore} />
      </div>

      <div className="grid gap-3 text-sm">
        <span className="font-semibold text-muted">Logistics and novelty</span>
        <div className="grid gap-1">
          <div className="flex items-center gap-1">
            <label htmlFor="lambda">
              Prefer sites near a road <span className="num text-xs text-faint">λ = {p.lambda.toFixed(2)} (0 = off)</span>
            </label>
            <InfoButton id="road" title="Prefer sites near a road" open={open.has("road")} onToggle={() => toggle("road")} />
          </div>
          <input id="lambda" type="range" min={0} max={30} step={5} value={Math.round(p.lambda * 100)} onChange={(e) => p.onLambda(Number(e.target.value) / 100)} />
          <InfoPanel id="road" title="Prefer sites near a road" open={open.has("road")} explanation={CONTROL_EXPLANATION.road} />
        </div>
        <div className="grid gap-1">
          <div className="flex items-center gap-1">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={p.newOnly} onChange={(e) => p.onNewOnly(e.target.checked)} /> Only new candidates (hide well-known analog regions)
            </label>
            <InfoButton id="new-only" title="Only new candidates" open={open.has("new-only")} onToggle={() => toggle("new-only")} />
          </div>
          <InfoPanel
            id="new-only"
            title="Only new candidates"
            open={open.has("new-only")}
            explanation={CONTROL_EXPLANATION.newOnly}
            actionHeading={EXPLANATION_HEADINGS.switch}
          />
        </div>
      </div>
    </aside>
  );
}

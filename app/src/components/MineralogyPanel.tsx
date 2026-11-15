import { useState } from "react";
import type { Analog, MineralogyBlock, MineralogyMeta, MineralogySourceMeta, Target } from "../lib/types";
import { EXPLANATION_HEADINGS, MINERALOGY_EXPLANATION } from "../lib/explanations";
import { InfoButton, InfoPanel } from "./InfoToggle";

interface Props {
  target: Target;
  analog: Analog;
  meta: MineralogyMeta | undefined;
  bodyName: string;
}

const EARTH_SOURCE = "emit_l3asa";
const TINY = 0.05; // values below this are shown as nothing: they are far under any detection level

/** Oxide content first, then minerals by abundance, then indices. */
const order = (unit: string) => (unit === "wt%" ? 0 : unit === "index" ? 2 : 1);

const fmt = (v: number, unit: string) => `${unit === "index" ? v.toFixed(2) : v.toFixed(1)}${unit === "%" ? " %" : unit === "index" ? "" : ` ${unit}`}`;

/** One side of the card: summary, the values with their own labels and units, and what to know about the source. */
function Side({ title, block, source, emptyText }: { title: string; block: MineralogyBlock | null | undefined; source: MineralogySourceMeta | undefined; emptyText: string }) {
  const rows =
    block?.status === "ok" && block.values && source
      ? source.variables
          .map((v) => ({ v, value: block.values?.[v.key] }))
          .filter((r): r is { v: typeof r.v; value: number } => r.value != null && (r.v.unit === "index" || r.value >= TINY))
          .sort((a, b) => order(a.v.unit) - order(b.v.unit) || b.value - a.value)
      : [];
  return (
    <div className="min-w-0 bg-surface-2 p-3">
      <div className="eyebrow text-faint break-words">{title}</div>
      <p className="mt-1 text-sm font-medium break-words">{block?.status === "ok" ? block.summary : (block?.note ?? emptyText)}</p>
      {rows.length > 0 && (
        <dl className="mt-2 grid gap-y-1 text-xs">
          {rows.map(({ v, value }) => (
            <div key={v.key} className="flex justify-between gap-2 border-b border-line pb-0.5">
              <dt className="text-muted">{v.label}</dt>
              <dd className="num font-semibold">{fmt(value, v.unit)}</dd>
            </div>
          ))}
        </dl>
      )}
      {block?.status === "ok" && rows.length === 0 && <p className="mt-1 text-xs text-muted">Every mineral is below 0.05 %.</p>}
      {source && source.caveats.length > 0 && (
        <details className="mt-2 text-xs text-muted">
          <summary className="cursor-pointer">How reliable is this?</summary>
          <ul className="mt-1 grid list-disc gap-1 pl-4">
            {source.caveats.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

/** Mineral context of the selected target and Earth analog. Display only: nothing here enters the score. */
export function MineralogyPanel({ target, analog, meta, bodyName }: Props) {
  const [open, setOpen] = useState(false);
  if (!meta) return null;
  const targetSource = target.mineralogy ? meta.sources[target.mineralogy.source] : undefined;
  const earthSource = meta.sources[EARTH_SOURCE];
  const earthProcessed = Boolean(earthSource);

  return (
    <div className="panel p-4">
      <span className="rule mb-3" aria-hidden="true" />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="eyebrow">Mineralogy</h3>
          <InfoButton id="mineralogy" title="Mineralogy" open={open} onToggle={() => setOpen((o) => !o)} />
        </div>
        <span className="tag tag-outline">Context, not scored</span>
      </div>
      <div className="mt-2">
        <InfoPanel id="mineralogy" title="Mineralogy" open={open} explanation={MINERALOGY_EXPLANATION} actionHeading={EXPLANATION_HEADINGS.read} />
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Side
          title={`${bodyName} target${targetSource ? `, ${targetSource.name.split(" (")[0]}` : ""}`}
          block={target.mineralogy}
          source={targetSource}
          emptyText="This export has no mineral data for this target."
        />
        <Side
          title={`Earth analog${earthSource ? `, ${earthSource.name.split(" (")[0]}` : ", EMIT"}`}
          block={earthProcessed ? analog.mineralogy : null}
          source={earthSource}
          emptyText={earthProcessed ? "No EMIT value for this analog." : "Earth mineral data are not in this export yet."}
        />
      </div>
    </div>
  );
}

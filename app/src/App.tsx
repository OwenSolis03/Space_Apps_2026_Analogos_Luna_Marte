import { useEffect, useMemo, useState } from "react";
import type { Body, Dimension, DimensionInfo, Universe, Weights } from "./lib/types";
import { ZERO_WEIGHTS, fullWeights } from "./lib/types";
import { availableDimensions, fmtLat, fmtLon, pct, rankTargets } from "./lib/msi";
import { BODY_LABEL, TILES } from "./lib/content";
import { ScenarioPanel } from "./components/ScenarioPanel";
import { SiteMap, type MapPoint } from "./components/SiteMap";
import { RankList } from "./components/RankList";
import { Dossier } from "./components/Dossier";

const DATA_URL = `${import.meta.env.BASE_URL}data/analogs_universe.json`;
const BODIES: Body[] = ["Mars", "Moon"];

type Load = { state: "loading" } | { state: "error"; message: string } | { state: "ready"; data: Universe };

export default function App() {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [body, setBody] = useState<Body>("Mars");
  const [presetId, setPresetId] = useState<string | null>(null);
  const [weights, setWeights] = useState<Weights>({ ...ZERO_WEIGHTS, topography: 0.5, roughness: 0.5 });
  const [minScore, setMinScore] = useState(0);
  const [lambda, setLambda] = useState(0);
  const [newOnly, setNewOnly] = useState(false);
  const [targetId, setTargetId] = useState<string | null>(null);
  const [analogIndex, setAnalogIndex] = useState(0);

  useEffect(() => {
    fetch(DATA_URL)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status} reading ${DATA_URL}`);
        return r.json() as Promise<Universe>;
      })
      .then((data) => {
        setLoad({ state: "ready", data });
        const first = Object.keys(data.mission_presets)[0];
        if (first) {
          setPresetId(first);
          setWeights(fullWeights(data.mission_presets[first].weights));
        }
      })
      .catch((e: Error) => setLoad({ state: "error", message: e.message }));
  }, []);

  useEffect(() => {
    document.documentElement.dataset.body = body;
  }, [body]);

  const data = load.state === "ready" ? load.data : null;
  const bodyTargets = useMemo(() => data?.targets.filter((t) => t.body === body) ?? [], [data, body]);
  const available = useMemo(() => availableDimensions(bodyTargets), [bodyTargets]);
  const dimInfo = useMemo(() => {
    const out: Partial<Record<Dimension, DimensionInfo>> = {};
    for (const d of data?.metadata.dimensions ?? []) out[d.key] = d;
    return out;
  }, [data]);
  const { ranked, unranked } = useMemo(
    () =>
      rankTargets(
        bodyTargets,
        weights,
        minScore,
        lambda,
        newOnly,
        data?.metadata.scoring_policy?.earth_missing_score ?? 0,
        data?.metadata.scoring_policy?.min_preset_coverage ?? 0.6,
      ),
    [bodyTargets, weights, minScore, lambda, newOnly, data],
  );
  const selected = ranked.find((r) => r.target.id === targetId) ?? ranked[0] ?? null;
  const safeAnalog = selected && analogIndex < selected.analogs.length ? analogIndex : 0;

  const targetPoints: MapPoint[] = useMemo(
    () =>
      ranked.map((r) => ({
        id: r.target.id,
        lat: r.target.lat,
        lon: r.target.lon,
        label: `${r.target.name} · MSI ${pct(r.best)}`,
        selected: r.target.id === selected?.target.id,
        weight: r.best,
      })),
    [ranked, selected?.target.id],
  );
  const earthPoints: MapPoint[] = useMemo(
    () =>
      selected?.analogs.map((x, i) => ({
        id: String(i),
        lat: x.analog.lat,
        lon: x.analog.lon,
        label: `#${i + 1} · ${fmtLat(x.analog.lat)}, ${fmtLon(x.analog.lon)} · MSI ${pct(x.score)}`,
        selected: i === safeAnalog,
        weight: x.score,
      })) ?? [],
    [selected, safeAnalog],
  );

  const selectTarget = (id: string) => {
    setTargetId(id);
    setAnalogIndex(0);
  };
  const changeBody = (b: Body) => {
    setBody(b);
    setTargetId(null);
    setAnalogIndex(0);
    if (data && presetId) {
      const current = data.mission_presets[presetId];
      if (current?.applies_to && !current.applies_to.includes(b)) {
        const first = Object.entries(data.mission_presets).find(
          ([, p]) => !p.applies_to || p.applies_to.includes(b),
        );
        if (first) {
          setPresetId(first[0]);
          setWeights(fullWeights(first[1].weights));
        }
      }
    }
  };
  const changeWeight = (d: Dimension, v: number) => {
    setWeights((w) => ({ ...w, [d]: v }));
    setPresetId(null);
  };
  const choosePreset = (id: string) => {
    if (!data) return;
    setPresetId(id);
    setWeights(fullWeights(data.mission_presets[id].weights));
  };

  const newSites = useMemo(() => {
    const ids = new Set<string>();
    for (const t of bodyTargets) for (const a of t.analogs) if (a.classification === "NEW_CANDIDATE") ids.add(a.id);
    return ids.size;
  }, [bodyTargets]);
  const curated = bodyTargets.filter((t) => t.type === "CURATED").length;
  const B = BODY_LABEL[body];

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-[1000] border-b border-frame bg-bg">
        <div className="mx-auto flex max-w-[82rem] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <a href="#top" className="flex items-center gap-3 font-display text-[length:var(--text-label)] font-medium tracking-[0.12em] uppercase">
            <span aria-hidden="true" className="size-3 bg-accent" />
            Planetary Analog Finder
          </a>
          <nav aria-label="Sections" className="hidden gap-6 text-muted md:flex">
            <a className="hover:text-fg" href="#explorar">Explore</a>
            <a className="hover:text-fg" href="#ficha">Site sheet</a>
            <a className="hover:text-fg" href="#metodo">Methodology</a>
          </nav>
          <div role="group" aria-label="Target body" className="ml-auto inline-flex gap-2">
            {BODIES.map((b) => (
              <button
                key={b}
                type="button"
                aria-pressed={body === b}
                onClick={() => changeBody(b)}
                className="chip"
              >
                {BODY_LABEL[b].name}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main id="top" className="mx-auto max-w-[82rem] px-4">
        <section className="relative grid gap-8 py-12 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)] lg:items-end">
          <div aria-hidden="true" className="dotgrid pointer-events-none absolute top-8 right-0 hidden h-48 w-80 lg:block" />
          <div className="relative">
            <span className="rule" aria-hidden="true" />
            <p className="eyebrow mt-4">NASA Space Apps 2026 · Endurance CXXV · Hermosillo</p>
            <h1 className="display-a mt-4 text-[clamp(1.5rem,4.2vw,3.5rem)]">
              Rehearse <span className="text-accent-ink">{B.name}</span> without leaving Earth
            </h1>
            <p className="mt-6 max-w-[40ch] text-lg leading-7 font-light text-muted sm:text-2xl sm:leading-9">
              We compare {B.adj} terrain with thousands of Earth cells, score each pair with open data, and show, site by site, what matches
              and where the analogy breaks.
            </p>
          </div>
          <dl className="relative grid grid-cols-3 border-t-[length:var(--stroke-bar)] border-accent">
            <div className="min-w-0 pt-3 pr-3">
              <dt className="text-muted">Earth cells evaluated</dt>
              <dd className="code text-xl sm:text-4xl">{data?.metadata.earth_patches_evaluated?.toLocaleString("en-US") ?? "..."}</dd>
            </div>
            <div className="min-w-0 pt-3 pr-3">
              <dt className="text-muted">{B.adj} targets ({curated} mission sites)</dt>
              <dd className="code text-xl sm:text-4xl">{data ? bodyTargets.length : "..."}</dd>
            </div>
            <div className="min-w-0 pt-3">
              <dt className="text-muted">new Earth candidate sites</dt>
              <dd className="code text-xl sm:text-4xl">{data ? newSites.toLocaleString("en-US") : "..."}</dd>
            </div>
          </dl>
        </section>

        {load.state === "loading" && <p className="py-10 text-muted" role="status">Loading analog data...</p>}
        {load.state === "error" && (
          <div role="alert" className="panel my-6 p-4">
            <p className="font-medium text-accent-ink">
              <span className="tag tag-signal mr-2">Error</span>The analog data could not be loaded.
            </p>
            <p className="mt-1 text-sm text-muted">
              {load.message}. Check that <code className="num">app/public/data/analogs_universe.json</code> exists (exported by <code className="num">pipeline/export.py</code>).
            </p>
          </div>
        )}

        {data && (
          <>
            <section id="explorar" aria-labelledby="explorar-h" className="scroll-mt-20 border-t border-line py-12">
              <div className="mb-5 grid gap-1">
                <h2 id="explorar-h" className="display-c text-[clamp(1.75rem,4vw,3rem)]">Explorer</h2>
                <p className="max-w-[70ch] text-sm text-muted">
                  Pick a mission case and adjust the weights. The ranking is recalculated in your browser. Dimensions that do not apply to {B.name} are disabled.
                </p>
              </div>
              <div className="grid gap-4 md:grid-cols-[19rem_minmax(0,1fr)] xl:grid-cols-[20rem_minmax(0,1fr)_20rem]">
                <ScenarioPanel
                  body={body}
                  presets={data.mission_presets}
                  presetId={presetId}
                  onPreset={choosePreset}
                  weights={weights}
                  onWeight={changeWeight}
                  available={available}
                  dimInfo={dimInfo}
                  bodyName={B.name}
                  minScore={minScore}
                  onMinScore={setMinScore}
                  lambda={lambda}
                  onLambda={setLambda}
                  newOnly={newOnly}
                  onNewOnly={setNewOnly}
                />
                <div className="grid min-w-0 content-start gap-4">
                  <SiteMap
                    title={`${B.name} · terrain targets`}
                    kind="target"
                    tiles={TILES[body]}
                    geographic
                    points={targetPoints}
                    onSelect={selectTarget}
                    note="click a point to open its sheet"
                  />
                  <SiteMap
                    title="Earth · analogs of the selected target"
                    kind="earth"
                    tiles={TILES.Earth}
                    geographic={false}
                    points={earthPoints}
                    onSelect={(id) => setAnalogIndex(Number(id))}
                  />
                </div>
                <div className="md:col-span-2 xl:col-span-1">
                  <RankList ranked={ranked} unranked={unranked} total={bodyTargets.length} selectedId={selected?.target.id ?? null} onSelect={selectTarget} />
                </div>
              </div>
            </section>

            <section id="ficha" aria-labelledby="ficha-h" className="scroll-mt-20 border-t border-line py-12">
              <div className="mb-5 grid gap-1">
                <h2 id="ficha-h" className="display-c text-[clamp(1.75rem,4vw,3rem)]">Site sheet</h2>
                <p className="max-w-[70ch] text-sm text-muted">How close each analog is, feature by feature, and what Earth cannot reproduce.</p>
              </div>
              {selected ? (
                <Dossier ranked={selected} analogIndex={safeAnalog} onAnalog={setAnalogIndex} limits={data.limits[body]} mineralogyMeta={data.metadata.mineralogy} />
              ) : (
                <p className="text-sm text-muted">Select a target in the ranking or on the map to see its sheet.</p>
              )}
            </section>

            <section id="metodo" aria-labelledby="metodo-h" className="scroll-mt-20 border-t border-line py-12">
              <h2 id="metodo-h" className="display-c mb-5 text-[clamp(1.75rem,4vw,3rem)]">Methodology</h2>
              <ol className="grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-5">
                {[
                  ["Targets", "Mission sites (Artemis III regions, Mars landing sites) plus terrain archetypes clustered from MOLA and LOLA."],
                  [
                    "Same measurement",
                    `${data.metadata.earth_patches_evaluated?.toLocaleString("en-US")} bare-ground Earth patches and every target measured on the same ${data.metadata.patch?.size_km ?? 32} km patch at ${data.metadata.patch?.res_m ?? 500} m per pixel.`,
                  ],
                  ["Sub-scores", "Seven dimensions: terrain uses an RBF kernel on robust z-scores; thermal, dust and ice compare ranks within each planet."],
                  ["MSI", "MSI = Σ w·S / Σ w over the dimensions that apply, recalculated in the browser; optional road-distance factor λ."],
                  ["Where it breaks", "Features beyond 1.5 σ or a different rock class, plus the fixed physical limits of each body."],
                ].map(([h, p], i) => (
                  <li key={h} className="border-t-[length:var(--stroke-bar)] border-accent pt-3">
                    <span className="num text-xs text-accent-ink">{i + 1}</span>
                    <h3 className="mt-1">{h}</h3>
                    <p className="mt-1 text-sm text-muted">{p}</p>
                  </li>
                ))}
              </ol>
              <div className="mt-6 grid gap-6 lg:grid-cols-2">
                <div className="grid content-start gap-2 text-sm">
                  <h3>Dimensions</h3>
                  <ul className="grid gap-2">
                    {(data.metadata.dimensions ?? []).map((d) => (
                      <li key={d.key}>
                        <b className="font-semibold">{d.label}</b> <span className="text-xs text-faint">({d.bodies.join(", ")})</span>
                        <span className="block text-muted">{d.description}</span>
                        <span className="block text-xs text-faint">{d.source}</span>
                      </li>
                    ))}
                  </ul>
                  {data.metadata.scoring_policy?.rules && (
                    <div className="mt-3 border-t border-line pt-3">
                      <h4 className="text-muted">Missing-data scoring policy</h4>
                      <ul className="mt-1 list-disc pl-4 text-xs text-muted space-y-1">
                        {data.metadata.scoring_policy.rules.map((rule, idx) => (
                          <li key={idx}>{rule}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
                <div className="grid content-start gap-2 text-sm">
                  <h3>Not modelled</h3>
                  <ul className="grid gap-2">
                    {(data.metadata.not_modelled ?? []).map((n) => (
                      <li key={n.item}>
                        <b className="font-semibold">{n.item}</b>
                        <span className="block text-muted">{n.note}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
              <div className="mt-6 grid gap-2 text-sm">
                <h3>Source data</h3>
                <ul className="grid gap-1 sm:grid-cols-2">
                  {(data.metadata.datasets ?? []).map((d) => (
                    <li key={d.name}>
                      {d.url ? (
                        <a className="underline decoration-line underline-offset-2 hover:decoration-fg" href={d.url} target="_blank" rel="noreferrer">
                          {d.name}
                        </a>
                      ) : (
                        d.name
                      )}{" "}
                      <span className="text-muted">· {d.source}</span>
                    </li>
                  ))}
                </ul>
                {(data.metadata.citations ?? []).length > 0 && (
                  <details className="text-xs text-muted">
                    <summary className="cursor-pointer">References</summary>
                    <ul className="mt-2 grid gap-1">
                      {data.metadata.citations!.map((c) => (
                        <li key={c}>{c}</li>
                      ))}
                    </ul>
                  </details>
                )}
                <p className="text-xs text-muted">
                  {data.metadata.source}. Version {data.metadata.version}, generated {data.metadata.generated_at.slice(0, 10)}.
                </p>
              </div>
            </section>
          </>
        )}
      </main>

      <footer className="mx-auto flex max-w-[82rem] flex-wrap justify-between gap-4 border-t border-line px-4 pt-6 pb-10 text-muted">
        <span>Planetary Analog Finder · prototype</span>
        <span>Endurance CXXV · NASA Space Apps Challenge 2026 · NASA Space Apps Sonora, Hermosillo</span>
      </footer>
    </div>
  );
}

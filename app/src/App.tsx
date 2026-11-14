import { useEffect, useMemo, useState } from "react";
import type { Body, Dimension, Universe, Weights } from "./lib/types";
import { availableDimensions, fmtLat, fmtLon, pct, rankTargets } from "./lib/msi";
import { BODY_LABEL, TILES } from "./lib/content";
import { ScenarioPanel } from "./components/ScenarioPanel";
import { SiteMap, type MapPoint } from "./components/SiteMap";
import { RankList } from "./components/RankList";
import { Dossier } from "./components/Dossier";

const DATA_URL = `${import.meta.env.BASE_URL}data/sample.json`;
const BODIES: Body[] = ["Mars", "Moon"];

type Load = { state: "loading" } | { state: "error"; message: string } | { state: "ready"; data: Universe };

export default function App() {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [body, setBody] = useState<Body>("Mars");
  const [presetId, setPresetId] = useState<string | null>(null);
  const [weights, setWeights] = useState<Weights>({ topography: 0.5, roughness: 0.5, environment: 0, thermal: 0 });
  const [minScore, setMinScore] = useState(0);
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
          setWeights(data.mission_presets[first].weights);
        }
      })
      .catch((e: Error) => setLoad({ state: "error", message: e.message }));
  }, []);

  useEffect(() => {
    document.documentElement.dataset.body = body;
  }, [body]);

  const data = load.state === "ready" ? load.data : null;
  const bodyTargets = useMemo(() => data?.targets.filter((t) => t.body === body) ?? [], [data, body]);
  const available = useMemo(() => availableDimensions(data?.targets ?? []), [data]);
  const ranked = useMemo(() => rankTargets(bodyTargets, weights, minScore), [bodyTargets, weights, minScore]);
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
  };
  const changeWeight = (d: Dimension, v: number) => {
    setWeights((w) => ({ ...w, [d]: v }));
    setPresetId(null);
  };
  const choosePreset = (id: string) => {
    if (!data) return;
    setPresetId(id);
    setWeights(data.mission_presets[id].weights);
  };

  const best = bodyTargets.length ? Math.max(...bodyTargets.flatMap((t) => t.analogs.map((a) => a.v1_similarity ?? 0))) : 0;
  const B = BODY_LABEL[body];

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-[1000] border-b border-line bg-bg/90 backdrop-blur">
        <div className="mx-auto flex max-w-[82rem] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <a href="#top" className="flex items-center gap-2 font-display text-base font-extrabold">
            <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
              <circle cx="9" cy="13" r="7" fill="none" stroke="var(--earth)" strokeWidth="2" />
              <circle cx="17" cy="13" r="7" fill="none" stroke="var(--accent)" strokeWidth="2" />
            </svg>
            Planetary Analog Finder
          </a>
          <nav aria-label="Sections" className="hidden gap-5 text-sm text-muted md:flex">
            <a className="hover:text-fg" href="#explorar">Explore</a>
            <a className="hover:text-fg" href="#ficha">Site sheet</a>
            <a className="hover:text-fg" href="#metodo">Methodology</a>
          </nav>
          <div role="group" aria-label="Target body" className="ml-auto inline-flex rounded-full border border-line bg-surface p-1">
            {BODIES.map((b) => (
              <button
                key={b}
                type="button"
                aria-pressed={body === b}
                onClick={() => changeBody(b)}
                className="min-h-9 cursor-pointer rounded-full px-4 text-sm text-muted transition-colors hover:text-fg active:bg-surface-2 aria-pressed:bg-accent aria-pressed:text-on-accent"
              >
                {BODY_LABEL[b].name}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main id="top" className="mx-auto max-w-[82rem] px-4">
        <section className="grid gap-8 py-10 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)] lg:items-end">
          <div>
            <p className="eyebrow">NASA Space Apps 2026 · Endurance CXXV · Hermosillo</p>
            <h1 className="mt-3 max-w-[18ch] text-display leading-[1.02] font-extrabold sm:text-5xl lg:text-6xl">
              Rehearse <span className="text-accent">{B.name}</span> without leaving Earth
            </h1>
            <p className="mt-4 max-w-[60ch] text-muted">
              We compare {B.adj} terrain with thousands of Earth cells, score each pair with open data, and show, site by site, what matches
              and where the analogy breaks.
            </p>
          </div>
          <dl className="grid grid-cols-3 border-t-2 border-fg">
            <div className="pt-3 pr-3">
              <dt className="text-xs text-muted">Earth cells evaluated</dt>
              <dd className="num font-display text-2xl font-semibold sm:text-3xl">{data?.metadata.earth_patches_evaluated?.toLocaleString("en-US") ?? "..."}</dd>
            </div>
            <div className="pt-3 pr-3">
              <dt className="text-xs text-muted">{B.adj} terrain targets</dt>
              <dd className="num font-display text-2xl font-semibold sm:text-3xl">{data ? bodyTargets.length : "..."}</dd>
            </div>
            <div className="pt-3">
              <dt className="text-xs text-muted">best v1 similarity</dt>
              <dd className="num font-display text-2xl font-semibold sm:text-3xl">{data ? best.toFixed(1) : "..."}</dd>
            </div>
          </dl>
        </section>

        {load.state === "loading" && <p className="py-10 text-muted" role="status">Loading analog data...</p>}
        {load.state === "error" && (
          <div role="alert" className="my-6 rounded-panel border border-bad bg-surface p-4">
            <p className="font-semibold text-bad">The analog data could not be loaded.</p>
            <p className="mt-1 text-sm text-muted">
              {load.message}. Check that <code className="num">app/public/data/sample.json</code> exists (generate it with <code className="num">python tools/v1_to_sample.py</code>).
            </p>
          </div>
        )}

        {data && (
          <>
            <section id="explorar" aria-labelledby="explorar-h" className="scroll-mt-20 border-t border-line py-8">
              <div className="mb-5 grid gap-1">
                <h2 id="explorar-h" className="text-2xl font-semibold">Explorer</h2>
                <p className="max-w-[70ch] text-sm text-muted">
                  Pick a mission case and adjust the weights. The ranking is recalculated in your browser. Dimensions the current pipeline has no data for are disabled.
                </p>
              </div>
              <div className="grid gap-4 md:grid-cols-[16rem_minmax(0,1fr)] xl:grid-cols-[16rem_minmax(0,1fr)_20rem]">
                <ScenarioPanel
                  presets={data.mission_presets}
                  presetId={presetId}
                  onPreset={choosePreset}
                  weights={weights}
                  onWeight={changeWeight}
                  available={available}
                  minScore={minScore}
                  onMinScore={setMinScore}
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
                  <RankList ranked={ranked} total={bodyTargets.length} selectedId={selected?.target.id ?? null} onSelect={selectTarget} />
                </div>
              </div>
            </section>

            <section id="ficha" aria-labelledby="ficha-h" className="scroll-mt-20 border-t border-line py-8">
              <div className="mb-5 grid gap-1">
                <h2 id="ficha-h" className="text-2xl font-semibold">Site sheet</h2>
                <p className="max-w-[70ch] text-sm text-muted">How close each analog is, feature by feature, and what Earth cannot reproduce.</p>
              </div>
              {selected ? (
                <Dossier ranked={selected} analogIndex={safeAnalog} onAnalog={setAnalogIndex} limits={data.limits[body]} />
              ) : (
                <p className="text-sm text-muted">Select a target in the ranking or on the map to see its sheet.</p>
              )}
            </section>

            <section id="metodo" aria-labelledby="metodo-h" className="scroll-mt-20 border-t border-line py-8">
              <h2 id="metodo-h" className="mb-5 text-2xl font-semibold">Methodology</h2>
              <ol className="grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-5">
                {[
                  ["Targets", "Terrain windows on Mars (MOLA-HRSC) and the Moon (LOLA), clustered into 40 archetypes per body."],
                  ["Earth cells", `${data.metadata.earth_patches_evaluated?.toLocaleString("en-US")} Copernicus DEM cells with slope, P90, elevation σ and TRI.`],
                  ["Sub-scores", "RBF kernel per feature, averaged per dimension: S = exp(-(x_T - x_E)² / 2σ²)."],
                  ["MSI", "MSI = Σ w·S / Σ w with the mission case weights, recalculated in the browser."],
                  ["Where it breaks", "Features more than 1.5 σ from the target, plus the fixed physical limits of each body."],
                ].map(([h, p], i) => (
                  <li key={h} className="border-t-2 border-fg pt-3">
                    <span className="num text-xs text-accent">{i + 1}</span>
                    <h3 className="mt-1 text-base font-semibold">{h}</h3>
                    <p className="mt-1 text-sm text-muted">{p}</p>
                  </li>
                ))}
              </ol>
              <div className="mt-6 grid gap-2 text-sm">
                <h3 className="text-base font-semibold">Source data</h3>
                <ul className="grid gap-1 sm:grid-cols-2">
                  {data.metadata.datasets.map((d) => (
                    <li key={d.name}>
                      <a className="underline decoration-line underline-offset-2 hover:decoration-fg" href={d.url} target="_blank" rel="noreferrer">
                        {d.name}
                      </a>{" "}
                      <span className="text-muted">· {d.source}</span>
                    </li>
                  ))}
                </ul>
                <p className="text-xs text-muted">
                  Sample data: {data.metadata.source}. Version {data.metadata.version}.
                </p>
              </div>
            </section>
          </>
        )}
      </main>

      <footer className="mx-auto flex max-w-[82rem] flex-wrap justify-between gap-4 border-t border-line px-4 pt-6 pb-10 text-sm text-muted">
        <span>Planetary Analog Finder · prototype</span>
        <span>Endurance CXXV · NASA Space Apps Challenge 2026 · UTH Hermosillo</span>
      </footer>
    </div>
  );
}

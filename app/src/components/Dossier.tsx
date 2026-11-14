import type { Analog, Dimension, Limit, Mismatch, Target } from "../lib/types";
import type { RankedTarget } from "../lib/msi";
import { fmtLat, fmtLon, fmtNum, pct } from "../lib/msi";
import { BODY_LABEL, DIM_LABEL, FEATURE_LABEL, GEO_CLASS_LABEL, fmtValue, limitLabel, suggestedUses } from "../lib/content";
import { Radar } from "./Radar";

interface Props {
  ranked: RankedTarget;
  analogIndex: number;
  onAnalog: (i: number) => void;
  limits: Limit[];
}

type Row = { key: string; label: string; unit: string; target: number | string | null | undefined; earth: number | string | null | undefined };

/** Non-terrain comparisons (geology, dust, ice) built from the structured fields of the export. */
function processRows(t: Target, a: Analog): Row[] {
  const rows: Row[] = [];
  if (t.geology?.geo_class || a.geology?.geo_class)
    rows.push({ key: "geo_class", label: "Rock class (regional)", unit: "", target: t.geology?.geo_class, earth: a.geology?.geo_class });
  if (t.dust && a.dust) {
    rows.push({ key: "dust_level_rank", label: "Dust level rank", unit: "", target: t.dust.level_rank, earth: a.dust.level_rank });
    rows.push({ key: "dust_seasonality_rank", label: "Dust seasonality rank", unit: "", target: t.dust.seasonality_rank, earth: a.dust.seasonality_rank });
  }
  if (t.ice?.cold_rank != null || (a.sub_scores.ice != null && a.ice?.cold_rank != null))
    rows.push({ key: "cold_rank", label: "Cold-trap rank", unit: "", target: t.ice?.cold_rank, earth: a.ice?.cold_rank });
  return rows;
}

function MatchCell({ mm }: { mm: Mismatch | undefined }) {
  if (!mm)
    return (
      <span className="inline-flex items-center gap-1 text-earth">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
        match
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 text-bad">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /></svg>
      {mm.z_diff == null ? "differs" : <>mismatch <span className="num text-xs">(z {mm.z_diff > 0 ? "+" : ""}{mm.z_diff})</span></>}
    </span>
  );
}

const km = (v: number | null | undefined) => (v == null ? "n/a" : `${Math.round(v).toLocaleString("en-US")} km`);

export function Dossier({ ranked, analogIndex, onAnalog, limits }: Props) {
  const t = ranked.target;
  const { analog: a, score } = ranked.analogs[analogIndex];
  const body = BODY_LABEL[t.body].name;
  const mismatchByFeature = new Map(a.mismatches.map((m) => [m.feature, m]));
  const terrain = Object.keys(t.features).filter((k) => k in a.features && k !== "mean_elev_m");
  const process = processRows(t, a);
  const shown = new Set([...terrain, ...process.map((r) => r.key)]);
  const extra: Row[] = a.mismatches
    .filter((m) => !shown.has(m.feature) && !m.feature.startsWith("no_earth_data:"))
    .map((m) => ({ key: m.feature, label: FEATURE_LABEL[m.feature]?.label ?? m.feature, unit: FEATURE_LABEL[m.feature]?.unit ?? "", target: m.target, earth: m.earth }));
  const notes = [
    a.subsurface_note,
    a.polar_cold ? "Polar cold environment on Earth: useful for cold-trap and ice operations." : null,
    a.geology?.ice_surface ? "Ice-covered surface on Earth." : null,
  ].filter(Boolean) as string[];
  const breaks = a.mismatches.map((m) => {
    if (m.feature.startsWith("no_earth_data:")) {
      const dim = m.feature.split(":")[1] as Dimension;
      return `no Earth data for ${DIM_LABEL[dim]?.label.toLowerCase() ?? dim}`;
    }
    return m.feature === "geo_class"
      ? `rock class (${fmtValue(m.earth)} on Earth, ${fmtValue(m.target)} on ${body})`
      : (FEATURE_LABEL[m.feature]?.label ?? m.feature).toLowerCase();
  });

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
      <div className="grid min-w-0 content-start gap-4">
        <div className="grid gap-3 sm:grid-cols-[1fr_auto_1fr] sm:items-stretch">
          <div className="min-w-0 rounded-panel border border-accent bg-surface p-4">
            <div className="eyebrow">
              {body} · {t.type === "CURATED" ? (t.category ?? "mission site") : "terrain archetype"}
            </div>
            <div className="mt-1 font-display text-lg font-semibold">{t.name}</div>
            <div className="num mt-1 text-xs break-words text-muted">
              {fmtLat(t.lat)}, {fmtLon(t.lon)} · {t.id}
            </div>
            {t.why && <p className="mt-2 text-sm">{t.why}</p>}
            {t.geology?.geo_class && (
              <p className="mt-1 text-xs text-muted">
                Regional geology: {GEO_CLASS_LABEL[t.geology.geo_class] ?? t.geology.geo_class}
                {t.geology.unit ? ` (unit ${t.geology.unit})` : ""}
              </p>
            )}
            {t.source_url && (
              <a className="mt-2 inline-block text-xs underline hover:text-fg" href={t.source_url} target="_blank" rel="noreferrer">
                Source
              </a>
            )}
          </div>
          <span className="self-center justify-self-center num text-xs text-faint">versus</span>
          <div className="min-w-0 rounded-panel border border-earth bg-surface p-4">
            <div className="eyebrow">
              Earth · analog #{analogIndex + 1} ·{" "}
              {a.classification === "KNOWN_ANALOG" ? <span className="text-warn">known analog region</span> : <span className="text-earth">new candidate</span>}
            </div>
            <div className="mt-1 font-display text-lg font-semibold">
              {a.known_region ? `${a.known_region}${a.country ? `, ${a.country}` : ""}` : (a.country ?? "Copernicus DEM cell")}
            </div>
            <div className="num mt-1 text-xs break-words text-muted">
              {fmtLat(a.lat)}, {fmtLon(a.lon)}
            </div>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
              <dt className="text-muted">Nearest road</dt>
              <dd className="num">{km(a.logistics?.dist_road_km)}</dd>
              <dt className="text-muted">Nearest airport</dt>
              <dd className="num">
                {km(a.logistics?.dist_airport_km)}
                {a.logistics?.nearest_airport_iata ? ` · ${a.logistics.nearest_airport_iata}` : ""}
              </dd>
              {a.earth_env?.ndvi_max != null && (
                <>
                  <dt className="text-muted">Max NDVI</dt>
                  <dd className="num">{a.earth_env.ndvi_max.toFixed(2)}</dd>
                </>
              )}
              {a.earth_env?.lst_amplitude_c != null && (
                <>
                  <dt className="text-muted">Day-night ΔT</dt>
                  <dd className="num">{a.earth_env.lst_amplitude_c.toFixed(1)} °C</dd>
                </>
              )}
            </dl>
          </div>
        </div>

        <div className="flex flex-wrap gap-2" role="group" aria-label="Analogs for this target">
          {ranked.analogs.map((x, i) => (
            <button key={x.analog.id} type="button" className="chip num" aria-pressed={i === analogIndex} onClick={() => onAnalog(i)}>
              #{i + 1} · {pct(x.score)}
            </button>
          ))}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[32rem] border-collapse text-sm">
            <caption className="sr-only">Target features versus the Earth analog</caption>
            <thead>
              <tr className="border-b border-line text-left text-xs text-muted">
                <th className="px-2 py-2 font-semibold">Feature</th>
                <th className="px-2 py-2 text-right font-semibold">{body}</th>
                <th className="px-2 py-2 text-right font-semibold">Earth</th>
                <th className="px-2 py-2 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {terrain.map((k) => {
                const f = FEATURE_LABEL[k] ?? { label: k, unit: "" };
                return (
                  <tr key={k} className="border-b border-line">
                    <td className="px-2 py-2">{f.label}</td>
                    <td className="num px-2 py-2 text-right">{fmtNum(t.features[k])} {f.unit}</td>
                    <td className="num px-2 py-2 text-right">{fmtNum(a.features[k])} {f.unit}</td>
                    <td className="px-2 py-2"><MatchCell mm={mismatchByFeature.get(k)} /></td>
                  </tr>
                );
              })}
              {[...process, ...extra].map((r) => (
                <tr key={r.key} className="border-b border-line">
                  <td className="px-2 py-2">{r.label}</td>
                  <td className="num px-2 py-2 text-right">{fmtValue(r.target, r.unit)}</td>
                  <td className="num px-2 py-2 text-right">{fmtValue(r.earth, r.unit)}</td>
                  <td className="px-2 py-2">
                    {r.target == null || r.earth == null ? <span className="text-xs text-faint">no data</span> : <MatchCell mm={mismatchByFeature.get(r.key)} />}
                  </td>
                </tr>
              ))}
              {a.earth_missing_dims?.map((dim) => (
                <tr key={`missing-${dim}`} className="border-b border-line">
                  <td className="px-2 py-2 italic">{DIM_LABEL[dim]?.label ?? dim}</td>
                  <td className="num px-2 py-2 text-right">measured</td>
                  <td className="num px-2 py-2 text-right">no Earth measurement, scored 0</td>
                  <td className="px-2 py-2">
                    <MatchCell mm={{ feature: `no_earth_data:${dim}`, earth: "none", target: "measured", z_diff: null }} />
                  </td>
                </tr>
              ))}
              <tr className="border-b border-line text-faint">
                <td className="px-2 py-2">Mean elevation</td>
                <td className="num px-2 py-2 text-right">{fmtNum(t.features.mean_elev_m)} m</td>
                <td className="num px-2 py-2 text-right">{fmtNum(a.features.mean_elev_m)} m</td>
                <td className="px-2 py-2 text-xs">not comparable (datum)</td>
              </tr>
            </tbody>
          </table>
          <p className="mt-1 text-xs text-muted">Ranks are percentiles within each planet (0 = lowest, 1 = highest), so they compare how extreme a site is at home, not absolute values.</p>
        </div>

        <div className="rounded-panel bg-surface-2 p-4">
          <div className="eyebrow">Suggested field use</div>
          <ul className="mt-2 grid list-disc gap-1 pl-5 text-sm">
            {[...suggestedUses(t.features, t.body, t.lat), ...notes].map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-muted">Rule of thumb from slope and roughness, plus the site notes from the pipeline.</p>
        </div>
      </div>

      <div className="grid min-w-0 content-start gap-4">
        <div className="rounded-panel border border-line bg-surface p-4">
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="text-base font-semibold">Similarity profile</h3>
            <span className="eyebrow">
              MSI <span className="num text-fg">{pct(score)}</span>
            </span>
          </div>
          <Radar values={a.sub_scores} availableDims={t.available_dims} earthMissingDims={a.earth_missing_dims} />
        </div>

        <div className="rounded-panel border border-line bg-surface p-4">
          <h3 className="flex items-center gap-2 text-base font-semibold">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-bad" aria-hidden="true"><circle cx="12" cy="12" r="10" /><path d="m4.9 4.9 14.2 14.2" /></svg>
            Where the analogy breaks
          </h3>
          {breaks.length > 0 ? (
            <p className="mt-2 text-sm">At this site: {breaks.join("; ")}.</p>
          ) : (
            <p className="mt-2 text-sm text-muted">At this site no measured feature is beyond 1.5 σ; the physical limits below still apply.</p>
          )}
          <ul className="mt-3 grid gap-3">
            {limits.map((l) => (
              <li key={l.factor} className="grid gap-1 border-t border-dashed border-line pt-3 text-sm sm:grid-cols-[8rem_minmax(0,1fr)] sm:gap-3">
                <span>
                  <b className="font-semibold break-words">{limitLabel(l.factor)}</b>
                  <span className="num block text-xs text-muted">
                    {l.earth} / {l.target}
                  </span>
                </span>
                <span>
                  {l.consequence}{" "}
                  {l.source && (
                    <a className="text-xs text-muted underline hover:text-fg" href={l.source} target="_blank" rel="noreferrer">
                      source
                    </a>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

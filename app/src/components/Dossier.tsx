import type { Limit } from "../lib/types";
import type { RankedTarget } from "../lib/msi";
import { fmtLat, fmtLon, fmtNum, pct } from "../lib/msi";
import { BODY_LABEL, FEATURE_LABEL, LIMIT_LABEL, suggestedUses } from "../lib/content";
import { Radar } from "./Radar";

interface Props {
  ranked: RankedTarget;
  analogIndex: number;
  onAnalog: (i: number) => void;
  limits: Limit[];
}

export function Dossier({ ranked, analogIndex, onAnalog, limits }: Props) {
  const t = ranked.target;
  const { analog: a, score } = ranked.analogs[analogIndex];
  const body = BODY_LABEL[t.body].name;
  const mismatchByFeature = new Map(a.mismatches.map((m) => [m.feature, m]));
  const features = Object.keys(t.features).filter((k) => k in a.features && k !== "mean_elev_m");

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
      <div className="grid min-w-0 content-start gap-4">
        <div className="grid gap-3 sm:grid-cols-[1fr_auto_1fr] sm:items-stretch">
          <div className="min-w-0 rounded-panel border border-accent bg-surface p-4">
            <div className="eyebrow">{body} · target</div>
            <div className="mt-1 font-display text-lg font-semibold">{t.name}</div>
            <div className="num mt-1 text-xs break-words text-muted">
              {fmtLat(t.lat)}, {fmtLon(t.lon)} · {t.id}
            </div>
          </div>
          <span className="self-center justify-self-center num text-xs text-faint">versus</span>
          <div className="min-w-0 rounded-panel border border-earth bg-surface p-4">
            <div className="eyebrow">Earth · analog #{analogIndex + 1}</div>
            <div className="mt-1 font-display text-lg font-semibold">{a.known_region ?? a.country ?? "Copernicus DEM cell"}</div>
            <div className="num mt-1 text-xs break-words text-muted">
              {fmtLat(a.lat)}, {fmtLon(a.lon)}
              {a.v1_similarity != null && <> · v1 similarity {a.v1_similarity.toFixed(1)}</>}
            </div>
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
              {features.map((k) => {
                const f = FEATURE_LABEL[k] ?? { label: k, unit: "" };
                const mm = mismatchByFeature.get(k);
                return (
                  <tr key={k} className="border-b border-line">
                    <td className="px-2 py-2">{f.label}</td>
                    <td className="num px-2 py-2 text-right">{fmtNum(t.features[k])} {f.unit}</td>
                    <td className="num px-2 py-2 text-right">{fmtNum(a.features[k])} {f.unit}</td>
                    <td className="px-2 py-2">
                      {mm ? (
                        <span className="inline-flex items-center gap-1 text-bad">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /></svg>
                          mismatch <span className="num text-xs">(z {mm.z_diff > 0 ? "+" : ""}{mm.z_diff})</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-earth">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
                          match
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
              <tr className="border-b border-line text-faint">
                <td className="px-2 py-2">Mean elevation</td>
                <td className="num px-2 py-2 text-right">{fmtNum(t.features.mean_elev_m)} m</td>
                <td className="num px-2 py-2 text-right">{fmtNum(a.features.mean_elev_m)} m</td>
                <td className="px-2 py-2 text-xs">not comparable (datum)</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="rounded-panel bg-surface-2 p-4">
          <div className="eyebrow">Suggested field use</div>
          <ul className="mt-2 grid list-disc gap-1 pl-5 text-sm">
            {suggestedUses(t.features, t.body, t.lat).map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-muted">Provisional rule based on slope and TRI. Per-preset test protocols arrive with T11.</p>
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
          <Radar values={a.sub_scores} />
        </div>

        <div className="rounded-panel border border-line bg-surface p-4">
          <h3 className="flex items-center gap-2 text-base font-semibold">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-bad" aria-hidden="true"><circle cx="12" cy="12" r="10" /><path d="m4.9 4.9 14.2 14.2" /></svg>
            Where the analogy breaks
          </h3>
          {a.mismatches.length > 0 && (
            <p className="mt-2 text-sm">
              At this site: {a.mismatches.map((m) => FEATURE_LABEL[m.feature]?.label ?? m.feature).join(", ")} beyond 1.5 σ.
            </p>
          )}
          <ul className="mt-3 grid gap-3">
            {limits.map((l) => (
              <li key={l.factor} className="grid gap-1 border-t border-dashed border-line pt-3 text-sm sm:grid-cols-[8rem_minmax(0,1fr)] sm:gap-3">
                <span>
                  <b className="font-semibold">{LIMIT_LABEL[l.factor] ?? l.factor}</b>
                  <span className="num block text-xs text-muted">
                    {l.earth} / {l.target}
                  </span>
                </span>
                <span>{l.consequence}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-muted">
            Provisional text, pending science review (T11).{" "}
            <a className="underline hover:text-fg" href={limits[0]?.source} target="_blank" rel="noreferrer">
              NASA fact sheet
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
